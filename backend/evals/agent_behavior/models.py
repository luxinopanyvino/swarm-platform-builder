"""Tipos del harness EDD (SPEC-014 / T9.3 / AC3).

Un harness de evaluación vale lo que valga su **reproducibilidad**: si dos
ejecuciones del mismo dataset sobre el mismo perfil no se pueden comparar, sus
números no sirven para decidir nada, y menos para bloquear una PR (T9.5).

De ahí la forma de estos tipos: el informe no lleva solo las puntuaciones, lleva
**con qué se obtuvieron** — modelo, parámetros, versión y hash del dataset, y en
qué modo se ejecutó. Un número sin esa procedencia no se puede comparar con el de
la semana pasada.
"""
from __future__ import annotations

import platform
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvalCase:
    """Un caso del dataset: la entrada, y lo que se espera saber de la salida."""

    id: str
    agent: str
    #: Entrada del agente. Sus claves son las del `AgentState` que el agente lee.
    input: Dict[str, Any] = field(default_factory=dict)
    #: Documentos que **existen de verdad** en el RAG de este caso. Es la
    #: referencia con la que se comprueba que una cita no está inventada.
    corpus: List[Dict[str, Any]] = field(default_factory=list)
    #: Lo que se espera del comportamiento: formato, presupuesto, umbrales…
    expect: Dict[str, Any] = field(default_factory=dict)
    #: Salida grabada, para el modo `replay`. Ver `providers.py`.
    recorded_output: Optional[str] = None
    recorded_usage: Dict[str, Any] = field(default_factory=dict)
    #: Decisión grabada de un agente que decide (el revisor): `{score, coherent,
    #: hitl_outcome}`. Va aparte de `recorded_output` porque el revisor **no
    #: produce texto**: su salida es esta estructura, y meterla en un campo de
    #: texto obligaría a cada métrica a parsearla a su manera.
    recorded_decision: Optional[Dict[str, Any]] = None
    #: Veredicto grabado del juez, para poder reproducir en `replay` una métrica
    #: asistida sin llamar a ningún modelo. Ver `judge.py`.
    recorded_judgement: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class MetricResult:
    """Resultado de una métrica sobre un caso."""

    name: str
    #: 0..100. Una escala única hace comparables métricas de naturalezas distintas
    #: y permite declarar umbrales sin traducir unidades en cada una.
    score: float
    passed: bool
    #: Por qué salió ese número. Sin esto, un informe rojo no dice qué arreglar.
    detail: str = ""
    skipped_reason: Optional[str] = None


@dataclass
class CaseResult:
    case_id: str
    agent: str
    metrics: List[MetricResult] = field(default_factory=list)
    output: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    #: Lo que el agente **decidió**, si decide algo. Lo rellena el runner desde
    #: el proveedor, igual que los tokens: quien lo sabe lo anota, y la métrica
    #: solo lo lee. Sin esto el revisor sería inevaluable, porque su salida no es
    #: texto.
    decision: Optional[Dict[str, Any]] = None
    #: Veredicto del juez para las métricas asistidas. Lo pide el runner —donde
    #: se sabe el modo— y no la métrica, que debe seguir siendo una función pura.
    judgement: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.error is None and all(m.passed for m in self.metrics)


@dataclass
class RunContext:
    """Con qué se ejecutó. Es lo que hace comparables dos informes."""

    provider_mode: str
    agent: str
    model: str
    params: Dict[str, Any] = field(default_factory=dict)
    dataset_id: str = ""
    dataset_version: str = ""
    dataset_sha256: str = ""
    #: De dónde salieron las salidas grabadas del dataset: `recorded` (de una
    #: ejecución real del agente) o `handwritten` (escritas a mano). No es lo
    #: mismo como evidencia, y un informe que no lo diga deja creer que sí.
    dataset_provenance: str = ""
    llm_provider: str = ""
    python: str = field(default_factory=lambda: platform.python_version())
    git_sha: str = ""


@dataclass
class EvalReport:
    """Informe de una ejecución del harness."""

    context: RunContext
    cases: List[CaseResult] = field(default_factory=list)
    #: Instante de la ejecución. Va **aparte** del resto a propósito: es lo único
    #: que cambia entre dos ejecuciones idénticas, y aislarlo permite comparar
    #: informes byte a byte sin él.
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def passed(self) -> bool:
        return all(caso.passed for caso in self.cases)

    def scores(self) -> Dict[str, float]:
        """Media por métrica, sobre los casos donde no se saltó."""
        acumulado: Dict[str, List[float]] = {}
        for caso in self.cases:
            for metrica in caso.metrics:
                if metrica.skipped_reason is None:
                    acumulado.setdefault(metrica.name, []).append(metrica.score)
        return {
            nombre: round(sum(valores) / len(valores), 2)
            for nombre, valores in sorted(acumulado.items())
            if valores
        }

    def totals(self) -> Dict[str, Any]:
        return {
            "cases": len(self.cases),
            "passed": sum(1 for c in self.cases if c.passed),
            "tokens_in": sum(c.tokens_in for c in self.cases),
            "tokens_out": sum(c.tokens_out for c in self.cases),
        }

    def to_dict(self, *, include_timestamp: bool = True) -> Dict[str, Any]:
        datos: Dict[str, Any] = {
            "context": asdict(self.context),
            "totals": self.totals(),
            "scores": self.scores(),
            "passed": self.passed,
            "cases": [asdict(caso) for caso in self.cases],
        }
        if include_timestamp:
            datos["generated_at"] = self.generated_at
        return datos
