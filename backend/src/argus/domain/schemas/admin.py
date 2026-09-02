"""Pydantic schemas for admin API."""

from __future__ import annotations

from datetime import time
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from argus.domain.enums import NotificationChannel, ScheduleDay


class CreateTenantRequest(BaseModel):
    name: str
    slug: str = Field(max_length=63)
    aggregation_window_secs: int = 300


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    aggregation_window_secs: int

    model_config = {"from_attributes": True}


class AssignTenantAdminRequest(BaseModel):
    email: str
    idp_subject: str


class TenantUserResponse(BaseModel):
    id: UUID
    tenant_id: UUID | None
    email: str
    idp_subject: str
    role: str

    model_config = {"from_attributes": True}


class CreateMarketRequest(BaseModel):
    name: str
    timezone: str = "UTC"


class MarketResponse(BaseModel):
    id: UUID
    name: str
    timezone: str

    model_config = {"from_attributes": True}


class CreateCameraRequest(BaseModel):
    name: str
    edge_device_id: str


class CameraResponse(BaseModel):
    id: UUID
    market_id: UUID
    name: str
    edge_device_id: str
    is_active: bool

    model_config = {"from_attributes": True}


class CreateRegionRequest(BaseModel):
    name: str
    polygon: list[dict[str, float]]


class RegionResponse(BaseModel):
    id: UUID
    camera_id: UUID
    name: str
    polygon: list[dict[str, float]]

    model_config = {"from_attributes": True}


class CreateContextModeRequest(BaseModel):
    name: str
    description: str | None = None


class ContextModeResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class CreateScheduleRequest(BaseModel):
    day_of_week: ScheduleDay
    start_time: time
    end_time: time
    market_id: UUID | None = None


class ScheduleResponse(BaseModel):
    id: UUID
    context_mode_id: UUID
    day_of_week: ScheduleDay
    start_time: time
    end_time: time
    market_id: UUID | None

    model_config = {"from_attributes": True}


class CreateLensRequest(BaseModel):
    name: str
    system_prompt: str
    output_schema: dict[str, Any]


class LensResponse(BaseModel):
    id: UUID
    context_mode_id: UUID
    name: str
    system_prompt: str
    output_schema: dict[str, Any]
    version: int

    model_config = {"from_attributes": True}


class CreateRuleRequest(BaseModel):
    context_mode_id: UUID
    name: str
    condition: dict[str, Any]
    severity_weight: int = 1
    region_ids: list[UUID] = Field(default_factory=list)


class RuleResponse(BaseModel):
    id: UUID
    context_mode_id: UUID
    name: str
    condition: dict[str, Any]
    severity_weight: int
    region_ids: list[UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class CreateNotificationConfigRequest(BaseModel):
    channel: NotificationChannel
    recipient: str


class NotificationConfigResponse(BaseModel):
    id: UUID
    channel: NotificationChannel
    recipient: str
    is_active: bool

    model_config = {"from_attributes": True}


class NotificationDeliveryResponse(BaseModel):
    id: UUID
    decision_id: UUID
    channel: NotificationChannel
    status: str
    provider_message_id: str | None
    error_detail: str | None

    model_config = {"from_attributes": True}
