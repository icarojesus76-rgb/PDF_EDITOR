"""
Endpoints para gerenciamento de Versões.

Implementa a API REST para operações de versionamento de PDFs.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import PDFEditorException
from app.core.logging_config import logger
from app.schemas.version_schema import (
    VersionResponse,
    VersionListResponse,
    VersionStatistics,
    VersionVerifyChecksumResponse,
)
from app.services.version_service import VersionService

router = APIRouter(
    prefix="/versions",
    tags=["Versions"],
    responses={
        500: {"description": "Erro interno do servidor"},
        422: {"description": "Erro de validação"},
    },
)


def get_version_service(db: Session = Depends(get_db)) -> VersionService:
    """Factory para injeção de dependência do VersionService."""
    return VersionService(db=db)


@router.get(
    "/template/{template_id}",
    response_model=VersionListResponse,
    summary="Lista histórico de versões",
    description="Retorna lista paginada de todas as versões de um template.",
)
async def list_versions(
    template_id: int,
    status: str | None = Query(None, description="Filtrar por status"),
    limit: int = Query(50, ge=1, le=100, description="Máximo de registros"),
    offset: int = Query(0, ge=0, description="Número de registros para pular"),
    service: VersionService = Depends(get_version_service),
) -> VersionListResponse:
    """
    Lista todas as versões de um template com paginação.

    Args:
        template_id: ID do template
        status: Filtrar por status (active, archived, superseded, draft)
        limit: Limite de resultados (padrão: 50, max: 100)
        offset: Offset para paginação

    Returns:
        VersionListResponse com lista de versões e metadados de paginação
    """
    try:
        versions, total = service.list_versions(
            template_id=template_id,
            status=status,
            limit=limit,
            offset=offset,
        )

        return VersionListResponse(
            items=[VersionResponse.model_validate(v) for v in versions],
            total=total,
            limit=limit,
            offset=offset,
        )

    except PDFEditorException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/template/{template_id}/all",
    response_model=list[VersionResponse],
    summary="Lista todas as versões",
    description="Retorna todas as versões de um template sem paginação.",
)
async def list_all_versions(
    template_id: int,
    service: VersionService = Depends(get_version_service),
) -> list[VersionResponse]:
    """
    Lista todas as versões de um template.

    Args:
        template_id: ID do template

    Returns:
        Lista completa de versões
    """
    try:
        versions = service.list_all_versions(template_id)
        return [VersionResponse.model_validate(v) for v in versions]

    except PDFEditorException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/template/{template_id}/latest",
    response_model=VersionResponse,
    summary="Busca versão mais recente",
    description="Retorna a versão mais recente de um template.",
)
async def get_latest_version(
    template_id: int,
    service: VersionService = Depends(get_version_service),
) -> VersionResponse:
    """
    Retorna a versão mais recente de um template.

    Args:
        template_id: ID do template

    Returns:
        Versão mais recente

    Raises:
        404: Se nenhuma versão existir
    """
    try:
        version = service.get_latest_version(template_id)
        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NO_VERSIONS", "message": "Nenhuma versão encontrada"},
            )
        return VersionResponse.model_validate(version)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/template/{template_id}/statistics",
    response_model=VersionStatistics,
    summary="Estatísticas de versionamento",
    description="Retorna estatísticas do histórico de versões de um template.",
)
async def get_version_statistics(
    template_id: int,
    service: VersionService = Depends(get_version_service),
) -> VersionStatistics:
    """
    Retorna estatísticas de versionamento de um template.

    Inclui:
    - Total de versões
    - Versões ativas, arquivadas e substituídas
    - Tamanho total dos arquivos
    - Número da versão mais recente

    Args:
        template_id: ID do template

    Returns:
        Estatísticas de versionamento
    """
    try:
        stats = service.get_template_statistics(template_id)
        return VersionStatistics(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/{version_id}",
    response_model=VersionResponse,
    summary="Busca versão por ID",
    description="Retorna detalhes de uma versão específica.",
)
async def get_version(
    version_id: int,
    service: VersionService = Depends(get_version_service),
) -> VersionResponse:
    """
    Retorna detalhes de uma versão pelo ID.

    Args:
        version_id: ID da versão

    Returns:
        Dados completos da versão

    Raises:
        404: Se versão não encontrada
    """
    try:
        version = service.get_version(version_id)
        return VersionResponse.model_validate(version)

    except PDFEditorException as e:
        if e.code == "VERSION_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/{version_id}/download",
    summary="Download de versão",
    description="Faz download do arquivo PDF de uma versão.",
)
async def download_version(
    version_id: int,
    service: VersionService = Depends(get_version_service),
) -> StreamingResponse:
    """
    Faz download do arquivo PDF de uma versão.

    Args:
        version_id: ID da versão

    Returns:
        Arquivo PDF como streaming response

    Raises:
        404: Se versão não encontrada ou arquivo não existir
    """
    try:
        version = service.get_version(version_id)
        pdf_bytes = service.get_version_pdf_bytes(version_id)

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{version.name}_v{version.version_number}.pdf"',
                "Content-Length": str(len(pdf_bytes)),
                "X-Version-Number": str(version.version_number),
                "X-Checksum": version.checksum,
            },
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "FILE_NOT_FOUND",
                "message": f"Arquivo da versão {version_id} não encontrado",
            },
        )
    except PDFEditorException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/{version_id}/verify",
    response_model=VersionVerifyChecksumResponse,
    summary="Verifica integridade da versão",
    description="Verifica se o arquivo não foi corrompido usando checksum SHA256.",
)
async def verify_version_checksum(
    version_id: int,
    service: VersionService = Depends(get_version_service),
) -> VersionVerifyChecksumResponse:
    """
    Verifica integridade do arquivo via checksum.

    Compara o checksum armazenado com o checksum calculado do arquivo físico.

    Args:
        version_id: ID da versão

    Returns:
        Resultado da verificação com checksums

    Raises:
        404: Se versão não encontrada
    """
    try:
        version = service.get_version(version_id)
        is_valid = service.verify_checksum(version_id)

        return VersionVerifyChecksumResponse(
            version_id=version_id,
            is_valid=is_valid,
            stored_checksum=version.checksum,
            computed_checksum=None,
            message="Checksum válido - arquivo íntegro"
            if is_valid
            else "Checksum inválido - arquivo pode estar corrompido",
        )

    except PDFEditorException as e:
        if e.code == "VERSION_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/{version_id}/lineage",
    response_model=list[dict],
    summary="Linhagem da versão",
    description="Retorna a cadeia de versões desde a raiz até esta versão.",
)
async def get_version_lineage(
    version_id: int,
    service: VersionService = Depends(get_version_service),
) -> list[dict]:
    """
    Retorna a linhagem completa de uma versão.

    Desde a primeira versão até a versão atual, mostrando
    a cadeia de descendência.

    Args:
        version_id: ID da versão

    Returns:
        Lista de versões na ordem cronológica

    Raises:
        404: Se versão não encontrada
    """
    try:
        lineage = service.get_version_lineage(version_id)

        return [
            {
                "id": v.id,
                "version_number": v.version_number,
                "name": v.name,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "created_by": v.created_by,
            }
            for v in lineage
        ]

    except PDFEditorException as e:
        if e.code == "VERSION_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/template/{template_id}/v/{version_number}",
    response_model=VersionResponse,
    summary="Busca versão por número",
    description="Retorna uma versão específica pelo número.",
)
async def get_version_by_number(
    template_id: int,
    version_number: int,
    service: VersionService = Depends(get_version_service),
) -> VersionResponse:
    """
    Retorna uma versão específica pelo número.

    Args:
        template_id: ID do template
        version_number: Número da versão

    Returns:
        Dados da versão

    Raises:
        404: Se versão não encontrada
    """
    try:
        version = service.get_version_by_number(template_id, version_number)
        return VersionResponse.model_validate(version)

    except PDFEditorException as e:
        if e.code == "VERSION_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )
