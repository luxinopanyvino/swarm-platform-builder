"""Agent seeding utilities: each project type gets its own set of default agents."""
import yaml
from pathlib import Path

from sqlalchemy import select

from app.models import AgentProfileModel, ProjectUseCaseType
from app.core.database import AsyncSessionLocal


# ── Agent templates per use-case type ─────────────────────────────────────────

def _alejandria_magazine_agents() -> list[dict]:
    """Try to load from .agent.md files; fall back to hardcoded."""
    search_paths = [Path("app/agents"), Path("../app/agents")]
    agents_dir = next((p for p in search_paths if p.exists()), None)
    if agents_dir:
        results = []
        for filepath in agents_dir.glob("*.agent.md"):
            try:
                raw = filepath.read_text(encoding="utf-8")
                frontmatter: dict = {}
                content = raw
                if raw.startswith("---"):
                    parts = raw.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1]) or {}
                        content = parts[2].lstrip()
                slug = filepath.stem.replace(".agent", "")
                results.append({
                    "slug": slug,
                    "name": slug.replace("-", " ").title(),
                    "content": content,
                    "model": frontmatter.get("model") or "llama3.2:1b",
                    "temperature": float(frontmatter.get("temperature") or 0.7),
                    "rag_enabled": bool(frontmatter.get("rag_enabled", True)),
                    "rag_collection": frontmatter.get("rag_collection") or "rag_docs",
                    "rag_chunk_size": int(frontmatter.get("rag_chunk_size") or 500),
                    "rag_chunk_overlap": int(frontmatter.get("rag_chunk_overlap") or 50),
                    "prompt_template": frontmatter.get("prompt_template") or "",
                    "is_builtin": True,
                })
            except Exception:
                pass
        if results:
            return results

    # Fallback hardcoded
    return [
        {"slug": "investigador", "name": "Investigador", "is_builtin": True,
         "content": "# Investigador\n\n## Rol\nInvestiga fuentes académicas y extrae información relevante.\n",
         "model": "llama3.2:1b", "temperature": 0.3},
        {"slug": "redactor", "name": "Redactor", "is_builtin": True,
         "content": "# Redactor\n\n## Rol\nRedacta el artículo científico a partir de la investigación.\n",
         "model": "llama3.2:1b", "temperature": 0.7},
        {"slug": "revisor", "name": "Revisor", "is_builtin": True,
         "content": "# Revisor\n\n## Rol\nEvalúa el borrador con un score 0-100 y genera feedback.\n",
         "model": "llama3.2:1b", "temperature": 0.4},
        {"slug": "formateador", "name": "Formateador", "is_builtin": True,
         "content": "# Formateador\n\n## Rol\nReformatea citas en APA, IEEE o Vancouver.\n",
         "model": "llama3.2:1b", "temperature": 0.2},
        {"slug": "publicador", "name": "Publicador", "is_builtin": True,
         "content": "# Publicador\n\n## Rol\nGuarda el artículo final y lo marca como PUBLISHED.\n",
         "model": "llama3.2:1b", "temperature": 0.1},
    ]


def _desarrollo_agents() -> list[dict]:
    return [
        {"slug": "arquitecto", "name": "Arquitecto", "is_builtin": True,
         "content": "# Arquitecto\n\n## Rol\nDiseña la arquitectura técnica del sistema, define patrones y tecnologías.\n\n## Dominio\nArquitectura de software, diseño de sistemas, patrones de diseño.\n\n## Salida esperada\nDocumento de arquitectura, diagramas de componentes, decisiones técnicas.\n",
         "model": "llama3.2:1b", "temperature": 0.4},
        {"slug": "backend-dev", "name": "Backend Dev", "is_builtin": True,
         "content": "# Backend Dev\n\n## Rol\nImplementa la lógica de negocio, APIs REST/GraphQL y persistencia de datos.\n\n## Dominio\nPython, FastAPI, Node.js, bases de datos, microservicios.\n\n## Salida esperada\nCódigo backend funcional, endpoints documentados, tests unitarios.\n",
         "model": "llama3.2:1b", "temperature": 0.5},
        {"slug": "frontend-dev", "name": "Frontend Dev", "is_builtin": True,
         "content": "# Frontend Dev\n\n## Rol\nCrea interfaces de usuario responsivas y accesibles.\n\n## Dominio\nReact, TypeScript, CSS, UX/UI, accesibilidad WCAG.\n\n## Salida esperada\nComponentes React, páginas, estilos y pruebas de interfaz.\n",
         "model": "llama3.2:1b", "temperature": 0.5},
        {"slug": "qa-tester", "name": "QA Tester", "is_builtin": True,
         "content": "# QA Tester\n\n## Rol\nDefine y ejecuta casos de prueba, detecta bugs y valida calidad.\n\n## Dominio\nPruebas funcionales, pruebas de integración, automatización con Pytest/Playwright.\n\n## Salida esperada\nPlan de pruebas, casos de test, reporte de bugs.\n",
         "model": "llama3.2:1b", "temperature": 0.3},
        {"slug": "devops", "name": "DevOps", "is_builtin": True,
         "content": "# DevOps\n\n## Rol\nAutomatiza pipelines CI/CD, gestiona infraestructura y despliegues.\n\n## Dominio\nDocker, Kubernetes, GitHub Actions, Terraform, monitoreo.\n\n## Salida esperada\nPipelines CI/CD, configuración de infraestructura, scripts de despliegue.\n",
         "model": "llama3.2:1b", "temperature": 0.3},
        {"slug": "code-reviewer", "name": "Code Reviewer", "is_builtin": True,
         "content": "# Code Reviewer\n\n## Rol\nRevisa pull requests, detecta vulnerabilidades y malas prácticas.\n\n## Dominio\nSeguridad, clean code, SOLID, OWASP Top 10.\n\n## Salida esperada\nComentarios de revisión, score de calidad, lista de mejoras.\n",
         "model": "llama3.2:1b", "temperature": 0.4},
    ]


