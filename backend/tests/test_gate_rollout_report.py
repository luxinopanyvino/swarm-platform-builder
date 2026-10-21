"""Reporte del despliegue gradual de la compuerta (DEC-4)."""
import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gate_rollout_report", REPO / "scripts" / "gate_rollout_report.py")
rollout = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rollout)


def informe(passed, **estados):
    return {"passed": passed, "criteria": [{"criterion": c, "status": s} for c, s in estados.items()]}


def test_cuenta_los_que_pasan_y_por_que_criterio_bloquean_los_demas():
    informes = [
        informe(True, imrad_structure="passed", placeholders="passed"),
        informe(False, imrad_structure="failed", placeholders="passed"),
        informe(False, reference_existence="not_verified", imrad_structure="failed"),
    ]
    r = rollout.resumir(informes, min_articulos=3)
    assert (r["total"], r["pasan"]) == (3, 1)
    assert r["bloquean_por"] == {"imrad_structure": 2, "reference_existence": 1}
    assert r["bloqueados_por_un_solo_criterio"] == 1  # el segundo: corrección acotada
    assert r["detalle_estado"]["reference_existence:not_verified"] == 1


def test_con_muestra_pequena_nunca_recomienda_activar():
    r = rollout.resumir([informe(True)] * 5, min_articulos=20)
    assert r["fraccion_pasa"] == 1.0 and not r["muestra_suficiente"] and not r["listo_para_activar"]
    assert "muestra insuficiente" in rollout.informe(r)


def test_recomienda_activar_solo_con_muestra_y_fraccion_suficientes():
    bien = [informe(True)] * 9 + [informe(False, placeholders="failed")]
    assert rollout.resumir(bien, min_articulos=10, min_pasa=0.8)["listo_para_activar"] is True
    mal = [informe(True)] * 5 + [informe(False, placeholders="failed")] * 5
    r = rollout.resumir(mal, min_articulos=10, min_pasa=0.8)
    assert not r["listo_para_activar"] and "aún no" in rollout.informe(r)


def test_sin_informes_no_divide_por_cero():
    r = rollout.resumir([])
    assert r["total"] == 0 and r["fraccion_pasa"] == 0.0 and not r["listo_para_activar"]


def test_el_reporte_solo_lee():
    fuente = (REPO / "scripts" / "gate_rollout_report.py").read_text(encoding="utf-8")
    for escritura in (".add(", ".commit(", ".delete(", "update(", "insert("):
        assert escritura not in fuente, escritura
