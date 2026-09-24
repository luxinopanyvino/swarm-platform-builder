"""Coherencia de los bloques `sdd-sync` de todas las specs (SPEC-028…031).

`scripts/validate_specs.py` es el gate duro y comprueba lo suyo: esquema, formato
de IDs, duplicados de tarea, y que un `acceptance` apunte a un AC que existe. Estos
casos cubren tres invariantes que no mira y que sí se han roto o han estado a punto:

* **El prefijo de la tarea debe casar con su épica.** `T14.3` dentro de `E15` pasa
  el validador y solo se ve al mirar el Project.
* **Una dependencia debe tener destino.** El validador comprueba el *formato*
  (`T<n>.<m>` o `#<issue>`), no que exista. Y el destino puede estar en **otra
  spec** —`T9.1` depende de `T5.1`, que vive en SPEC-019—, así que la comprobación
  es global y no por fichero.
* **Una épica nueva no debe pisar a una existente.** SPEC-026 y SPEC-027 nacieron
  con E10 y E11, que ya eran de SPEC-021 y SPEC-022; saltó `validate_specs.py`, pero
  de rebote. Compartir épica **es legítimo aquí** —E2 la declaran SPEC-002
  (Superseded), SPEC-016 y SPEC-024—, así que lo que se fija es que las specs
  nuevas no se pongan encima de otra sin querer.
"""
import re
from pathlib import Path

import pytest
import yaml

REPO_DIR = Path(__file__).resolve().parents[2]
SPECS_DIR = REPO_DIR / "docs" / "specs"

#: Las specs de este plan y la épica que cada una reclama en exclusiva.
EPICAS_NUEVAS = {
    "SPEC-026-qa-test-strategy.md": "E14",
    "SPEC-027-model-evaluation-deepeval.md": "E15",
    "SPEC-028-dashboard-swarm-status.md": "E16",
    "SPEC-029-traceability-view-and-integrity.md": "E17",
    "SPEC-030-reference-input-and-run-control.md": "E18",
    "SPEC-031-format-learning-finetune.md": "E19",
}


def _bloques():
    """(nombre, datos) del bloque `sdd-sync` de cada spec que lo tenga."""
    for ruta in sorted(SPECS_DIR.glob("SPEC-*.md")):
        texto = ruta.read_text(encoding="utf-8")
        for m in re.finditer(r"```ya?ml\s*\n(.*?)```", texto, re.DOTALL):
            cuerpo = m.group(1)
            if "sdd-sync" in cuerpo.splitlines()[0]:
                yield ruta.name, yaml.safe_load(cuerpo)
                break


def test_el_prefijo_de_cada_tarea_casa_con_su_epica():
    descuadres = [
        f"{spec}: {t['id']} en épica {datos['epic']['id']}"
        for spec, datos in _bloques()
        for t in (datos.get("tasks") or [])
        if not t["id"].startswith(f"T{datos['epic']['id'][1:]}.")
    ]
    assert not descuadres, descuadres


def test_toda_dependencia_tiene_destino():
    """Global a propósito: las dependencias cruzan specs (T9.1 → T5.1)."""
    conocidas = {t["id"] for _, datos in _bloques() for t in (datos.get("tasks") or [])}
    rotas = [
        f"{spec}: {t['id']} → {dep}"
        for spec, datos in _bloques()
        for t in (datos.get("tasks") or [])
        for dep in (t.get("depends_on") or [])
        if not dep.startswith("#") and dep not in conocidas
    ]
    assert not rotas, rotas


@pytest.mark.parametrize("spec_name,epica", sorted(EPICAS_NUEVAS.items()))
def test_las_epicas_nuevas_no_pisan_a_ninguna_existente(spec_name, epica):
    duenos = [s for s, datos in _bloques() if datos["epic"]["id"] == epica]
    assert duenos == [spec_name], (
        f"{epica} la declara además {[d for d in duenos if d != spec_name]}"
    )