def _marketing_agents() -> list[dict]:
    return [
        {"slug": "estratega", "name": "Estratega", "is_builtin": True,
         "content": "# Estratega\n\n## Rol\nDefine la estrategia de marketing, objetivos y KPIs de campaña.\n\n## Dominio\nMarketing digital, buyer personas, funnel de ventas, branding.\n\n## Salida esperada\nPlan de campaña, brief estratégico, métricas de éxito.\n",
         "model": "llama3.2:1b", "temperature": 0.5},
        {"slug": "copywriter", "name": "Copywriter", "is_builtin": True,
         "content": "# Copywriter\n\n## Rol\nRedacta textos persuasivos para anuncios, emails y landing pages.\n\n## Dominio\nCopywriting, storytelling, SEO on-page, psicología del consumidor.\n\n## Salida esperada\nTextos de anuncios, emails, titulares, calls to action.\n",
         "model": "llama3.2:1b", "temperature": 0.8},
        {"slug": "social-media", "name": "Social Media", "is_builtin": True,
         "content": "# Social Media\n\n## Rol\nCrea contenido para redes sociales y gestiona la comunidad.\n\n## Dominio\nInstagram, LinkedIn, X, TikTok, calendarios editoriales.\n\n## Salida esperada\nPosts, stories, calendarios de contenido, hashtags.\n",
         "model": "llama3.2:1b", "temperature": 0.8},
        {"slug": "seo-specialist", "name": "SEO Specialist", "is_builtin": True,
         "content": "# SEO Specialist\n\n## Rol\nOptimiza contenido y estructura para posicionamiento en buscadores.\n\n## Dominio\nKeyword research, SEO técnico, link building, Google Analytics.\n\n## Salida esperada\nInforme de palabras clave, contenido optimizado, recomendaciones técnicas.\n",
         "model": "llama3.2:1b", "temperature": 0.4},
        {"slug": "analista", "name": "Analista", "is_builtin": True,
         "content": "# Analista\n\n## Rol\nAnaliza métricas de campañas y propone optimizaciones basadas en datos.\n\n## Dominio\nGA4, Meta Ads, A/B testing, dashboards, reporting.\n\n## Salida esperada\nReporte de resultados, insights, recomendaciones de mejora.\n",
         "model": "llama3.2:1b", "temperature": 0.3},
    ]


def _tiqueting_agents() -> list[dict]:
    return [
        {"slug": "clasificador", "name": "Clasificador", "is_builtin": True,
         "content": "# Clasificador\n\n## Rol\nClasifica y prioriza tickets entrantes por urgencia, tipo y área.\n\n## Dominio\nTriaje de soporte, SLAs, categorización ITIL.\n\n## Salida esperada\nTicket clasificado con prioridad, categoría y área asignada.\n",
         "model": "llama3.2:1b", "temperature": 0.2},
        {"slug": "agente-soporte", "name": "Agente de Soporte", "is_builtin": True,
         "content": "# Agente de Soporte\n\n## Rol\nResponde consultas de usuarios con soluciones claras y amigables.\n\n## Dominio\nAtención al cliente, base de conocimiento, empatía, escalado.\n\n## Salida esperada\nRespuesta al usuario, pasos de resolución, estado del ticket.\n",
         "model": "llama3.2:1b", "temperature": 0.6},
        {"slug": "escalador", "name": "Escalador", "is_builtin": True,
         "content": "# Escalador\n\n## Rol\nIdentifica tickets que requieren escalado a nivel 2 o 3 y los redirige.\n\n## Dominio\nMatriz de escalado, SLAs críticos, comunicación con equipos técnicos.\n\n## Salida esperada\nDecisión de escalado, resumen ejecutivo para el equipo receptor.\n",
         "model": "llama3.2:1b", "temperature": 0.3},
        {"slug": "resolutor", "name": "Resolutor", "is_builtin": True,
         "content": "# Resolutor\n\n## Rol\nResuelve tickets técnicos complejos y documenta la solución.\n\n## Dominio\nDiagnóstico técnico, resolución de incidentes, documentación.\n\n## Salida esperada\nSolución aplicada, documentación en base de conocimiento, cierre de ticket.\n",
         "model": "llama3.2:1b", "temperature": 0.4},
        {"slug": "qa-calidad", "name": "QA Calidad", "is_builtin": True,
         "content": "# QA Calidad\n\n## Rol\nRevisa la calidad de las respuestas de soporte y mide satisfacción.\n\n## Dominio\nCSAT, NPS, auditoría de tickets, coaching de agentes.\n\n## Salida esperada\nScore de calidad, feedback al agente, reporte de satisfacción.\n",
         "model": "llama3.2:1b", "temperature": 0.3},
    ]


