"""
Schemas Pydantic para Version.

Define os schemas de entrada/saída para operações com versões.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VersionBase(BaseModel):
    """Schema base com campos comuns."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    changes_summary: Optional[str] = Field(None, max_length=2000)


class VersionCreate(VersionBase):
    """Schema para criação de nova versão."""

    template_id: int = Field(..., description="ID do template base")
    parent_version_id: Optional[int] = Field(
        None, description="ID da versão pai (null se primeira)"
    )


class VersionResponse(VersionBase):
    """Schema de resposta com todos os dados da versão."""

    id: int
    template_id: int
    parent_version_id: Optional[int]
    version_number: int
    file_path: str
    file_size: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    """Schema para listagem de versões."""

    items: list[VersionResponse]
    total: int


class VersionSummary(BaseModel):
    """Schema resumido para listagens simples."""

    id: int
    name: str
    version_number: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
