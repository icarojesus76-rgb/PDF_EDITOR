"""
Core configuration module.

Centraliza todas as configurações da aplicação usando Pydantic Settings.
Inclui validação, tipagem forte e suporte a variáveis de ambiente.
"""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Configurações globais da aplicação.

    Todos os valores podem ser sobrescritos via variáveis de ambiente.
    O arquivo .env é carregado automaticamente em ambiente de desenvolvimento.
    """

    # Aplicação
    APP_NAME: str = "PDF Editor API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Banco de dados
    DATABASE_URL: str = Field(
        default="sqlite:///./pdf_editor.db",
        description="SQLite database connection string",
    )

    # Armazenamento de arquivos
    STORAGE_PATH: Path = Field(
        default=Path("storage"),
        description="Caminho base para armazenamento de arquivos",
    )

    TEMPLATES_PATH: Path = Field(
        default=Path("storage/templates"),
        description="Diretório para templates originais (NUNCA sobrescreve)",
    )

    VERSIONS_PATH: Path = Field(
        default=Path("storage/versions"), description="Diretório para versões derivadas"
    )

    PREVIEWS_PATH: Path = Field(
        default=Path("storage/previews"),
        description="Diretório para pré-visualizações temporárias",
    )

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR"
    )
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/app.log"

    # Limites
    MAX_FILE_SIZE_MB: int = Field(
        default=50, description="Tamanho máximo de arquivo em MB"
    )
    ALLOWED_EXTENSIONS: list[str] = [".pdf"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def validate_paths(self) -> None:
        """Garante que todos os diretórios de storage existem."""
        self.TEMPLATES_PATH.mkdir(parents=True, exist_ok=True)
        self.VERSIONS_PATH.mkdir(parents=True, exist_ok=True)
        self.PREVIEWS_PATH.mkdir(parents=True, exist_ok=True)
        Path(self.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna singleton de configurações.

    Usa @lru_cache para garantir que Settings é instanciado apenas uma vez.
    Isso evita múltiplas leituras de .env e validações repetidas.
    """
    settings = Settings()
    settings.validate_paths()
    return settings
