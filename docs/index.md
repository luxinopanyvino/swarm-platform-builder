---
layout: home

hero:
  name: "Plataforma Agéntica"
  text: "Multiproyecto · v0.1.0"
  tagline: Orquestación de swarms de agentes IA con LangGraph, RAG con Qdrant y LLMs locales o cloud.
  actions:
    - theme: brand
      text: Empezar
      link: /guide/introduction
    - theme: alt
      text: Ver en GitHub
      link: https://github.com

features:
  - icon: 🤖
    title: Swarm de agentes
    details: Diseña flujos visuales conectando agentes especializados. Cada agente tiene su propio modelo LLM, temperatura y base documental RAG.
  - icon: 📚
    title: RAG con Qdrant
    details: Sube documentos PDF, TXT o Markdown. Se vectorizan con nomic-embed-text y quedan disponibles para los agentes en tiempo real.
  - icon: 🔀
    title: LangGraph Orchestrator
    details: El orquestador ejecuta el StateGraph en segundo plano y emite eventos en tiempo real vía Server-Sent Events (SSE).
  - icon: 📰
    title: AlexandrIA Magazine
    details: Proyecto de referencia. Un swarm de 5 agentes produce artículos científicos completos con investigación, redacción, revisión y formato APA/IEEE/Vancouver.
  - icon: 🔒
    title: Seguridad integrada
    details: Autenticación JWT, roles (admin, redactor, lector), control de acceso por recurso y validación de entradas en todos los endpoints.
  - icon: ⚙️
    title: Multiproveedor LLM
    details: Usa Ollama on-prem o conecta con OpenAI, Azure OpenAI, Groq o cualquier API compatible con el SDK de OpenAI.
---
