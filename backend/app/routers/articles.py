"""Articles router: CRUD and workflow for articles."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import joinedload
from app.models import (
    ArticleModel, ArticleStatus, CreateArticleDTO, UpdateArticleDTO,
    ArticleResponse, ArticleListResponse, UserModel, NotificationModel, UserRole,
    AuthorDTO, ThemeDTO, ScientificFormat
)
from app.core.database import get_session
from app.routers.auth import get_current_user
from pydantic import BaseModel


router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


async def resolve_article_theme(session: AsyncSession, article: ArticleModel) -> dict:
    """Resolve the paper theme for an article: project theme → article theme.

    The format preset is the third (widest) layer and is applied inside
    ``build_paper_html``; here we only merge the two stored layers, most
    specific last (SPEC-022/AC2).
    """
    from app.models import ProjectModel
    from app.modules.agents.adapters.paper_layout import resolve_theme

    project_theme = None
    if article.project_id:
        result = await session.execute(
            select(ProjectModel).where(ProjectModel.id == article.project_id)
        )
        project = result.scalars().first()
        project_theme = getattr(project, "theme", None) if project else None

    return resolve_theme(project_theme, getattr(article, "theme", None))


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    status: ArticleStatus | None = None,
    project_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List articles.

    - admin   → all articles (optionally filtered by project)
    - redactor → all articles (optionally filtered by project)
    - lector  → published articles only (read-only)
    - publico → 403 (use public magazine endpoint instead)
    """
    role = token_data.get("role", "redactor")
    if role == UserRole.PUBLICO:
        raise HTTPException(status_code=403, detail="Acceso no permitido")

    stmt = select(ArticleModel)
    if role == UserRole.LECTOR:
        stmt = stmt.where(ArticleModel.status == ArticleStatus.PUBLISHED)
    # admin and redactor see all articles

    if status and role != UserRole.LECTOR:
        stmt = stmt.where(ArticleModel.status == status)

    if project_id is not None:
        stmt = stmt.where(ArticleModel.project_id == project_id)

    count_stmt = stmt
    stmt = stmt.options(joinedload(ArticleModel.author)).offset(skip).limit(limit)
    result = await session.execute(stmt)
    items = result.unique().scalars().all()

    count_result = await session.execute(count_stmt)
    total = len(count_result.scalars().all())

    def _to_response(item: ArticleModel) -> ArticleResponse:
        r = ArticleResponse.model_validate(item)
        r.author_name = item.author.full_name if item.author else None
        return r

    return ArticleListResponse(
        items=[_to_response(item) for item in items],
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )


