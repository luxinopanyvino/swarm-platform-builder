"""Motor genérico de la plataforma (SPEC-013 / ADR-0005).

Este paquete agrupa la infraestructura reutilizable e independiente de
proyecto: el dispatcher LLM (`app.platform.llm`) y las capacidades tipadas
(`app.platform.capabilities`). El código específico de un proyecto (los
adapters de AlejandrIA) sigue en `app.modules.agents.adapters` hasta T8.3.

Nota sobre el nombre: `platform` es un subpaquete (`app.platform`) y no
colisiona con el módulo `platform` de la stdlib porque todos los imports del
backend son absolutos (`from app.platform... import ...`).
"""