@pytest.mark.parametrize("spec_name", sorted(EPICAS_NUEVAS))
def test_cada_criterio_de_aceptacion_lo_reclama_alguna_tarea(spec_name):
    """Un AC que ninguna tarea reclama es una promesa que el backlog no recoge.

    Acotado a las specs de este plan: **SPEC-022 tiene hoy su AC6 sin cubrir**, y
    arreglar la spec de otra épica no es asunto de esta. Queda dicho para que se
    decida aparte, en vez de esconderlo tras una excepción en el test.
    """
    ruta = SPECS_DIR / spec_name
    texto = ruta.read_text(encoding="utf-8")
    declarados = set(re.findall(r"\*\*(AC\d+)\*\*", texto))
    if not declarados:
        pytest.skip(f"{spec_name} aún no declara criterios (Draft)")
    datos = dict(_bloques())[spec_name]
    cubiertos = {ac for t in datos["tasks"] for ac in (t.get("acceptance") or [])}
    assert declarados <= cubiertos, f"AC sin tarea: {sorted(declarados - cubiertos)}"


#: Las dos tareas de la fase de decisión de SPEC-031 (PR #380): el spike que mide
#: la viabilidad (T19.1) y el ADR que fija el diseño (T19.2).
TAREAS_FASE_DECISION_FINETUNE = {"T19.1", "T19.2"}


def test_la_spec_de_finetune_no_siembra_implementacion_sin_adr():
    """Sin ADR aceptado, SPEC-031 solo puede sembrar su fase de decisión.

    Es la salvaguarda de la decisión: RAG se deshace borrando un documento y un
    fine-tune no, así que la retención y el aislamiento por proyecto se deciden
    antes de que existan issues de implementación que alguien pueda ponerse a
    resolver.

    Hasta el 2026-09-15 esto se comprobaba exigiendo que la spec siguiera en
    `Draft`. La PR #380 la pasó a `Ready` **solo para su fase de decisión**, así
    que la salvaguarda se reescribe sobre lo que de verdad protege: mientras el
    ADR relacionado siga pendiente, el bloque `sdd-sync` no declara más tareas que
    el spike y el ADR. Cuando el ADR se acepte (AC4), la spec lo enlaza y puede
    añadir las tareas de implementación; si se rechaza, pasa a `Superseded`.
    """
    spec_name = "SPEC-031-format-learning-finetune.md"
    texto = (SPECS_DIR / spec_name).read_text(encoding="utf-8")

    estado = re.search(r"^\s*-\s*\*\*Estado:\*\*\s*(\S+)", texto, re.MULTILINE)
    assert estado and estado.group(1) in {"Draft", "Ready", "Superseded"}, (
        f"Estado inesperado de SPEC-031: {estado and estado.group(1)}"
    )

    adr = re.search(r"^\s*-\s*\*\*ADR relacionado:\*\*\s*(.+)$", texto, re.MULTILINE)
    assert adr, "SPEC-031 debe declarar su ADR relacionado (aunque esté pendiente)"
    if "pendiente" not in adr.group(1).lower():
        pytest.skip("El ADR de fine-tune ya está enlazado: la spec puede ampliar sus tareas")

    tareas = {t["id"] for t in (dict(_bloques())[spec_name].get("tasks") or [])}
    sobrantes = tareas - TAREAS_FASE_DECISION_FINETUNE
    assert not sobrantes, (
        f"SPEC-031 siembra tareas de implementación sin ADR aceptado: {sorted(sobrantes)}"
    )


@pytest.mark.parametrize("spec_name", sorted(EPICAS_NUEVAS))
def test_cada_spec_del_plan_esta_en_el_backlog(spec_name):
    """El backlog es donde se mira el orden; una épica que no está ahí no existe."""
    backlog = (REPO_DIR / "docs" / "backlog" / "security-hardening-backlog.md").read_text(encoding="utf-8")
    assert spec_name.removesuffix(".md") in backlog, f"{spec_name} no aparece en el backlog"
