"""
Schemas Pydantic para Campos Editáveis (Field).

Define os schemas de entrada/saída para operações com campos.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator

from app.domain.models.field import FieldType, FieldAlignment


class FieldBase(BaseModel):
    """Schema base com campos comuns."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nome único do campo (identificador)",
    )
    label: Optional[str] = Field(
        None, max_length=255, description="Label exibido ao usuário"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Descrição/ajuda do campo"
    )

    # Posicionamento
    page: int = Field(default=0, ge=0, description="Número da página (0-indexed)")
    x: float = Field(..., ge=0, description="Posição X (canto superior esquerdo)")
    y: float = Field(..., ge=0, description="Posição Y (canto superior esquerdo)")
    width: float = Field(..., gt=0, description="Largura do campo")
    height: float = Field(..., gt=0, description="Altura do campo")

    # Aparência
    field_type: str = Field(
        default=FieldType.TEXT.value,
        description="Tipo do campo: text, number, date, multiline, checkbox",
    )
    font_family: Optional[str] = Field(
        default="Helvetica", max_length=100, description="Família da fonte"
    )
    font_size: Optional[float] = Field(
        default=12.0, gt=0, description="Tamanho da fonte em pontos"
    )
    alignment: Optional[str] = Field(
        default=FieldAlignment.LEFT.value,
        description="Alinhamento: left, center, right",
    )
    color: Optional[str] = Field(
        default="#000000",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Cor em hexadecimal (ex: #000000)",
    )
    background_color: Optional[str] = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Cor de fundo em hexadecimal"
    )

    # Comportamento
    required: bool = Field(default=False, description="Campo obrigatório")
    default_value: Optional[str] = Field(
        None, max_length=500, description="Valor padrão"
    )
    placeholder: Optional[str] = Field(
        None, max_length=255, description="Texto de placeholder"
    )
    max_length: Optional[int] = Field(None, ge=1, description="Máximo de caracteres")
    order: int = Field(default=0, ge=0, description="Ordem de exibição/navegação")
    is_active: bool = Field(default=True, description="Campo ativo/inativo")

    @field_validator("field_type")
    @classmethod
    def validate_field_type(cls, v):
        """Valida tipo de campo."""
        allowed = [t.value for t in FieldType]
        if v not in allowed:
            raise ValueError(f"Tipo deve ser um de: {', '.join(allowed)}")
        return v

    @field_validator("alignment")
    @classmethod
    def validate_alignment(cls, v):
        """Valida alinhamento."""
        if v is None:
            return v
        allowed = [a.value for a in FieldAlignment]
        if v not in allowed:
            raise ValueError(f"Alinhamento deve ser um de: {', '.join(allowed)}")
        return v


class FieldCreate(FieldBase):
    """Schema para criação de campo."""

    template_id: int = Field(..., description="ID do template associado")


class FieldUpdate(BaseModel):
    """Schema para atualização parcial de campo."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    label: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    page: Optional[int] = Field(None, ge=0)
    x: Optional[float] = Field(None, ge=0)
    y: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    field_type: Optional[str] = None
    font_family: Optional[str] = Field(None, max_length=100)
    font_size: Optional[float] = Field(None, gt=0)
    alignment: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    required: Optional[bool] = None
    default_value: Optional[str] = Field(None, max_length=500)
    placeholder: Optional[str] = Field(None, max_length=255)
    max_length: Optional[int] = Field(None, ge=1)
    order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class FieldResponse(FieldBase):
    """Schema de resposta completo."""

    id: int
    template_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    bounds: dict

    class Config:
        from_attributes = True


class FieldListResponse(BaseModel):
    """Schema para listagem de campos."""

    items: List[FieldResponse]
    total: int
    page: int
    page_size: int


class FieldSummary(BaseModel):
    """Schema resumido para listagens."""

    id: int
    name: str
    label: Optional[str]
    page: int
    field_type: str
    required: bool
    order: int
    is_active: bool

    class Config:
        from_attributes = True


class FieldBounds(BaseModel):
    """Schema para limites/bounding box do campo."""

    x: float
    y: float
    x2: float
    y2: float
    width: float
    height: float


class FieldOverlapCheck(BaseModel):
    """Schema para verificação de sobreposição."""

    field_id: int
    field_name: str
    overlap_area: float
    overlap_percentage: float


class TemplateFieldsResponse(BaseModel):
    """Schema para retornar todos os campos de um template."""

    template_id: int
    template_name: str
    total_fields: int
    fields_by_page: dict  # {page_number: [FieldSummary]}
    fields: List[FieldResponse]


class FieldPositionUpdate(BaseModel):
    """Schema para atualização rápida de posição (drag & drop)."""

    x: float = Field(..., ge=0)
    y: float = Field(..., ge=0)
    width: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    page: Optional[int] = Field(None, ge=0)
