"""
Serviço de renderização de PDF.

Responsável por gerar PDFs derivados a partir de templates originais,
renderizando os valores preenchidos pelo usuário nas coordenadas
dos campos mapeados.
"""

import io
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import PDFEditorException
from app.core.logging_config import logger
from app.domain.models.field import Field, FieldAlignment
from app.domain.models.template import Template
from app.domain.models.version import Version, VersionStatus


class PDFRendererException(PDFEditorException):
    """Erro durante renderização do PDF."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message=message, detail=detail, code="PDF_RENDERER_ERROR")


class RenderFieldNotFoundError(PDFEditorException):
    """Campo para renderização não encontrado."""

    def __init__(self, field_name: str):
        super().__init__(
            message=f"Campo '{field_name}' não encontrado para renderização",
            code="RENDER_FIELD_NOT_FOUND",
        )


class FontManager:
    """
    Gerenciador de fontes para renderização de PDF.

    Suporta fontes padrão (Helvetica, Times, Courier) e fontes TTF personalizadas.
    """

    STANDARD_FONTS = {
        "helvetica": "Helvetica",
        "helvetica-bold": "Helvetica-Bold",
        "helvetica-oblique": "Helvetica-Oblique",
        "helvetica-bold-oblique": "Helvetica-BoldOblique",
        "times": "Times-Roman",
        "times-bold": "Times-Bold",
        "times-italic": "Times-Italic",
        "times-bold-italic": "Times-BoldItalic",
        "courier": "Courier",
        "courier-bold": "Courier-Bold",
        "courier-oblique": "Courier-Oblique",
        "courier-bold-oblique": "Courier-BoldOblique",
    }

    _registered_fonts: set[str] = set()

    @classmethod
    def register_font(cls, font_name: str, font_path: str) -> None:
        """
        Registra uma fonte TTF personalizada.

        Args:
            font_name: Nome para referenciar a fonte
            font_path: Caminho para o arquivo TTF
        """
        if font_name in cls._registered_fonts:
            return

        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            cls._registered_fonts.add(font_name)
            logger.debug(f"Fonte registrada: {font_name}")
        except Exception as e:
            logger.warning(f"Não foi possível registrar fonte {font_name}: {e}")

    @classmethod
    def get_font_name(cls, font_family: str) -> str:
        """
        Retorna o nome da fonte para uso no ReportLab.

        Args:
            font_family: Nome da família da fonte

        Returns:
            Nome da fonte válida para ReportLab
        """
        normalized = font_family.lower().replace(" ", "-")

        if normalized in cls.STANDARD_FONTS:
            return cls.STANDARD_FONTS[normalized]

        if normalized in cls._registered_fonts:
            return normalized

        return "Helvetica"


@dataclass
class TextLine:
    """Representa uma linha de texto renderizada."""

    text: str
    x: float
    y: float
    width: float
    height: float


@dataclass
class RenderContext:
    """Contexto de renderização para um campo específico."""

    field: Field
    value: str
    page_height: float


class TextRenderer:
    """
    Renderizador de texto com suporte a quebra de linha automática.

    Responsável por quebrar texto quando ultrapassa os limites do campo,
    respeitando alinhamento e altura máxima.
    """

    def __init__(self, font_manager: FontManager):
        self.font_manager = font_manager

    def wrap_text(
        self,
        text: str,
        font_family: str,
        font_size: float,
        max_width: float,
        max_height: float,
    ) -> list[TextLine]:
        """
        Quebra o texto em linhas que cabem na caixa do campo.

        Args:
            text: Texto a ser renderizado
            font_family: Família da fonte
            font_size: Tamanho da fonte em pontos
            max_width: Largura máxima disponível
            max_height: Altura máxima disponível

        Returns:
            Lista de linhas renderizáveis
        """
        if not text:
            return []

        font_name = self.font_manager.get_font_name(font_family)
        lines = []
        words = text.split()

        if not words:
            return []

        current_line = ""
        y_position = 0
        line_height = font_size * 1.2

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            test_width = self._measure_text(test_line, font_name, font_size)

            if test_width > max_width and current_line:
                lines.append(
                    TextLine(
                        text=current_line,
                        x=0,
                        y=y_position,
                        width=test_width,
                        height=font_size,
                    )
                )
                y_position += line_height
                current_line = word
            else:
                current_line = test_line

        if current_line:
            final_width = self._measure_text(current_line, font_name, font_size)
            lines.append(
                TextLine(
                    text=current_line,
                    x=0,
                    y=y_position,
                    width=final_width,
                    height=font_size,
                )
            )

        if max_height > 0:
            max_lines = int(max_height / line_height)
            if len(lines) > max_lines:
                lines = lines[:max_lines]

        return lines

    def _measure_text(self, text: str, font_name: str, font_size: float) -> float:
        """
        Mede a largura do texto para uma fonte e tamanho específicos.

        Args:
            text: Texto a medir
            font_name: Nome da fonte
            font_size: Tamanho da fonte

        Returns:
            Largura em pontos
        """
        from reportlab.pdfbase.pdfmetrics import stringWidth

        return stringWidth(text, font_name, font_size)

    def calculate_alignment_offset(
        self,
        text_width: float,
        box_width: float,
        alignment: str,
    ) -> float:
        """
        Calcula o deslocamento X baseado no alinhamento.

        Args:
            text_width: Largura do texto
            box_width: Largura da caixa
            alignment: Alinhamento (left, center, right)

        Returns:
            Deslocamento X em pontos
        """
        available_space = box_width - text_width

        if alignment == FieldAlignment.CENTER.value:
            return available_space / 2
        elif alignment == FieldAlignment.RIGHT.value:
            return max(available_space, 0)
        else:
            return 0


@dataclass
class PageRenderer:
    """
    Renderizador de uma página do PDF.

    Recebe uma página do PDF base e permite renderizar campos sobre ela.
    """

    page: fitz.Page
    page_width: float
    page_height: float

    def insert_text(
        self,
        x: float,
        y: float,
        text: str,
        font_name: str = "helv",
        font_size: float = 12,
        color: tuple = (0, 0, 0),
    ) -> None:
        """
        Insere texto na página usando PyMuPDF.

        Args:
            x: Posição X
            y: Posição Y (do topo)
            text: Texto a inserir
            font_name: Nome da fonte
            font_size: Tamanho da fonte
            color: Cor em RGB (0-1)
        """
        try:
            self.page.insert_text(
                (x, y),
                text,
                fontsize=font_size,
                fontname=font_name,
                color=color,
            )
        except Exception as e:
            logger.warning(f"Erro ao inserir texto com fonte {font_name}: {e}")
            self.page.insert_text((x, y), text, fontsize=font_size, color=color)


class PDFRendererService:
    """
    Serviço principal de renderização de PDF.

    Coordena a criação de versões derivadas a partir de templates,
    renderizando os valores preenchidos pelo usuário nas coordenadas
    dos campos mapeados.
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.font_manager = FontManager()
        self.text_renderer = TextRenderer(self.font_manager)

    def render_version(
        self,
        template_id: int,
        field_values: dict[str, str],
        version_name: str,
        description: Optional[str] = None,
        parent_version_id: Optional[int] = None,
    ) -> Version:
        """
        Renderiza uma nova versão do template com os valores fornecidos.

        Args:
            template_id: ID do template base
            field_values: Dicionário {nome_campo: valor}
            version_name: Nome da versão
            description: Descrição opcional
            parent_version_id: ID da versão pai (opcional)

        Returns:
            Versão criada com o PDF renderizado

        Raises:
            TemplateNotFoundError: Se template não existir
            RenderFieldNotFoundError: Se algum campo não existir
        """
        logger.info(
            f"Iniciando renderização: template={template_id}, version='{version_name}'"
        )

        template = self._get_template(template_id)
        fields = self._get_template_fields(template_id)

        self._validate_field_values(fields, field_values)

        pdf_bytes = self._render_pdf(template, fields, field_values)

        version = self._save_version(
            template=template,
            pdf_bytes=pdf_bytes,
            version_name=version_name,
            description=description,
            parent_version_id=parent_version_id,
            field_values=field_values,
        )

        logger.info(
            f"Versão renderizada: ID={version.id}, version_number={version.version_number}"
        )
        return version

    def _get_template(self, template_id: int) -> Template:
        """Busca template pelo ID."""
        from app.core.exceptions import TemplateNotFoundError

        template = self.db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise TemplateNotFoundError(template_id)
        return template

    def _get_template_fields(self, template_id: int) -> list[Field]:
        """Busca campos ativos do template."""
        return (
            self.db.query(Field)
            .filter(
                Field.template_id == template_id,
                Field.is_active == True,
            )
            .order_by(Field.page, Field.order, Field.id)
            .all()
        )

    def _validate_field_values(
        self, fields: list[Field], field_values: dict[str, str]
    ) -> None:
        """Valida que todos os campos requeridos têm valores."""
        missing_fields = []

        for field in fields:
            if field.required and (
                field.name not in field_values or not field_values[field.name]
            ):
                missing_fields.append(field.name)

        if missing_fields:
            raise PDFRendererException(
                message=f"Campos obrigatórios não preenchidos: {', '.join(missing_fields)}"
            )

    def _render_pdf(
        self,
        template: Template,
        fields: list[Field],
        field_values: dict[str, str],
    ) -> bytes:
        """
        Renderiza o PDF com os valores preenchidos.

        Usa PyMuPDF para copiar as páginas do template e insere o texto
        dos campos sobre elas usando a camada de anotação do PDF.

        Args:
            template: Template original
            fields: Campos mapeados
            field_values: Valores a renderizar

        Returns:
            Bytes do PDF renderizado
        """
        from app.services.file_storage import FileStorageService

        storage = FileStorageService()
        template_path = storage.get_file_path(template.file_path)

        output = io.BytesIO()

        try:
            src_doc = fitz.open(str(template_path))
            output_doc = fitz.open()

            for page_num, src_page in enumerate(src_doc):
                output_page = output_doc.new_page(
                    width=src_page.rect.width,
                    height=src_page.rect.height,
                )

                src_page.show_page(output_page)

                page_fields = [f for f in fields if f.page == page_num]

                for field in page_fields:
                    value = field_values.get(field.name, "")
                    if value:
                        self._render_field_on_page(
                            output_page, field, value, src_page.rect.height
                        )

            output_doc.save(output)
            output_doc.close()
            src_doc.close()

            return output.getvalue()

        except Exception as e:
            logger.error(f"Erro ao renderizar PDF: {e}")
            raise PDFRendererException(
                message="Falha ao renderizar PDF",
                detail=str(e),
            )

    def _render_field_on_page(
        self,
        page: fitz.Page,
        field: Field,
        value: str,
        page_height: float,
    ) -> None:
        """
        Renderiza um campo específico em uma página.

        Args:
            page: Página do PyMuPDF
            field: Campo a renderizar
            value: Valor a inserir
            page_height: Altura da página (para cálculo de Y)
        """
        font_name = self._map_font_for_pymupdf(field.font_family)
        font_size = field.font_size or 12
        color = self._hex_to_rgb(field.color or "#000000")

        x = field.x
        y = field.y

        if field.field_type in ("multiline",):
            lines = self._wrap_text_for_pymupdf(
                value, font_name, font_size, field.width, field.height
            )
            for line in lines:
                page.insert_text(
                    (x + line["offset_x"], y + line["y"]),
                    line["text"],
                    fontsize=font_size,
                    fontname=font_name,
                    color=color,
                )
        else:
            alignment = field.alignment or FieldAlignment.LEFT.value
            offset_x = self._calculate_offset(
                value, font_name, font_size, field.width, alignment
            )
            page.insert_text(
                (x + offset_x, y),
                value,
                fontsize=font_size,
                fontname=font_name,
                color=color,
            )

    def _map_font_for_pymupdf(self, font_family: str) -> str:
        """Mapeia nome de fonte para nome do PyMuPDF."""
        font_map = {
            "helvetica": "helv",
            "helvetica-bold": "helvb",
            "helvetica-oblique": "helvo",
            "helvetica-bold-oblique": "helvbo",
            "times": "tipr",
            "times-bold": "tipb",
            "times-italic": "tipi",
            "times-bold-italic": "tipbi",
            "courier": "cour",
            "courier-bold": "courb",
            "courier-oblique": "couri",
            "courier-bold-oblique": "courbo",
        }
        return font_map.get(font_family.lower(), "helv")

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        """Converte cor hexadecimal para RGB (0-1)."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            return (r, g, b)
        return (0, 0, 0)

    def _wrap_text_for_pymupdf(
        self,
        text: str,
        font_name: str,
        font_size: float,
        max_width: float,
        max_height: float,
    ) -> list[dict]:
        """Quebra texto em linhas para PyMuPDF."""
        if not text:
            return []

        from reportlab.pdfbase.pdfmetrics import stringWidth

        words = text.split()
        lines = []
        current_line = ""
        line_height = font_size * 1.2

        rl_font = self.font_manager.get_font_name(font_name)

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            test_width = stringWidth(test_line, rl_font, font_size)

            if test_width > max_width and current_line:
                lines.append(
                    {
                        "text": current_line,
                        "offset_x": 0,
                        "y": len(lines) * line_height,
                    }
                )
                current_line = word
            else:
                current_line = test_line

        if current_line:
            lines.append(
                {
                    "text": current_line,
                    "offset_x": 0,
                    "y": len(lines) * line_height,
                }
            )

        if max_height > 0:
            max_lines = int(max_height / line_height)
            if len(lines) > max_lines:
                lines = lines[:max_lines]

        return lines

    def _calculate_offset(
        self,
        text: str,
        font_name: str,
        font_size: float,
        box_width: float,
        alignment: str,
    ) -> float:
        """Calcula deslocamento X para alinhamento."""
        from reportlab.pdfbase.pdfmetrics import stringWidth

        rl_font = self.font_manager.get_font_name(font_name)
        text_width = stringWidth(text, rl_font, font_size)
        available_space = box_width - text_width

        if alignment == FieldAlignment.CENTER.value:
            return max(available_space / 2, 0)
        elif alignment == FieldAlignment.RIGHT.value:
            return max(available_space, 0)
        return 0

    def _save_version(
        self,
        template: Template,
        pdf_bytes: bytes,
        version_name: str,
        description: Optional[str],
        parent_version_id: Optional[int],
        field_values: dict[str, str],
    ) -> Version:
        """Salva a versão no banco e no storage."""
        from app.services.file_storage import FileStorageService

        storage = FileStorageService()

        version_number = self._get_next_version_number(template.id, parent_version_id)

        unique_id = uuid.uuid4().hex
        filename = f"{unique_id}_v{version_number}_{template.id}.pdf"
        relative_path = f"versions/{filename}"

        full_path = storage.settings.STORAGE_PATH / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(pdf_bytes)

        changes_summary = self._generate_changes_summary(field_values)

        version = Version(
            template_id=template.id,
            parent_version_id=parent_version_id,
            version_number=version_number,
            name=version_name,
            description=description,
            file_path=relative_path,
            file_size=len(pdf_bytes),
            changes_summary=changes_summary,
            status=VersionStatus.ACTIVE.value,
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        return version

    def _get_next_version_number(
        self, template_id: int, parent_version_id: Optional[int]
    ) -> int:
        """Calcula o próximo número de versão."""
        if parent_version_id:
            parent = (
                self.db.query(Version).filter(Version.id == parent_version_id).first()
            )
            if parent:
                return parent.version_number + 1

        max_version = (
            self.db.query(Version)
            .filter(Version.template_id == template_id)
            .order_by(Version.version_number.desc())
            .first()
        )

        return (max_version.version_number + 1) if max_version else 1

    def _generate_changes_summary(self, field_values: dict[str, str]) -> str:
        """Gera resumo das alterações."""
        if not field_values:
            return "Versão inicial"

        changed_fields = list(field_values.keys())
        return f"Campos preenchidos: {', '.join(changed_fields[:5])}"

    def get_version(self, version_id: int) -> Version:
        """Busca uma versão pelo ID."""
        from app.core.exceptions import VersionNotFoundError

        version = self.db.query(Version).filter(Version.id == version_id).first()
        if not version:
            raise VersionNotFoundError(version_id)
        return version

    def list_versions(self, template_id: int) -> list[Version]:
        """Lista todas as versões de um template."""
        return (
            self.db.query(Version)
            .filter(Version.template_id == template_id)
            .order_by(Version.version_number.desc())
            .all()
        )
