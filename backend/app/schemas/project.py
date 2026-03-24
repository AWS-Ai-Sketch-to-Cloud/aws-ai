from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.constants import CONTRACT_VERSION


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class ProjectCreateResponse(BaseModel):
    projectId: str
    name: str
    description: str | None = None
    ownerId: str | None = None
    createdAt: str
    contractVersion: Literal["v2"] = CONTRACT_VERSION


class ProjectListItem(BaseModel):
    projectId: str
    name: str
    description: str | None = None
    createdAt: str
    updatedAt: str


class ProjectListResponse(BaseModel):
    items: list[ProjectListItem]
    contractVersion: Literal["v2"] = CONTRACT_VERSION
