"""SPEC-032 AC3 y AC4 / T20.3 — existencia y coincidencia de referencias (PR-REG-12).

El resolutor se prueba con un `fetch` simulado: ningún test sale a la red.
"""
import asyncio

import pytest

from app.platform.publication_gate import CriterionStatus
from app.platform.publication_gate.reference_resolver import (
    CROSSREF,
    OPENALEX,
    PositiveCache,
    ResolverConfig,
    check_reference_existence,
    journals_match,
    normalize_doi,
    title_similarity,
)


class Resp:
    def __init__(self, status=200, data=None, bad_json=False):
        self.status_code, self._data, self._bad = status, data, bad_json

    def json(self):
        if self._bad:
            raise ValueError("no json")
        return self._data


def cr(doi, title, authors, year, journal, type_="journal-article"):
    return {
        "DOI": doi, "title": [title], "type": type_,
        "author": [{"family": a} for a in authors],
        "issued": {"date-parts": [[year]]}, "container-title": [journal],
    }


NATURE = cr("10.1038/nature14539", "Deep learning", ["LeCun", "Bengio", "Hinton"], 2015, "Nature")


class Fake:
    """Enruta por prefijo de URL; registra las llamadas."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    async def __call__(self, url, *, params=None, headers=None, timeout=10.0):
        self.calls.append((url, params))
        for prefix, handler in self.routes:
            if url.startswith(prefix):
                r = handler(url, params) if callable(handler) else handler
                if isinstance(r, Exception):
                    raise r
                return r
        raise AssertionError(f"URL inesperada: {url}")


async def _nosleep(_):
    pass


def run(sources, fake, cfg=ResolverConfig(), **kw):
    return asyncio.run(
        check_reference_existence(sources, cfg, fetch=fake, sleep=_nosleep, **kw)
    )


FUENTE = {
    "title": "Deep learning", "authors": "LeCun, Y., Bengio, Y., Hinton, G.",
    "year": "2015", "journal": "Nature", "doi": "10.1038/nature14539",
}


def crossref_ok(item=NATURE):
    return [(CROSSREF + "/", Resp(200, {"message": item}))]


# ── AC3: existencia y coincidencia ──────────────────────────────────────────


def test_referencia_valida_pasa():
    res, _ = run([FUENTE], Fake(crossref_ok()))
    assert res.status is CriterionStatus.PASSED and not res.blocking


def test_doi_inventado_es_failed_y_bloquea():
    fake = Fake([(CROSSREF + "/", Resp(404)), (OPENALEX + "/", Resp(404))])
    res, _ = run([{**FUENTE, "doi": "10.9999/inventado"}], fake)
    assert res.status is CriterionStatus.FAILED and res.blocking
    assert "no existe" in res.evidence[0]["reason"]


def test_si_crossref_no_lo_tiene_se_prueba_openalex():
    oa = {"doi": "https://doi.org/10.1038/nature14539", "title": "Deep learning",
          "publication_year": 2015, "type": "article",
          "authorships": [{"author": {"display_name": n}} for n in
                          ("Yann LeCun", "Yoshua Bengio", "Geoffrey Hinton")],
          "primary_location": {"source": {"display_name": "Nature"}}}
    fake = Fake([(CROSSREF + "/", Resp(404)), (OPENALEX + "/", Resp(200, oa))])
    res, _ = run([FUENTE], fake)
    assert res.status is CriterionStatus.PASSED


@pytest.mark.parametrize(
    "campo,valor,texto",
    [
        ("title", "Un título totalmente distinto", "título"),
        ("authors", "Smith, J., Jones, K.", "autores"),
        ("year", "2010", "año"),
        ("journal", "Science", "revista"),
    ],
)
def test_una_discrepancia_es_bloqueante(campo, valor, texto):
    res, _ = run([{**FUENTE, campo: valor}], Fake(crossref_ok()))
    assert res.status is CriterionStatus.FAILED
    assert texto in res.evidence[0]["reason"]


def test_primer_autor_distinto_falla():
    res, _ = run([{**FUENTE, "authors": "Hinton, G., Bengio, Y., LeCun, Y."}], Fake(crossref_ok()))
    assert res.status is CriterionStatus.FAILED


def test_et_al_solo_exige_el_primer_autor():
    res, _ = run([{**FUENTE, "authors": "LeCun et al."}], Fake(crossref_ok()))
    assert res.status is CriterionStatus.PASSED


def test_ano_con_diferencia_de_uno_solo_vale_en_preprint():
    pre = cr("10.48550/arXiv.1706.03762", "Attention Is All You Need", ["Vaswani", "Shazeer"],
             2017, "arXiv", "posted-content")
    src = {"title": "Attention Is All You Need", "authors": "Vaswani, A., Shazeer, N.",
           "year": "2018", "journal": "arXiv", "doi": "10.48550/arXiv.1706.03762"}
    assert run([src], Fake(crossref_ok(pre)))[0].status is CriterionStatus.PASSED
    # …pero no en un artículo publicado.
    assert run([{**FUENTE, "year": "2016"}], Fake(crossref_ok()))[0].status is CriterionStatus.FAILED


def test_sin_doi_se_resuelve_por_titulo_y_autores_y_se_enriquece():
    src = {"title": "Deep learning", "authors": "LeCun, Bengio, Hinton", "year": "", "journal": "", "doi": ""}
    fake = Fake([(CROSSREF, Resp(200, {"message": {"items": [NATURE]}}))])
    res, enriched = run([src], fake)
    assert res.status is CriterionStatus.PASSED
    assert enriched[0]["doi"] == "10.1038/nature14539"
    assert enriched[0]["year"] == "2015" and enriched[0]["journal"] == "Nature"


def test_sin_doi_y_sin_titulo_o_autores_no_se_verifica():
    res, _ = run([{"title": "informe-final", "authors": "", "doi": ""}], Fake([]))
    assert res.status is CriterionStatus.NOT_VERIFIED and res.blocking


def test_sin_candidatos_fiables_no_se_verifica():
    src = {"title": "Deep learning", "authors": "LeCun", "doi": ""}
    fake = Fake([(CROSSREF, Resp(200, {"message": {"items": []}})),
                 (OPENALEX, Resp(200, {"results": []}))])
    res, _ = run([src], fake)
    assert res.status is CriterionStatus.NOT_VERIFIED


def test_varios_candidatos_igualmente_plausibles_no_se_verifica():
    otro = cr("10.1000/otro", "Deep learning", ["LeCun", "Bengio", "Hinton"], 2015, "Nature")
    src = {"title": "Deep learning", "authors": "LeCun, Bengio, Hinton", "doi": ""}
    fake = Fake([(CROSSREF, Resp(200, {"message": {"items": [NATURE, otro]}}))])
    res, _ = run([src], fake)
    assert res.status is CriterionStatus.NOT_VERIFIED
    assert "varios candidatos" in res.evidence[0]["reason"]


def test_doi_aportado_a_mano_se_verifica_igual():
    # Mismo camino: un DOI manual que no existe falla como cualquier otro.
    fake = Fake([(CROSSREF + "/", Resp(404)), (OPENALEX + "/", Resp(404))])
    res, _ = run([{"title": "x", "authors": "y", "doi": "https://doi.org/10.1/aportado"}], fake)
    assert res.status is CriterionStatus.FAILED
    assert "10.1/aportado" in fake.calls[0][0]


def test_la_sintesis_del_llm_no_se_consulta():
    fake = Fake([])
    res, _ = run([{"url": "synthesis://llm", "title": "x"}], fake)
    assert res.status is CriterionStatus.PASSED and fake.calls == []


# ── AC4: falla cerrada ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "fallo",
    [TimeoutError("agotado"), ConnectionError("caído"), Resp(500), Resp(429),
     Resp(200, bad_json=True), Resp(200, ["no", "es", "dict"])],
)
def test_servicio_caido_deja_not_verified_y_no_aprueba(fallo):
    fake = Fake([(CROSSREF + "/", fallo), (OPENALEX + "/", fallo)])
    res, _ = run([FUENTE], fake)
    assert res.status is CriterionStatus.NOT_VERIFIED and res.blocking
    assert "servicio no disponible" in res.evidence[0]["reason"]


def test_un_proveedor_caido_y_el_otro_sin_el_doi_no_prueba_que_no_exista():
    fake = Fake([(CROSSREF + "/", TimeoutError("x")), (OPENALEX + "/", Resp(404))])
    res, _ = run([FUENTE], fake)
    assert res.status is CriterionStatus.NOT_VERIFIED


def test_reintenta_con_espera_exponencial_y_se_recupera():
    esperas, estados = [], iter([Resp(503), Resp(429), Resp(200, {"message": NATURE})])

    async def sleep(s):
        esperas.append(s)

    fake = Fake([(CROSSREF + "/", lambda *a: next(estados))])
    res, _ = asyncio.run(check_reference_existence(
        [FUENTE], ResolverConfig(backoff_s=1.0, retries=2), fetch=fake, sleep=sleep))
    assert res.status is CriterionStatus.PASSED and esperas == [1.0, 2.0]


def test_un_failed_no_se_degrada_ni_un_not_verified_se_aprueba():
    fake = Fake([(CROSSREF + "/", lambda u, p: Resp(404) if "malo" in u else Resp(500)),
                 (OPENALEX + "/", lambda u, p: Resp(404) if "malo" in u else Resp(500))])
    res, _ = run([{**FUENTE, "doi": "10.1/malo"}, {**FUENTE, "doi": "10.1/caido"}], fake)
    assert res.status is CriterionStatus.FAILED
    assert {e["status"] for e in res.evidence} == {"failed", "not_verified"}


def test_tiempo_maximo_por_evaluacion():
    t = iter(range(0, 1000, 100))  # cada lectura del reloj avanza 100 s
    fake = Fake(crossref_ok())
    res, _ = asyncio.run(check_reference_existence(
        [FUENTE, {**FUENTE, "doi": "10.1/b"}], ResolverConfig(max_total_s=120),
        fetch=fake, sleep=_nosleep, clock=lambda: next(t)))
    assert res.status is CriterionStatus.NOT_VERIFIED
    assert any("tiempo máximo" in e["reason"] for e in res.evidence)


# ── Caché: solo positivos ───────────────────────────────────────────────────


def test_la_cache_evita_la_segunda_consulta_de_un_positivo():
    fake = Fake(crossref_ok())
    cache = PositiveCache()
    run([FUENTE], fake, cache=cache)
    run([FUENTE], fake, cache=cache)
    assert len(fake.calls) == 1


def test_un_fallo_no_se_cachea():
    cache = PositiveCache()
    run([FUENTE], Fake([(CROSSREF + "/", Resp(500)), (OPENALEX + "/", Resp(500))]), cache=cache)
    fake = Fake(crossref_ok())
    res, _ = run([FUENTE], fake, cache=cache)
    assert res.status is CriterionStatus.PASSED and fake.calls


def test_la_cache_caduca():
    reloj = [0.0]
    cache = PositiveCache(ttl_days=30, clock=lambda: reloj[0])
    fake = Fake(crossref_ok())
    run([FUENTE], fake, cache=cache)
    reloj[0] = 31 * 86400
    run([FUENTE], fake, cache=cache)
    assert len(fake.calls) == 2


# ── Normalización ───────────────────────────────────────────────────────────


def test_normaliza_doi_y_titulos_y_revistas():
    assert normalize_doi("https://doi.org/10.1/ABC") == "10.1/abc"
    assert normalize_doi("doi: 10.1/abc") == "10.1/abc"
    assert title_similarity("Deep Learning!", "deep  learning") == 1.0
    assert journals_match("Proc. Natl. Acad. Sci.", "Proceedings of the National Academy of Sciences")
    assert journals_match("J. Mach. Learn. Res.", "Journal of Machine Learning Research")
    assert not journals_match("Nature", "Science")


# ── Objetivo medible de AC3 (sobre registros simulados, no sobre la red) ────

REALES = [
    ("10.1038/nature14539", "Deep learning", ["LeCun", "Bengio", "Hinton"], 2015, "Nature"),
    ("10.1109/CVPR.2016.90", "Deep Residual Learning for Image Recognition",
     ["He", "Zhang", "Ren", "Sun"], 2016, "2016 IEEE Conference on Computer Vision and Pattern Recognition (CVPR)"),
    ("10.1038/171737a0", "Molecular Structure of Nucleic Acids: A Structure for Deoxyribose Nucleic Acid",
     ["Watson", "Crick"], 1953, "Nature"),
    ("10.1038/nature16961", "Mastering the game of Go with deep neural networks and tree search",
     ["Silver", "Huang", "Maddison"], 2016, "Nature"),
    ("10.1162/neco.1997.9.8.1735", "Long Short-Term Memory", ["Hochreiter", "Schmidhuber"], 1997, "Neural Computation"),
    ("10.1038/nature14236", "Human-level control through deep reinforcement learning",
     ["Mnih", "Kavukcuoglu", "Silver"], 2015, "Nature"),
    ("10.1145/3065386", "ImageNet classification with deep convolutional neural networks",
     ["Krizhevsky", "Sutskever", "Hinton"], 2017, "Communications of the ACM"),
    ("10.1126/science.1127647", "Reducing the Dimensionality of Data with Neural Networks",
     ["Hinton", "Salakhutdinov"], 2006, "Science"),
    ("10.1016/j.neunet.2014.09.003", "Deep learning in neural networks: An overview",
     ["Schmidhuber"], 2015, "Neural Networks"),
    ("10.1007/BF00994018", "Support-vector networks", ["Cortes", "Vapnik"], 1995, "Machine Learning"),
]


def test_objetivo_de_resolucion_al_menos_90_por_ciento():
    registros = {d.lower(): cr(d, t, a, y, j) for d, t, a, y, j in REALES}
    fake = Fake([(CROSSREF + "/", lambda u, p: Resp(200, {"message": registros[u[len(CROSSREF) + 1:]]}))])
    aprobadas = 0
    for d, t, a, y, j in REALES:
        src = {"title": t, "authors": ", ".join(a), "year": str(y), "journal": j, "doi": d}
        res, _ = run([src], fake)
        aprobadas += res.status is CriterionStatus.PASSED
    assert aprobadas / len(REALES) >= 0.90


def test_la_salida_a_la_red_pasa_por_la_puerta_de_egress():
    import inspect

    from app.platform.publication_gate import reference_resolver as m

    fuente = inspect.getsource(m)
    assert "safe_get" in fuente
    assert "httpx" not in fuente and "verify=False" not in fuente


# ── DataCite: DOI de arXiv (DEC-1) ──────────────────────────────────────────

DATACITE = "https://api.datacite.org/dois"


def dc(doi, title, creators, year, publisher="arXiv", type_="Preprint"):
    return {"data": {"attributes": {
        "doi": doi, "titles": [{"title": title}],
        "creators": [{"familyName": c, "name": f"{c}, X."} for c in creators],
        "publicationYear": year, "publisher": publisher,
        "types": {"resourceTypeGeneral": type_},
    }}}


ARXIV = dc("10.48550/arxiv.1706.03762", "Attention is all you need",
           ["Vaswani", "Shazeer", "Parmar"], 2017)
FUENTE_ARXIV = {
    "title": "Attention is all you need", "authors": "Vaswani, A., Shazeer, N., Parmar, N.",
    "year": "2017", "journal": "arXiv", "doi": "10.48550/arXiv.1706.03762",
}


def test_un_doi_de_arxiv_se_resuelve_en_datacite_sin_preguntar_a_crossref():
    fake = Fake([(DATACITE + "/", Resp(200, ARXIV))])
    res, enriched = run([FUENTE_ARXIV], fake)
    assert res.status is CriterionStatus.PASSED
    assert [u for u, _ in fake.calls] == [f"{DATACITE}/10.48550/arxiv.1706.03762"]  # el DOI va normalizado
    assert enriched[0]["doi"] == "10.48550/arxiv.1706.03762"


def test_un_404_de_datacite_es_concluyente_y_no_se_pregunta_a_openalex():
    fake = Fake([(DATACITE + "/", Resp(404))])
    res, _ = run([FUENTE_ARXIV], fake)
    assert res.status is CriterionStatus.FAILED
    assert all(u.startswith(DATACITE) for u, _ in fake.calls)


def test_si_datacite_no_responde_cae_a_crossref_y_openalex_y_nunca_aprueba_por_ausencia():
    fake = Fake([
        (DATACITE + "/", Resp(503)),
        (CROSSREF + "/", Resp(404)),
        (OPENALEX + "/", Resp(503)),
    ])
    res, _ = run([FUENTE_ARXIV], fake)
    assert res.status is CriterionStatus.NOT_VERIFIED


def test_los_demas_doi_no_tocan_datacite():
    fake = Fake([(CROSSREF + "/", Resp(200, {"message": NATURE}))])
    res, _ = run([FUENTE], fake)
    assert res.status is CriterionStatus.PASSED
    assert not any(u.startswith(DATACITE) for u, _ in fake.calls)


def test_el_titulo_o_los_autores_distintos_en_datacite_siguen_fallando():
    mal = dc("10.48550/arxiv.1706.03762", "Otro trabajo distinto", ["Nadie"], 2017)
    res, _ = run([FUENTE_ARXIV], Fake([(DATACITE + "/", Resp(200, mal))]))
    assert res.status is CriterionStatus.FAILED
