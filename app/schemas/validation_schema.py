"""
Schemas para Validação de Campos.

Define schemas para validação de valores de campos editáveis.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class FieldValidationConfig(BaseModel):
    """Configuração de validação de um campo."""

    name: str = Field(..., description="Nome único do campo")
    label: Optional[str] = Field(None, description="Label exibido ao usuário")
    field_type: str = Field(default="text", description="Tipo do campo")
    required: bool = Field(default=False, description="Se o campo é obrigatório")
    max_length: Optional[int] = Field(None, description="Limite máximo de caracteres")
    min_length: Optional[int] = Field(None, description="Limite mínimo de caracteres")
    width: Optional[float] = Field(
        None, description="Largura do campo para detecção de overflow"
    )
    height: Optional[float] = Field(
        None, description="Altura do campo para detecção de overflow"
    )
    font_size: Optional[float] = Field(None, description="Tamanho da fonte")
    font_family: Optional[str] = Field(None, description="Família da fonte")


class FieldValidationItem(BaseModel):
    """Resultado da validação de um campo."""

    field_name: str
    is_valid: bool
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    formatted_value: Optional[str] = None
    original_value: Optional[str] = None


class FieldValuesRequest(BaseModel):
    """Requisição para validar valores de campos."""

    field_configs: list[FieldValidationConfig] = Field(
        ..., description="Configurações dos campos a validar"
    )
    field_values: dict[str, str] = Field(
        ..., description="Valores dos campos {field_name: value}"
    )


class FieldValidationResponse(BaseModel):
    """Resposta da validação de campos."""

    is_valid: bool
    total_fields: int
    valid_fields: int
    invalid_fields: int
    field_results: list[FieldValidationItem]
    formatted_values: dict[str, str] = Field(
        default_factory=dict, description="Valores formatados após validação"
    )


class FieldValueValidationRequest(BaseModel):
    """Requisição para validar um único campo."""

    field_name: str = Field(..., description="Nome do campo")
    field_type: str = Field(default="text", description="Tipo do campo")
    value: Optional[str] = Field(None, description="Valor a validar")
    required: bool = Field(default=False, description="Se o campo é obrigatório")
    max_length: Optional[int] = Field(None, description="Limite máximo de caracteres")
    min_length: Optional[int] = Field(None, description="Limite mínimo de caracteres")
    label: Optional[str] = Field(None, description="Label do campo")
    width: Optional[float] = Field(None, description="Largura do campo")
    height: Optional[float] = Field(None, description="Altura do campo")
    font_size: Optional[float] = Field(None, description="Tamanho da fonte")
    font_family: Optional[str] = Field(None, description="Família da fonte")


class FieldValueValidationResponse(BaseModel):
    """Resposta da validação de um único campo."""

    is_valid: bool
    field_name: str
    errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    formatted_value: Optional[str] = None
    original_value: Optional[str] = None


class FieldFormatRequest(BaseModel):
    """Requisição para formatar um campo."""

    field_name: str
    field_type: str
    value: str


class FieldFormatResponse(BaseModel):
    """Resposta da formatação de um campo."""

    field_name: str
    original_value: str
    formatted_value: Optional[str]
    format_applied: bool
