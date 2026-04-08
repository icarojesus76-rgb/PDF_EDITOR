"""
Modelo de domínio para Version de PDF.

Cada versão representa uma edição derivada de um template.
O versionamento é hierárquico: cada versão pode ser base de uma nova versão.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.models.template import Template


class VersionStatus(str, Enum):
    """Status possíveis de uma versão."""

    DRAFT = "draft"  # Versão em elaboração
    ACTIVE = "active"  # Versão ativa/atual
    ARCHIVED = "archived"  # Versão arquivada
    SUPERSEDED = "superseded"  # Versão substituída por nova


class Version(Base):
    """
    Entidade Version - Representa uma edição derivada do template.

    Cada versão é uma cópia derivada do template original ou de outra versão.
    Mantém rastreamento completo da linhagem do documento.

    Attributes:
        id: Identificador único
        template_id: ID do template raiz (nunca muda)
        parent_version_id: ID da versão pai (null se base do template)
        version_number: Número sequencial (1, 2, 3...)
        name: Nome/descrição da versão
        description: Descrição das mudanças
        file_path: Caminho do arquivo PDF gerado
        file_size: Tamanho em bytes
        changes_summary: Resumo das alterações realizadas
        status: Estado atual da versão
        created_at: Data de criação
    """

    __tablename__ = "versions"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_version_id = Column(
        Integer,
        ForeignKey("versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version_number = Column(Integer, nullable=False, default=1)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=False)
    changes_summary = Column(Text, nullable=True)
    status = Column(String(50), default=VersionStatus.DRAFT.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relacionamentos
    template = relationship("Template", back_populates="versions")
    parent_version = relationship(
        "Version", remote_side=[id], foreign_keys=[parent_version_id]
    )

    def __repr__(self) -> str:
        return f"<Version(id={self.id}, v{self.version_number}, template={self.template_id})>"

    @property
    def full_version_name(self) -> str:
        """Retorna nome completo da versão: v1, v2, etc."""
        return f"v{self.version_number}"

    def to_dict(self) -> dict:
        """Serializa a versão para dicionário (API response)."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "parent_version_id": self.parent_version_id,
            "version_number": self.version_number,
            "name": self.name,
            "description": self.description,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "changes_summary": self.changes_summary,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
