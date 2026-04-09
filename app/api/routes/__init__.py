"""
Routes module - Definição de rotas da API.

Agrupa todos os endpoints da aplicação por versão.
"""

from fastapi import APIRouter

from app.api.routes import templates, versions, previews, validation, audit, fields

api_router = APIRouter()

api_router.include_router(templates.router)
api_router.include_router(versions.router)
api_router.include_router(previews.router)
api_router.include_router(validation.router)
api_router.include_router(audit.router)
api_router.include_router(fields.router)

__all__ = ["api_router"]
