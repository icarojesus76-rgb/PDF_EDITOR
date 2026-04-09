"""
Modelo de domínio para Version de PDF.

Cada versão representa uma edição derivada de um template.
O versionamento é hierárquico: cada versão pode ser base de uma nova versão.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
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
        file_path: Caminho do arquivo PDF gerado
        file_size: Tamanho em bytes
        checksum: Hash SHA256 do arquivo (verificação de integridade)
        field_data: Dados usados no preenchimento (JSON)
        created_by: Usuário responsável pela criação
        observation: Observação opcional
        changes_summary: Resumo das alterações realizadas
        status: Estado atual da versão
        created_at: Data de criação
        updated_at: Data da última atualização
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
    checksum = Column(String(64), nullable=False, comment="SHA256 hash for integrity")
    field_data = Column(JSON, nullable=True, comment="Dados do preenchimento")
    created_by = Column(String(100), nullable=True, comment="Usuário responsável")
    observation = Column(Text, nullable=True, comment="Observação opcional")
    changes_summary = Column(Text, nullable=True)
    status = Column(String(50), default=VersionStatus.DRAFT.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

    @property
    def file_exists(self) -> bool:
        """Verifica se o arquivo físico existe."""
        from pathlib import Path
        from app.core.config import get_settings

        settings = get_settings()
        return (settings.STORAGE_PATH / self.file_path).exists()

    def to_dict(self, include_file_url: bool = False) -> dict:
        """Serializa a versão para dicionário (API response)."""
        result = {
            "id": self.id,
            "template_id": self.template_id,
            "parent_version_id": self.parent_version_id,
            "version_number": self.version_number,
            "name": self.name,
            "description": self.description,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "field_data": self.field_data,
            "created_by": self.created_by,
            "observation": self.observation,
            "changes_summary": self.checksum,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "file_exists": self.file_exists,
        }

        if include_file_url:
            from app.core.config import get_settings

            settings = get_settings()
            result["file_url"] = f"/api/v1/versions/{self.id}/download"

        return result
