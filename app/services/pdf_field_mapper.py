"""
Serviço de mapeamento de campos editáveis em PDF.

Responsável por gerenciar campos editáveis associados a templates PDF.
Inclui validações de coordenadas, detecção de sobreposição e
operações CRUD sobre campos.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.domain.models.template import Template
from app.domain.models.field import Field, FieldType, FieldAlignment
from app.domain.models.pdf_metadata import PDFMetadata, PDFPageMetadata
from app.core.exceptions import TemplateNotFoundError, PDFEditorException
from app.core.logging_config import logger


class FieldValidationError(PDFEditorException):
    """Erro na validação de campo."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message=message, detail=detail, code="FIELD_VALIDATION_ERROR")


class FieldOverlapError(PDFEditorException):
    """Erro de sobreposição de campos."""

    def __init__(self, overlaps: list[dict]):
        self.overlaps = overlaps
        super().__init__(
            message="Campos estão sobrepondo",
            detail=f"Encontradas {len(overlaps)} sobreposições",
            code="FIELD_OVERLAP_ERROR",
        )


class FieldNotFoundError(PDFEditorException):
    """Campo não encontrado."""

    def __init__(self, field_id: int):
        super().__init__(
            message=f"Campo com ID {field_id} não encontrado",
            detail=f"Field ID: {field_id}",
            code="FIELD_NOT_FOUND",
        )


