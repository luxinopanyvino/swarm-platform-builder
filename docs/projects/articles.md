# Gestión de artículos y revisión

## Ciclo editorial

El flujo de revisión humana complementa la revisión automática del agente Revisor:

1. El autor redacta y ejecuta el pipeline hasta que el resultado le satisface.
2. El autor pulsa **Enviar a revisión** → estado pasa a `in_review`.
3. El **admin** accede a **Artículos en revisión** y abre el artículo.
4. El admin puede:
   - **Aprobar** → el artículo pasa a `published` y aparece en la revista pública.
   - **Rechazar** → vuelve a `draft` con un comentario visible para el autor.
5. El autor recibe una **notificación** con el resultado.

::: info
Solo el rol `admin` puede aprobar o rechazar artículos. El agente Revisor realiza una revisión automática de calidad del borrador, pero la decisión editorial final recae siempre en un administrador humano.
:::

## Asignar revisor

Desde el panel de administración:

1. Ve a **Usuarios** y crea una cuenta con rol `admin` para el revisor (o promueve una existente).
2. El revisor puede acceder a todos los artículos en estado `in_review`.
3. Aprueba o rechaza desde el detalle del artículo.

## Operaciones por rol

| Operación | admin | redactor | lector |
|---|:---:|:---:|:---:|
| Crear artículo | ✓ | ✓ | — |
| Editar artículo (propio) | ✓ | ✓ | — |
| Enviar a revisión | ✓ | ✓ | — |
| Aprobar / Rechazar | ✓ | — | — |
| Ver artículos publicados | ✓ | ✓ | ✓ |
| Ver borradores ajenos | ✓ | ✓ | — |
| Gestionar usuarios | ✓ | — | — |
