"""
Modelo de domínio para Template de PDF.

Um Template representa o PDF original enviado pelo usuário.
Este arquivo NUNCA pode ser modificado após o upload - é a raiz
imutável de todas as versões derivadas.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.models.version import Version
    from app.domain.models.pdf_metadata import PDFMetadata
    from app.domain.models.field import Field


class TemplateStatus(str, Enum):
    """Status possíveis de um template."""

    ACTIVE = "active"  # Template ativo, pode gerar versões
    ARCHIVED = "archived"  # Template arquivado (soft delete)
    DELETED = "deleted"  # Template deletado


class Template(Base):
    """
    Entidade Template - Representa um PDF original uploaded.

    Este modelo é a raiz de todo o versionamento. O arquivo original
    armazenado em TEMPLATES_PATH nunca é modificado ou sobrescrito.

    Attributes:
        id: Identificador único
        name: Nome original do arquivo (sem caminho)
        original_filename: Nome completo com extensão
        file_path: Caminho relativo ao storage (para portabilidade)
        file_size: Tamanho em bytes
        checksum: Hash SHA256 do arquivo (verificação de integridade)
        status: Estado atual do template
        created_at: Data de upload (imutável)
        updated_at: Data da última modificação no registro
    """

    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=False, comment="SHA256 hash for integrity")
    status = Column(
        SQLEnum(TemplateStatus, name="template_status"),
        default=TemplateStatus.ACTIVE,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    versions = relationship(
        "Version",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    metadata = relationship(
        "PDFMetadata",
        back_populates="template",
        uselist=False,  # One-to-one
        cascade="all, delete-orphan",
    )
    fields = relationship(
        "Field",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="Field.order, Field.id",
    )

    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name='{self.name}', status={self.status})>"

    @property
    def version_count(self) -> int:
        """Retorna quantidade de versões geradas a partir deste template."""
        return self.versions.count()

    def to_dict(self) -> dict:
        """Serializa o template para dicionário (API response)."""
        return {
            "id": self.id,
            "name": self.name,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
            if self.updated_at is not None
            else None,
            "version_count": self.version_count,
        }
