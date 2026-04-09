"""
Serviço centralizado de Auditoria.

Fornece API unificada para registro de logs de auditoria em todas
as operações do sistema. Implementa logging assíncrono, tratamento
de falhas e resiliência.
"""

import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.logging_config import logger
from app.domain.models.audit_log import AuditAction, AuditLog, AuditStatus


class AuditService:
    """
    Serviço para gerenciamento de logs de auditoria.

    Responsabilidades:
    - Registro assíncrono de ações auditáveis
    - Contexto de requisição (usuário, IP, etc.)
    - Resiliência em caso de falhas
    - Consulta e agregação de logs
    """

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: AuditAction,
        status: AuditStatus = AuditStatus.SUCCESS,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        template_id: Optional[int] = None,
        template_name: Optional[str] = None,
        version_id: Optional[int] = None,
        version_number: Optional[int] = None,
        field_id: Optional[int] = None,
        field_name: Optional[str] = None,
        preview_id: Optional[int] = None,
        payload: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        """
        Registra uma ação de auditoria.

        Args:
            action: Tipo de ação realizada
            status: Resultado da ação
            user_id: ID do usuário
            user_email: Email do usuário
            user_name: Nome do usuário
            template_id: ID do template afetado
            template_name: Nome do template (cache)
            version_id: ID da versão afetada
            version_number: Número da versão (cache)
            field_id: ID do campo afetado
            field_name: Nome do campo (cache)
            preview_id: ID do preview afetado
            payload: Dados relevantes da ação
            ip_address: Endereço IP do cliente
            user_agent: User agent do cliente
            request_id: ID da requisição
            error_message: Mensagem de erro se falhou

        Returns:
            AuditLog criado
        """
        try:
            sanitized_payload = self._sanitize_payload(payload)

            audit_log = AuditLog(
                user_id=user_id,
                user_email=user_email,
                user_name=user_name,
                action=action.value,
                status=status.value,
                template_id=template_id,
                template_name=template_name,
                version_id=version_id,
                version_number=version_number,
                field_id=field_id,
                field_name=field_name,
                preview_id=preview_id,
                payload=sanitized_payload,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                error_message=error_message,
                created_at=datetime.utcnow(),
            )

            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)

            logger.debug(f"Audit log created: {action.value} - {status.value}")
            return audit_log

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            self.db.rollback()
            raise

    def log_success(
        self,
        action: AuditAction,
        **kwargs: Any,
    ) -> AuditLog:
        """Registra uma ação bem-sucedida."""
        return self.log(action=action, status=AuditStatus.SUCCESS, **kwargs)

    def log_failure(
        self,
        action: AuditAction,
        error_message: str,
        **kwargs: Any,
    ) -> AuditLog:
        """Registra uma ação que falhou."""
        return self.log(
            action=action,
            status=AuditStatus.FAILURE,
            error_message=error_message,
            **kwargs,
        )

    def log_template_upload(
        self,
        template_id: int,
        template_name: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        **kwargs: Any,
    ) -> AuditLog:
        """Registra upload de template."""
        return self.log(
            action=AuditAction.TEMPLATE_UPLOAD,
            template_id=template_id,
            template_name=template_name,
            user_id=user_id,
            user_email=user_email,
            payload={
                "filename": template_name,
                "size_kb": kwargs.get("file_size", 0) / 1024,
            },
            **kwargs,
        )

    def log_field_create(
        self,
        field_id: int,
        field_name: str,
        template_id: int,
        field_data: dict,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AuditLog:
        """Registra criação de campo."""
        return self.log(
            action=AuditAction.FIELD_CREATE,
            field_id=field_id,
            field_name=field_name,
            template_id=template_id,
            user_id=user_id,
            payload={
                "field_name": field_name,
                "field_type": field_data.get("field_type"),
                "page": field_data.get("page"),
            },
            **kwargs,
        )

    def log_field_update(
        self,
        field_id: int,
        field_name: str,
        template_id: int,
        changes: dict,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AuditLog:
        """Registra atualização de campo."""
        return self.log(
            action=AuditAction.FIELD_UPDATE,
            field_id=field_id,
            field_name=field_name,
            template_id=template_id,
            user_id=user_id,
            payload={"changes": list(changes.keys())},
            **kwargs,
        )

    def log_preview_generate(
        self,
        preview_id: int,
        template_id: int,
        field_count: int,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AuditLog:
        """Registra geração de preview."""
        return self.log(
            action=AuditAction.PREVIEW_GENERATE,
            preview_id=preview_id,
            template_id=template_id,
            user_id=user_id,
            payload={"field_count": field_count},
            **kwargs,
        )

    def log_version_create(
        self,
        version_id: int,
        version_number: int,
        template_id: int,
        template_name: str,
        field_count: int,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AuditLog:
        """Registra criação de versão."""
        return self.log(
            action=AuditAction.VERSION_CREATE,
            version_id=version_id,
            version_number=version_number,
            template_id=template_id,
            template_name=template_name,
            user_id=user_id,
            payload={
                "version_number": version_number,
                "field_count": field_count,
            },
            **kwargs,
        )

    def log_version_download(
        self,
        version_id: int,
        version_number: int,
        template_id: int,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> AuditLog:
        """Registra download de versão."""
        return self.log(
            action=AuditAction.VERSION_DOWNLOAD,
            version_id=version_id,
            version_number=version_number,
            template_id=template_id,
            user_id=user_id,
            payload={"version_number": version_number},
            **kwargs,
        )

    def query_logs(
        self,
        template_id: Optional[int] = None,
        version_id: Optional[int] = None,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        status: Optional[AuditStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """
        Consulta logs de auditoria com filtros.

        Args:
            template_id: Filtrar por template
            version_id: Filtrar por versão
            user_id: Filtrar por usuário
            action: Filtrar por tipo de ação
            status: Filtrar por status
            start_date: Data inicial
            end_date: Data final
            limit: Limite de resultados
            offset: Offset para paginação

        Returns:
            Tupla (lista de logs, total)
        """
        query = self.db.query(AuditLog)

        if template_id:
            query = query.filter(AuditLog.template_id == template_id)
        if version_id:
            query = query.filter(AuditLog.version_id == version_id)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action.value)
        if status:
            query = query.filter(AuditLog.status == status.value)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        total = query.count()

        logs = (
            query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
        )

        return logs, total

    def get_template_audit_trail(
        self,
        template_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retorna histórico de auditoria de um template."""
        return self.query_logs(
            template_id=template_id,
            limit=limit,
            offset=offset,
        )

    def get_user_activity(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AuditLog], int]:
        """Retorna atividade de um usuário."""
        return self.query_logs(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    def _sanitize_payload(self, payload: Optional[dict]) -> Optional[dict]:
        """Remove dados sensíveis do payload."""
        if not payload:
            return None

        sensitive_keys = {"password", "token", "secret", "api_key", "authorization"}
        sanitized = {}

        for key, value in payload.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_payload(value)
            else:
                sanitized[key] = value

        return sanitized if sanitized else None


class AuditContext:
    """
    Gerenciador de contexto para auditoria.

    Uso:
        with AuditContext(db, user_id="123", ip="192.168.1.1") as ctx:
            audit_service.log(AuditAction.TEMPLATE_UPLOAD, context=ctx, ...)
    """

    def __init__(
        self,
        db: Session,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.db = db
        self.user_id = user_id
        self.user_email = user_email
        self.user_name = user_name
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.request_id = request_id or str(uuid.uuid4())
        self._audit_service: Optional[AuditService] = None

    def __enter__(self) -> "AuditContext":
        self._audit_service = AuditService(self.db)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    @property
    def audit(self) -> AuditService:
        """Retorna o serviço de auditoria."""
        if not self._audit_service:
            self._audit_service = AuditService(self.db)
        return self._audit_service

    def log(
        self,
        action: AuditAction,
        status: AuditStatus = AuditStatus.SUCCESS,
        **kwargs: Any,
    ) -> AuditLog:
        """Loga ação usando o contexto atual."""
        return self.audit.log(
            action=action,
            status=status,
            user_id=self.user_id,
            user_email=self.user_email,
            user_name=self.user_name,
            ip_address=self.ip_address,
            user_agent=self.user_agent,
            request_id=self.request_id,
            **kwargs,
        )


@contextmanager
def audit_context(
    db: Session,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    user_name: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Generator[AuditContext, None, None]:
    """
    Context manager para auditoria.

    Usage:
        with audit_context(db, user_id="123", ip_address="...") as ctx:
            ctx.log(AuditAction.TEMPLATE_UPLOAD, template_id=1, ...)
    """
    ctx = AuditContext(
        db=db,
        user_id=user_id,
        user_email=user_email,
        user_name=user_name,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
    yield ctx
