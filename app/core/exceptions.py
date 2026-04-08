"""
Exceções customizadas da aplicação.

Define exceções específicas do domínio para melhor rastreamento
e tratamento de erros. Cada exceção inclui contexto para debug.
"""

from typing import Any


class PDFEditorException(Exception):
    """
    Exceção base da aplicação.

    Todas as exceções específicas herdam desta classe.
    Inclui contexto adicional para日志 e debugging.
    """

    def __init__(
        self, message: str, detail: str | None = None, code: str = "GENERIC_ERROR"
    ):
        self.message = message
        self.detail = detail
        self.code = code
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Converte exceção em dicionário para resposta da API."""
        return {"error": self.code, "message": self.message, "detail": self.detail}


class FileValidationError(PDFEditorException):
    """Erro ao validar arquivo (tipo, tamanho, formato inválido)."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message=message, detail=detail, code="FILE_VALIDATION_ERROR")


class FileStorageError(PDFEditorException):
    """Erro ao salvar ou recuperar arquivos do storage."""

    def __init__(self, message: str, detail: str | None = None):
        super().__init__(message=message, detail=detail, code="FILE_STORAGE_ERROR")


class TemplateNotFoundError(PDFEditorException):
    """Template não encontrado no banco de dados."""

    def __init__(self, template_id: int):
        super().__init__(
            message=f"Template com ID {template_id} não encontrado",
            detail=f"Tentativa de acessar template inexistente: {template_id}",
            code="TEMPLATE_NOT_FOUND",
        )


class TemplateAlreadyExistsError(PDFEditorException):
    """Tentativa de criar template com nome duplicado."""

    def __init__(self, filename: str):
        super().__init__(
            message=f"Template '{filename}' já existe",
            detail=f"Tentativa de criar template duplicado: {filename}",
            code="TEMPLATE_DUPLICATE",
        )


class InvalidPDFError(PDFEditorException):
    """Arquivo não é um PDF válido ou está corrompido."""

    def __init__(self, message: str = "Arquivo não é um PDF válido"):
        super().__init__(message=message, code="INVALID_PDF")


class VersionNotFoundError(PDFEditorException):
    """Versão de documento não encontrada."""

    def __init__(self, version_id: int):
        super().__init__(
            message=f"Versão com ID {version_id} não encontrada",
            detail=f"Tentativa de acessar versão inexistente: {version_id}",
            code="VERSION_NOT_FOUND",
        )
