"""
Endpoints para gerenciamento de Templates.

Implementa a API REST para operações de upload, consulta
e gestão de templates PDF.
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import PDFEditorException
from app.core.logging_config import logger
from app.schemas import TemplateResponse, TemplateListResponse, TemplateSummary
from app.services import FileStorageService, PDFValidationService, TemplateService

router = APIRouter(
    prefix="/templates",
    tags=["Templates"],
    responses={
        500: {"description": "Erro interno do servidor"},
        422: {"description": "Erro de validação"},
    },
)


def get_template_service(db: Session = Depends(get_db)) -> TemplateService:
    """Factory para injeção de dependência do TemplateService."""
    return TemplateService(
        db=db, file_storage=FileStorageService(), pdf_validator=PDFValidationService()
    )


@router.post(
    "/upload",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de novo template PDF",
    description="Recebe um arquivo PDF, valida e salva como template original.",
)
async def upload_template(
    file: UploadFile = File(..., description="Arquivo PDF para upload"),
    name: str | None = Query(
        None, description="Nome customizado para o template (opcional)"
    ),
    service: TemplateService = Depends(get_template_service),
) -> TemplateResponse:
    """
    Faz upload de um novo template PDF.

    - O arquivo é validado (PDF válido, tamanho, extensão)
    - Salvo em /storage/templates/ com nome único
    - Registro criado no banco de dados
    - O arquivo original NUNCA é sobrescrito

    Args:
        file: Arquivo PDF enviado via multipart/form-data
        name: Nome opcional customizado

    Returns:
        TemplateResponse com dados do template criado

    Raises:
        400: Se arquivo inválido ou muito grande
        409: Se template com mesmo checksum já existe
    """
    logger.info(f"Recebendo upload: {file.filename}")

    try:
        # Lê conteúdo do arquivo
        content = await file.read()

        # Cria template via service
        template = service.create_template(
            filename=file.filename, file_content=content, custom_name=name
        )

        return TemplateResponse.model_validate(template)

    except PDFEditorException as e:
        # Converte exceção de domínio em HTTPException
        status_map = {
            "FILE_VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
            "INVALID_PDF": status.HTTP_400_BAD_REQUEST,
            "TEMPLATE_DUPLICATE": status.HTTP_409_CONFLICT,
            "FILE_STORAGE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        http_status = status_map.get(e.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(status_code=http_status, detail=e.to_dict())


@router.get(
    "/",
    response_model=TemplateListResponse,
    summary="Lista todos os templates",
    description="Retorna lista paginada de templates.",
)
async def list_templates(
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(20, ge=1, le=100, description="Máximo de registros"),
    service: TemplateService = Depends(get_template_service),
) -> TemplateListResponse:
    """
    Lista todos os templates com paginação.

    Args:
        skip: Offset (padrão: 0)
        limit: Limit por página (padrão: 20, max: 100)

    Returns:
        Lista paginada de templates
    """
    templates, total = service.list_templates(skip=skip, limit=limit)

    return TemplateListResponse(
        items=[TemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Busca template por ID",
    description="Retorna detalhes de um template específico.",
)
async def get_template(
    template_id: int, service: TemplateService = Depends(get_template_service)
) -> TemplateResponse:
    """
    Retorna detalhes de um template pelo ID.

    Args:
        template_id: ID do template

    Returns:
        TemplateResponse com dados completos

    Raises:
        404: Se template não encontrado
    """
    try:
        template = service.get_template(template_id)
        return TemplateResponse.model_validate(template)
    except PDFEditorException as e:
        if e.code == "TEMPLATE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )
