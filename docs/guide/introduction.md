# ¿Qué es la Plataforma Agéntica?

La **Plataforma Agéntica Multiproyecto** es un framework de orquestación de agentes IA que permite crear proyectos independientes, cada uno con su propio swarm de agentes configurables, base documental RAG y flujo de trabajo personalizado.

## Concepto

```
Plataforma
├── Proyecto A: AlexandrIA Magazine
│   ├── Agentes: investigador, redactor, revisor, formateador, publicador
│   └── Flujo: investigador → redactor → revisor → formateador → publicador
│
├── Proyecto B: Desarrollo de software
│   ├── Agentes: arquitecto, backend-dev, frontend-dev, qa-tester, code-reviewer
│   └── Flujo: arquitecto → backend-dev → qa-tester → code-reviewer
│
└── Proyecto C: Marketing
    ├── Agentes: estratega, copywriter, seo-specialist
    └── Flujo personalizado
```

## Ciclo de vida de una ejecución

1. El usuario crea un **artefacto** (artículo, ticket, tarea…) en su proyecto.
2. Selecciona una **secuencia de agentes** y lanza la ejecución.
3. El **Orchestrator** (LangGraph `StateGraph`) ejecuta cada nodo en el orden indicado.
4. Cada agente recibe el estado acumulado, lo enriquece y lo pasa al siguiente.
5. Los eventos se emiten en tiempo real vía **Server-Sent Events (SSE)**.
6. Al terminar, el artefacto se actualiza en la base de datos.

## Tipos de proyecto disponibles

| Tipo | Descripción |
|---|---|
| `alexandria_magazine` | Revista científica con swarm editorial |
| `desarrollo` | Ciclo de desarrollo de software |
| `marketing` | Producción de contenido y campañas |
| `tiqueting` | Gestión y resolución de tickets de soporte |
| `diseno` | Flujos de diseño y revisión visual |
| `custom` | Proyecto completamente personalizable |

## Primeros pasos

<div class="tip custom-block">

**Nuevo en la plataforma?** Ve directamente a [Instalación local](/guide/installation) y tendrás el stack completo corriendo en menos de 10 minutos.

</div>
