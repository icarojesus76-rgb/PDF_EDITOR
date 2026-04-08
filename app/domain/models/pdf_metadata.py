"""
Modelo de domínio para Metadados de PDF.

Armazena informações estruturadas sobre o layout e conteúdo
de cada página do PDF template. Usado para preparar campos
editáveis sem modificar o arquivo original.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.models.template import Template


class PDFMetadata(Base):
    """
    Entidade PDFMetadata - Metadados extraídos do PDF.

    Contém informações detalhadas sobre o layout, dimensões,
    textos e elementos visuais de cada página do template.

    Os metadados são imutáveis (sincronizados com o template)
    e servem de base para posicionamento de campos editáveis.

    Attributes:
        id: Identificador único
        template_id: FK para o template
        page_count: Quantidade total de páginas
        metadata_json_path: Caminho do arquivo JSON com metadados completos
        extracted_at: Data da extração
        page_dimensions: Dimensões de cada página (JSON)
    """

    __tablename__ = "pdf_metadata"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Um metadata por template
        index=True,
    )

    # Informações gerais
    page_count = Column(Integer, nullable=False)
    pdf_version = Column(String(10), nullable=True)
    title = Column(String(500), nullable=True)
    author = Column(String(255), nullable=True)
    creator = Column(String(255), nullable=True)
    producer = Column(String(255), nullable=True)

    # Caminho para arquivo JSON com metadados detalhados
    metadata_json_path = Column(String(1000), nullable=False)

    # Dimensões das páginas (formato: [{"page": 0, "width": 595, "height": 842}, ...])
    page_dimensions = Column(JSON, nullable=False)

    # Estatísticas
    total_text_blocks = Column(Integer, default=0)
    total_images = Column(Integer, default=0)
    total_forms = Column(Integer, default=0)

    # Timestamps
    extracted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    template = relationship("Template", back_populates="metadata")
    pages = relationship(
        "PDFPageMetadata",
        back_populates="pdf_metadata",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<PDFMetadata(id={self.id}, template={self.template_id}, pages={self.page_count})>"


class PDFPageMetadata(Base):
    """
    Entidade PDFPageMetadata - Metadados de uma página específica.

    Contém informações detalhadas de uma única página,
    incluindo textos, blocos e elementos visuais.
    """

    __tablename__ = "pdf_page_metadata"

    id = Column(Integer, primary_key=True, index=True)
    pdf_metadata_id = Column(
        Integer,
        ForeignKey("pdf_metadata.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Informações da página
    page_number = Column(Integer, nullable=False)  # 0-indexed
    width = Column(Integer, nullable=False)  # em pontos (1/72 polegada)
    height = Column(Integer, nullable=False)  # em pontos
    rotation = Column(Integer, default=0)  # Rotação em graus

    # Conteúdo textual (JSON com blocos de texto)
    text_blocks = Column(JSON, default=list)

    # Imagens na página (JSON com bounding boxes)
    images = Column(JSON, default=list)

    # Formulários/fields na página
    form_fields = Column(JSON, default=list)

    # Anotações
    annotations = Column(JSON, default=list)

    # Relacionamentos
    pdf_metadata = relationship("PDFMetadata", back_populates="pages")

    def __repr__(self) -> str:
        return f"<PDFPageMetadata(page={self.page_number}, blocks={len(self.text_blocks or [])})>"

    def to_dict(self) -> dict:
        """Serializa página para dicionário."""
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "text_blocks": self.text_blocks,
            "images": self.images,
            "form_fields": self.form_fields,
            "annotations": self.annotations,
        }