@router.post("", response_model=ArticleResponse, status_code=201)
async def create_article(
    req: CreateArticleDTO,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Create a new article (admin and redactor only)."""
    role = token_data.get("role", "redactor")
    if role not in (UserRole.ADMIN, UserRole.REDACTOR):
        raise HTTPException(status_code=403, detail="Sin permisos para crear artículos")

    article = ArticleModel(
        title=req.title,
        body=req.body,
        author_id=UUID(token_data["user_id"]),
        project_id=req.project_id,
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get an article by ID. Unpublished articles are only visible to admins and their author."""
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    role = token_data.get("role", "redactor")
    user_id = token_data.get("user_id")
    is_admin = role == UserRole.ADMIN
    is_redactor = role == UserRole.REDACTOR
    is_owner = str(article.author_id) == user_id
    is_published = article.status == ArticleStatus.PUBLISHED
    is_assigned_reviewer = article.reviewer_id and str(article.reviewer_id) == user_id

    # admins and redactors (internal users) can view any article
    # lectors can view published articles or articles where they are the assigned reviewer
    if not is_admin and not is_redactor and not is_owner and not is_published and not is_assigned_reviewer:
        raise HTTPException(status_code=403, detail="Forbidden")

    return ArticleResponse.model_validate(article)


@router.put("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: UUID,
    req: UpdateArticleDTO,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update an article (admin or owner redactor only)."""
    role = token_data.get("role", "redactor")
    if role not in (UserRole.ADMIN, UserRole.REDACTOR):
        raise HTTPException(status_code=403, detail="Sin permisos para editar artículos")

    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if role != UserRole.ADMIN and str(article.author_id) != token_data["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if req.title is not None:
        article.title = req.title
    if req.body is not None:
        article.body = req.body
    if req.scientific_format is not None:
        article.scientific_format = req.scientific_format
    if req.authors is not None:
        article.authors = [a.model_dump() for a in req.authors]
    if req.abstract is not None:
        article.abstract = req.abstract
    if req.theme is not None:
        # Sanitised on the way in so the stored theme only ever holds allowlisted
        # values — the layout sanitises again on render (defence in depth).
        from app.modules.agents.adapters.paper_layout import sanitize_theme

        article.theme = sanitize_theme(req.theme.model_dump(exclude_none=True))

    session.add(article)
    await session.commit()
    await session.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.post("/{article_id}/submit", response_model=ArticleResponse)
async def submit_for_review(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Submit article for review (draft â†’ in_review)."""
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if str(article.author_id) != token_data["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    if article.status != ArticleStatus.DRAFT:
        raise HTTPException(status_code=409, detail="Article not in draft status")
    
    article.status = ArticleStatus.IN_REVIEW
    session.add(article)
    await session.commit()
    await session.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.post("/{article_id}/approve", response_model=ArticleResponse)
async def approve_article(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Approve article (in_review → published). Admin, redactor, or the assigned reviewer."""
    role = token_data.get("role", "redactor")
    current_user_id = UUID(token_data["user_id"])

    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    is_assigned_reviewer = article.reviewer_id == current_user_id
    if role != UserRole.ADMIN and not is_assigned_reviewer:
        raise HTTPException(status_code=403, detail="Solo el administrador o el revisor asignado puede aprobar artículos")

    if article.status != ArticleStatus.IN_REVIEW:
        raise HTTPException(status_code=409, detail="Article not under review")
    
    article.status = ArticleStatus.PUBLISHED
    article.reviewer_id = UUID(token_data["user_id"])
    article.published_at = __import__("datetime").datetime.utcnow()
    
    session.add(article)

    # Mark the reviewer's assignment notification as read
    notif_stmt = select(NotificationModel).where(
        NotificationModel.article_id == article_id,
        NotificationModel.user_id == UUID(token_data["user_id"]),
        NotificationModel.read == False  # noqa: E712
    )
    notif_res = await session.execute(notif_stmt)
    for n in notif_res.scalars().all():
        n.read = True
        session.add(n)

    # Notify the author
    notification = NotificationModel(
        user_id=article.author_id,
        article_id=article.id,
        title="Artículo aprobado y publicado",
        message=f"Tu artículo '{article.title}' ha sido aprobado y publicado."
    )
    session.add(notification)

    await session.commit()
    await session.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.post("/{article_id}/publish", response_model=ArticleResponse)
async def publish_article_direct(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Publish a draft article directly (draft → published). Admin or redactor only."""
    role = token_data.get("role", "author")
    if role not in (UserRole.ADMIN, UserRole.REDACTOR):
        raise HTTPException(status_code=403, detail="Solo administradores y redactores pueden publicar directamente")

    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.status == ArticleStatus.PUBLISHED:
        raise HTTPException(status_code=409, detail="El artículo ya está publicado")

    article.status = ArticleStatus.PUBLISHED
    article.published_at = __import__("datetime").datetime.utcnow()
    session.add(article)

    # Notify the author if different from the publisher
    if article.author_id != UUID(token_data["user_id"]):
        notification = NotificationModel(
            user_id=article.author_id,
            article_id=article.id,
            title="Artículo publicado",
            message=f"Tu artículo '{article.title}' ha sido publicado.",
        )
        session.add(notification)

    await session.commit()
    await session.refresh(article)
    return ArticleResponse.model_validate(article)


@router.post("/{article_id}/reject", response_model=ArticleResponse)
async def reject_article(
    article_id: UUID,
    comment: str,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Reject article (in_review → draft). Admin, redactor, or the assigned reviewer."""
    role = token_data.get("role", "redactor")
    current_user_id = UUID(token_data["user_id"])

    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    is_assigned_reviewer = article.reviewer_id == current_user_id
    if role != UserRole.ADMIN and not is_assigned_reviewer:
        raise HTTPException(status_code=403, detail="Solo el administrador o el revisor asignado puede rechazar artículos")

    if article.status != ArticleStatus.IN_REVIEW:
        raise HTTPException(status_code=409, detail="Article not under review")
    
    article.status = ArticleStatus.REJECTED
    article.rejection_comment = comment
    article.reviewer_id = UUID(token_data["user_id"])
    
    session.add(article)

    # Mark the reviewer's assignment notification as read
    notif_stmt = select(NotificationModel).where(
        NotificationModel.article_id == article_id,
        NotificationModel.user_id == UUID(token_data["user_id"]),
        NotificationModel.read == False  # noqa: E712
    )
    notif_res = await session.execute(notif_stmt)
    for n in notif_res.scalars().all():
        n.read = True
        session.add(n)

    # Notify the author
    notification = NotificationModel(
        user_id=article.author_id,
        article_id=article.id,
        title="Artículo rechazado",
        message=f"Tu artículo '{article.title}' ha sido rechazado. Comentario: {comment}"
    )
    session.add(notification)

    await session.commit()
    await session.refresh(article)
    
    return ArticleResponse.model_validate(article)


@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete an article (author only)."""
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if str(article.author_id) != token_data["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    await session.delete(article)
    await session.commit()


class AssignReviewerDTO(BaseModel):
    # Accepts email address or full name (e.g. "Juan García" or "juan@example.com")
    reviewer_identifier: str


@router.post("/{article_id}/assign-reviewer", response_model=ArticleResponse)
async def assign_reviewer(
    article_id: UUID,
    req: AssignReviewerDTO,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Assign a reviewer to the article and set status to IN_REVIEW.

    ``reviewer_identifier`` can be the reviewer's email address or full name.
    """
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    res = await session.execute(stmt)
    article = res.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if str(article.author_id) != token_data["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: Only the author can assign a reviewer")

    identifier = req.reviewer_identifier.strip()

    # Try email first, then full_name
    res_user = await session.execute(select(UserModel).where(UserModel.email == identifier))
    reviewer = res_user.scalars().first()
    if not reviewer:
        res_user = await session.execute(select(UserModel).where(UserModel.full_name == identifier))
        reviewer = res_user.scalars().first()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found (tried email and full name)")

    article.reviewer_id = reviewer.id
    article.status = ArticleStatus.IN_REVIEW
    session.add(article)

    # Create an in-app notification
    notification = NotificationModel(
        user_id=reviewer.id,
        article_id=article.id,
        title="Nueva revisión asignada",
        message=f"Has sido asignado como revisor para el artículo '{article.title}'."
    )
    session.add(notification)

    await session.commit()
    await session.refresh(article)
    return ArticleResponse.model_validate(article)


@router.get("/{article_id}/paper", response_class=HTMLResponse)
async def get_article_paper(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return the printable paper-layout HTML for an article.

    Serves the stored ``paper_html`` produced by the Publicador. If it is empty
    (e.g. the article was never run through the Publicador), the layout is built
    on the fly so the paper view always works. Visibility matches get_article.
    """
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    role = token_data.get("role", "redactor")
    user_id = token_data.get("user_id")
    is_admin = role == UserRole.ADMIN
    is_redactor = role == UserRole.REDACTOR
    is_owner = str(article.author_id) == user_id
    is_published = article.status == ArticleStatus.PUBLISHED
    is_assigned_reviewer = article.reviewer_id and str(article.reviewer_id) == user_id
    if not is_admin and not is_redactor and not is_owner and not is_published and not is_assigned_reviewer:
        raise HTTPException(status_code=403, detail="Forbidden")

    paper_html = article.paper_html or ""
    if not paper_html.strip():
        from app.modules.agents.adapters.paper_layout import build_paper_html
        from app.platform.assets import make_project_resolver

        fmt = (article.scientific_format.value if article.scientific_format else None) or "apa"
        paper_html = build_paper_html(
            title=article.title or "",
            authors=article.authors or [],
            abstract=article.abstract or "",
            body_markdown=article.body or "",
            scientific_format=fmt,
            theme=await resolve_article_theme(session, article),
            asset_resolver=make_project_resolver(str(article.project_id or "")),
        )

    return HTMLResponse(content=paper_html)


class PaperPreviewDTO(BaseModel):
    """Unsaved edits to preview. Every field is optional: what is not sent falls
    back to what the article already has, so the panel can preview a single
    changed control without resending the whole document."""
    title: str | None = None
    body: str | None = None
    abstract: str | None = None
    authors: list[AuthorDTO] | None = None
    scientific_format: ScientificFormat | None = None
    theme: ThemeDTO | None = None


@router.post("/{article_id}/assets", status_code=201)
async def upload_article_asset(
    article_id: UUID,
    file: UploadFile = File(...),
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload a figure for an article, stored in its **project's** asset store.

    Validated by real content (magic bytes, T2.3) before anything is written, so
    a renamed payload never lands on disk. Returns the ``asset:<id>`` reference
    to paste into the body as ``![pie de figura](asset:<id>)``.
    """
    from app.platform.assets import ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES, save_image
    from app.platform.uploads import validate_upload

    role = token_data.get("role", "redactor")
    if role not in (UserRole.ADMIN, UserRole.REDACTOR):
        raise HTTPException(status_code=403, detail="Sin permisos para subir figuras")

    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if role != UserRole.ADMIN and str(article.author_id) != token_data["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    raw = await file.read()
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Imagen demasiado grande (máx. {MAX_IMAGE_BYTES // (1024 * 1024)} MB)",
        )
    detected = validate_upload(file.filename, raw, ALLOWED_IMAGE_EXTENSIONS)

    asset_id = save_image(str(article.project_id or ""), raw, detected)
    return {
        "id": asset_id,
        "ref": f"asset:{asset_id}",
        "markdown": f"![{file.filename or 'figura'}](asset:{asset_id})",
        "type": detected,
    }


@router.post("/{article_id}/preview", response_class=HTMLResponse)
async def preview_article_paper(
    article_id: UUID,
    req: PaperPreviewDTO,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Render the paper layout for *unsaved* edits. Nothing is persisted.

    Uses the very same ``build_paper_html`` as the published paper, so the
    preview is byte-identical to what printing to PDF will produce — that is the
    point of doing this server-side instead of re-implementing the layout in the
    browser (SPEC-022/AC3).

    Visibility matches ``get_article_paper``; a preview never reveals an article
    the caller could not already read.
    """
    from app.modules.agents.adapters.paper_layout import build_paper_html, resolve_theme
    from app.platform.assets import make_project_resolver

    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    result = await session.execute(stmt)
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    role = token_data.get("role", "redactor")
    user_id = token_data.get("user_id")
    is_admin = role == UserRole.ADMIN
    is_redactor = role == UserRole.REDACTOR
    is_owner = str(article.author_id) == user_id
    is_published = article.status == ArticleStatus.PUBLISHED
    is_assigned_reviewer = article.reviewer_id and str(article.reviewer_id) == user_id
    if not is_admin and not is_redactor and not is_owner and not is_published and not is_assigned_reviewer:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Stored values are the base; the request overrides only what it sends.
    fmt = req.scientific_format or article.scientific_format
    fmt_value = (fmt.value if fmt else None) or "apa"
    authors = (
        [a.model_dump() for a in req.authors] if req.authors is not None
        else (article.authors or [])
    )
    # Theme cascade with the unsaved theme as the most specific layer.
    theme = resolve_theme(
        await resolve_article_theme(session, article),
        req.theme.model_dump(exclude_none=True) if req.theme else None,
    )

    html = build_paper_html(
        title=req.title if req.title is not None else (article.title or ""),
        authors=authors,
        abstract=req.abstract if req.abstract is not None else (article.abstract or ""),
        body_markdown=req.body if req.body is not None else (article.body or ""),
        scientific_format=fmt_value,
        theme=theme,
        asset_resolver=make_project_resolver(str(article.project_id or "")),
    )
    return HTMLResponse(content=html)


@router.post("/{article_id}/format-body", response_model=ArticleResponse)
async def format_article_body(
    article_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Run the formateador agent on the article body and save the formatted result.

    Useful after manual plain-text edits to convert prose to markdown with
    proper citation formatting.
    """
    stmt = select(ArticleModel).where(ArticleModel.id == article_id)
    res = await session.execute(stmt)
    article = res.scalars().first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    if str(article.author_id) != token_data["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not (article.body or "").strip():
        raise HTTPException(status_code=422, detail="Article body is empty — nothing to format")

    from app.modules.agents.adapters.formateador import run_formateador

    scientific_format = (article.scientific_format.value if article.scientific_format else None) or "apa"
    state = {
        "draft_text": article.body,
        "scientific_format": scientific_format,
        "agent_settings": {},
    }
    result_state = await run_formateador(state)
    formatted = result_state.get("formatted_text") or article.body
    article.body = formatted

    session.add(article)
    await session.commit()
    await session.refresh(article)
    return ArticleResponse.model_validate(article)


