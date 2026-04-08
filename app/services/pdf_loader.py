"""
Serviço de carregamento e análise de PDF com PyMuPDF.

Responsável por extrair metadados detalhados do PDF incluindo:
- Informações do documento (páginas, versão, autor)
- Dimensões de cada página
- Blocos de texto com posicionamento
- Imagens e elementos visuais
- Campos de formulário existentes

Esses metadados são usados para preparar o template para
receber campos editáveis sem modificar o arquivo original.
"""

import json
import uuid
from pathlib import Path
from typing import BinaryIO
from dataclasses import dataclass, asdict

import fitz  # PyMuPDF

from app.core.config import get_settings
from app.core.exceptions import FileStorageError, InvalidPDFError
from app.core.logging_config import logger


@dataclass
class TextBlock:
    """Representa um bloco de texto extraído do PDF."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font: str | None = None
    size: float | None = None
    flags: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImageInfo:
    """Representa uma imagem encontrada no PDF."""

    xref: int
    x0: float
    y0: float
    x1: float
    y1: float
    width: int
    height: int
    ext: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FormField:
    """Representa um campo de formulário no PDF."""

    field_name: str
    field_type: str
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
    value: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PageMetadata:
    """Metadados de uma página específica."""

    page_number: int
    width: float
    height: float
    rotation: int
    text_blocks: list[dict]
    images: list[dict]
    form_fields: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PDFDocumentMetadata:
    """Metadados completos de um documento PDF."""

    page_count: int
    pdf_version: str | None
    title: str | None
    author: str | None
    creator: str | None
    producer: str | None
    creation_date: str | None
    modification_date: str | None
    pages: list[dict]
    total_text_blocks: int
    total_images: int
    total_forms: int

    def to_dict(self) -> dict:
        return asdict(self)


class PDFLoaderService:
    """
    Serviço para carregamento e análise detalhada de PDFs.

    Usa PyMuPDF (fitz) para extrair informações estruturadas
    sobre o layout e conteúdo do documento.
    """

    def __init__(self):
        self.settings = get_settings()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Garante que o diretório de metadados exista."""
        metadata_path = self.settings.STORAGE_PATH / "metadata"
        metadata_path.mkdir(parents=True, exist_ok=True)

    def extract_metadata(
        self, file_content: bytes, filename: str
    ) -> PDFDocumentMetadata:
        """
        Extrai metadados completos de um PDF.

        Args:
            file_content: Bytes do arquivo PDF
            filename: Nome do arquivo para logging

        Returns:
            PDFDocumentMetadata com informações estruturadas

        Raises:
            InvalidPDFError: Se o arquivo não for um PDF válido
        """
        logger.info(f"Extraindo metadados de: {filename}")

        try:
            # Abre o PDF da memória
            doc = fitz.open(stream=file_content, filetype="pdf")

            if doc.is_encrypted:
                logger.warning(f"PDF criptografado: {filename}")
                # Tenta descriptografar com senha vazia
                if not doc.authenticate(""):
                    raise InvalidPDFError(
                        "PDF criptografado. Não é possível extrair metadados."
                    )

            # Extrai metadados do documento
            metadata = doc.metadata or {}

            # Processa cada página
            pages_metadata = []
            total_blocks = 0
            total_images = 0
            total_forms = 0

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_meta = self._extract_page_metadata(page, page_num)
                pages_metadata.append(page_meta.to_dict())

                total_blocks += len(page_meta.text_blocks)
                total_images += len(page_meta.images)
                total_forms += len(page_meta.form_fields)

            doc_metadata = PDFDocumentMetadata(
                page_count=len(doc),
                pdf_version=doc.metadata.get("format", None),
                title=metadata.get("title", None),
                author=metadata.get("author", None),
                creator=metadata.get("creator", None),
                producer=metadata.get("producer", None),
                creation_date=metadata.get("creationDate", None),
                modification_date=metadata.get("modDate", None),
                pages=pages_metadata,
                total_text_blocks=total_blocks,
                total_images=total_images,
                total_forms=total_forms,
            )

            doc.close()

            logger.info(
                f"Metadados extraídos: {doc_metadata.page_count} páginas, "
                f"{total_blocks} blocos de texto, {total_images} imagens"
            )

            return doc_metadata

        except fitz.FileDataError as e:
            logger.error(f"Erro ao abrir PDF: {e}")
            raise InvalidPDFError(f"Arquivo não é um PDF válido: {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado na extração: {e}")
            raise InvalidPDFError(f"Falha ao extrair metadados: {str(e)}")

    def _extract_page_metadata(self, page: fitz.Page, page_num: int) -> PageMetadata:
        """
        Extrai metadados de uma página específica.

        Args:
            page: Objeto Page do PyMuPDF
            page_num: Número da página (0-indexed)

        Returns:
            PageMetadata com informações da página
        """
        rect = page.rect

        # Extrai blocos de texto
        text_blocks = self._extract_text_blocks(page)

        # Extrai informações de imagens
        images = self._extract_images(page)

        # Extrai campos de formulário
        form_fields = self._extract_form_fields(page, page_num)

        return PageMetadata(
            page_number=page_num,
            width=rect.width,
            height=rect.height,
            rotation=page.rotation,
            text_blocks=text_blocks,
            images=images,
            form_fields=form_fields,
        )

    def _extract_text_blocks(self, page: fitz.Page) -> list[dict]:
        """
        Extrai blocos de texto com suas posições.

        Args:
            page: Objeto Page do PyMuPDF

        Returns:
            Lista de TextBlock como dicionários
        """
        blocks = []

        # Obtém blocos de texto com flags detalhados
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES)

        for block in text_dict.get("blocks", []):
            if "lines" in block:  # É um bloco de texto
                # Extrai texto completo do bloco
                text_content = ""
                for line in block["lines"]:
                    for span in line["spans"]:
                        text_content += span.get("text", "")

                if text_content.strip():  # Ignora blocos vazios
                    text_block = TextBlock(
                        text=text_content.strip(),
                        x0=block["bbox"][0],
                        y0=block["bbox"][1],
                        x1=block["bbox"][2],
                        y1=block["bbox"][3],
                        font=span.get("font", None),
                        size=span.get("size", None),
                        flags=span.get("flags", None),
                    )
                    blocks.append(text_block.to_dict())

        return blocks

    def _extract_images(self, page: fitz.Page) -> list[dict]:
        """
        Extrai informações sobre imagens na página.

        Args:
            page: Objeto Page do PyMuPDF

        Returns:
            Lista de ImageInfo como dicionários
        """
        images = []

        for img_index, img in enumerate(page.get_images(), start=1):
            xref = img[0]

            try:
                # Obtém informações da imagem
                pix = fitz.Pixmap(page.parent, xref)

                # Encontra a posição da imagem na página
                img_rect = None
                for img_info in page.get_image_info():
                    if img_info.get("xref") == xref:
                        img_rect = img_info.get("bbox")
                        break

                image_info = ImageInfo(
                    xref=xref,
                    x0=img_rect[0] if img_rect else 0,
                    y0=img_rect[1] if img_rect else 0,
                    x1=img_rect[2] if img_rect else 0,
                    y1=img_rect[3] if img_rect else 0,
                    width=pix.width,
                    height=pix.height,
                    ext="png" if pix.n > 4 else "jpeg",
                )
                images.append(image_info.to_dict())

            except Exception as e:
                logger.warning(f"Erro ao processar imagem {xref}: {e}")
                continue

        return images

    def _extract_form_fields(self, page: fitz.Page, page_num: int) -> list[dict]:
        """
        Extrai campos de formulário da página.

        Args:
            page: Objeto Page do PyMuPDF
            page_num: Número da página

        Returns:
            Lista de FormField como dicionários
        """
        fields = []

        # Obtém widgets (campos de formulário)
        for widget in page.widgets():
            field = FormField(
                field_name=widget.field_name or f"field_{page_num}_{widget.field_type}",
                field_type=self._get_field_type_name(widget.field_type),
                x0=widget.rect.x0,
                y0=widget.rect.y0,
                x1=widget.rect.x1,
                y1=widget.rect.y1,
                page=page_num,
                value=widget.field_value,
            )
            fields.append(field.to_dict())

        return fields

    def _get_field_type_name(self, field_type: int) -> str:
        """Converte código de tipo de campo para nome legível."""
        type_names = {
            fitz.PDF_WIDGET_TYPE_TEXT: "text",
            fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
            fitz.PDF_WIDGET_TYPE_RADIOBUTTON: "radiobutton",
            fitz.PDF_WIDGET_TYPE_LISTBOX: "listbox",
            fitz.PDF_WIDGET_TYPE_COMBOBOX: "combobox",
            fitz.PDF_WIDGET_TYPE_SIGNATURE: "signature",
            fitz.PDF_WIDGET_TYPE_BUTTON: "button",
        }
        return type_names.get(field_type, f"unknown_{field_type}")

    def save_metadata_json(
        self, metadata: PDFDocumentMetadata, template_id: int
    ) -> str:
        """
        Salva metadados em arquivo JSON.

        Args:
            metadata: Metadados do documento
            template_id: ID do template para nomear o arquivo

        Returns:
            Caminho relativo do arquivo JSON salvo
        """
        try:
            # Gera nome do arquivo
            json_filename = f"template_{template_id}_metadata.json"
            relative_path = f"metadata/{json_filename}"
            full_path = self.settings.STORAGE_PATH / relative_path

            # Salva JSON
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"Metadados salvos em: {relative_path}")

            return relative_path

        except Exception as e:
            logger.error(f"Erro ao salvar metadados JSON: {e}")
            raise FileStorageError(
                message="Falha ao salvar arquivo de metadados", detail=str(e)
            )

    def load_metadata_json(self, relative_path: str) -> dict:
        """
        Carrega metadados de arquivo JSON.

        Args:
            relative_path: Caminho relativo ao storage

        Returns:
            Dicionário com metadados
        """
        full_path = self.settings.STORAGE_PATH / relative_path

        if not full_path.exists():
            raise FileStorageError(
                message=f"Arquivo de metadados não encontrado: {relative_path}"
            )

        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
