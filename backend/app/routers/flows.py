"""Flows router: CRUD for saved visual LangGraph flows."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    SavedFlowModel, CreateSavedFlowDTO, UpdateSavedFlowDTO, SavedFlowResponse, UserRole
)
from app.database import get_session
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/v1/flows", tags=["flows"])


@router.get("", response_model=list[SavedFlowResponse])
async def list_flows(
    project_id: UUID | None = None,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List saved flows. Admins and redactors see all; others see only their own.
    Optionally scoped to a project via project_id query param."""
    is_admin = token_data.get("role") == UserRole.ADMIN
    is_redactor = token_data.get("role") == UserRole.REDACTOR
    stmt = select(SavedFlowModel) if (is_admin or is_redactor) else select(SavedFlowModel).where(SavedFlowModel.author_id == UUID(token_data["user_id"]))
    if project_id is not None:
        stmt = stmt.where(SavedFlowModel.project_id == project_id)
    result = await session.execute(stmt)
    flows = result.scalars().all()
    return [SavedFlowResponse.model_validate(flow) for flow in flows]


@router.post("", response_model=SavedFlowResponse, status_code=201)
async def create_flow(
    req: CreateSavedFlowDTO,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Save a new visual flow."""
    flow = SavedFlowModel(
        name=req.name,
        author_id=UUID(token_data["user_id"]),
        project_id=req.project_id,
        nodes=req.nodes,
        edges=req.edges,
        flow_sequence=req.flow_sequence
    )
    session.add(flow)
    await session.commit()
    await session.refresh(flow)
    return SavedFlowResponse.model_validate(flow)


@router.get("/{flow_id}", response_model=SavedFlowResponse)
async def get_flow(
    flow_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a saved flow by ID. Admins and redactors can access any flow."""
    is_admin = token_data.get("role") == UserRole.ADMIN
    is_redactor = token_data.get("role") == UserRole.REDACTOR
    stmt = select(SavedFlowModel).where(SavedFlowModel.id == flow_id) if (is_admin or is_redactor) else select(SavedFlowModel).where(
        SavedFlowModel.id == flow_id,
        SavedFlowModel.author_id == UUID(token_data["user_id"])
    )
    result = await session.execute(stmt)
    flow = result.scalars().first()
    if not flow:
        raise HTTPException(status_code=404, detail="Saved flow not found")
    return SavedFlowResponse.model_validate(flow)


@router.put("/{flow_id}", response_model=SavedFlowResponse)
async def update_flow(
    flow_id: UUID,
    req: UpdateSavedFlowDTO,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a saved flow. Admins and redactors can update any flow."""
    is_admin = token_data.get("role") == UserRole.ADMIN
    is_redactor = token_data.get("role") == UserRole.REDACTOR
    stmt = select(SavedFlowModel).where(SavedFlowModel.id == flow_id) if (is_admin or is_redactor) else select(SavedFlowModel).where(
        SavedFlowModel.id == flow_id,
        SavedFlowModel.author_id == UUID(token_data["user_id"])
    )
    result = await session.execute(stmt)
    flow = result.scalars().first()
    if not flow:
        raise HTTPException(status_code=404, detail="Saved flow not found")

    if req.name is not None:
        flow.name = req.name
    if req.nodes is not None:
        flow.nodes = req.nodes
    if req.edges is not None:
        flow.edges = req.edges
    if req.flow_sequence is not None:
        flow.flow_sequence = req.flow_sequence

    session.add(flow)
    await session.commit()
    await session.refresh(flow)
    return SavedFlowResponse.model_validate(flow)


@router.delete("/{flow_id}", status_code=204)
async def delete_flow(
    flow_id: UUID,
    token_data=Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a saved flow. Admins and redactors can delete any flow."""
    is_admin = token_data.get("role") == UserRole.ADMIN
    is_redactor = token_data.get("role") == UserRole.REDACTOR
    stmt = select(SavedFlowModel).where(SavedFlowModel.id == flow_id) if (is_admin or is_redactor) else select(SavedFlowModel).where(
        SavedFlowModel.id == flow_id,
        SavedFlowModel.author_id == UUID(token_data["user_id"])
    )
    result = await session.execute(stmt)
    flow = result.scalars().first()
    if not flow:
        raise HTTPException(status_code=404, detail="Saved flow not found")

    await session.delete(flow)
    await session.commit()
    return None
