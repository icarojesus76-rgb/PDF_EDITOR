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


class VersionCreateRequest(BaseModel):
    """Schema para criação de versão via API."""

    name: str = Field(..., min_length=1, max_length=255, description="Nome da versão")
    field_data: dict = Field(..., description="Dados do preenchimento")
    created_by: Optional[str] = Field(
        None, max_length=100, description="Usuário responsável"
    )
    description: Optional[str] = Field(None, description="Descrição da versão")
    observation: Optional[str] = Field(None, description="Observação opcional")
    parent_version_id: Optional[int] = Field(None, description="ID da versão pai")


class VersionUpdateRequest(BaseModel):
    """Schema para atualização de versão."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    observation: Optional[str] = None


class VersionStatusUpdate(BaseModel):
    """Schema para atualização de status."""

    status: str = Field(..., description="Novo status")
    observation: Optional[str] = Field(None, description="Observação")


class VersionResponse(BaseModel):
    """Schema de resposta com todos os dados da versão."""

    id: int
    template_id: int
    parent_version_id: Optional[int]
    version_number: int
    name: str
    description: Optional[str]
    file_path: str
    file_size: int
    checksum: str
    field_data: Optional[dict]
    created_by: Optional[str]
    observation: Optional[str]
    changes_summary: Optional[str]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    file_exists: bool

    class Config:
        from_attributes = True


class VersionListResponse(BaseModel):
    """Schema para listagem de versões com paginação."""

    items: list[VersionResponse]
    total: int
    limit: int
    offset: int


class VersionSummary(BaseModel):
    """Schema resumido para listagens simples."""

    id: int
    name: str
    version_number: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class VersionStatistics(BaseModel):
    """Schema para estatísticas de versionamento."""

    template_id: int
    total_versions: int
    active_versions: int
    archived_versions: int
    superseded_versions: int
    total_size_bytes: int
    latest_version: Optional[int]


class VersionLineageItem(BaseModel):
    """Item na linhagem de versão."""

    id: int
    version_number: int
    name: str
    created_at: str
    created_by: Optional[str]


class VersionDownloadResponse(BaseModel):
    """Schema para download de versão."""

    id: int
    version_number: int
    name: str
    checksum: str
    file_size: int
    content_type: str = "application/pdf"


class VersionVerifyChecksumResponse(BaseModel):
    """Schema para resposta de verificação de checksum."""

    version_id: int
    is_valid: bool
    stored_checksum: str
    computed_checksum: Optional[str]
    message: str
