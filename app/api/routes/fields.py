"""
Endpoints para gerenciamento de Campos.

Implementa a API REST para operações CRUD de campos editáveis.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import PDFEditorException
from app.core.logging_config import logger
from app.schemas.field_schema import (
    FieldCreate,
    FieldUpdate,
    FieldResponse,
    FieldListResponse,
    TemplateFieldsResponse,
)
from app.services.field_service import FieldService

router = APIRouter(
    prefix="/fields",
    tags=["Fields"],
    responses={
        500: {"description": "Erro interno do servidor"},
        422: {"description": "Erro de validação"},
    },
)


def get_field_service(db: Session = Depends(get_db)) -> FieldService:
    """Factory para injeção de dependência do FieldService."""
    return FieldService(db=db)


@router.post(
    "/",
    response_model=FieldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria novo campo",
    description="Cria um novo campo editável em um template.",
)
async def create_field(
    field_data: FieldCreate,
    service: FieldService = Depends(get_field_service),
) -> FieldResponse:
    """Cria um novo campo."""
    try:
        field = service.create_field(field_data)
        return FieldResponse.model_validate(field)
    except PDFEditorException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())


@router.get(
    "/template/{template_id}",
    response_model=TemplateFieldsResponse,
    summary="Lista campos do template",
    description="Retorna todos os campos de um template.",
)
async def get_template_fields(
    template_id: int,
    service: FieldService = Depends(get_field_service),
) -> TemplateFieldsResponse:
    """Retorna todos os campos de um template."""
    try:
        result = service.get_template_fields(template_id)
        return result
    except PDFEditorException as e:
        if e.code == "TEMPLATE_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.get(
    "/{field_id}",
    response_model=FieldResponse,
    summary="Busca campo por ID",
    description="Retorna detalhes de um campo específico.",
)
async def get_field(
    field_id: int,
    service: FieldService = Depends(get_field_service),
) -> FieldResponse:
    """Retorna detalhes de um campo."""
    try:
        field = service.get_field(field_id)
        return FieldResponse.model_validate(field)
    except PDFEditorException as e:
        if e.code == "FIELD_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )


@router.put(
    "/{field_id}",
    response_model=FieldResponse,
    summary="Atualiza campo",
    description="Atualiza as propriedades de um campo.",
)
async def update_field(
    field_id: int,
    field_data: FieldUpdate,
    service: FieldService = Depends(get_field_service),
) -> FieldResponse:
    """Atualiza um campo."""
    try:
        field = service.update_field(field_id, field_data)
        return FieldResponse.model_validate(field)
    except PDFEditorException as e:
        if e.code == "FIELD_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.to_dict())


@router.delete(
    "/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta campo",
    description="Remove um campo do template.",
)
async def delete_field(
    field_id: int,
    service: FieldService = Depends(get_field_service),
):
    """Deleta um campo."""
    try:
        service.delete_field(field_id)
    except PDFEditorException as e:
        if e.code == "FIELD_NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.to_dict()
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.to_dict()
        )
