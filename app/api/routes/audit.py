"""
Endpoints para Auditoria.

Implementa a API REST para consulta de logs de auditoria.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging_config import logger
from app.domain.models.audit_log import AuditAction, AuditStatus
from app.schemas.audit_schema import (
    AuditLogFilter,
    AuditLogListResponse,
    AuditLogResponse,
    AuditSummaryResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
    responses={
        500: {"description": "Erro interno do servidor"},
        422: {"description": "Erro de validação"},
    },
)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Factory para injeção de dependência do AuditService."""
    return AuditService(db=db)


@router.get(
    "/",
    response_model=AuditLogListResponse,
    summary="Consultar logs de auditoria",
    description="Retorna lista paginada de logs de auditoria com filtros.",
)
async def query_audit_logs(
    template_id: Optional[int] = Query(None, description="Filtrar por template"),
    version_id: Optional[int] = Query(None, description="Filtrar por versão"),
    user_id: Optional[str] = Query(None, description="Filtrar por usuário"),
    action: Optional[str] = Query(None, description="Filtrar por tipo de ação"),
    status_filter: Optional[str] = Query(None, description="Filtrar por status"),
    start_date: Optional[datetime] = Query(None, description="Data inicial"),
    end_date: Optional[datetime] = Query(None, description="Data final"),
    limit: int = Query(50, ge=1, le=100, description="Máximo de registros"),
    offset: int = Query(0, ge=0, description="Número de registros para pular"),
    service: AuditService = Depends(get_audit_service),
) -> AuditLogListResponse:
    """
    Consulta logs de auditoria com filtros.

    Args:
        template_id: Filtrar por template
        version_id: Filtrar por versão
        user_id: Filtrar por usuário
        action: Filtrar por tipo de ação (TEMPLATE_UPLOAD, FIELD_CREATE, etc.)
        status_filter: Filtrar por status (success, failure, partial)
        start_date: Data inicial
        end_date: Data final
        limit: Limite de resultados (padrão: 50, max: 100)
        offset: Offset para paginação

    Returns:
        Lista paginada de logs de auditoria
    """
    try:
        action_enum = None
        if action:
            try:
                action_enum = AuditAction(action)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action: {action}. Valid values: {[a.value for a in AuditAction]}",
                )

        status_enum = None
        if status_filter:
            try:
                status_enum = AuditStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}. Valid values: {[s.value for s in AuditStatus]}",
                )

        logs, total = service.query_logs(
            template_id=template_id,
            version_id=version_id,
            user_id=user_id,
            action=action_enum,
            status=status_enum,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total,
            limit=limit,
            offset=offset,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/template/{template_id}",
    response_model=AuditLogListResponse,
    summary="Auditoria de template",
    description="Retorna histórico de auditoria de um template específico.",
)
async def get_template_audit_trail(
    template_id: int,
    limit: int = Query(50, ge=1, le=100, description="Máximo de registros"),
    offset: int = Query(0, ge=0, description="Número de registros para pular"),
    service: AuditService = Depends(get_audit_service),
) -> AuditLogListResponse:
    """
    Retorna histórico de auditoria de um template.

    Args:
        template_id: ID do template
        limit: Limite de resultados
        offset: Offset para paginação

    Returns:
        Lista de ações realizadas no template
    """
    try:
        logs, total = service.get_template_audit_trail(
            template_id=template_id,
            limit=limit,
            offset=offset,
        )

        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Error getting template audit trail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/user/{user_id}",
    response_model=AuditLogListResponse,
    summary="Atividade do usuário",
    description="Retorna histórico de atividades de um usuário específico.",
)
async def get_user_activity(
    user_id: str,
    limit: int = Query(50, ge=1, le=100, description="Máximo de registros"),
    offset: int = Query(0, ge=0, description="Número de registros para pular"),
    service: AuditService = Depends(get_audit_service),
) -> AuditLogListResponse:
    """
    Retorna atividade de um usuário.

    Args:
        user_id: ID do usuário
        limit: Limite de resultados
        offset: Offset para paginação

    Returns:
        Lista de ações realizadas pelo usuário
    """
    try:
        logs, total = service.get_user_activity(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Error getting user activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/summary",
    response_model=AuditSummaryResponse,
    summary="Resumo de auditoria",
    description="Retorna estatísticas agregadas dos logs de auditoria.",
)
async def get_audit_summary(
    template_id: Optional[int] = Query(None, description="Filtrar por template"),
    start_date: Optional[datetime] = Query(None, description="Data inicial"),
    end_date: Optional[datetime] = Query(None, description="Data final"),
    service: AuditService = Depends(get_audit_service),
) -> AuditSummaryResponse:
    """
    Retorna resumo de auditoria.

    Inclui contagem de ações por tipo, status e usuário.

    Args:
        template_id: Filtrar por template
        start_date: Data inicial
        end_date: Data final

    Returns:
        Resumo estatístico
    """
    try:
        logs, _ = service.query_logs(
            template_id=template_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,
            offset=0,
        )

        actions_by_type: dict[str, int] = {}
        actions_by_status: dict[str, int] = {}
        actions_by_user: dict[str, int] = {}

        for log in logs:
            actions_by_type[log.action] = actions_by_type.get(log.action, 0) + 1
            actions_by_status[log.status] = actions_by_status.get(log.status, 0) + 1
            if log.user_id:
                actions_by_user[log.user_id] = actions_by_user.get(log.user_id, 0) + 1

        return AuditSummaryResponse(
            total_actions=len(logs),
            actions_by_type=actions_by_type,
            actions_by_status=actions_by_status,
            actions_by_user=actions_by_user,
            template_id=template_id,
            period_start=start_date,
            period_end=end_date,
        )

    except Exception as e:
        logger.error(f"Error getting audit summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
