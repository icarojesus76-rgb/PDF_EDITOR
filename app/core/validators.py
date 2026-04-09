"""
Módulo de Validação de Campos Editáveis.

Fornece validações avançadas para campos de formulário com suporte a:
- Campos obrigatórios
- Limite de caracteres
- Tipo numérico
- Tipo data
- Máscara de CPF/CNPJ
- Texto multi-linha com limite visual
- Detecção de overflow
- Normalização de espaços
- Formatação automática por tipo
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ValidationError:
    """Erro de validação individual."""

    field_name: str
    message: str
    code: str
    value: Optional[str] = None


@dataclass
class ValidationResult:
    """Resultado da validação de um campo."""

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    formatted_value: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    def add_error(
        self, field_name: str, message: str, code: str, value: Optional[str] = None
    ):
        self.is_valid = False
        self.errors.append(ValidationError(field_name, message, code, value))

    def add_warning(self, message: str):
        self.warnings.append(message)


class FieldValidator:
    """
    Validador de campos editáveis.

    Valida e formata valores de acordo com a configuração do campo.
    """

    CPF_PATTERN = re.compile(r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$")
    CNPJ_PATTERN = re.compile(r"^\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}$")
    CPF_DIGITS = re.compile(r"\d")
    CNPJ_DIGITS = re.compile(r"\d")

    DATE_FORMATS = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
    ]

    @staticmethod
    def validate_required(
        value: Optional[str], field_name: str, label: Optional[str] = None
    ) -> ValidationResult:
        """Valida se campo obrigatório foi preenchido."""
        result = ValidationResult(is_valid=True)

        display_name = label or field_name

        if value is None or value.strip() == "":
            result.add_error(
                field_name=field_name,
                message=f"Campo '{display_name}' é obrigatório",
                code="REQUIRED_FIELD",
                value=value,
            )

        return result

    @staticmethod
    def validate_max_length(
        value: Optional[str],
        field_name: str,
        max_length: int,
        label: Optional[str] = None,
    ) -> ValidationResult:
        """Valida limite máximo de caracteres."""
        result = ValidationResult(is_valid=True)

        if value is None:
            return result

        display_name = label or field_name

        if len(value) > max_length:
            result.add_error(
                field_name=field_name,
                message=f"Campo '{display_name}' excede o limite de {max_length} caracteres (atual: {len(value)})",
                code="MAX_LENGTH_EXCEEDED",
                value=value,
            )

        return result

    @staticmethod
    def validate_min_length(
        value: Optional[str],
        field_name: str,
        min_length: int,
        label: Optional[str] = None,
    ) -> ValidationResult:
        """Valida limite mínimo de caracteres."""
        result = ValidationResult(is_valid=True)

        if value is None:
            return result

        display_name = label or field_name

        if len(value) < min_length:
            result.add_error(
                field_name=field_name,
                message=f"Campo '{display_name}' deve ter pelo menos {min_length} caracteres",
                code="MIN_LENGTH_NOT_MET",
                value=value,
            )

        return result

    @staticmethod
    def validate_number(
        value: Optional[str], field_name: str, label: Optional[str] = None
    ) -> ValidationResult:
        """Valida se o valor é numérico válido."""
        result = ValidationResult(is_valid=True)

        if value is None or value.strip() == "":
            return result

        display_name = label or field_name
        clean_value = value.strip().replace(",", ".")

        try:
            float(clean_value)
        except ValueError:
            result.add_error(
                field_name=field_name,
                message=f"Campo '{display_name}' deve conter apenas números",
                code="INVALID_NUMBER",
                value=value,
            )

        return result

    @staticmethod
    def validate_integer(
        value: Optional[str], field_name: str, label: Optional[str] = None
    ) -> ValidationResult:
        """Valida se o valor é um número inteiro válido."""
        result = ValidationResult(is_valid=True)

        if value is None or value.strip() == "":
            return result

        display_name = label or field_name
        clean_value = value.strip().replace(",", "")

        try:
            int(clean_value)
        except ValueError:
            result.add_error(
                field_name=field_name,
                message=f"Campo '{display_name}' deve conter apenas números inteiros",
                code="INVALID_INTEGER",
                value=value,
            )

        return result

    @staticmethod
    def validate_date(
        value: Optional[str], field_name: str, label: Optional[str] = None
    ) -> ValidationResult:
        """Valida se o valor é uma data válida."""
        result = ValidationResult(is_valid=True)

        if value is None or value.strip() == "":
            return result

        display_name = label or field_name

        parsed_date = None
        for fmt in FieldValidator.DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(value.strip(), fmt)
                break
            except ValueError:
                continue

        if parsed_date is None:
            result.add_error(
                field_name=field_name,
                message=f"Campo '{display_name}' deve ser uma data válida (DD/MM/AAAA)",
                code="INVALID_DATE",
                value=value,
            )
            return result

        result.formatted_value = parsed_date.strftime("%d/%m/%Y")

        return result

    @staticmethod
    def validate_cpf(
        value: Optional[str], field_name: str, label: Optional[str] = None
    ) -> ValidationResult:
        """Valida CPF com verificação de dígitos verificadores."""
        result = ValidationResult(is_valid=True)

        if value is None or value.strip() == "":
            return result

        display_name = label or field_name
        digits = FieldValidator.CPF_DIGITS.findall(value)

        if len(digits) != 11:
            result.add_error(
                field_name=field_name,
                message=f"CPF deve conter 11 dígitos",
                code="INVALID_CPF_LENGTH",
                value=value,
            )
            return result

        cpf = "".join(digits)

        if not FieldValidator._validate_cpf_digits(cpf):
            result.add_error(
                field_name=field_name,
                message=f"CPF inválido (dígitos verificadores incorretos)",
                code="INVALID_CPF_CHECKSUM",
                value=value,
            )
            return result

        result.formatted_value = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

        return result

    @staticmethod
    def _validate_cpf_digits(cpf: str) -> bool:
        """Valida dígitos verificadores do CPF."""
        if cpf == cpf[0] * 11:
            return False

        for i in range(9, 11):
            total = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
            digit = (total % 11) % 10
            if digit != int(cpf[i]):
                return False

        return True

    @staticmethod
    def validate_cnpj(
        value: Optional[str], field_name: str, label: Optional[str] = None
    ) -> ValidationResult:
        """Valida CNPJ com verificação de dígitos verificadores."""
        result = ValidationResult(is_valid=True)

        if value is None or value.strip() == "":
            return result

        display_name = label or field_name
        digits = FieldValidator.CNPJ_DIGITS.findall(value)

        if len(digits) != 14:
            result.add_error(
                field_name=field_name,
                message=f"CNPJ deve conter 14 dígitos",
                code="INVALID_CNPJ_LENGTH",
                value=value,
            )
            return result

        cnpj = "".join(digits)

        if not FieldValidator._validate_cnpj_digits(cnpj):
            result.add_error(
                field_name=field_name,
                message=f"CNPJ inválido (dígitos verificadores incorretos)",
                code="INVALID_CNPJ_CHECKSUM",
                value=value,
            )
            return result

        result.formatted_value = (
            f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        )

        return result

    @staticmethod
    def _validate_cnpj_digits(cnpj: str) -> bool:
        """Valida dígitos verificadores do CNPJ."""
        weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

        def calc_digit(digits: str, weights: list[int]) -> int:
            total = sum(int(d) * w for d, w in zip(digits, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder

        digit_1 = calc_digit(cnpj[:12], weights_1)
        digit_2 = calc_digit(cnpj[:13], weights_2)

        return digit_1 == int(cnpj[12]) and digit_2 == int(cnpj[13])

    @staticmethod
    def normalize_whitespace(value: Optional[str]) -> Optional[str]:
        """Normaliza espaços em branco (remove espaços extras, trim)."""
        if value is None:
            return None

        value = re.sub(r"\s+", " ", value.strip())

        return value

    @staticmethod
    def check_text_overflow(
        value: Optional[str],
        field_width: float,
        field_height: float,
        font_size: float,
        font_family: str = "helvetica",
    ) -> ValidationResult:
        """
        Detecta overflow de texto com base nas dimensões do campo.

        Args:
            value: Texto a verificar
            field_width: Largura do campo em pontos
            field_height: Altura do campo em pontos
            font_size: Tamanho da fonte em pontos

        Returns:
            ValidationResult com warnings se houver overflow
        """
        result = ValidationResult(is_valid=True)

        if value is None or value == "":
            return result

        char_width_estimate = font_size * 0.6

        lines = value.split("\n")

        for i, line in enumerate(lines):
            line_width = len(line) * char_width_estimate

            if line_width > field_width:
                result.add_warning(
                    f"Linha {i + 1} excede a largura do campo ({line_width:.1f}pt > {field_width:.1f}pt)"
                )

        total_height = len(lines) * font_size * 1.2

        if total_height > field_height:
            result.add_warning(
                f"Altura total do texto ({total_height:.1f}pt) excede altura do campo ({field_height:.1f}pt)"
            )

        return result


class FieldValidationService:
    """
    Serviço de validação completo para campos de formulário.

    Coordena múltiplas validações e retorna resultado consolidado.
    """

    def __init__(self):
        self.validator = FieldValidator()

    def validate_field(
        self,
        field_name: str,
        field_type: str,
        value: Optional[str],
        required: bool = False,
        max_length: Optional[int] = None,
        min_length: Optional[int] = None,
        label: Optional[str] = None,
        field_width: Optional[float] = None,
        field_height: Optional[float] = None,
        font_size: Optional[float] = None,
        font_family: Optional[str] = None,
    ) -> ValidationResult:
        """
        Valida um campo completo.

        Args:
            field_name: Nome do campo
            field_type: Tipo do campo (text, number, date, multiline, checkbox)
            value: Valor a validar
            required: Se o campo é obrigatório
            max_length: Limite máximo de caracteres
            min_length: Limite mínimo de caracteres
            label: Label exibido ao usuário
            field_width: Largura do campo (para detecção de overflow)
            field_height: Altura do campo (para detecção de overflow)
            font_size: Tamanho da fonte (para detecção de overflow)
            font_family: Família da fonte (para detecção de overflow)

        Returns:
            ValidationResult com resultado consolidado
        """
        result = ValidationResult(is_valid=True)

        display_name = label or field_name

        normalized_value = self.validator.normalize_whitespace(value)

        if required and not normalized_value:
            result.add_error(
                field_name=field_name,
                message=f"Campo '{display_name}' é obrigatório",
                code="REQUIRED_FIELD",
                value=value,
            )
            return result

        if not normalized_value:
            return result

        if max_length is not None:
            if len(normalized_value) > max_length:
                result.add_error(
                    field_name=field_name,
                    message=f"Campo '{display_name}' excede o limite de {max_length} caracteres (atual: {len(normalized_value)})",
                    code="MAX_LENGTH_EXCEEDED",
                    value=normalized_value,
                )

        if min_length is not None:
            if len(normalized_value) < min_length:
                result.add_error(
                    field_name=field_name,
                    message=f"Campo '{display_name}' deve ter pelo menos {min_length} caracteres",
                    code="MIN_LENGTH_NOT_MET",
                    value=normalized_value,
                )

        field_type_lower = field_type.lower() if field_type else "text"

        if field_type_lower == "number":
            num_result = self.validator.validate_number(
                normalized_value, field_name, label
            )
            result.errors.extend(num_result.errors)
            if not num_result.is_valid:
                result.is_valid = False

        elif field_type_lower == "date":
            date_result = self.validator.validate_date(
                normalized_value, field_name, label
            )
            result.errors.extend(date_result.errors)
            if date_result.formatted_value:
                normalized_value = date_result.formatted_value
            if not date_result.is_valid:
                result.is_valid = False

        elif field_type_lower == "text":
            pass

        elif field_type_lower == "multiline":
            pass

        elif field_type_lower == "checkbox":
            pass

        result.formatted_value = normalized_value

        if field_width and field_height and font_size:
            overflow_result = self.validator.check_text_overflow(
                normalized_value,
                field_width,
                field_height,
                font_size,
                font_family or "helvetica",
            )
            result.warnings.extend(overflow_result.warnings)

        return result

    def validate_fields(
        self,
        field_configs: list[dict],
        field_values: dict[str, str],
    ) -> tuple[bool, list[ValidationError], dict[str, str]]:
        """
        Valida múltiplos campos.

        Args:
            field_configs: Lista de configurações dos campos
            field_values: Dicionário de valores {field_name: value}

        Returns:
            Tupla (is_valid, errors, formatted_values)
        """
        all_errors: list[ValidationError] = []
        formatted_values: dict[str, str] = {}

        for config in field_configs:
            field_name = config.get("name", "")
            value = field_values.get(field_name)

            result = self.validate_field(
                field_name=field_name,
                field_type=config.get("field_type", "text"),
                value=value,
                required=config.get("required", False),
                max_length=config.get("max_length"),
                min_length=config.get("min_length"),
                label=config.get("label"),
                field_width=config.get("width"),
                field_height=config.get("height"),
                font_size=config.get("font_size"),
                font_family=config.get("font_family"),
            )

            all_errors.extend(result.errors)

            if result.formatted_value is not None:
                formatted_values[field_name] = result.formatted_value
            elif value is not None:
                formatted_values[field_name] = value

        return len(all_errors) == 0, all_errors, formatted_values


def validate_field_value(
    field_name: str,
    field_type: str,
    value: Optional[str],
    required: bool = False,
    max_length: Optional[int] = None,
    **kwargs,
) -> ValidationResult:
    """
    Função de conveniência para validar um único campo.
    """
    service = FieldValidationService()
    return service.validate_field(
        field_name=field_name,
        field_type=field_type,
        value=value,
        required=required,
        max_length=max_length,
        **kwargs,
    )
