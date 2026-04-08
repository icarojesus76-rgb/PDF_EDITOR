"""
API module - Configuração da API FastAPI.

Define a aplicação FastAPI, eventos de startup/shutdown
e middlewares globais.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging_config import setup_logging
from app.api.routes import api_router

settings = get_settings()
logger = setup_logging()


def create_application() -> FastAPI:
    """
    Factory para criar a aplicação FastAPI.

    Configura:
    - Título, descrição e versionamento
    - CORS para desenvolvimento
    - Eventos de startup/shutdown
    - Routers
    - Middlewares

    Returns:
        Aplicação FastAPI configurada
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="API para gestão e versionamento de PDFs. Templates imutáveis + versões derivadas.",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS (para frontend em desenvolvimento)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Produção: limitar a origens específicas
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Eventos de lifecycle
    @app.on_event("startup")
    async def startup_event():
        """Executa na inicialização da aplicação."""
        logger.info("Iniciando PDF Editor API...")
        init_db()  # Cria tabelas se não existirem
        logger.info("Banco de dados inicializado")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Executa no encerramento da aplicação."""
        logger.info("Encerrando PDF Editor API...")

    # Registra rotas
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Endpoint de health check."""
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "service": settings.APP_NAME,
        }

    @app.get("/", tags=["Root"])
    async def root():
        """Endpoint raiz com informações da API."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "api": settings.API_V1_PREFIX,
        }

    return app


# Instância da aplicação (usada por uvicorn)
app = create_application()
