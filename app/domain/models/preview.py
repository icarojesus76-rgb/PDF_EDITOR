"""
Modelo de domínio para Preview de PDF.

Armazena pré-visualizações temporárias que podem ser confirmadas
para geração de versão oficial ou descartadas.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.models.template import Template


class PreviewStatus(str, Enum):
    """Status possíveis de um preview."""

    PENDING = "pending"  # Preview gerado, aguardando confirmação
    CONFIRMED = "confirmed"  # Confirmado - convertido para versão
    EXPIRED = "expired"  # Expirado - descartado automaticamente
    CANCELLED = "cancelled"  # Cancelado pelo usuário


class Preview(Base):
    """
    Entidade Preview - Pré-visualização temporária de PDF.

    Armazena dados temporários antes da confirmação para geração
    de versão oficial. O preview pode ser confirmado (cria versão)
    ou cancelado (descarta o preview).

    Attributes:
        id: Identificador único
        template_id: ID do template base
        preview_token: Token único para acesso ao preview
        field_data: Dados do preenchimento
        pdf_path: Caminho do PDF temporário
        image_paths: Caminhos das imagens por página (opcional)
        file_size: Tamanho em bytes
        created_by: Usuário que criou o preview
        status: Estado atual do preview
        expires_at: Data de expiração
        created_at: Data de criação
        confirmed_at: Data de confirmação (se confirmado)
        version_id: ID da versão criada (se confirmado)
    """

    __tablename__ = "previews"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    preview_token = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="Token único para acesso",
    )
    field_data = Column(JSON, nullable=False, comment="Dados do preenchimento")
    pdf_path = Column(String(1000), nullable=False, comment="Caminho do PDF temporário")
    image_paths = Column(JSON, nullable=True, comment="Caminhos das imagens por página")
    file_size = Column(Integer, nullable=False, comment="Tamanho em bytes")
    created_by = Column(String(100), nullable=True, comment="Usuário responsável")
    status = Column(String(20), default=PreviewStatus.PENDING.value, nullable=False)
    expires_at = Column(DateTime, nullable=False, comment="Data de expiração")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True, comment="Data de confirmação")
    version_id = Column(
        Integer,
        ForeignKey("versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Versão criada a partir deste preview",
    )

    # Relacionamentos
    template = relationship("Template", back_populates="previews")
    version = relationship("Version", foreign_keys=[version_id])

    def __repr__(self) -> str:
        return f"<Preview(id={self.id}, template={self.template_id}, status={self.status})>"

    @property
    def is_expired(self) -> bool:
        """Verifica se o preview expirou."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_active(self) -> bool:
        """Verifica se o preview está ativo (pendente)."""
        return self.status == PreviewStatus.PENDING.value and not self.is_expired

    def to_dict(self, include_token: bool = False) -> dict:
        """Serializa o preview para dicionário."""
        result = {
            "id": self.id,
            "template_id": self.template_id,
            "field_data": self.field_data,
            "pdf_path": self.pdf_path,
            "image_paths": self.image_paths,
            "file_size": self.file_size,
            "created_by": self.created_by,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "confirmed_at": self.confirmed_at.isoformat()
            if self.confirmed_at
            else None,
            "version_id": self.version_id,
            "is_expired": self.is_expired,
            "is_active": self.is_active,
        }

        if include_token:
            result["preview_token"] = self.preview_token

        return result
