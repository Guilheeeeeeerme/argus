"""Pydantic schemas for admin API."""

from __future__ import annotations

from datetime import time
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from argus.domain.enums import NotificationChannel, ScheduleDay


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


class CreateLocationRequest(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "UTC"


class LocationResponse(BaseModel):
    id: UUID
    name: str
    address: str | None
    sketch: str | None
    timezone: str

    model_config = {"from_attributes": True}


class CreateCameraRequest(BaseModel):
    name: str
    stream_url: str | None = None
    stream_username: str | None = None
    stream_password: str | None = None
    placement_x: float | None = None
    placement_y: float | None = None


class UpdateCameraRequest(BaseModel):
    name: str | None = None
    stream_url: str | None = None
    stream_username: str | None = None
    stream_password: str | None = None
    placement_x: float | None = None
    placement_y: float | None = None


class CameraResponse(BaseModel):
    id: UUID
    location_id: UUID
    name: str
    stream_url: str | None
    stream_username: str | None
    placement_x: float | None
    placement_y: float | None
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


class CreateRuleSetRequest(BaseModel):
    name: str
    description: str | None = None


class RuleSetResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


class CreateScheduleRequest(BaseModel):
    day_of_week: ScheduleDay
    start_time: time
    end_time: time
    location_id: UUID | None = None


class ScheduleResponse(BaseModel):
    id: UUID
    rule_set_id: UUID
    day_of_week: ScheduleDay
    start_time: time
    end_time: time
    location_id: UUID | None

    model_config = {"from_attributes": True}


class CreateRecipeRequest(BaseModel):
    name: str
    system_prompt: str
    output_schema: dict[str, Any]


class RecipeResponse(BaseModel):
    id: UUID
    rule_set_id: UUID
    name: str
    system_prompt: str
    output_schema: dict[str, Any]
    version: int

    model_config = {"from_attributes": True}


class CreateRuleRequest(BaseModel):
    rule_set_id: UUID
    name: str
    detection_class: str | None = None
    confidence_threshold: float = 0.5
    condition: dict[str, Any]
    severity_weight: int = 1
    region_ids: list[UUID] = Field(default_factory=list)


class UpdateRuleRequest(BaseModel):
    name: str | None = None
    detection_class: str | None = None
    confidence_threshold: float | None = None
    condition: dict[str, Any] | None = None
    severity_weight: int | None = None
    region_ids: list[UUID] | None = None


class RuleResponse(BaseModel):
    id: UUID
    rule_set_id: UUID
    name: str
    detection_class: str | None
    confidence_threshold: float
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
