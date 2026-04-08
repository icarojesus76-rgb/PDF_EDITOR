"""
Schemas Pydantic para Template.

Define os schemas de entrada/saída para operações com templates.
Usado para validação de dados e documentação automática da API (OpenAPI).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TemplateBase(BaseModel):
    """Schema base com campos comuns."""

    name: str = Field(..., min_length=1, max_length=255, description="Nome do template")
    description: Optional[str] = Field(
        default=None, max_length=1000, description="Descrição opcional do template"
    )


class TemplateCreate(TemplateBase):
    """Schema para criação de template (via upload)."""

    pass  # Campos vêm do arquivo uploadado


class TemplateResponse(TemplateBase):
    """Schema de resposta com todos os dados do template."""

    id: int = Field(..., description="ID único do template")
    original_filename: str = Field(..., description="Nome original do arquivo")
    file_path: str = Field(..., description="Caminho do arquivo no storage")
    file_size: int = Field(..., description="Tamanho em bytes")
    checksum: str = Field(..., description="Hash SHA256 para verificação")
    status: str = Field(..., description="Status atual: active, archived, deleted")
    created_at: datetime = Field(..., description="Data de criação")
    updated_at: Optional[datetime] = Field(None, description="Data de atualização")
    version_count: int = Field(..., description="Quantidade de versões geradas")

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema para listagem de templates."""

    items: list[TemplateResponse]
    total: int
    page: int
    page_size: int


class TemplateSummary(BaseModel):
    """Schema resumido para listagens simples."""

    id: int
    name: str
    status: str
    created_at: datetime
    version_count: int

    class Config:
        from_attributes = True
