"""Harness EDD de comportamiento de agentes (SPEC-014 / T9.3 / AC3).

AC3: dado un perfil de agente de la plataforma y un dataset, el harness produce
un informe de métricas **reproducible** (modelo y parámetros fijados y
registrados) **sin depender de servicios externos no declarados**.

Esas dos exigencias tiran en direcciones opuestas —medir el comportamiento real
obliga a llamar al modelo, y un modelo generativo ni repite ni está disponible en
la CI—, así que el harness tiene dos modos explícitos. La mitad de estos tests
existe para que **no se puedan confundir**: un `replay` presentado como prueba de
que el agente va bien sería lo peor que le podría pasar a este harness.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from evals.agent_behavior import loader, metrics, providers, report, runner  # noqa: E402
from evals.agent_behavior.models import CaseResult, EvalCase  # noqa: E402

DATASETS = ROOT_DIR / "evals" / "agent_behavior" / "datasets"


# ── Datasets: se validan al cargarlos ───────────────────────────────────────

def test_los_datasets_del_repo_cargan():
    assert loader.available(), "no hay ningún dataset"
    for identificador in loader.available():
        dataset = loader.load_by_id(identificador)
        assert dataset.cases
        assert dataset.version
        assert len(dataset.sha256) == 64


def test_el_hash_del_dataset_cambia_con_su_contenido(tmp_path):
    """Sin hash, dos ejecuciones con el mismo `version` y distinto contenido
    parecerían comparables y no lo serían."""
    ruta = tmp_path / "d.jsonl"
    cabecera = json.dumps({"id": "d", "version": "1"})
    caso = json.dumps({"id": "c", "agent": "redactor", "recorded_output": "x"})
    ruta.write_text(f"{cabecera}\n{caso}\n", encoding="utf-8")
    primero = loader.load(ruta).sha256

    ruta.write_text(f"{cabecera}\n{caso}\n{json.dumps({'id': 'c2', 'agent': 'redactor'})}\n",
                    encoding="utf-8")
    assert loader.load(ruta).sha256 != primero


@pytest.mark.parametrize(
    "contenido, fragmento",
    [
        ("", "vacío"),
        ('{"id": "d"}\n', "cabecera"),
        ('{"id":"d","version":"1"}\n{"agent":"redactor"}\n', "no tiene 'id'"),
        ('{"id":"d","version":"1"}\n{"id":"c"}\n', "a qué agente"),
        ('{"id":"d","version":"1"}\n{"id":"c","agent":"r"}\n{"id":"c","agent":"r"}\n', "repetido"),
        ('{"id":"d","version":"1"}\n{no es json}\n', "JSON válido"),
        ('{"id":"d","version":"1"}\n{"id":"c","agent":"r","input":[]}\n', "'input' debe ser"),
    ],
)
def test_un_dataset_roto_se_rechaza_diciendo_la_linea(tmp_path, contenido, fragmento):
    """Un caso mal formado descubierto a mitad de una evaluación es tiempo tirado,
    y en la CI sería un fallo que no distingue «dataset roto» de «el agente ha
    regresado»."""
    ruta = tmp_path / "roto.jsonl"
    ruta.write_text(contenido, encoding="utf-8")
    with pytest.raises(loader.DatasetError) as error:
        loader.load(ruta)
    assert fragmento in str(error.value)


# ── Las métricas muerden ────────────────────────────────────────────────────

def _caso(**campos) -> EvalCase:
    base = {"id": "c", "agent": "redactor"}
    base.update(campos)
    return EvalCase(**base)


def _resultado(salida="", **campos) -> CaseResult:
    resultado = CaseResult(case_id="c", agent="redactor", output=salida)
    for clave, valor in campos.items():
        setattr(resultado, clave, valor)
    return resultado


def test_una_cita_inventada_baja_la_fidelidad():
    """La métrica que da sentido al RAG: un agente que se inventa las fuentes es
    peor que uno que no cita, porque su salida **parece** verificable."""
    caso = _caso(corpus=[{"doc_title": "Real"}], expect={"min_citations": 1})
    resultado = _resultado("[Fuente: Real] y [Fuente: Inventada]")
    metrica = metrics.get("citation_fidelity").run(caso, resultado)
    assert metrica.score == 50.0 and not metrica.passed
    assert "Inventada" in metrica.detail


def test_citar_solo_fuentes_reales_puntua_cien():
    caso = _caso(corpus=[{"doc_title": "Real"}], expect={"min_citations": 1})
    metrica = metrics.get("citation_fidelity").run(caso, _resultado("[Fuente: Real]"))
    assert metrica.score == 100.0 and metrica.passed


def test_no_citar_no_es_alucinar():
    """Salvo que el caso exija citas: entonces sí es un fallo."""
    caso = _caso(corpus=[{"doc_title": "Real"}])
    assert metrics.get("citation_fidelity").run(caso, _resultado("sin citas")).skipped_reason

    exigente = _caso(corpus=[{"doc_title": "Real"}], expect={"min_citations": 1})
    fallo = metrics.get("citation_fidelity").run(exigente, _resultado("sin citas"))
    assert not fallo.passed and fallo.score == 0.0


def test_perder_el_estilo_de_cita_se_detecta():
    """Cambiar el prompt del formateador y perder las citas de IEEE no se nota
    leyendo el artículo por encima."""
    caso = _caso(expect={"scientific_format": "ieee"})
    con_ieee = metrics.get("format_compliance").run(caso, _resultado("Como muestra [1]."))
    sin_ieee = metrics.get("format_compliance").run(caso, _resultado("Como muestra (Ng, 2023)."))
    assert con_ieee.passed and not sin_ieee.passed


def test_falta_una_seccion_exigida():
    caso = _caso(expect={"required_sections": ["Introducción", "Conclusiones"]})
    metrica = metrics.get("format_compliance").run(
        caso, _resultado("# T\n\n## Introducción\n\ntexto\n")
    )
    assert metrica.score == 50.0 and not metrica.passed
    assert "Conclusiones" in metrica.detail


def test_el_presupuesto_distingue_el_margen_y_no_solo_el_aprobado():
    """Consumir el 60% y el 99% no son lo mismo aunque los dos «pasen»."""
    caso = _caso(expect={"max_tokens_out": 1000})
    holgado = metrics.get("budget").run(caso, _resultado(tokens_out=200))
    justo = metrics.get("budget").run(caso, _resultado(tokens_out=980))
    excedido = metrics.get("budget").run(caso, _resultado(tokens_out=1500))

    assert holgado.passed and justo.passed and not excedido.passed
    assert holgado.score > justo.score
    assert "excedido" in excedido.detail


def test_una_metrica_que_no_aplica_se_salta_con_motivo():
    """Aprobar por no haber mirado es mentir con buena nota."""
    for nombre in ("citation_fidelity", "format_compliance", "budget"):
        metrica = metrics.get(nombre)
        assert not metrica.applies_to(_caso())


def test_una_metrica_desconocida_dice_cuales_hay():
    with pytest.raises(KeyError) as error:
        metrics.get("inventada")
    assert "citation_fidelity" in str(error.value)


# ── AC3: reproducibilidad, y sin servicios externos ─────────────────────────

@pytest.mark.asyncio
async def test_el_modo_replay_no_toca_ningun_servicio_externo(monkeypatch):
    """La comprobación literal de «sin depender de servicios externos».

    Se rompe el dispatcher del LLM: si el harness lo llamara en `replay`, esto
    fallaría en vez de pasar.
    """
    from app.platform import llm

    async def _prohibido(*args, **kwargs):
        raise AssertionError("el modo replay no debe llamar al LLM")

    monkeypatch.setattr(llm, "call_llm", _prohibido)
    monkeypatch.setattr(llm, "call_llm_stream", _prohibido)

    informe = await runner.run("redactor-smoke", mode="replay")
    assert informe.passed
    assert informe.context.provider_mode == "replay"


@pytest.mark.asyncio
async def test_dos_ejecuciones_en_replay_dan_el_mismo_informe():
    """La reproducibilidad que pide AC3, comparada byte a byte.

    El instante de generación se excluye a propósito: es lo único que cambia por
    el mero hecho de repetir, y aislarlo hace que «ha cambiado el informe»
    signifique «ha cambiado el comportamiento».
    """
    primero = await runner.run("redactor-smoke", mode="replay")
    segundo = await runner.run("redactor-smoke", mode="replay")
    assert report.fingerprint(primero) == report.fingerprint(segundo)


@pytest.mark.asyncio
async def test_el_informe_registra_con_que_se_hizo():
    """Un número sin procedencia no se puede comparar con el de la semana pasada."""
    informe = await runner.run("redactor-smoke", mode="replay")
    contexto = informe.context
    assert contexto.agent == "redactor"
    assert contexto.model                      # modelo resuelto por la plataforma
    assert contexto.dataset_version
    assert len(contexto.dataset_sha256) == 64
    assert contexto.provider_mode == "replay"


@pytest.mark.asyncio
async def test_un_caso_sin_salida_grabada_falla_diciendo_por_que(tmp_path, monkeypatch):
    """Y no en silencio: un caso sin grabar en `replay` no es un caso que pase."""
    ruta = tmp_path / "sin-grabar.jsonl"
    ruta.write_text(
        json.dumps({"id": "sin-grabar", "version": "1"}) + "\n"
        + json.dumps({"id": "c", "agent": "redactor"}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(loader, "DATASETS_DIR", tmp_path)

    informe = await runner.run("sin-grabar", mode="replay")
    assert not informe.passed
    assert "recorded_output" in informe.cases[0].error


@pytest.mark.asyncio
async def test_el_dataset_de_regresiones_falla_a_proposito():
    """Es documentación ejecutable de qué detecta el harness: si pasara, es que
    alguna métrica ha dejado de mirar."""
    informe = await runner.run("redactor-regressions", mode="replay")
    assert not informe.passed

    fallos = {
        caso.case_id: {m.name for m in caso.metrics if not m.passed}
        for caso in informe.cases
    }
    assert fallos["cita-inventada"] == {"citation_fidelity"}
    assert fallos["formato-perdido"] == {"format_compliance"}
    assert fallos["presupuesto-excedido"] == {"budget"}


@pytest.mark.asyncio
async def test_el_smoke_pasa_para_poder_usarse_como_gate():
    informe = await runner.run("redactor-smoke", mode="replay")
    assert informe.passed


# ── El informe: dos lectores, dos formatos ──────────────────────────────────

@pytest.mark.asyncio
async def test_el_informe_avisa_de_que_replay_no_evalua_al_modelo():
    """Confundir un `replay` con una medición real es el peor fallo posible aquí."""
    informe = await runner.run("redactor-smoke", mode="replay")
    markdown = report.to_markdown(informe)
    assert "no al modelo" in markdown or "**no al modelo**" in markdown
    assert "replay" in markdown


@pytest.mark.asyncio
async def test_el_modo_va_en_el_nombre_del_fichero(tmp_path):
    """Para que no se confunda ni mirando el listado del directorio."""
    informe = await runner.run("redactor-smoke", mode="replay")
    rutas = report.save(informe, tmp_path)
    assert all("replay" in ruta.name for ruta in rutas)
    assert {ruta.suffix for ruta in rutas} == {".json", ".md"}
    # El JSON es para el gate de T9.5: tiene que parsear sin leer prosa.
    datos = json.loads((tmp_path / f"{informe.context.dataset_id}--redactor--replay.json").read_text())
    assert datos["context"]["provider_mode"] == "replay"
    assert "scores" in datos and "cases" in datos


@pytest.mark.asyncio
async def test_el_hash_del_dataset_viaja_al_informe(tmp_path):
    """Dos ejecuciones del mismo `version` con contenido distinto no son
    comparables, y sin el hash lo parecerían: es la única evidencia de *qué*
    casos se corrieron. Tiene que llegar al informe, no quedarse en el loader."""
    informe = await runner.run("redactor-smoke", mode="replay")
    esperado = loader.load_by_id("redactor-smoke").sha256

    assert informe.context.dataset_sha256 == esperado
    assert esperado[:16] in report.to_markdown(informe)

    rutas = report.save(informe, tmp_path)
    datos = json.loads(next(r for r in rutas if r.suffix == ".json").read_text(encoding="utf-8"))
    assert datos["context"]["dataset_sha256"] == esperado


def test_editar_un_caso_sin_subir_la_version_cambia_el_hash(tmp_path):
    """Que es lo que hace que el cambio se vea: la versión la sube una persona
    y se puede olvidar; el hash no."""
    cabecera = '{"id": "d", "version": "1"}\n'
    caso = '{"id": "c", "agent": "redactor", "recorded_output": "%s"}\n'

    antes = tmp_path / "antes.jsonl"
    antes.write_text(cabecera + caso % "hola", encoding="utf-8")
    despues = tmp_path / "despues.jsonl"
    despues.write_text(cabecera + caso % "adios", encoding="utf-8")

    uno, otro = loader.load(antes), loader.load(despues)
    assert uno.version == otro.version
    assert uno.sha256 != otro.sha256


def test_el_modo_live_construye_el_proveedor_de_la_plataforma():
    """No una copia: si el harness llamara al LLM por su cuenta mediría algo
    parecido al agente, y las regresiones viven justo en esa diferencia."""
    proveedor = providers.build("live", "redactor")
    assert proveedor.mode == "live"
    assert proveedor.__class__.__name__ == "PlatformProvider"


def test_un_modo_desconocido_se_rechaza():
    with pytest.raises(ValueError):
        providers.build("inventado", "redactor")


# ── Frontera con el otro harness del repo ───────────────────────────────────

def test_no_se_mezcla_con_el_benchmark_de_modelos():
    """`model_benchmark` compara modelos *foundation* (SPEC-025) y este evalúa el
    comportamiento de los agentes (SPEC-014). Son preguntas distintas y ADR-0006
    marca la frontera; que compartan directorio no puede volverse un enredo.

    Lo que no puede pasar es que el código se **acople**: nombrar al otro harness
    en una docstring para decir dónde está la frontera es justo lo contrario,
    así que se mira el árbol de imports, no el texto."""
    import ast

    import evals.agent_behavior as harness

    codigo = ROOT_DIR / "evals" / "agent_behavior"
    ficheros = list(codigo.rglob("*.py"))
    assert ficheros, "no se ha encontrado el código del harness"

    for fichero in ficheros:
        arbol = ast.parse(fichero.read_text(encoding="utf-8"), filename=str(fichero))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nombres = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nombres = [nodo.module or ""]
            else:
                continue
            for nombre in nombres:
                assert not nombre.startswith("evals.model_benchmark"), f"{fichero.name}: {nombre}"

    # Y la frontera está escrita donde se lee al abrir el paquete.
    assert "model_benchmark" in (harness.__doc__ or "")
