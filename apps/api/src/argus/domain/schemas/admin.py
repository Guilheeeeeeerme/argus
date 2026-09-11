"""Pydantic schemas for admin API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateCompanyRequest(BaseModel):
    name: str
    slug: str = Field(max_length=63)
    aggregation_window_secs: int = 300


class UpdateCompanyRequest(BaseModel):
    name: str | None = None
    slug: str | None = Field(default=None, max_length=63)
    aggregation_window_secs: int | None = None


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    aggregation_window_secs: int

    model_config = {"from_attributes": True}


class AssignCompanyAdminRequest(BaseModel):
    email: str
    password: str | None = None
    idp_subject: str | None = None


class CreateCompanyUserRequest(BaseModel):
    company_id: UUID | None = None
    email: str
    password: str | None = None
    idp_subject: str | None = None
    role: str = "manager"


class UpdateCompanyUserRequest(BaseModel):
    email: str | None = None
    company_id: UUID | None = None
    role: str | None = None
    password: str | None = None


class CompanyUserResponse(BaseModel):
    id: UUID
    company_id: UUID | None
    email: str
    idp_subject: str | None
    role: str

    model_config = {"from_attributes": True}


class CreateEstablishmentRequest(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "UTC"
    active: bool = True


class UpdateEstablishmentRequest(BaseModel):
    name: str | None = None
    address: str | None = None
    timezone: str | None = None
    active: bool | None = None


class EstablishmentResponse(BaseModel):
    id: UUID
    name: str
    address: str | None
    timezone: str
    active: bool = True

    model_config = {"from_attributes": True}


class CreateCameraRequest(BaseModel):
    name: str
    stream_url: str | None = None
    stream_username: str | None = None
    stream_password: str | None = None
    is_active: bool = True


class UpdateCameraRequest(BaseModel):
    name: str | None = None
    stream_url: str | None = None
    stream_username: str | None = None
    stream_password: str | None = None
    is_active: bool | None = None


class CameraResponse(BaseModel):
    id: UUID
    establishment_id: UUID
    name: str
    stream_url: str | None
    stream_username: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class CreatePromptSetRequest(BaseModel):
    name: str
    prompts: list["CreatePromptRequest"] = Field(default_factory=list)


class UpdatePromptSetRequest(BaseModel):
    name: str | None = None


class PromptSetResponse(BaseModel):
    id: UUID
    camera_id: UUID
    name: str
    prompts: list["PromptResponse"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CreatePromptRequest(BaseModel):
    text: str
    enabled: bool = True
    sort_order: int = 0


class UpdatePromptRequest(BaseModel):
    text: str | None = None
    enabled: bool | None = None
    sort_order: int | None = None


class PromptResponse(BaseModel):
    id: UUID
    prompt_set_id: UUID
    text: str
    enabled: bool
    sort_order: int

    model_config = {"from_attributes": True}


class CreateWebhookEndpointRequest(BaseModel):
    name: str
    establishment_id: UUID | None = None
    active: bool = True


class UpdateWebhookEndpointRequest(BaseModel):
    name: str | None = None
    establishment_id: UUID | None = None
    active: bool | None = None


class WebhookEndpointResponse(BaseModel):
    id: UUID
    name: str
    establishment_id: UUID | None
    active: bool
    token: str | None = None  # raw token only on create/rotate

    model_config = {"from_attributes": True}


class InboundWebhookRequest(BaseModel):
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    establishment_id: UUID | None = None
    camera_id: UUID | None = None


class ContextEventResponse(BaseModel):
    id: UUID
    webhook_id: UUID
    establishment_id: UUID | None
    camera_id: UUID | None
    kind: str
    payload: dict[str, Any]
    received_at: datetime

    model_config = {"from_attributes": True}
