"""
Domain module - Entidades e lógica de negócio.

Este módulo contém os modelos de domínio e entidades do negócio.
Segue o princípio de domínio rico (Rich Domain Model) com
lógica de negócio encapsulada nas entidades quando apropriado.
"""

from app.domain.models.template import Template, TemplateStatus
from app.domain.models.version import Version, VersionStatus
from app.domain.models.pdf_metadata import PDFMetadata, PDFPageMetadata

__all__ = [
    "Template",
    "TemplateStatus",
    "Version",
    "VersionStatus",
    "PDFMetadata",
    "PDFPageMetadata",
]
