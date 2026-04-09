"""
Schemas para Preview de PDF.

Define schemas de requisição e resposta para operações de preview.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PreviewCreateRequest(BaseModel):
    """Schema para criação de preview."""

    template_id: int = Field(..., description="ID do template base")
    field_values: dict[str, str] = Field(..., description="Valores dos campos")
    created_by: Optional[str] = Field(
        None, max_length=100, description="Usuário responsável"
    )
    generate_images: bool = Field(True, description="Gerar imagens por página")
    validate_fields: bool = Field(
        True, description="Validar campos antes de criar preview"
    )
    skip_validation: bool = Field(
        False, description="Pular validação e criar preview mesmo com erros"
    )


class PreviewConfirmRequest(BaseModel):
    """Schema para confirmação de preview."""

    version_name: str = Field(
        ..., min_length=1, max_length=255, description="Nome da versão"
    )
    description: Optional[str] = Field(None, description="Descrição da versão")


class PreviewResponse(BaseModel):
    """Schema de resposta para preview."""

    id: int
    template_id: int
    field_data: dict
    pdf_path: str
    image_paths: Optional[list[str]]
    file_size: int
    created_by: Optional[str]
    status: str
    expires_at: str
    created_at: str
    confirmed_at: Optional[str]
    version_id: Optional[int]
    is_expired: bool
    is_active: bool

    class Config:
        from_attributes = True


class PreviewTokenResponse(BaseModel):
    """Schema de resposta com token após criação."""

    preview: PreviewResponse
    token: str
    message: str = "Preview criado com sucesso"


class PreviewConfirmResponse(BaseModel):
    """Schema de resposta após confirmação."""

    version_id: int
    version_number: int
    message: str = "Preview confirmado - versão oficial criada"


class PreviewCancelResponse(BaseModel):
    """Schema de resposta após cancelamento."""

    preview_id: int
    message: str = "Preview cancelado"


class PreviewListResponse(BaseModel):
    """Schema para listagem de previews."""

    items: list[PreviewResponse]
    total: int


class PreviewImageResponse(BaseModel):
    """Schema para informações de imagem de preview."""

    preview_id: int
    page: int
    image_url: str


class FieldValidationError(BaseModel):
    """Erro de validação de campo."""

    field_name: str
    code: str
    message: str
    value: Optional[str] = None


class PreviewValidationResult(BaseModel):
    """Resultado da validação dos campos do preview."""

    is_valid: bool
    errors: list[FieldValidationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    formatted_values: dict[str, str] = Field(default_factory=dict)
