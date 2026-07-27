"""Pydantic models for CogniChem API request/response envelopes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: int


class ApiKeyListItem(BaseModel):
    id: str
    name: str
    key_prefix: str | None = None
    scopes: list[str] = Field(default_factory=list)
    created_at: datetime
    last_used_at: datetime | None = None
    rotated_at: datetime | None = None


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyListItem]
    limit: int
    count: int


class ApiKeyCreatedResponse(ApiKeyListItem):
    api_key: str


class JobSubmitRequest(BaseModel):
    job_name: str
    job_type: str
    payload: dict[str, Any]
    resource: str = "default"


class JobSubmitResponse(BaseModel):
    process_id: str


class JobSubmitMultipleResponse(BaseModel):
    process_ids: list[str] = Field(default_factory=list)


class ListJobsResponse(BaseModel):
    job_names: list[str] = Field(default_factory=list)
    job_pids: list[str] = Field(default_factory=list)


class ProcessStatus(BaseModel):
    process_id: str
    status: str
    message: str | None = None


class JobInfoResponse(BaseModel):
    process_id: str
    info: dict[str, Any]


class MessageResponse(BaseModel):
    message: str


class BinaryResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    content: bytes
    filename: str | None = None
    media_type: str | None = None


class InferenceSubmitRequest(BaseModel):
    model_type: str
    model_name: str
    payload: dict[str, Any]


class ListProcessIdsResponse(BaseModel):
    process_ids: list[str] = Field(default_factory=list)


class DataResult(BaseModel):
    data: Any


class UsageLimitsResponse(BaseModel):
    usage_limits: dict[str, Any]


class AuthCheckResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    message: str | None = None
