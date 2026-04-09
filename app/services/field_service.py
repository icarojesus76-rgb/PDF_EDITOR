"""
Serviço de gerenciamento de Campos.

Contém a lógica de negócio para operações CRUD de campos editáveis.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import PDFEditorException
from app.core.logging_config import logger
from app.domain.models.field import Field
from app.domain.models.template import Template
from app.schemas.field_schema import (
    FieldCreate,
    FieldUpdate,
    TemplateFieldsResponse,
    FieldResponse,
)


class FieldNotFoundError(PDFEditorException):
    """Campo não encontrado."""

    def __init__(self, field_id: int):
        super().__init__(
            message=f"Campo com ID {field_id} não encontrado",
            code="FIELD_NOT_FOUND",
        )


class FieldService:
    """Serviço para gerenciamento de campos editáveis."""

    def __init__(self, db: Session):
        self.db = db

    def create_field(self, field_data: FieldCreate) -> Field:
        """Cria um novo campo."""
        template = (
            self.db.query(Template)
            .filter(Template.id == field_data.template_id)
            .first()
        )

        if not template:
            raise PDFEditorException(
                message=f"Template {field_data.template_id} não encontrado",
                code="TEMPLATE_NOT_FOUND",
            )

        existing_field = (
            self.db.query(Field)
            .filter(
                Field.template_id == field_data.template_id,
                Field.name == field_data.name,
            )
            .first()
        )

        if existing_field:
            raise PDFEditorException(
                message=f"Campo '{field_data.name}' já existe neste template",
                code="FIELD_DUPLICATE",
            )

        field = Field(
            template_id=field_data.template_id,
            name=field_data.name,
            label=field_data.label,
            description=field_data.description,
            page=field_data.page,
            x=field_data.x,
            y=field_data.y,
            width=field_data.width,
            height=field_data.height,
            field_type=field_data.field_type,
            font_family=field_data.font_family,
            font_size=field_data.font_size,
            alignment=field_data.alignment,
            color=field_data.color,
            background_color=field_data.background_color,
            required=field_data.required,
            default_value=field_data.default_value,
            placeholder=field_data.placeholder,
            max_length=field_data.max_length,
            order=field_data.order,
            is_active=field_data.is_active,
        )

        self.db.add(field)
        self.db.commit()
        self.db.refresh(field)

        logger.info(f"Campo criado: ID={field.id}, name={field.name}")

        return field

    def get_field(self, field_id: int) -> Field:
        """Busca um campo pelo ID."""
        field = self.db.query(Field).filter(Field.id == field_id).first()

        if not field:
            raise FieldNotFoundError(field_id)

        return field

    def get_template_fields(self, template_id: int) -> TemplateFieldsResponse:
        """Retorna todos os campos de um template."""
        template = self.db.query(Template).filter(Template.id == template_id).first()

        if not template:
            raise PDFEditorException(
                message=f"Template {template_id} não encontrado",
                code="TEMPLATE_NOT_FOUND",
            )

        fields = (
            self.db.query(Field)
            .filter(Field.template_id == template_id)
            .order_by(Field.page, Field.order, Field.id)
            .all()
        )

        fields_by_page = {}
        for field in fields:
            page_num = field.page
            if page_num not in fields_by_page:
                fields_by_page[page_num] = []
            fields_by_page[page_num].append(
                {
                    "id": field.id,
                    "name": field.name,
                    "label": field.label,
                    "page": field.page,
                    "field_type": field.field_type,
                    "required": field.required,
                    "order": field.order,
                    "is_active": field.is_active,
                }
            )

        return TemplateFieldsResponse(
            template_id=template_id,
            template_name=template.name,
            total_fields=len(fields),
            fields_by_page=fields_by_page,
            fields=[FieldResponse.model_validate(f) for f in fields],
        )

    def update_field(self, field_id: int, field_data: FieldUpdate) -> Field:
        """Atualiza um campo."""
        field = self.get_field(field_id)

        update_data = field_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(field, key, value)

        self.db.commit()
        self.db.refresh(field)

        logger.info(f"Campo atualizado: ID={field.id}")

        return field

    def delete_field(self, field_id: int) -> None:
        """Deleta um campo."""
        field = self.get_field(field_id)

        self.db.delete(field)
        self.db.commit()

        logger.info(f"Campo deletado: ID={field_id}")
