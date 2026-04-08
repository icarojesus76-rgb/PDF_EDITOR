"""
Core module - Configurações centrais da aplicação.

Este módulo contém configurações globais, banco de dados,
logging e exceções customizadas que são a base do sistema.
"""

from app.core.config import Settings, get_settings
from app.core.database import Base, engine, get_db, SessionLocal, init_db
from app.core.logging_config import setup_logging, logger
from app.core.exceptions import (
    PDFEditorException,
    FileValidationError,
    FileStorageError,
    TemplateNotFoundError,
    TemplateAlreadyExistsError,
    InvalidPDFError,
    VersionNotFoundError,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Database
    "Base",
    "engine",
    "get_db",
    "SessionLocal",
    "init_db",
    # Logging
    "setup_logging",
    "logger",
    # Exceptions
    "PDFEditorException",
    "FileValidationError",
    "FileStorageError",
    "TemplateNotFoundError",
    "TemplateAlreadyExistsError",
    "InvalidPDFError",
    "VersionNotFoundError",
]
