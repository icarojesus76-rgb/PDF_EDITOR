"""
Modelo de domínio para AuditLog.

Registra todas as ações importantes realizadas no sistema para fins
de auditoria e conformidade. Cada registro contém informações completas
sobre quem fez, quando, o que foi feito e o resultado.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Index
from sqlalchemy.orm import relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.models.template import Template
    from app.domain.models.version import Version


class AuditAction(str, Enum):
    """Ações auditáveis do sistema."""

    TEMPLATE_UPLOAD = "TEMPLATE_UPLOAD"
    TEMPLATE_ARCHIVE = "TEMPLATE_ARCHIVE"
    TEMPLATE_DELETE = "TEMPLATE_DELETE"
    FIELD_CREATE = "FIELD_CREATE"
    FIELD_UPDATE = "FIELD_UPDATE"
    FIELD_DELETE = "FIELD_DELETE"
    PREVIEW_GENERATE = "PREVIEW_GENERATE"
    PREVIEW_CONFIRM = "PREVIEW_CONFIRM"
    PREVIEW_CANCEL = "PREVIEW_CANCEL"
    VERSION_CREATE = "VERSION_CREATE"
    VERSION_DOWNLOAD = "VERSION_DOWNLOAD"
    VERSION_ARCHIVE = "VERSION_ARCHIVE"
    VERSION_DELETE = "VERSION_DELETE"


class AuditStatus(str, Enum):
    """Status do resultado da ação."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class AuditLog(Base):
    """
    Entidade AuditLog - Registro de auditoria.

    Armazena um histórico estruturado de todas as operações importantes
    do sistema para compliance, debugging e análise de uso.

    Attributes:
        id: Identificador único
        user_id: Identificação do usuário que executou a ação
        user_email: Email do usuário (cache para quando usuário for deletado)
        action: Tipo de ação realizada
        status: Resultado da ação (success/failure/partial)
        template_id: ID do template afetado (opcional)
        version_id: ID da versão afetada (opcional)
        field_id: ID do campo afetado (opcional)
        preview_id: ID do preview afetado (opcional)
        payload: Dados relevantes da ação (JSON resumido)
        ip_address: Endereço IP do cliente
        user_agent: User agent do cliente
        request_id: ID da requisição (para correlação)
        error_message: Mensagem de erro se falhou
        created_at: Data e hora da ação
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        String(100), nullable=True, index=True, comment="ID do usuário no sistema"
    )
    user_email = Column(String(255), nullable=True, comment="Email do usuário (cache)")
    user_name = Column(String(255), nullable=True, comment="Nome do usuário (cache)")

    action = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Tipo de ação (AuditAction)",
    )
    status = Column(
        String(20),
        nullable=False,
        default=AuditStatus.SUCCESS.value,
        comment="Status da ação",
    )

    template_id = Column(
        Integer,
        nullable=True,
        index=True,
        comment="ID do template afetado",
    )
    template_name = Column(
        String(255), nullable=True, comment="Nome do template (cache)"
    )

    version_id = Column(
        Integer, nullable=True, index=True, comment="ID da versão afetada"
    )
    version_number = Column(Integer, nullable=True, comment="Número da versão (cache)")

    field_id = Column(Integer, nullable=True, index=True, comment="ID do campo afetado")
    field_name = Column(String(100), nullable=True, comment="Nome do campo (cache)")

    preview_id = Column(
        Integer, nullable=True, index=True, comment="ID do preview afetado"
    )

    payload = Column(JSON, nullable=True, comment="Dados relevantes da ação")

    ip_address = Column(String(45), nullable=True, comment="Endereço IP (IPv4 ou IPv6)")
    user_agent = Column(String(500), nullable=True, comment="User agent do cliente")
    request_id = Column(
        String(36), nullable=True, index=True, comment="ID da requisição"
    )

    error_message = Column(Text, nullable=True, comment="Mensagem de erro se falhou")

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
        comment="Data e hora da ação",
    )

    __table_args__ = (
        Index("idx_audit_template_action", "template_id", "action"),
        Index("idx_audit_user_action", "user_id", "action"),
        Index("idx_audit_created_action", "created_at", "action"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, status={self.status})>"

    def to_dict(self, include_payload: bool = True) -> dict:
        """
        Serializa o registro de auditoria.

        Args:
            include_payload: Se deve incluir o payload na serialização

        Returns:
            Dicionário com dados do registro
        """
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "action": self.action,
            "status": self.status,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "version_id": self.version_id,
            "version_number": self.version_number,
            "field_id": self.field_id,
            "field_name": self.field_name,
            "preview_id": self.preview_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        if include_payload:
            result["payload"] = self.payload

        return result
