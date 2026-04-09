"""
Serviço de Preview de PDF.

Gerencia a criação, confirmação e cancelamento de pré-visualizações
antes da geração oficial de versões.
"""

import hashlib
import io
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import fitz
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import PDFEditorException
from app.core.logging_config import logger
from app.domain.models.field import Field
from app.domain.models.preview import Preview, PreviewStatus
from app.domain.models.template import Template
from app.domain.models.version import Version, VersionStatus


class PreviewNotFoundError(PDFEditorException):
    """Preview não encontrado."""

    def __init__(self, preview_id: int = None, token: str = None):
        identifier = f"ID {preview_id}" if preview_id else f"token {token}"
        super().__init__(
            message=f"Preview com {identifier} não encontrado",
            code="PREVIEW_NOT_FOUND",
        )


class PreviewExpiredError(PDFEditorException):
    """Preview expirado."""

    def __init__(self, preview_id: int):
        super().__init__(
            message=f"Preview {preview_id} expirou",
            code="PREVIEW_EXPIRED",
        )


class PreviewAlreadyConfirmedError(PDFEditorException):
    """Preview já confirmado."""

    def __init__(self, preview_id: int):
        super().__init__(
            message=f"Preview {preview_id} já foi confirmado",
            code="PREVIEW_ALREADY_CONFIRMED",
        )