def _diseno_agents() -> list[dict]:
    return [
        {"slug": "art-director", "name": "Art Director", "is_builtin": True,
         "content": "# Art Director\n\n## Rol\nDefine la dirección visual del proyecto, identidad y guías de estilo.\n\n## Dominio\nBranding, tipografía, paleta de colores, composición visual.\n\n## Salida esperada\nBrief creativo, guía de estilo, moodboard, directrices de marca.\n",
         "model": "llama3.2:1b", "temperature": 0.6},
        {"slug": "ui-designer", "name": "UI Designer", "is_builtin": True,
         "content": "# UI Designer\n\n## Rol\nDiseña interfaces de usuario atractivas, accesibles y usables.\n\n## Dominio\nFigma, sistemas de diseño, WCAG, componentes reutilizables.\n\n## Salida esperada\nMockups, wireframes, especificaciones de componentes, design tokens.\n",
         "model": "llama3.2:1b", "temperature": 0.7},
        {"slug": "ux-researcher", "name": "UX Researcher", "is_builtin": True,
         "content": "# UX Researcher\n\n## Rol\nInvestiga necesidades de usuarios mediante entrevistas y tests de usabilidad.\n\n## Dominio\nEntrevistas, card sorting, heatmaps, journey maps, heurísticas Nielsen.\n\n## Salida esperada\nInforme de investigación, personas, pain points, recomendaciones UX.\n",
         "model": "llama3.2:1b", "temperature": 0.5},
        {"slug": "revisor-visual", "name": "Revisor Visual", "is_builtin": True,
         "content": "# Revisor Visual\n\n## Rol\nRevisa que los diseños cumplen con la guía de estilo y estándares de calidad.\n\n## Dominio\nQA de diseño, consistencia visual, pixel-perfect, accesibilidad.\n\n## Salida esperada\nLista de correcciones, score de consistencia, aprobación o rechazo.\n",
         "model": "llama3.2:1b", "temperature": 0.3},
        {"slug": "motion-designer", "name": "Motion Designer", "is_builtin": True,
         "content": "# Motion Designer\n\n## Rol\nDefine animaciones, transiciones y microinteracciones para la interfaz.\n\n## Dominio\nAnimación CSS, Lottie, Framer Motion, principios de animación.\n\n## Salida esperada\nEspecificaciones de animación, assets Lottie, guía de microinteracciones.\n",
         "model": "llama3.2:1b", "temperature": 0.6},
    ]


_AGENTS_BY_TYPE = {
    ProjectUseCaseType.ALEJANDRIA_MAGAZINE: _alejandria_magazine_agents,
    ProjectUseCaseType.DESARROLLO:          _desarrollo_agents,
    ProjectUseCaseType.MARKETING:           _marketing_agents,
    ProjectUseCaseType.TIQUETING:           _tiqueting_agents,
    ProjectUseCaseType.DISENO:              _diseno_agents,
    # CUSTOM intentionally omitted — user builds from scratch
}

_DEFAULTS = {
    "model": "llama3.2:1b",
    "temperature": 0.7,
    "rag_enabled": False,
    "rag_collection": "rag_docs",
    "rag_chunk_size": 500,
    "rag_chunk_overlap": 50,
    "prompt_template": "",
    "is_builtin": True,
}


async def seed_agents_for_project(project_id, use_case_type: ProjectUseCaseType) -> None:
    """Seed agent profiles for a project according to its use-case type."""
    factory = _AGENTS_BY_TYPE.get(use_case_type)
    if factory is None:
        return  # CUSTOM — start empty

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(AgentProfileModel)
            .where(AgentProfileModel.project_id == project_id)
            .limit(1)
        )
        if existing.scalars().first():
            return  # Already seeded

        for agent_data in factory():
            merged = {**_DEFAULTS, **agent_data}
            session.add(AgentProfileModel(
                project_id=project_id,
                slug=merged["slug"],
                name=merged["name"],
                content=merged.get("content", ""),
                model=merged["model"],
                temperature=merged["temperature"],
                rag_enabled=merged["rag_enabled"],
                rag_collection=merged["rag_collection"],
                rag_chunk_size=merged["rag_chunk_size"],
                rag_chunk_overlap=merged["rag_chunk_overlap"],
                prompt_template=merged["prompt_template"],
                is_builtin=merged["is_builtin"],
            ))
        await session.commit()
