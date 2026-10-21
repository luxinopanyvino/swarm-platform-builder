# ADR-0011: Compuerta de publicación determinista con falla cerrada

- **Estado:** Propuesto
- **Fecha:** 2026-10-21
- **Decisores:** Equipo de plataforma
- **Specs relacionadas:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md)
- **Origen:** *Framework de redacción y validación de papers* v0.1 (29/09/2026), §3, §7, §10 y §20

## Contexto

Hoy un manuscrito llega a «Publicado» sin que nada compruebe sus defectos verificables:
`run_publicador` escribe el texto y marca `PUBLISHED`; el Revisor aprueba por defecto cuando
falla; tras tres vueltas el flujo avanza igualmente; y `POST /articles/{id}/publish` publica
un borrador sin pasar por ninguna comprobación. Las referencias salen de documentos subidos al
RAG, sin identificador, y nada verifica que existan.

El framework exige tres condiciones para publicar (Revisor ≥ 80 sin bloqueantes de juicio,
compuerta determinista sin bloqueantes sobre el texto final, aprobación humana explícita) y
fija que **lo que no se puede comprobar no se aprueba** (§20, regla 4).

Introducir la compuerta implica decisiones difíciles de revertir: una **dependencia externa
en el camino crítico de publicar** (Crossref y OpenAlex), una política de fallo, un estado
nuevo en el ciclo de vida del artículo y una única autoridad sobre «puede publicarse».

## Decisión

1. **Una compuerta determinista, sin LLM**, en el Publicador, evaluada sobre el **texto final
   tras el Formateador**. Es un registro de criterios declarado por proyecto
   (`gate:` en `template.yaml`); el módulo no nombra agentes ni disciplinas.
2. **Falla cerrada.** Si un criterio no se puede comprobar, su estado es `not_verified` y
   **bloquea**. Nunca se aprueba por ausencia de respuesta. Los criterios cuyo dato aún no
   existe se declaran `not_implemented`: **no bloquean** y el informe los lista como pendientes
   con la fase que los construye. Es una concesión transitoria y visible, no una excepción
   silenciosa.
3. **Referencias (V09) resueltas contra Crossref y OpenAlex** por DOI o, sin él, por título y
   autores; sin excepción para «documento interno». El autor puede aportar el DOI a mano, que
   se verifica igual. Solo se envían **metadatos de referencias**, nunca el texto.
4. **Una sola función de decisión** (`can_publish`) que todo camino a `PUBLISHED` consulta:
   el agente, `approve` y `publish`.
5. **Aprobación humana explícita**, de una persona distinta de quien lanzó el pipeline, que
   queda registrada con usuario, decisión, fecha y huella del texto aprobado.
6. **Estado `requires_human_review`** cuando se agotan las vueltas con bloqueantes; solo una
   persona sale de él.
7. **Informe de compuerta persistido** y versionado por la huella del texto evaluado.

## Alternativas consideradas

- **Excepción para documentos aportados por el autor** (sin DOI). Más cómoda, pero el framework
  no la prevé (§2.4, §7 nivel 1) y reabre exactamente la puerta que cierra V09. Descartada.
- **Entrada de referencias solo por búsqueda externa.** Es el destino (Fase 4), pero no
  resuelve el corpus ya subido ni cabe en esta fase. Aplazada, no rechazada.
- **Un LLM como validador de referencias.** Es el fallo que el framework documenta (§7:
  citas inventadas); la comprobación debe ser determinista y externa al modelo. Descartada.
- **Compuerta que solo avisa.** Conserva el comportamiento actual con un aviso añadido; no
  cumple la regla de publicación. Solo se admite como **modo de despliegue temporal**
  (`PUBLICATION_GATE_ENFORCE=false`), nunca como diseño.
- **Falla abierta ante Crossref caído.** Mantiene el flujo vivo a costa de publicar sin
  verificar; contradice §20. Descartada.

## Consecuencias

- **Positivas:** un manuscrito con marcadores de posición, referencias inexistentes o sin
  aprobación humana deja de poder publicarse por ningún camino; cada publicación deja un
  expediente auditable; la compuerta es reutilizable por otros proyectos.
- **Negativas / coste:**
  - Publicar depende de la disponibilidad de dos servicios externos; un corte detiene la
    publicación (es la consecuencia deseada de la falla cerrada) y obliga a reintentar.
  - Los documentos subidos a mano sin DOI resoluble quedarán `not_verified` hasta que el autor
    aporte el identificador: fricción asumida a cambio de integridad.
  - Cambia un comportamiento visible: el pipeline ya no deja el artículo `PUBLISHED`.
  - Nueva tabla de informes con retención propia.
- **Seguimiento:** Fase 2 (contratos y devolución automática al agente responsable), Fase 3
  (Revisor por criterio: sustituye la definición provisional de «bloqueante de juicio»),
  Fase 4 (búsqueda externa y registro de búsqueda). Si el panel de validación cambia la
  decisión de V09, este ADR se reemplaza.
