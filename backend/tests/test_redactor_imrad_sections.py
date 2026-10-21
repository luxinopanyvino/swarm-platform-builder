"""SPEC-032 AC11 / T20.5 — el Redactor pide Resultados y Discusión por separado."""
from app.modules.agents.adapters import redactor


def test_las_plantillas_separan_resultados_y_discusion():
    for tpl, res, dis in (
        (redactor._DEFAULT_TEMPLATE_ES, "- Resultados\n", "- Discusión\n"),
        (redactor._DEFAULT_TEMPLATE_EN, "- Results\n", "- Discussion\n"),
    ):
        assert res in tpl and dis in tpl
        assert "Resultados y Discusión" not in tpl.replace("Resultados y Discusión son DOS", "")
        assert "Preliminary Results and Discussion" not in tpl


def test_el_reparto_de_palabras_no_funde_las_secciones():
    src = open(redactor.__file__, encoding="utf-8").read()
    assert "Resultados y Discusi\u00f3n: ~" not in src
    assert "Results and Discussion: ~" not in src
