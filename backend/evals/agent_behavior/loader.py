"""Carga y validación de datasets de evaluación (SPEC-014 / T9.3 / AC3).

Un dataset es un `.jsonl`: una línea de cabecera con `id` y `version`, y luego un
caso por línea. JSONL y no YAML porque un dataset crece por líneas y así el diff
de una PR enseña **qué caso se añadió** en vez de un bloque reindentado.

Se valida al cargar y con mensajes que dicen la línea: un caso mal formado
descubierto a mitad de una evaluación de veinte minutos es tiempo tirado, y en la
CI (T9.5) sería un fallo que no distingue «el dataset está roto» de «el agente ha
regresado».

El **hash** del fichero entra en el informe. Sin él, dos ejecuciones con el mismo
`version` pero distinto contenido parecerían comparables y no lo serían.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from evals.agent_behavior.models import EvalCase

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


class DatasetError(ValueError):
    """El dataset no es utilizable. El mensaje dice qué línea y por qué."""


#: Cómo se obtuvieron las salidas grabadas. `recorded` es evidencia del modelo;
#: `handwritten` es evidencia de la métrica. Confundirlas es el mismo error que
#: presentar un `replay` como medición real, así que el dataset lo declara y el
#: informe lo repite.
PROCEDENCIAS = ("recorded", "handwritten", "mixed")
SIN_DECLARAR = "no declarada"


@dataclass(frozen=True)
class Dataset:
    id: str
    version: str
    sha256: str
    path: Path
    cases: Tuple[EvalCase, ...]
    provenance: str = SIN_DECLARAR

    def for_agent(self, agent: str) -> Tuple[EvalCase, ...]:
        return tuple(caso for caso in self.cases if caso.agent == agent)

    def agents(self) -> Tuple[str, ...]:
        return tuple(sorted({caso.agent for caso in self.cases}))


def _exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise DatasetError(mensaje)


def _campo(datos: Dict[str, Any], nombre: str, tipo: type, vacio: Any, donde: str) -> Any:
    """Devuelve `datos[nombre]` exigiendo el tipo **antes** de aplicar el defecto.

    Con `datos.get(nombre) or vacio` un valor falso del tipo equivocado (`[]` en
    un campo que debe ser objeto) se convertiría en el defecto y pasaría la
    validación: el dataset roto se aceptaría y el caso se evaluaría sin su
    entrada. Ausente o `null` sí es «no lo declaro» y toma el defecto.
    """
    valor = datos.get(nombre)
    if valor is None:
        return vacio
    _exigir(isinstance(valor, tipo) and not isinstance(valor, bool),
            f"{donde} '{nombre}' debe ser {'un objeto' if tipo is dict else 'una lista'}")
    return valor


def _linea(numero: int, cruda: str, ruta: Path) -> Dict[str, Any]:
    try:
        datos = json.loads(cruda)
    except json.JSONDecodeError as error:
        raise DatasetError(f"{ruta.name}:{numero} no es JSON válido: {error}") from error
    _exigir(isinstance(datos, dict), f"{ruta.name}:{numero} debe ser un objeto JSON")
    return datos


def load(path: Path) -> Dataset:
    """Lee y valida el dataset que hay en `path`."""
    _exigir(path.is_file(), f"No existe el dataset {path}")
    crudo = path.read_bytes()
    sha = hashlib.sha256(crudo).hexdigest()

    lineas = [
        (numero, texto)
        for numero, texto in enumerate(crudo.decode("utf-8").splitlines(), start=1)
        if texto.strip() and not texto.lstrip().startswith("//")
    ]
    _exigir(bool(lineas), f"{path.name} está vacío")

    numero, cruda = lineas[0]
    cabecera = _linea(numero, cruda, path)
    _exigir("id" in cabecera and "version" in cabecera,
            f"{path.name}:{numero} la primera línea debe ser la cabecera con 'id' y 'version'")

    procedencia = str(cabecera.get("provenance") or SIN_DECLARAR)
    _exigir(procedencia in PROCEDENCIAS or procedencia == SIN_DECLARAR,
            f"{path.name}:{numero} 'provenance' debe ser una de {', '.join(PROCEDENCIAS)}")

    casos: List[EvalCase] = []
    vistos: set[str] = set()
    for numero, cruda in lineas[1:]:
        datos = _linea(numero, cruda, path)
        caso_id = str(datos.get("id") or "")
        _exigir(bool(caso_id), f"{path.name}:{numero} el caso no tiene 'id'")
        _exigir(caso_id not in vistos, f"{path.name}:{numero} el caso '{caso_id}' está repetido")
        vistos.add(caso_id)

        agente = str(datos.get("agent") or "")
        _exigir(bool(agente), f"{path.name}:{numero} el caso '{caso_id}' no dice a qué agente evalúa")

        donde = f"{path.name}:{numero}"
        entrada = _campo(datos, "input", dict, {}, donde)
        corpus = _campo(datos, "corpus", list, [], donde)
        espera = _campo(datos, "expect", dict, {}, donde)

        casos.append(EvalCase(
            id=caso_id,
            agent=agente,
            input=entrada,
            corpus=corpus,
            expect=espera,
            recorded_output=datos.get("recorded_output"),
            recorded_usage=_campo(datos, "recorded_usage", dict, {}, donde),
            recorded_decision=_campo(datos, "recorded_decision", dict, None, donde),
            recorded_judgement=_campo(datos, "recorded_judgement", dict, None, donde),
        ))

    _exigir(bool(casos), f"{path.name} no tiene ningún caso")
    return Dataset(
        id=str(cabecera["id"]),
        version=str(cabecera["version"]),
        sha256=sha,
        path=path,
        cases=tuple(casos),
        provenance=procedencia,
    )


def load_by_id(dataset_id: str) -> Dataset:
    """Carga por identificador, buscando en `evals/agent_behavior/datasets/`."""
    ruta = DATASETS_DIR / f"{dataset_id}.jsonl"
    return load(ruta)


def available() -> List[str]:
    if not DATASETS_DIR.is_dir():
        return []
    return sorted(p.stem for p in DATASETS_DIR.glob("*.jsonl"))
