"""
Schemas Pydantic para Auditoria.

Define os schemas de entrada/saída para operações de auditoria.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.domain.models.audit_log import AuditAction, AuditStatus


class AuditLogBase(BaseModel):
    """Schema base para AuditLog."""

    user_id: Optional[str] = Field(None, description="ID do usuário")
    user_email: Optional[str] = Field(None, description="Email do usuário")
    user_name: Optional[str] = Field(None, description="Nome do usuário")
    action: str = Field(..., description="Tipo de ação")
    status: str = Field(..., description="Status da ação")


class AuditLogResponse(AuditLogBase):
    """Schema de resposta para AuditLog."""

    id: int = Field(..., description="ID único do registro")
    template_id: Optional[int] = Field(None, description="ID do template afetado")
    template_name: Optional[str] = Field(None, description="Nome do template")
    version_id: Optional[int] = Field(None, description="ID da versão afetada")
    version_number: Optional[int] = Field(None, description="Número da versão")
    field_id: Optional[int] = Field(None, description="ID do campo afetado")
    field_name: Optional[str] = Field(None, description="Nome do campo")
    preview_id: Optional[int] = Field(None, description="ID do preview afetado")
    payload: Optional[dict[str, Any]] = Field(None, description="Dados da ação")
    ip_address: Optional[str] = Field(None, description="Endereço IP")
    user_agent: Optional[str] = Field(None, description="User agent")
    request_id: Optional[str] = Field(None, description="ID da requisição")
    error_message: Optional[str] = Field(None, description="Mensagem de erro")
    created_at: datetime = Field(..., description="Data e hora da ação")

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Schema para listagem de logs de auditoria."""

    items: list[AuditLogResponse]
    total: int = Field(..., description="Total de registros")
    limit: int = Field(..., description="Limite por página")
    offset: int = Field(..., description="Offset")


class AuditLogFilter(BaseModel):
    """Schema para filtros de consulta de auditoria."""

    template_id: Optional[int] = Field(None, description="Filtrar por template")
    version_id: Optional[int] = Field(None, description="Filtrar por versão")
    user_id: Optional[str] = Field(None, description="Filtrar por usuário")
    action: Optional[AuditAction] = Field(None, description="Filtrar por ação")
    status: Optional[AuditStatus] = Field(None, description="Filtrar por status")
    start_date: Optional[datetime] = Field(None, description="Data inicial")
    end_date: Optional[datetime] = Field(None, description="Data final")
    limit: int = Field(50, ge=1, le=100, description="Limite de resultados")
    offset: int = Field(0, ge=0, description="Offset")


class AuditSummaryResponse(BaseModel):
    """Schema para resumo de auditoria."""

    total_actions: int = Field(..., description="Total de ações")
    actions_by_type: dict[str, int] = Field(..., description="Ações por tipo")
    actions_by_status: dict[str, int] = Field(..., description="Ações por status")
    actions_by_user: dict[str, int] = Field(..., description="Ações por usuário")
    template_id: Optional[int] = Field(None, description="ID do template")
    period_start: Optional[datetime] = Field(None, description="Início do período")
    period_end: Optional[datetime] = Field(None, description="Fim do período")


class AuditContextRequest(BaseModel):
    """Schema para contexto de auditoria (recebido via headers/cookies)."""

    user_id: Optional[str] = Field(None, description="ID do usuário")
    user_email: Optional[str] = Field(None, description="Email do usuário")
    user_name: Optional[str] = Field(None, description="Nome do usuário")
    ip_address: Optional[str] = Field(None, description="Endereço IP")
    user_agent: Optional[str] = Field(None, description="User agent")
    request_id: Optional[str] = Field(None, description="ID da requisição")
