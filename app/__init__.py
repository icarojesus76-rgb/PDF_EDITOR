"""
PDF Editor API - Aplicação principal.

Aplicação FastAPI para gestão e versionamento de PDFs.
Arquitetura limpa com separação de camadas.

Camadas:
- api: Endpoints e routing
- core: Configuração, logging, database, exceções
- domain: Entidades e modelos de negócio
- schemas: Schemas Pydantic para validação
- services: Lógica de negócio
- infrastructure: Implementações técnicas (storage, etc.)
"""

from app.api import app

__version__ = "1.0.0"

__all__ = ["app"]
