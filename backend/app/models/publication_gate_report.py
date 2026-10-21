"""Informe de la compuerta de publicación (SPEC-032 / T20.6 / AC6, ADR-0011).

Una fila por evaluación, ligada al texto evaluado por su huella SHA-256. Una nueva
evaluación **crea otra fila**: no sobrescribe, porque el historial es lo que
permite saber qué se aprobó y con qué evidencia. El informe vigente de un artículo
es el último cuya huella coincide con su cuerpo; si el texto cambió, ese informe ya
no vale y hay que reevaluar.

Solo lo escribe el backend: no hay endpoint que acepte un informe de fuera.
"""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    Column, DateTime, ForeignKey, Index, JSON, String, UUID as SA_UUID,
)

from app.core.database import Base


class PublicationGateReportModel(Base):
    __tablename__ = "publication_gate_reports"
    __table_args__ = (
        Index("ix_publication_gate_reports_article_created", "article_id", "created_at"),
    )

    id = Column(SA_UUID(as_uuid=True), primary_key=True, default=uuid4)
    # `CASCADE`: sin el artículo, el informe no describe nada.
    article_id = Column(
        SA_UUID(as_uuid=True), ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # `SET NULL`, como la traza: purgar la ejecución no se lleva el informe.
    run_id = Column(SA_UUID(as_uuid=True), ForeignKey("agent_runs.run_id", ondelete="SET NULL"))
    #: Huella del texto evaluado.
    text_sha256 = Column(String(64), nullable=False)
    #: `{"passed", "criteria": [...], "pending": [...]}` (`GateReport.as_dict`).
    criteria = Column(JSON, nullable=False, default=dict)
    #: Fuentes tras resolver y enriquecer, para poder reevaluar sin repetir la investigación.
    sources = Column(JSON, nullable=False, default=list)
    #: Quién pidió la evaluación; nulo si la hizo el pipeline.
    created_by = Column(SA_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class GateReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    article_id: UUID
    run_id: UUID | None = None
    text_sha256: str
    criteria: dict
    created_by: UUID | None = None
    created_at: datetime
