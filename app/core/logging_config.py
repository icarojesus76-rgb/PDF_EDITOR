"""
Módulo de logging estruturado.

Fornece configuração centralizada de logs com suporte a:
- Logs em arquivo e console
- Níveis configuráveis
- Formatação estruturada
- Rotação de arquivos (futuro)
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.core.config import get_settings


def setup_logging() -> logging.Logger:
    """
    Configura e retorna o logger principal da aplicação.

    Configura dois handlers:
    - Console: para desenvolvimento
    - Arquivo: para produção e análise

    Returns:
        Logger configurado para uso em toda a aplicação
    """
    settings = get_settings()

    # Cria logger raiz
    logger = logging.getLogger("pdf_editor")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Limpa handlers existentes (evita duplicação em hot reload)
    logger.handlers.clear()

    # Formatador com timestamp e contexto
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler para console (sempre ativo)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para arquivo
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=str(log_path),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"Logging configurado. Nível: {settings.LOG_LEVEL}")

    return logger


# Logger padrão para importação em outros módulos
logger = logging.getLogger("pdf_editor")
