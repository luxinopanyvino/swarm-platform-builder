"""
Graph-based web scraper for the Investigador agent.

Architecture
------------
1. **Seed URLs** — arXiv + Wikipedia give starting nodes from the search query.
2. **NetworkX DiGraph** — each fetched URL becomes a node; outbound links become
   directed edges.  Relevance score (keyword overlap) is stored as node attribute.
3. **BFS expansion** — from seed nodes the scraper traverses up to ``max_depth``
   levels, pruning branches whose relevance score falls below ``min_relevance``.
4. **Fetch strategy** — tries ``requests`` first (fast, ~1 s per page).
   If the response is empty / JS-gated (detected by low text-to-HTML ratio),
   falls back to **Playwright headless Chromium** which can render SPAs.
5. **Result** — returns a list of ``ScrapedPage`` dataclasses ordered by
   relevance score, ready to be consumed by ``run_investigador``.

Security notes
--------------
- All URLs are validated (must start with http/https).
- Robots.txt is respected via ``_is_allowed_by_robots``.
- A 2-second per-domain rate-limit prevents hammering.
- Max payload per page is capped at 50 KB to avoid memory abuse.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from collections import deque

import math

import httpx
import networkx as nx

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

_UA = "Mozilla/5.0 (compatible; AlexandrIA/1.0; +research)"
_HEADERS = {"User-Agent": _UA, "Accept-Language": "es,en;q=0.9"}
_MAX_PAGE_BYTES = 50_000          # 50 KB cap on raw HTML per page
_MIN_TEXT_RATIO = 0.08            # below this → probably JS-heavy → try Playwright
_RATE_LIMIT_SECS = 2.0            # min seconds between requests to the same domain
_PLAYWRIGHT_TIMEOUT = 18_000      # ms — page.goto timeout
_REQUEST_TIMEOUT = 12.0           # seconds — httpx timeout

# Tags whose text content is always discarded (nav, ads, etc.)
_NOISE_TAGS = {
    "script", "style", "noscript", "nav", "footer", "header",
    "aside", "form", "button", "input", "select", "iframe",
}

# Only follow links that look like real content (not login / CDN / image)
_SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf",
    ".zip", ".tar", ".gz", ".mp4", ".mp3", ".exe", ".dmg",
}

_SKIP_PATTERNS = re.compile(
    r"(login|logout|signin|signup|register|cart|checkout|cookie|privacy|terms"
    r"|adverti|sponsor|cdn\.|static\.)",
    re.IGNORECASE,
)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class ScrapedPage:
    """Holds the extracted content of a single web page."""
    url: str
    title: str
    text: str                       # cleaned plain text
    links: List[str] = field(default_factory=list)
    relevance: float = 0.0
    fetched_with: str = "requests"  # "requests" | "playwright"

    def snippet(self, chars: int = 400) -> str:
        return self.text[:chars].replace("\n", " ")


# ── Domain-level rate limiter ─────────────────────────────────────────────────

_domain_last_fetch: Dict[str, float] = {}


def _domain_of(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower()


async def _rate_limit(url: str) -> None:
    domain = _domain_of(url)
    last = _domain_last_fetch.get(domain, 0.0)
    wait = _RATE_LIMIT_SECS - (time.monotonic() - last)
    if wait > 0:
        await asyncio.sleep(wait)
    _domain_last_fetch[domain] = time.monotonic()


# ── URL helpers ───────────────────────────────────────────────────────────────

def _normalise(url: str, base: str) -> Optional[str]:
    """Resolve relative URL against base; return None for non-http or skipped."""
    try:
        full = urllib.parse.urljoin(base, url.strip())
        parsed = urllib.parse.urlparse(full)
        if parsed.scheme not in ("http", "https"):
            return None
        # Drop fragment
        clean = parsed._replace(fragment="").geturl()
        # Skip by extension
        path = parsed.path.lower()
        if any(path.endswith(ext) for ext in _SKIP_EXTENSIONS):
            return None
        # Skip noisy patterns
        if _SKIP_PATTERNS.search(clean):
            return None
        return clean
    except Exception:
        return None


def _is_valid_url(url: str) -> bool:
    try:
        p = urllib.parse.urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


# ── Robots.txt cache ──────────────────────────────────────────────────────────

_robots_cache: Dict[str, bool] = {}   # domain → allowed (very simple: True if no disallow for *)


async def _is_allowed_by_robots(url: str) -> bool:
    """Quick robots.txt check — only blocks if explicitly disallowed for *."""
    domain = _domain_of(url)
    if domain in _robots_cache:
        return _robots_cache[domain]
    robots_url = f"https://{domain}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=5.0, verify=False) as c:
            r = await c.get(robots_url, headers=_HEADERS)
            if r.status_code == 200:
                # Very simple: look for "User-agent: *" + "Disallow: /"
                text = r.text.lower()
                in_star = False
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith("user-agent:"):
                        in_star = "*" in line
                    elif in_star and line.startswith("disallow: /") and line == "disallow: /":
                        _robots_cache[domain] = False
                        return False
    except Exception:
        pass
    _robots_cache[domain] = True
    return True


# ── HTML → plain text ─────────────────────────────────────────────────────────

def _html_to_text(html: str) -> Tuple[str, str, List[str], float]:
    """
    Parse HTML with BeautifulSoup.

    Returns (title, text, links, text_ratio).
    text_ratio < _MIN_TEXT_RATIO hints at a JS-heavy page.
    """
    try:
        from bs4 import BeautifulSoup  # lazy import — not needed at module load
    except ImportError:
        # Fallback: regex strip
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()
        ratio = len(clean) / max(len(html), 1)
        return "", clean[:_MAX_PAGE_BYTES], [], ratio

    soup = BeautifulSoup(html[:_MAX_PAGE_BYTES * 3], "lxml")

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""

    # Remove noise tags in-place
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    # Prefer main content areas
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|main|article|body", re.I))
        or soup.find(class_=re.compile(r"content|main|article|post|entry", re.I))
        or soup.body
        or soup
    )

    text = main.get_text(" ", strip=True) if main else ""
    text = re.sub(r" {2,}", " ", text).strip()
    text_ratio = len(text) / max(len(html), 1)

    # Extract links
    links: List[str] = []
    for a in (soup.find_all("a", href=True) if soup.body else []):
        href = a["href"].strip()
        if href and not href.startswith(("#", "javascript:", "mailto:")):
            links.append(href)

    return title, text[:_MAX_PAGE_BYTES], links, text_ratio


# ── Page fetchers ─────────────────────────────────────────────────────────────

async def _fetch_with_requests(url: str) -> Tuple[str, int]:
    """Fetch raw HTML via httpx (async). Returns (html, status_code)."""
    try:
        async with httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
            verify=False,
            headers=_HEADERS,
        ) as client:
            r = await client.get(url)
            ct = r.headers.get("content-type", "")
            if "text/" not in ct and "html" not in ct:
                return "", r.status_code
            return r.text, r.status_code
    except Exception as exc:
        logger.debug("requests fetch failed for %s: %s", url, exc)
        return "", 0


async def _fetch_with_playwright(url: str) -> str:
    """Render the page with headless Chromium and return inner HTML."""
    try:
        from playwright.async_api import async_playwright  # lazy import
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = await browser.new_context(
                user_agent=_UA,
                java_script_enabled=True,
                ignore_https_errors=True,
            )
            page = await ctx.new_page()
            await page.goto(url, timeout=_PLAYWRIGHT_TIMEOUT, wait_until="domcontentloaded")
            # Small wait for any lazy-loaded content
            await asyncio.sleep(1.5)
            html = await page.content()
            await browser.close()
            return html
    except Exception as exc:
        logger.warning("Playwright fetch failed for %s: %s", url, exc)
        return ""


async def _fetch_page(url: str, use_playwright_fallback: bool = True) -> Optional[ScrapedPage]:
    """
    Fetch a URL, parse it, and return a ``ScrapedPage``.

    Strategy:
    1. Try requests.
    2. If text_ratio < _MIN_TEXT_RATIO and playwright_fallback=True → retry with
       headless Chromium.
    """
    if not _is_valid_url(url):
        return None
    if not await _is_allowed_by_robots(url):
        logger.debug("robots.txt disallows %s", url)
        return None

    await _rate_limit(url)

    html, status = await _fetch_with_requests(url)
    fetched_with = "requests"

    if status not in (200, 203, 206) or not html:
        return None

    title, text, links, ratio = _html_to_text(html)

    # JS-heavy page — retry with Playwright
    if ratio < _MIN_TEXT_RATIO and use_playwright_fallback and len(text) < 200:
        logger.debug("Low text ratio %.3f for %s — trying Playwright", ratio, url)
        pw_html = await _fetch_with_playwright(url)
        if pw_html:
            title, text, links, _ = _html_to_text(pw_html)
            fetched_with = "playwright"

    if not text.strip():
        return None

    return ScrapedPage(
        url=url,
        title=title,
        text=text,
        links=links,
        fetched_with=fetched_with,
    )


# ── Relevance scoring ─────────────────────────────────────────────────────────

def _score_relevance(page: ScrapedPage, keywords: List[str]) -> float:
    """
    TF-like score used during BFS pruning: fraction of query keywords present
    in title (3×) + text. Fast, zero network calls.
    """
    if not keywords:
        return 1.0
    combined = (page.title + " " + page.text[:2000]).lower()
    title_low = page.title.lower()
    score = 0.0
    for kw in keywords:
        kw_low = kw.lower()
        if kw_low in title_low:
            score += 3
        elif kw_low in combined:
            score += 1
    return score / (len(keywords) * 3)


def _cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _semantic_rerank(
    pages: List[ScrapedPage],
    query: str,
    ollama_base_url: str,
    embed_model: str,
    log_fn=None,
) -> List[ScrapedPage]:
    """
    Re-rank *pages* by cosine similarity between the query embedding and each
    page's title+snippet embedding (via ``nomic-embed-text`` / Ollama).

    Falls back gracefully to the existing TF relevance score if Ollama is
    unavailable or returns empty vectors.
    """
    def _log(msg: str, level: str = "info") -> None:
        if log_fn:
            log_fn(msg, level)

    try:
        from app.modules.agents.adapters.rag import get_embedding  # lazy import
    except ImportError:
        _log("⚠️ rag.get_embedding no disponible — se mantiene orden TF.", "warning")
        return pages

    _log(f"🧮 Re-ranking semántico de {len(pages)} página(s) con {embed_model}...")

    # Embed query once
    query_vec = await get_embedding(query, ollama_base_url, embed_model)
    if not query_vec:
        _log("⚠️ No se obtuvo embedding del query — se mantiene orden TF.", "warning")
        return pages

    # Embed each page concurrently (title + first 400 chars of text)
    async def _page_embed(page: ScrapedPage) -> Optional[List[float]]:
        snippet = f"{page.title}. {page.text[:400]}"
        return await get_embedding(snippet, ollama_base_url, embed_model)

    vectors = await asyncio.gather(*(_page_embed(p) for p in pages), return_exceptions=True)

    reranked = 0
    for page, vec in zip(pages, vectors):
        if isinstance(vec, list) and vec:
            page.relevance = _cosine(query_vec, vec)
            reranked += 1
        # else: keep existing TF score

    _log(f"  ↳ {reranked}/{len(pages)} páginas con score semántico (coseno).")
    return sorted(pages, key=lambda p: p.relevance, reverse=True)


# ── Seed URL generators ───────────────────────────────────────────────────────

async def _arxiv_seeds(query: str, max_results: int = 5) -> List[str]:
    """Return arXiv abstract page URLs for the query."""
    try:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
        }
        async with httpx.AsyncClient(timeout=10.0, verify=False) as c:
            r = await c.get("https://export.arxiv.org/api/query", params=params)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        urls = []
        for entry in root.findall("atom:entry", ns):
            link = entry.find("atom:id", ns)
            if link is not None and link.text:
                # Convert API URL to HTML abstract page
                abstract_url = link.text.replace("http://arxiv.org/abs/", "https://arxiv.org/abs/")
                urls.append(abstract_url.strip())
        return urls
    except Exception as exc:
        logger.warning("arXiv seed failed: %s", exc)
        return []


async def _wikipedia_seeds(query: str, max_results: int = 3) -> List[str]:
    """Return Wikipedia article URLs for the query."""
    try:
        params = {
            "action": "opensearch",
            "search": query,
            "limit": max_results,
            "namespace": 0,
            "format": "json",
        }
        async with httpx.AsyncClient(timeout=8.0, verify=False) as c:
            r = await c.get("https://en.wikipedia.org/w/api.php", params=params)
        data = r.json()
        return data[3] if len(data) > 3 else []
    except Exception as exc:
        logger.warning("Wikipedia seed failed: %s", exc)
        return []


async def _semantic_scholar_seeds(query: str, max_results: int = 4) -> List[str]:
    """Return Semantic Scholar paper URLs."""
    try:
        params = {"query": query, "limit": max_results, "fields": "externalIds,title"}
        async with httpx.AsyncClient(timeout=10.0, verify=False) as c:
            r = await c.get("https://api.semanticscholar.org/graph/v1/paper/search", params=params)
        if r.status_code != 200:
            return []
        papers = r.json().get("data", [])
        urls = []
        for p in papers:
            ext = p.get("externalIds", {})
            doi = ext.get("DOI")
            arxiv_id = ext.get("ArXiv")
            if arxiv_id:
                urls.append(f"https://arxiv.org/abs/{arxiv_id}")
            elif doi:
                urls.append(f"https://doi.org/{doi}")
        return urls
    except Exception as exc:
        logger.warning("Semantic Scholar seed failed: %s", exc)
        return []


# ── Main scraper ──────────────────────────────────────────────────────────────

async def graph_scrape(
    query: str,
    keywords: List[str],
    *,
    max_pages: int = 12,
    max_depth: int = 2,
    min_relevance: float = 0.05,
    use_playwright: bool = True,
    ollama_base_url: str = "http://localhost:11434",
    embed_model: str = "nomic-embed-text",
    semantic_rerank: bool = True,
    log_fn=None,
) -> List[ScrapedPage]:
    """
    Perform a graph-based BFS web scrape starting from arXiv + Wikipedia seeds,
    then re-rank results by cosine similarity with query embedding.

    Parameters
    ----------
    query : str
        Full-text search query.
    keywords : list[str]
        Individual keywords used for relevance scoring and graph pruning.
    max_pages : int
        Hard cap on total pages fetched (resource efficiency).
    max_depth : int
        BFS depth limit from seed nodes.
    min_relevance : float
        Nodes below this score are not expanded (links not followed).
    use_playwright : bool
        Whether to fall back to headless Chromium for JS-heavy pages.
    ollama_base_url : str
        Base URL for Ollama API (used for semantic re-ranking).
    embed_model : str
        Ollama embedding model name (e.g. "nomic-embed-text").
    semantic_rerank : bool
        If True, re-rank final results by cosine similarity (embedding-based).
        BFS pruning always uses fast TF scoring regardless of this flag.
    log_fn : callable | None
        Optional logger function ``log_fn(msg, level="info")``.

    Returns
    -------
    list[ScrapedPage]
        Pages sorted by relevance score, descending.
    """
    def _log(msg: str, level: str = "info") -> None:
        if log_fn:
            log_fn(msg, level)
        logger.info("scraper: %s", msg)

    # ── 1. Gather seed URLs ──────────────────────────────────────────────────
    _log("🌱 Recopilando seeds (arXiv + Wikipedia + Semantic Scholar)...")
    seeds_arxiv, seeds_wiki, seeds_ss = await asyncio.gather(
        _arxiv_seeds(query, max_results=5),
        _wikipedia_seeds(query, max_results=3),
        _semantic_scholar_seeds(query, max_results=4),
        return_exceptions=True,
    )
    seed_urls: List[str] = []
    for result in (seeds_arxiv, seeds_wiki, seeds_ss):
        if isinstance(result, list):
            seed_urls.extend(result)

    # Deduplicate while preserving order
    seen_urls: set = set()
    unique_seeds: List[str] = []
    for u in seed_urls:
        if u not in seen_urls:
            seen_urls.add(u)
            unique_seeds.append(u)

    if not unique_seeds:
        _log("⚠️ No se obtuvieron seeds. Scraping no puede continuar.", "warning")
        return []

    _log(f"  → {len(unique_seeds)} seeds: {unique_seeds[0][:70]}{'...' if len(unique_seeds)>1 else ''}")

    # ── 2. Build graph and BFS ───────────────────────────────────────────────
    G: nx.DiGraph = nx.DiGraph()
    pages: Dict[str, ScrapedPage] = {}
    queue: deque = deque()   # (url, depth)
    fetched_count = 0

    for u in unique_seeds:
        G.add_node(u, depth=0, relevance=0.0, fetched=False)
        queue.append((u, 0))

    while queue and fetched_count < max_pages:
        url, depth = queue.popleft()

        if G.nodes[url].get("fetched", False):
            continue

        G.nodes[url]["fetched"] = True
        _log(f"  🔗 [{fetched_count+1}/{max_pages}] depth={depth} {url[:80]}")

        page = await _fetch_page(url, use_playwright_fallback=use_playwright)
        if page is None:
            G.nodes[url]["relevance"] = 0.0
            continue

        relevance = _score_relevance(page, keywords)
        page.relevance = relevance
        G.nodes[url]["relevance"] = relevance
        pages[url] = page
        fetched_count += 1

        _log(f"    ↳ relevance={relevance:.2f} via={page.fetched_with} text={len(page.text)}ch")

        # Don't expand low-relevance or deep nodes
        if relevance < min_relevance or depth >= max_depth:
            continue

        # Enqueue outbound links that look relevant
        for raw_link in page.links[:30]:   # cap link extraction per page
            norm = _normalise(raw_link, url)
            if not norm or norm in seen_urls:
                continue
            # Pre-filter by keyword presence in URL (cheap heuristic)
            url_low = norm.lower()
            kw_in_url = any(k.lower() in url_low for k in keywords)
            if not kw_in_url and depth >= 1:
                continue   # only follow keyword-URLs beyond depth 0
            seen_urls.add(norm)
            G.add_node(norm, depth=depth + 1, relevance=0.0, fetched=False)
            G.add_edge(url, norm)
            queue.append((norm, depth + 1))

    # ── 3. Semantic re-rank then return ─────────────────────────────────────
    results = list(pages.values())

    if semantic_rerank and results:
        results = await _semantic_rerank(
            results, query, ollama_base_url, embed_model, log_fn=_log
        )
    else:
        results = sorted(results, key=lambda p: p.relevance, reverse=True)

    _log(
        f"✅ Scraping completado: {len(results)} páginas, "
        f"grafo={G.number_of_nodes()} nodos / {G.number_of_edges()} aristas"
    )
    return results
