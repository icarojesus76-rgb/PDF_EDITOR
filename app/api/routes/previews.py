"""
Endpoints para gerenciamento de Previews.

Implementa a API REST para operações de pré-visualização de PDFs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import PDFEditorException
from app.core.logging_config import logger
from app.schemas.preview_schema import (
    PreviewCreateRequest,
    PreviewConfirmRequest,
    PreviewResponse,
    PreviewTokenResponse,
    PreviewConfirmResponse,
    PreviewCancelResponse,
    PreviewListResponse,
)
from app.services.preview_service import PreviewService

router = APIRouter(
    prefix="/previews",
    tags=["Previews"],
    responses={
        500: {"description": "Erro interno do servidor"},
        422: {"description": "Erro de validação"},
    },
)


def get_preview_service(db: Session = Depends(get_db)) -> PreviewService:
    """Factory para injeção de dependência do PreviewService."""
    return PreviewService(db=db)


@router.post(
    "/",
    response_model=PreviewTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar preview",
    description="Cria uma pré-visualização temporária com os valores fornecidos.",
)
async def create_preview(
    request: PreviewCreateRequest,
    service: PreviewService = Depends(get_preview_service),
) -> PreviewTokenResponse:
    """
    Cria uma nova pré-visualização temporária.

    O preview é salvo temporariamente e pode ser:
    - Confirmado para gerar versão oficial
    - Cancelado para descartar

    Args:
        request: Dados do preview (template_id, field_values, etc.)

    Returns:
        PreviewTokenResponse com token de acesso
    """
    try:
        preview = service.create_preview(
            template_id=request.template_id,
            field_values=request.field_values,
            created_by=request.created_by,
            generate_images=request.generate_images,
            validate_fields=request.validate_fields,
            skip_validation=request.skip_validation,
        )

        return PreviewTokenResponse(
            preview=PreviewResponse.model_validate(preview),
            token=preview.preview_token,
        )

    except PDFEditorException as e:
        status_map = {
            "TEMPLATE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "PREVIEW_RENDER_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "FIELD_VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        }
        http_status = status_map.get(e.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(status_code=http_status, detail=e.to_dict())


@router.get(
    "/{preview_id}",
    response_model=PreviewResponse,
    summary="Buscar preview por ID",
    description="Retorna detalhes de um preview específico.",
)
async def get_preview(
    preview_id: int,
    service: PreviewService = Depends(get_preview_service),
) -> PreviewResponse:
    """
    Retorna detalhes de um preview pelo ID.

    Args:
        preview_id: ID do preview

    Returns:
        Dados do preview

    Raises:
        404: Se preview não encontrado
    """
    try:
        preview = service.get_preview(preview_id)
        return PreviewResponse.model_validate(preview)

    except PDFEditorException as e:
        if e.code == "PREVIEW_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/token/{token}",
    response_model=PreviewResponse,
    summary="Buscar preview por token",
    description="Retorna detalhes de um preview pelo token.",
)
async def get_preview_by_token(
    token: str,
    service: PreviewService = Depends(get_preview_service),
) -> PreviewResponse:
    """
    Retorna detalhes de um preview pelo token.

    Args:
        token: Token único do preview

    Returns:
        Dados do preview

    Raises:
        404: Se preview não encontrado
    """
    try:
        preview = service.get_preview_by_token(token)
        return PreviewResponse.model_validate(preview)

    except PDFEditorException as e:
        if e.code == "PREVIEW_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/{preview_id}/download",
    summary="Download do PDF de preview",
    description="Faz download do arquivo PDF temporário do preview.",
)
async def download_preview_pdf(
    preview_id: int,
    service: PreviewService = Depends(get_preview_service),
) -> StreamingResponse:
    """
    Faz download do PDF do preview.

    Args:
        preview_id: ID do preview

    Returns:
        Arquivo PDF como streaming response
    """
    try:
        pdf_bytes = service.get_preview_pdf_bytes(preview_id)

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="preview_{preview_id}.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )

    except PDFEditorException as e:
        if e.code in (
            "PREVIEW_NOT_FOUND",
            "PREVIEW_EXPIRED",
            "PREVIEW_ALREADY_CONFIRMED",
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/{preview_id}/images",
    response_model=list[str],
    summary="Listar imagens do preview",
    description="Retorna URLs das imagens geradas para cada página.",
)
async def get_preview_images(
    preview_id: int,
    service: PreviewService = Depends(get_preview_service),
) -> list[str]:
    """
    Retorna os caminhos das imagens do preview.

    Args:
        preview_id: ID do preview

    Returns:
        Lista de caminhos das imagens
    """
    try:
        preview = service.get_preview(preview_id)

        if not preview.image_paths:
            return []

        return preview.image_paths

    except PDFEditorException as e:
        if e.code == "PREVIEW_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.post(
    "/{preview_id}/confirm",
    response_model=PreviewConfirmResponse,
    summary="Confirmar preview",
    description="Confirma o preview e gera versão oficial.",
)
async def confirm_preview(
    preview_id: int,
    request: PreviewConfirmRequest,
    service: PreviewService = Depends(get_preview_service),
) -> PreviewConfirmResponse:
    """
    Confirma um preview e gera versão oficial.

    Args:
        preview_id: ID do preview
        request: Dados para a versão (nome, descrição)

    Returns:
        ID e número da versão criada
    """
    try:
        version = service.confirm_preview(
            preview_id=preview_id,
            version_name=request.version_name,
            description=request.description,
        )

        return PreviewConfirmResponse(
            version_id=version.id,
            version_number=version.version_number,
        )

    except PDFEditorException as e:
        status_map = {
            "PREVIEW_NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "PREVIEW_EXPIRED": status.HTTP_410_GONE,
            "PREVIEW_ALREADY_CONFIRMED": status.HTTP_409_CONFLICT,
        }
        http_status = status_map.get(e.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(status_code=http_status, detail=e.to_dict())


@router.post(
    "/{preview_id}/cancel",
    response_model=PreviewCancelResponse,
    summary="Cancelar preview",
    description="Cancela e descarta um preview.",
)
async def cancel_preview(
    preview_id: int,
    service: PreviewService = Depends(get_preview_service),
) -> PreviewCancelResponse:
    """
    Cancela um preview e descarta os arquivos temporários.

    Args:
        preview_id: ID do preview

    Returns:
        Confirmação do cancelamento
    """
    try:
        service.cancel_preview(preview_id)

        return PreviewCancelResponse(preview_id=preview_id)

    except PDFEditorException as e:
        status_map = {
            "PREVIEW_NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "PREVIEW_ALREADY_CONFIRMED": status.HTTP_409_CONFLICT,
        }
        http_status = status_map.get(e.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(status_code=http_status, detail=e.to_dict())


@router.get(
    "/template/{template_id}/active",
    response_model=PreviewListResponse,
    summary="Listar previews ativos",
    description="Lista previews pendentes de um template.",
)
async def list_active_previews(
    template_id: int,
    service: PreviewService = Depends(get_preview_service),
) -> PreviewListResponse:
    """
    Lista previews ativos de um template.

    Args:
        template_id: ID do template

    Returns:
        Lista de previews ativos
    """
    try:
        previews = service.list_active_previews(template_id)

        return PreviewListResponse(
            items=[PreviewResponse.model_validate(p) for p in previews],
            total=len(previews),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post(
    "/cleanup",
    summary="Limpar previews expirados",
    description="Remove previews expirados do banco e do disco.",
)
async def cleanup_expired_previews(
    service: PreviewService = Depends(get_preview_service),
) -> dict:
    """
    Limpa previews expirados.

    Returns:
        Número de previews removidos
    """
    try:
        count = service.cleanup_expired_previews()

        return {"removed": count, "message": f"{count} previews expirados removidos"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
