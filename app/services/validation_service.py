"""
Serviço de Validação de Campos.

Fornece endpoints API para validação de campos editáveis.
"""

from typing import Optional

from app.core.validators import (
    FieldValidationService,
    ValidationResult,
    ValidationError,
)
from app.schemas.validation_schema import (
    FieldValidationConfig,
    FieldValidationItem,
    FieldValidationResponse,
    FieldValueValidationRequest,
    FieldValueValidationResponse,
)


class ValidationService:
    """Serviço para validação de campos via API."""

    def __init__(self):
        self.validator = FieldValidationService()

    def validate_fields(
        self,
        field_configs: list[FieldValidationConfig],
        field_values: dict[str, str],
    ) -> FieldValidationResponse:
        """
        Valida múltiplos campos.

        Args:
            field_configs: Lista de configurações dos campos
            field_values: Dicionário de valores {field_name: value}

        Returns:
            FieldValidationResponse com resultados
        """
        config_dicts = [config.model_dump() for config in field_configs]

        is_valid, errors, formatted_values = self.validator.validate_fields(
            field_configs=config_dicts,
            field_values=field_values,
        )

        error_map: dict[str, list[dict]] = {}
        for error in errors:
            if error.field_name not in error_map:
                error_map[error.field_name] = []
            error_map[error.field_name].append(
                {
                    "code": error.code,
                    "message": error.message,
                    "value": error.value,
                }
            )

        field_results: list[FieldValidationItem] = []

        for config in field_configs:
            field_name = config.name
            original_value = field_values.get(field_name)
            field_errors = error_map.get(field_name, [])

            field_result = FieldValidationItem(
                field_name=field_name,
                is_valid=len(field_errors) == 0,
                errors=field_errors,
                formatted_value=formatted_values.get(field_name),
                original_value=original_value,
            )
            field_results.append(field_result)

        return FieldValidationResponse(
            is_valid=is_valid,
            total_fields=len(field_configs),
            valid_fields=len([r for r in field_results if r.is_valid]),
            invalid_fields=len([r for r in field_results if not r.is_valid]),
            field_results=field_results,
            formatted_values=formatted_values,
        )

    def validate_single_field(
        self,
        request: FieldValueValidationRequest,
    ) -> FieldValueValidationResponse:
        """
        Valida um único campo.

        Args:
            request: Dados do campo a validar

        Returns:
            FieldValueValidationResponse com resultado
        """
        result = self.validator.validate_field(
            field_name=request.field_name,
            field_type=request.field_type,
            value=request.value,
            required=request.required,
            max_length=request.max_length,
            min_length=request.min_length,
            label=request.label,
            field_width=request.width,
            field_height=request.height,
            font_size=request.font_size,
            font_family=request.font_family,
        )

        errors = [
            {
                "code": error.code,
                "message": error.message,
                "value": error.value,
            }
            for error in result.errors
        ]

        return FieldValueValidationResponse(
            is_valid=result.is_valid,
            field_name=request.field_name,
            errors=errors,
            warnings=result.warnings,
            formatted_value=result.formatted_value,
            original_value=request.value,
        )
