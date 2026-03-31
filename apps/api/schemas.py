from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    image_url: str
    status: str
    created_at: datetime


class UploadResponse(BaseModel):
    project_id: UUID
    image_url: str
    status: str


class ProjectDetailResponse(BaseModel):
    id: UUID
    image_url: str
    status: str
    created_at: datetime
    layers: list[dict] = []
    psd_url: str | None = None


class UsageResponse(BaseModel):
    remaining: int
    plan: str
    total: int
