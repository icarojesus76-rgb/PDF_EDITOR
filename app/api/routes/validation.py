"""
Endpoints para Validação de Campos.

API REST para validação de campos editáveis com regras avançadas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.validators import ValidationError
from app.schemas.validation_schema import (
    FieldValidationResponse,
    FieldValueValidationRequest,
    FieldValueValidationResponse,
    FieldValuesRequest,
)
from app.services.validation_service import ValidationService
from app.services.template_service import TemplateService
from app.domain.models.field import Field

router = APIRouter(
    prefix="/validation",
    tags=["Validation"],
    responses={
        500: {"description": "Erro interno do servidor"},
        422: {"description": "Erro de validação"},
    },
)


def get_validation_service() -> ValidationService:
    """Factory para injeção de dependência do ValidationService."""
    return ValidationService()


def get_template_service(db: Session = Depends(get_db)) -> TemplateService:
    """Factory para injeção de dependência do TemplateService."""
    return TemplateService(db)


@router.post(
    "/fields",
    response_model=FieldValidationResponse,
    summary="Validar múltiplos campos",
    description="Valida uma lista de campos com base nas configurações fornecidas.",
)
async def validate_fields(
    request: FieldValuesRequest,
    service: ValidationService = Depends(get_validation_service),
) -> FieldValidationResponse:
    """
    Valida múltiplos campos de uma vez.

    Args:
        request: field_configs e field_values

    Returns:
        FieldValidationResponse com resultados por campo
    """
    return service.validate_fields(
        field_configs=request.field_configs,
        field_values=request.field_values,
    )


@router.post(
    "/field",
    response_model=FieldValueValidationResponse,
    summary="Validar um único campo",
    description="Valida um campo individual com suas configurações.",
)
async def validate_single_field(
    request: FieldValueValidationRequest,
    service: ValidationService = Depends(get_validation_service),
) -> FieldValueValidationResponse:
    """
    Valida um único campo.

    Args:
        request: Dados do campo a validar

    Returns:
        FieldValueValidationResponse com resultado
    """
    return service.validate_single_field(request)


@router.post(
    "/template/{template_id}/fields",
    response_model=FieldValidationResponse,
    summary="Validar campos de um template",
    description="Valida os valores com base na configuração dos campos do template.",
)
async def validate_template_fields(
    template_id: int,
    field_values: dict[str, str],
    service: ValidationService = Depends(get_validation_service),
    template_service: TemplateService = Depends(get_template_service),
) -> FieldValidationResponse:
    """
    Valida valores contra a configuração de campos de um template.

    Args:
        template_id: ID do template
        field_values: Valores a validar {field_name: value}

    Returns:
        FieldValidationResponse com resultados
    """
    try:
        template = template_service.get_template(template_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Template não encontrado", "template_id": template_id},
        )

    fields = (
        template_service.db.query(Field)
        .filter(Field.template_id == template_id, Field.is_active == True)
        .all()
    )

    if not fields:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Nenhum campo ativo encontrado para este template"},
        )

    field_configs = [
        {
            "name": f.name,
            "label": f.label,
            "field_type": f.field_type,
            "required": f.required,
            "max_length": f.max_length,
            "width": f.width,
            "height": f.height,
            "font_size": f.font_size,
            "font_family": f.font_family,
        }
        for f in fields
    ]

    from app.schemas.validation_schema import FieldValidationConfig

    configs = [FieldValidationConfig(**config) for config in field_configs]

    return service.validate_fields(
        field_configs=configs,
        field_values=field_values,
    )
