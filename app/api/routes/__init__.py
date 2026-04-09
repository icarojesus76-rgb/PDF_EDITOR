"""
Routes module - Definição de rotas da API.

Agrupa todos os endpoints da aplicação por versão.
"""

from fastapi import APIRouter

from app.api.routes import templates, versions, previews

# Router principal da API v1
api_router = APIRouter()

# Registra sub-routers
api_router.include_router(templates.router)
api_router.include_router(versions.router)
api_router.include_router(previews.router)

__all__ = ["api_router"]
