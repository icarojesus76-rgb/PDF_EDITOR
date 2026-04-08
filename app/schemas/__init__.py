"""
Schemas module - Schemas Pydantic para validação e serialização.

Contém todos os schemas de entrada/saída da API.
Separados por domínio para melhor organização.
"""

from app.schemas.template_schema import (
    TemplateBase,
    TemplateCreate,
    TemplateResponse,
    TemplateListResponse,
    TemplateSummary,
)
from app.schemas.version_schema import (
    VersionBase,
    VersionCreate,
    VersionResponse,
    VersionListResponse,
    VersionSummary,
)

__all__ = [
    "TemplateBase",
    "TemplateCreate",
    "TemplateResponse",
    "TemplateListResponse",
    "TemplateSummary",
    "VersionBase",
    "VersionCreate",
    "VersionResponse",
    "VersionListResponse",
    "VersionSummary",
]