class PreviewService:
    """
    Serviço para gerenciamento de pré-visualizações de PDF.

    Responsabilidades:
    - Criar preview temporário com dados do formulário
    - Gerar imagens de preview por página
    - Confirmar preview e gerar versão oficial
    - Cancelar preview e descartar arquivos temporários
    - Limpar previews expirados
    """

    PREVIEW_EXPIRY_HOURS = 24

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def create_preview(
        self,
        template_id: int,
        field_values: dict[str, str],
        created_by: Optional[str] = None,
        generate_images: bool = True,
    ) -> Preview:
        """
        Cria uma nova pré-visualização temporária.

        Args:
            template_id: ID do template base
            field_values: Valores dos campos para renderizar
            created_by: Usuário responsável
            generate_images: Se deve gerar imagens por página

        Returns:
            Preview criado com PDF e imagens temporários

        Raises:
            TemplateNotFoundError: Se template não existir
        """
        template = self._get_template(template_id)
        fields = self._get_template_fields(template_id)

        pdf_bytes = self._render_preview_pdf(template, fields, field_values)

        unique_id = uuid.uuid4().hex
        filename = f"preview_{unique_id}.pdf"
        relative_path = f"previews/{filename}"

        full_path = self.settings.STORAGE_PATH / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(pdf_bytes)

        image_paths = None
        if generate_images:
            image_paths = self._generate_preview_images(full_path, unique_id)

        preview_token = self._generate_token()

        expires_at = datetime.utcnow() + timedelta(hours=self.PREVIEW_EXPIRY_HOURS)

        preview = Preview(
            template_id=template_id,
            preview_token=preview_token,
            field_data=field_values,
            pdf_path=relative_path,
            image_paths=image_paths,
            file_size=len(pdf_bytes),
            created_by=created_by,
            status=PreviewStatus.PENDING.value,
            expires_at=expires_at,
        )

        self.db.add(preview)
        self.db.commit()
        self.db.refresh(preview)

        logger.info(f"Preview criado: ID={preview.id}, template={template_id}")

        return preview

    def get_preview(self, preview_id: int) -> Preview:
        """Busca preview pelo ID."""
        preview = self.db.query(Preview).filter(Preview.id == preview_id).first()
        if not preview:
            raise PreviewNotFoundError(preview_id)
        return preview

    def get_preview_by_token(self, token: str) -> Preview:
        """Busca preview pelo token."""
        preview = self.db.query(Preview).filter(Preview.preview_token == token).first()
        if not preview:
            raise PreviewNotFoundError(token=token)
        return preview

    def get_preview_pdf_bytes(self, preview_id: int) -> bytes:
        """Retorna os bytes do PDF do preview."""
        preview = self.get_preview(preview_id)

        if not preview.is_active and preview.status != PreviewStatus.CONFIRMED.value:
            if preview.is_expired:
                raise PreviewExpiredError(preview_id)
            raise PreviewAlreadyConfirmedError(preview_id)

        full_path = self.settings.STORAGE_PATH / preview.pdf_path
        if not full_path.exists():
            raise PreviewNotFoundError(preview_id)

        return full_path.read_bytes()

    def get_preview_image_paths(self, preview_id: int) -> list[str]:
        """Retorna os caminhos das imagens do preview."""
        preview = self.get_preview(preview_id)

        if not preview.image_paths:
            return []

        return [str(self.settings.STORAGE_PATH / path) for path in preview.image_paths]

    def confirm_preview(
        self,
        preview_id: int,
        version_name: str,
        description: Optional[str] = None,
    ) -> Version:
        """
        Confirma um preview e gera versão oficial.

        Args:
            preview_id: ID do preview
            version_name: Nome da versão
            description: Descrição opcional

        Returns:
            Versão oficial criada

        Raises:
            PreviewNotFoundError: Se preview não existir
            PreviewExpiredError: Se preview expirou
            PreviewAlreadyConfirmedError: Se já confirmado
        """
        preview = self.get_preview(preview_id)

        if preview.status == PreviewStatus.CONFIRMED.value:
            raise PreviewAlreadyConfirmedError(preview_id)

        if preview.is_expired:
            preview.status = PreviewStatus.EXPIRED.value
            self.db.commit()
            raise PreviewExpiredError(preview_id)

        pdf_bytes = self.get_preview_pdf_bytes(preview_id)

        version = self._create_version_from_preview(
            preview=preview,
            pdf_bytes=pdf_bytes,
            version_name=version_name,
            description=description,
        )

        preview.status = PreviewStatus.CONFIRMED.value
        preview.confirmed_at = datetime.utcnow()
        preview.version_id = version.id
        self.db.commit()

        self._cleanup_preview_files(preview)

        logger.info(f"Preview confirmado: ID={preview_id}, versão={version.id}")

        return version

    def cancel_preview(self, preview_id: int) -> Preview:
        """
        Cancela um preview e descarta os arquivos temporários.

        Args:
            preview_id: ID do preview

        Returns:
            Preview cancelado

        Raises:
            PreviewNotFoundError: Se preview não existir
        """
        preview = self.get_preview(preview_id)

        if preview.status == PreviewStatus.CONFIRMED.value:
            raise PreviewAlreadyConfirmedError(preview_id)

        preview.status = PreviewStatus.CANCELLED.value
        self.db.commit()

        self._cleanup_preview_files(preview)

        logger.info(f"Preview cancelado: ID={preview_id}")

        return preview

    def list_active_previews(self, template_id: Optional[int] = None) -> list[Preview]:
        """Lista previews ativos (pendentes e não expirados)."""
        query = self.db.query(Preview).filter(
            Preview.status == PreviewStatus.PENDING.value
        )

        if template_id:
            query = query.filter(Preview.template_id == template_id)

        previews = query.all()

        return [p for p in previews if not p.is_expired]

    def cleanup_expired_previews(self) -> int:
        """
        Limpa previews expirados do banco e do disco.

        Returns:
            Número de previews removidos
        """
        expired_previews = (
            self.db.query(Preview)
            .filter(Preview.status == PreviewStatus.PENDING.value)
            .all()
        )

        count = 0
        for preview in expired_previews:
            if preview.is_expired:
                preview.status = PreviewStatus.EXPIRED.value
                self._cleanup_preview_files(preview)
                count += 1

        self.db.commit()

        logger.info(f"Limpeza de previews expirados: {count} removidos")

        return count

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

    def _render_preview_pdf(
        self,
        template: Template,
        fields: list[Field],
        field_values: dict[str, str],
    ) -> bytes:
        """Renderiza o PDF do preview."""
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
                        self._render_field_on_page(output_page, field, value)

            output_doc.save(output)
            output_doc.close()
            src_doc.close()

            return output.getvalue()

        except Exception as e:
            logger.error(f"Erro ao renderizar preview PDF: {e}")
            raise PDFEditorException(
                message="Falha ao renderizar preview",
                detail=str(e),
                code="PREVIEW_RENDER_ERROR",
            )

    def _render_field_on_page(
        self,
        page: fitz.Page,
        field: Field,
        value: str,
    ) -> None:
        """Renderiza um campo no preview."""
        font_map = {
            "helvetica": "helv",
            "times": "tipr",
            "courier": "cour",
        }
        font_name = font_map.get(field.font_family.lower(), "helv")
        font_size = field.font_size or 12

        hex_color = field.color or "#000000"
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            color = (r, g, b)
        else:
            color = (0, 0, 0)

        page.insert_text(
            (field.x, field.y),
            value,
            fontsize=font_size,
            fontname=font_name,
            color=color,
        )

    def _generate_preview_images(self, pdf_path: Path, unique_id: str) -> list[str]:
        """Gera imagens para cada página do PDF."""
        image_paths = []

        try:
            doc = fitz.open(str(pdf_path))

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                img_filename = f"preview_{unique_id}_page{page_num + 1}.png"
                img_path = self.settings.PREVIEWS_PATH / img_filename
                img.save(img_path, "PNG")

                image_paths.append(f"previews/{img_filename}")

            doc.close()

        except Exception as e:
            logger.warning(f"Erro ao gerar imagens de preview: {e}")

        return image_paths

    def _generate_token(self) -> str:
        """Gera token único para o preview."""
        return uuid.uuid4().hex

    def _create_version_from_preview(
        self,
        preview: Preview,
        pdf_bytes: bytes,
        version_name: str,
        description: Optional[str],
    ) -> Version:
        """Cria versão oficial a partir de um preview."""
        from app.services.file_storage import FileStorageService

        storage = FileStorageService()

        version_number = self._get_next_version_number(preview.template_id)

        unique_id = uuid.uuid4().hex
        filename = f"{unique_id}_v{version_number}_{preview.template_id}.pdf"
        relative_path = f"versions/{filename}"

        full_path = storage.settings.STORAGE_PATH / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(pdf_bytes)

        checksum = hashlib.sha256(pdf_bytes).hexdigest()

        version = Version(
            template_id=preview.template_id,
            version_number=version_number,
            name=version_name,
            description=description,
            file_path=relative_path,
            file_size=len(pdf_bytes),
            checksum=checksum,
            field_data=preview.field_data,
            created_by=preview.created_by,
            status=VersionStatus.ACTIVE.value,
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        return version

    def _get_next_version_number(self, template_id: int) -> int:
        """Calcula próximo número de versão."""
        max_version = (
            self.db.query(Version)
            .filter(Version.template_id == template_id)
            .order_by(Version.version_number.desc())
            .first()
        )

        return (max_version.version_number + 1) if max_version else 1

    def _cleanup_preview_files(self, preview: Preview) -> None:
        """Remove arquivos temporários do preview."""
        try:
            pdf_path = self.settings.STORAGE_PATH / preview.pdf_path
            if pdf_path.exists():
                pdf_path.unlink()
                logger.debug(f"Arquivo PDF removido: {preview.pdf_path}")

            if preview.image_paths:
                for img_path in preview.image_paths:
                    full_path = self.settings.STORAGE_PATH / img_path
                    if full_path.exists():
                        full_path.unlink()
                        logger.debug(f"Imagem removida: {img_path}")

        except Exception as e:
            logger.warning(f"Erro ao limpar arquivos do preview: {e}")
