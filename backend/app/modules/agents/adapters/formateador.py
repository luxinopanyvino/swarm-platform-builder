import logging
import re
from typing import Dict, Any

from app.core.config import settings
from app.shared.llm import call_llm, get_default_model

logger = logging.getLogger(__name__)

_FORMAT_LABELS = {
    "apa": "APA 7th edition",
    "ieee": "IEEE",
    "vancouver": "Vancouver",
    "chicago": "Chicago 17th edition",
    "nature": "Nature / NLM numbered",
}

_FORMAT_INSTRUCTIONS = {
    "apa": "Use APA 7th edition style for in-text citations: (Author, Year). Do NOT generate the References list.",
    "ieee": "Use IEEE style for in-text citations: bracketed sequential numbers [1], [2]. Do NOT generate the References list.",
    "vancouver": "Use Vancouver style for in-text citations: sequential numbers. Do NOT generate the References list.",
    "chicago": "Use Chicago 17th edition style for in-text citations: (Author Year). Do NOT generate the References list.",
    "nature": "Use Nature numbered style for in-text citations: superscript sequential numbers. Do NOT generate the References list.",
}


def format_source_deterministic(s: dict, style: str, index: int) -> str:
    """Format a single source dictionary into a bibliography citation string deterministically."""
    title = s.get("title", "").strip() or "Untitled Document"
    authors = s.get("authors", "").strip() or "N/A"
    journal = s.get("journal", "").strip() or "Scientific Report"
    year = str(s.get("year", "")).strip() or "N/A"
    url = s.get("url", "").strip()
    doi = s.get("doi", "").strip()

    ref_link = f" https://doi.org/{doi}" if doi else (f" {url}" if url else "")

    if style == "apa":
        # Authors (Year). Title. Journal. URL/DOI
        return f"{authors} ({year}). *{title}*. {journal}.{ref_link}"
    elif style == "ieee":
        # [index] Authors, "Title," Journal, Year. URL/DOI
        return f"[{index}] {authors}, \"{title},\" *{journal}*, {year}.{ref_link}"
    elif style == "vancouver":
        # index. Authors. Title. Journal. Year. URL/DOI
        return f"{index}. {authors}. {title}. {journal}. {year}.{ref_link}"
    elif style == "chicago":
        # Authors. Year. "Title." Journal. URL/DOI
        return f"{authors}. {year}. \"{title}.\" *{journal}*.{ref_link}"
    elif style == "nature":
        # index. Authors. Title. Journal Vol, pages (Year). URL/DOI
        return f"{index}. {authors}. {title}. *{journal}* ({year}).{ref_link}"
    else:
        return f"[{index}] {authors}. {title}. {year}. {url}"


def clean_references_section(text: str) -> str:
    """Strip any markdown References or Bibliography section from the end of the text."""
    pattern = r"(?i)\n#+\s*(referencias|references|bibliografía|bibliography)\s*\n.*$"
    cleaned = re.sub(pattern, "", text, flags=re.DOTALL)
    return cleaned.strip()


async def run_formateador(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formateador Agent.
    Applies a specific scientific citation format (APA, IEEE, Vancouver, Chicago, Nature)
    to the draft. Uses native Python code to construct the References/Bibliography
    deterministically from the state's 'sources' list, preventing LLM inventions.
    """
    draft_text = state.get("draft_text") or ""
    if not draft_text:
        return {"formatted_text": ""}

    # Resolve format: agent_settings → state → default
    agent_cfg = (state.get("agent_settings") or {}).get("formateador", {})
    scientific_format = (
        agent_cfg.get("scientific_format")
        or state.get("scientific_format")
        or "apa"
    ).lower()

    # Resolve model: per-agent override → settings default
    model = agent_cfg.get("model") or get_default_model()

    format_label = _FORMAT_LABELS.get(scientific_format, scientific_format.upper())
    instruction = _FORMAT_INSTRUCTIONS.get(
        scientific_format,
        "Format in-text citations in APA 7th edition style.",
    )
    log = state.get("_log") or (lambda msg, level="info": None)

    logger.info(f"Running Formateador — format: {scientific_format}, model: {model}")
    log(f"📄 Aplicando formato bibliográfico determinista ({format_label})...")

    # 1. Clean the body draft from any existing bibliography
    cleaned_draft = clean_references_section(draft_text)

    # 2. Format in-text citations in the body text using LLM
    prompt = (
        f"You are a scientific manuscript formatter. Rewrite the manuscript below applying "
        f"{format_label} in-text citation style.\n\n"
        f"MANDATORY RULES:\n"
        f"1. Copy the ENTIRE manuscript text verbatim, preserving every paragraph, section, and sentence.\n"
        f"2. Only modify in-text citations to match {format_label}.\n"
        f"3. Do NOT output a 'References', 'Referencias', 'Bibliography' or 'Bibliografía' section at the end. Completely omit the references list.\n"
        f"4. Do NOT write explanations, steps, guides, or commentary of any kind.\n"
        f"5. Do NOT start with 'I can', 'I will', 'Here is', 'Sure', or any similar phrase.\n"
        f"6. Begin your output directly with the first line of the manuscript.\n\n"
        f"In-text citation rules:\n{instruction}\n\n"
        f"--- MANUSCRIPT START ---\n"
        f"{cleaned_draft}\n"
        f"--- MANUSCRIPT END ---\n\n"
        f"Output the reformatted manuscript now (no bibliography list):"
    )

    _REFUSAL_PATTERNS = (
        "i can't provide",
        "i cannot provide",
        "i'm unable",
        "i am unable",
        "here's how to",
        "here is how to",
        "follow these steps",
        "to format the manuscript",
        "you can follow",
        "you should follow",
    )

    formatted_body = cleaned_draft
    try:
        result = await call_llm(prompt, model=model, timeout=300.0, num_ctx=4096, keep_alive=0)
        result_lower = result.lower() if result else ""
        refused = any(pat in result_lower for pat in _REFUSAL_PATTERNS) if result else True
        if not refused and result and len(result) >= len(cleaned_draft) * 0.5:
            formatted_body = result.strip()
        else:
            logger.warning("Formateador: LLM failed or refused; falling back to original text body.")
    except Exception as exc:
        logger.warning("Formateador LLM call failed: %s; falling back to original body.", exc)

    # 3. Assemble references section deterministically using Python code
    sources = state.get("sources") or []

    formatted_refs = []
    seen_urls = set()
    unique_sources = []
    for s in sources:
        url = s.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_sources.append(s)
        elif not url:
            unique_sources.append(s)

    for idx, source in enumerate(unique_sources, start=1):
        ref_str = format_source_deterministic(source, scientific_format, idx)
        formatted_refs.append(ref_str)

    if formatted_refs:
        ref_title = "Referencias" if scientific_format in ("apa", "vancouver") else "References"
        bibliography_block = f"\n\n## {ref_title}\n" + "\n".join(formatted_refs)
        final_text = formatted_body + bibliography_block
        log(f"✅ Formato bibliográfico determinista aplicado: {len(formatted_refs)} fuentes indexadas.")
    else:
        final_text = formatted_body
        log("ℹ️ No se encontraron fuentes en el estado del artículo para generar la bibliografía.")

    return {"formatted_text": final_text, "scientific_format": scientific_format}
