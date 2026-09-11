"""PromptSet and Prompt CRUD nested under cameras."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from argus.api.deps import get_company_db, require_role
from argus.core.auth import AuthContext
from argus.domain.enums import UserRole
from argus.domain.models import Camera, Prompt, PromptSet
from argus.domain.schemas.admin import (
    CreatePromptRequest,
    CreatePromptSetRequest,
    PromptResponse,
    PromptSetResponse,
    UpdatePromptRequest,
    UpdatePromptSetRequest,
)

router = APIRouter(prefix="/companies/{company_id}", tags=["admin-prompt-sets"])

_MANAGER_PLUS = (UserRole.MANAGER, UserRole.ROOT, UserRole.ADMIN)


async def _get_camera(session: AsyncSession, company_id: UUID, camera_id: UUID) -> Camera:
    camera = await session.scalar(
        select(Camera).where(Camera.id == camera_id, Camera.company_id == company_id)
    )
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera


def _prompt_set_response(prompt_set: PromptSet) -> PromptSetResponse:
    return PromptSetResponse(
        id=prompt_set.id,
        camera_id=prompt_set.camera_id,
        name=prompt_set.name,
        prompts=[
            PromptResponse(
                id=p.id,
                prompt_set_id=p.prompt_set_id,
                text=p.text,
                enabled=p.enabled,
                sort_order=p.sort_order,
            )
            for p in sorted(prompt_set.prompts, key=lambda x: x.sort_order)
        ],
    )


@router.get("/cameras/{camera_id}/prompt-sets", response_model=list[PromptSetResponse])
async def list_prompt_sets(
    company_id: UUID,
    camera_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> list[PromptSetResponse]:
    await _get_camera(session, company_id, camera_id)
    rows = list(
        (
            await session.scalars(
                select(PromptSet)
                .where(PromptSet.camera_id == camera_id, PromptSet.company_id == company_id)
                .options(selectinload(PromptSet.prompts))
                .order_by(PromptSet.name)
            )
        ).all()
    )
    return [_prompt_set_response(ps) for ps in rows]


@router.post(
    "/cameras/{camera_id}/prompt-sets",
    response_model=PromptSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt_set(
    company_id: UUID,
    camera_id: UUID,
    body: CreatePromptSetRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> PromptSetResponse:
    await _get_camera(session, company_id, camera_id)
    prompt_set = PromptSet(company_id=company_id, camera_id=camera_id, name=body.name)
    session.add(prompt_set)
    await session.flush()
    for i, prompt_body in enumerate(body.prompts):
        session.add(
            Prompt(
                company_id=company_id,
                prompt_set_id=prompt_set.id,
                text=prompt_body.text,
                enabled=prompt_body.enabled,
                sort_order=prompt_body.sort_order if prompt_body.sort_order else i,
            )
        )
    await session.flush()
    await session.refresh(prompt_set, attribute_names=["prompts"])
    return _prompt_set_response(prompt_set)


@router.patch("/prompt-sets/{prompt_set_id}", response_model=PromptSetResponse)
async def update_prompt_set(
    company_id: UUID,
    prompt_set_id: UUID,
    body: UpdatePromptSetRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> PromptSetResponse:
    prompt_set = await session.scalar(
        select(PromptSet)
        .where(PromptSet.id == prompt_set_id, PromptSet.company_id == company_id)
        .options(selectinload(PromptSet.prompts))
    )
    if prompt_set is None:
        raise HTTPException(status_code=404, detail="PromptSet not found")
    if body.name is not None:
        prompt_set.name = body.name
    await session.flush()
    return _prompt_set_response(prompt_set)


@router.delete("/prompt-sets/{prompt_set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt_set(
    company_id: UUID,
    prompt_set_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> None:
    prompt_set = await session.scalar(
        select(PromptSet).where(PromptSet.id == prompt_set_id, PromptSet.company_id == company_id)
    )
    if prompt_set is None:
        raise HTTPException(status_code=404, detail="PromptSet not found")
    await session.delete(prompt_set)


@router.post(
    "/prompt-sets/{prompt_set_id}/prompts",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    company_id: UUID,
    prompt_set_id: UUID,
    body: CreatePromptRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Prompt:
    prompt_set = await session.scalar(
        select(PromptSet).where(PromptSet.id == prompt_set_id, PromptSet.company_id == company_id)
    )
    if prompt_set is None:
        raise HTTPException(status_code=404, detail="PromptSet not found")
    prompt = Prompt(
        company_id=company_id,
        prompt_set_id=prompt_set_id,
        text=body.text,
        enabled=body.enabled,
        sort_order=body.sort_order,
    )
    session.add(prompt)
    await session.flush()
    return prompt


@router.patch("/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    company_id: UUID,
    prompt_id: UUID,
    body: UpdatePromptRequest,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> Prompt:
    prompt = await session.scalar(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.company_id == company_id)
    )
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    for field in ("text", "enabled", "sort_order"):
        value = getattr(body, field)
        if value is not None:
            setattr(prompt, field, value)
    await session.flush()
    return prompt


@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    company_id: UUID,
    prompt_id: UUID,
    session: AsyncSession = Depends(get_company_db),
    _auth: AuthContext = Depends(require_role(*_MANAGER_PLUS)),
) -> None:
    prompt = await session.scalar(
        select(Prompt).where(Prompt.id == prompt_id, Prompt.company_id == company_id)
    )
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    await session.delete(prompt)
