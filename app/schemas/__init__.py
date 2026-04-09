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
from app.schemas.pdf_metadata_schema import (
    PDFMetadataResponse,
    PDFMetadataSummarySchema,
    PDFMetadataCreate,
    PageMetadataSchema,
    TextBlockSchema,
    ImageInfoSchema,
    FormFieldSchema,
    PageDimensionsSchema,
)
from app.schemas.validation_schema import (
    FieldValidationConfig,
    FieldValidationItem,
    FieldValuesRequest,
    FieldValidationResponse,
    FieldValueValidationRequest,
    FieldValueValidationResponse,
)
from app.schemas.preview_schema import (
    PreviewCreateRequest,
    PreviewConfirmRequest,
    PreviewResponse,
    PreviewTokenResponse,
    PreviewConfirmResponse,
    PreviewCancelResponse,
    PreviewListResponse,
    PreviewImageResponse,
    FieldValidationError,
    PreviewValidationResult,
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
    "PDFMetadataResponse",
    "PDFMetadataSummarySchema",
    "PDFMetadataCreate",
    "PageMetadataSchema",
    "TextBlockSchema",
    "ImageInfoSchema",
    "FormFieldSchema",
    "PageDimensionsSchema",
    "FieldValidationConfig",
    "FieldValidationItem",
    "FieldValuesRequest",
    "FieldValidationResponse",
    "FieldValueValidationRequest",
    "FieldValueValidationResponse",
    "PreviewCreateRequest",
    "PreviewConfirmRequest",
    "PreviewResponse",
    "PreviewTokenResponse",
    "PreviewConfirmResponse",
    "PreviewCancelResponse",
    "PreviewListResponse",
    "PreviewImageResponse",
    "FieldValidationError",
    "PreviewValidationResult",
]