class PDFFieldMapperService:
    """
    Serviço para mapeamento de campos editáveis em PDFs.

    Gerencia a criação, validação e posicionamento de campos
    que podem ser preenchidos posteriormente.

    Responsabilidades:
    - CRUD de campos
    - Validação de coordenadas contra dimensões da página
    - Detecção de sobreposição entre campos
    - Cálculo de áreas e posicionamentos
    """

    def __init__(self, db: Session):
        self.db = db

    def create_field(
        self,
        template_id: int,
        name: str,
        page: int,
        x: float,
        y: float,
        width: float,
        height: float,
        field_type: str = FieldType.TEXT.value,
        label: Optional[str] = None,
        description: Optional[str] = None,
        font_family: Optional[str] = "Helvetica",
        font_size: Optional[float] = 12.0,
        alignment: Optional[str] = FieldAlignment.LEFT.value,
        color: Optional[str] = "#000000",
        background_color: Optional[str] = None,
        required: bool = False,
        default_value: Optional[str] = None,
        placeholder: Optional[str] = None,
        max_length: Optional[int] = None,
        order: int = 0,
        check_overlaps: bool = True,
        tolerance: float = 2.0,
    ) -> Field:
        """
        Cria um novo campo editável em um template.

        Fluxo:
        1. Verifica se template existe
        2. Valida coordenadas contra dimensões da página
        3. Verifica sobreposição com campos existentes (se solicitado)
        4. Cria o campo no banco

        Args:
            template_id: ID do template
            name: Nome único do campo
            page: Número da página (0-indexed)
            x: Posição X (canto superior esquerdo)
            y: Posição Y (canto superior esquerdo)
            width: Largura do campo
            height: Altura do campo
            field_type: Tipo do campo
            ... outros parâmetros opcionais
            check_overlaps: Se deve verificar sobreposição
            tolerance: Tolerância em pontos para verificação

        Returns:
            Field criado

        Raises:
            TemplateNotFoundError: Se template não existir
            FieldValidationError: Se coordenadas inválidas
            FieldOverlapError: Se houver sobreposição
        """
        logger.info(f"Criando campo '{name}' no template {template_id}")

        # 1. Busca template e metadados
        template = self._get_template(template_id)
        metadata = self._get_metadata(template_id)

        # 2. Valida coordenadas
        self._validate_coordinates(metadata, page, x, y, width, height)

        # 3. Verifica sobreposição
        if check_overlaps:
            overlaps = self._check_overlaps(
                template_id, page, x, y, width, height, tolerance=tolerance
            )
            if overlaps:
                raise FieldOverlapError(overlaps)

        # 4. Cria o campo
        field = Field(
            template_id=template_id,
            name=name,
            label=label,
            description=description,
            page=page,
            x=x,
            y=y,
            width=width,
            height=height,
            field_type=field_type,
            font_family=font_family,
            font_size=font_size,
            alignment=alignment,
            color=color,
            background_color=background_color,
            required=required,
            default_value=default_value,
            placeholder=placeholder,
            max_length=max_length,
            order=order,
        )

        self.db.add(field)
        self.db.commit()
        self.db.refresh(field)

        logger.info(f"Campo criado: ID={field.id}, name='{name}'")

        return field

    def get_field(self, field_id: int) -> Field:
        """
        Busca um campo pelo ID.

        Args:
            field_id: ID do campo

        Returns:
            Field encontrado

        Raises:
            FieldNotFoundError: Se não encontrar
        """
        field = self.db.query(Field).filter(Field.id == field_id).first()

        if not field:
            raise FieldNotFoundError(field_id)

        return field

    def get_template_fields(
        self, template_id: int, page: Optional[int] = None, active_only: bool = True
    ) -> List[Field]:
        """
        Lista campos de um template.

        Args:
            template_id: ID do template
            page: Filtrar por página (opcional)
            active_only: Se deve retornar apenas campos ativos

        Returns:
            Lista de campos
        """
        self._get_template(template_id)  # Valida existência

        query = self.db.query(Field).filter(Field.template_id == template_id)

        if page is not None:
            query = query.filter(Field.page == page)

        if active_only:
            query = query.filter(Field.is_active == True)

        return query.order_by(Field.order, Field.id).all()

    def update_field(
        self,
        field_id: int,
        check_overlaps: bool = True,
        tolerance: float = 2.0,
        **updates,
    ) -> Field:
        """
        Atualiza um campo existente.

        Args:
            field_id: ID do campo
            check_overlaps: Se deve verificar sobreposição após update
            tolerance: Tolerância para verificação
            **updates: Campos a atualizar

        Returns:
            Field atualizado
        """
        field = self.get_field(field_id)

        # Guarda valores antigos para verificação
        old_page = field.page
        old_x, old_y = field.x, field.y
        old_w, old_h = field.width, field.height

        # Atualiza campos permitidos
        allowed_fields = {
            "name",
            "label",
            "description",
            "page",
            "x",
            "y",
            "width",
            "height",
            "field_type",
            "font_family",
            "font_size",
            "alignment",
            "color",
            "background_color",
            "required",
            "default_value",
            "placeholder",
            "max_length",
            "order",
            "is_active",
        }

        for key, value in updates.items():
            if key in allowed_fields and value is not None:
                setattr(field, key, value)

        # Valida novas coordenadas se posição mudou
        if (
            "page" in updates
            or "x" in updates
            or "y" in updates
            or "width" in updates
            or "height" in updates
        ):
            metadata = self._get_metadata(field.template_id)
            self._validate_coordinates(
                metadata, field.page, field.x, field.y, field.width, field.height
            )

            # Verifica sobreposição se posição mudou
            if check_overlaps:
                overlaps = self._check_overlaps(
                    field.template_id,
                    field.page,
                    field.x,
                    field.y,
                    field.width,
                    field.height,
                    exclude_field_id=field_id,
                    tolerance=tolerance,
                )
                if overlaps:
                    # Rollback das alterações
                    self.db.rollback()
                    raise FieldOverlapError(overlaps)

        self.db.commit()
        self.db.refresh(field)

        logger.info(f"Campo atualizado: ID={field_id}")

        return field

    def update_field_position(
        self,
        field_id: int,
        x: float,
        y: float,
        width: Optional[float] = None,
        height: Optional[float] = None,
        page: Optional[int] = None,
        check_overlaps: bool = True,
    ) -> Field:
        """
        Atualiza apenas posição de um campo (drag & drop).

        Args:
            field_id: ID do campo
            x: Nova posição X
            y: Nova posição Y
            width: Nova largura (opcional)
            height: Nova altura (opcional)
            page: Nova página (opcional)
            check_overlaps: Se deve verificar sobreposição

        Returns:
            Field atualizado
        """
        field = self.get_field(field_id)

        updates = {"x": x, "y": y}
        if width is not None:
            updates["width"] = width
        if height is not None:
            updates["height"] = height
        if page is not None:
            updates["page"] = page

        return self.update_field(field_id, check_overlaps=check_overlaps, **updates)

    def delete_field(self, field_id: int) -> None:
        """
        Deleta um campo.

        Args:
            field_id: ID do campo
        """
        field = self.get_field(field_id)

        self.db.delete(field)
        self.db.commit()

        logger.info(f"Campo deletado: ID={field_id}")

    def check_overlaps(
        self,
        template_id: int,
        page: int,
        x: float,
        y: float,
        width: float,
        height: float,
        exclude_field_id: Optional[int] = None,
        tolerance: float = 2.0,
    ) -> List[dict]:
        """
        Verifica sobreposições de um retângulo com campos existentes.

        Args:
            template_id: ID do template
            page: Número da página
            x, y, width, height: Dimensões do retângulo
            exclude_field_id: ID de campo a ignorar
            tolerance: Tolerância em pontos

        Returns:
            Lista de sobreposições encontradas
        """
        return self._check_overlaps(
            template_id, page, x, y, width, height, exclude_field_id, tolerance
        )

    def get_fields_by_area(
        self,
        template_id: int,
        page: int,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> List[Field]:
        """
        Busca campos dentro de uma área retangular.

        Args:
            template_id: ID do template
            page: Número da página
            x, y, width, height: Área de busca

        Returns:
            Lista de campos dentro da área
        """
        x2, y2 = x + width, y + height

        fields = (
            self.db.query(Field)
            .filter(
                Field.template_id == template_id,
                Field.page == page,
                Field.is_active == True,
            )
            .all()
        )

        result = []
        for field in fields:
            fx2, fy2 = field.x + field.width, field.y + field.height

            # Verifica se há interseção
            if field.x < x2 and fx2 > x and field.y < y2 and fy2 > y:
                result.append(field)

        return result

    def duplicate_template_fields(
        self, source_template_id: int, target_template_id: int
    ) -> List[Field]:
        """
        Duplica todos os campos de um template para outro.

        Útil ao criar novo template baseado em outro.

        Args:
            source_template_id: Template de origem
            target_template_id: Template de destino

        Returns:
            Lista de novos campos criados
        """
        source_fields = self.get_template_fields(source_template_id, active_only=False)

        new_fields = []
        for field in source_fields:
            # Cria cópia com novo nome
            new_field = Field(
                template_id=target_template_id,
                name=f"{field.name}_copy",
                label=field.label,
                description=field.description,
                page=field.page,
                x=field.x,
                y=field.y,
                width=field.width,
                height=field.height,
                field_type=field.field_type,
                font_family=field.font_family,
                font_size=field.font_size,
                alignment=field.alignment,
                color=field.color,
                background_color=field.background_color,
                required=field.required,
                default_value=field.default_value,
                placeholder=field.placeholder,
                max_length=field.max_length,
                order=field.order,
                is_active=field.is_active,
            )
            self.db.add(new_field)
            new_fields.append(new_field)

        self.db.commit()

        logger.info(
            f"Campos duplicados: {len(new_fields)} de "
            f"template {source_template_id} para {target_template_id}"
        )

        return new_fields

    # === Métodos privados ===

    def _get_template(self, template_id: int) -> Template:
        """Busca template ou lança exceção."""
        template = self.db.query(Template).filter(Template.id == template_id).first()

        if not template:
            raise TemplateNotFoundError(template_id)

        return template

    def _get_metadata(self, template_id: int) -> PDFMetadata:
        """Busca metadados do template ou lança exceção."""
        metadata = (
            self.db.query(PDFMetadata)
            .filter(PDFMetadata.template_id == template_id)
            .first()
        )

        if not metadata:
            raise FieldValidationError(
                message="Metadados do template não encontrados",
                detail="Execute a extração de metadados primeiro",
            )

        return metadata

    def _validate_coordinates(
        self,
        metadata: PDFMetadata,
        page: int,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        """
        Valida coordenadas contra dimensões reais da página.

        Raises:
            FieldValidationError: Se coordenadas inválidas
        """
        # Verifica se página existe
        if page < 0 or page >= metadata.page_count:
            raise FieldValidationError(
                message=f"Página {page} não existe",
                detail=f"PDF tem {metadata.page_count} páginas (0 a {metadata.page_count - 1})",
            )

        # Obtém dimensões da página
        page_dims = None
        for dim in metadata.page_dimensions:
            if dim.get("page") == page:
                page_dims = dim
                break

        if not page_dims:
            raise FieldValidationError(
                message=f"Dimensões da página {page} não encontradas"
            )

        page_width = page_dims["width"]
        page_height = page_dims["height"]

        # Valida posições
        if x < 0 or y < 0:
            raise FieldValidationError(
                message="Posições X e Y devem ser não-negativas", detail=f"x={x}, y={y}"
            )

        # Valida dimensões
        if width <= 0 or height <= 0:
            raise FieldValidationError(
                message="Largura e altura devem ser maiores que zero",
                detail=f"width={width}, height={height}",
            )

        # Valida se campo cabe na página
        if x + width > page_width:
            raise FieldValidationError(
                message="Campo ultrapassa largura da página",
                detail=f"x + width = {x + width}, página width = {page_width}",
            )

        if y + height > page_height:
            raise FieldValidationError(
                message="Campo ultrapassa altura da página",
                detail=f"y + height = {y + height}, página height = {page_height}",
            )

    def _check_overlaps(
        self,
        template_id: int,
        page: int,
        x: float,
        y: float,
        width: float,
        height: float,
        exclude_field_id: Optional[int] = None,
        tolerance: float = 2.0,
    ) -> List[dict]:
        """
        Verifica sobreposições com campos existentes.

        Returns:
            Lista de dicts com info das sobreposições
        """
        # Busca campos na mesma página
        query = self.db.query(Field).filter(
            Field.template_id == template_id,
            Field.page == page,
            Field.is_active == True,
        )

        if exclude_field_id:
            query = query.filter(Field.id != exclude_field_id)

        existing_fields = query.all()

        # Cria retângulo candidato com tolerância
        cand_x1 = x - tolerance
        cand_y1 = y - tolerance
        cand_x2 = x + width + tolerance
        cand_y2 = y + height + tolerance

        overlaps = []

        for field in existing_fields:
            field_x1 = field.x - tolerance
            field_y1 = field.y - tolerance
            field_x2 = field.x + field.width + tolerance
            field_y2 = field.y + field.height + tolerance

            # Verifica interseção
            if not (
                cand_x2 <= field_x1
                or cand_x1 >= field_x2
                or cand_y2 <= field_y1
                or cand_y1 >= field_y2
            ):
                # Calcula área de sobreposição
                overlap_x1 = max(cand_x1, field_x1)
                overlap_y1 = max(cand_y1, field_y1)
                overlap_x2 = min(cand_x2, field_x2)
                overlap_y2 = min(cand_y2, field_y2)

                overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
                field_area = field.width * field.height
                overlap_pct = (overlap_area / field_area) * 100 if field_area > 0 else 0

                overlaps.append(
                    {
                        "field_id": field.id,
                        "field_name": field.name,
                        "overlap_area": round(overlap_area, 2),
                        "overlap_percentage": round(overlap_pct, 2),
                        "existing_bounds": {
                            "x": field.x,
                            "y": field.y,
                            "width": field.width,
                            "height": field.height,
                        },
                    }
                )

        return overlaps
