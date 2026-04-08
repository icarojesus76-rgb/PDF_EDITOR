"""
Routes module - Definição de rotas da API.

Agrupa todos os endpoints da aplicação por versão.
"""

from fastapi import APIRouter

from app.api.routes import templates

# Router principal da API v1
api_router = APIRouter()

# Registra sub-routers
api_router.include_router(templates.router)

__all__ = ["api_router"]
