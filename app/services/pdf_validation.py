"""
Serviço de validação de PDF.

Valida arquivos enviados verificando:
- Formato (é PDF válido?)
- Tamanho máximo
- Integridade do arquivo
"""

import io

from PyPDF2 import PdfReader

from app.core.config import get_settings
from app.core.exceptions import FileValidationError, InvalidPDFError
from app.core.logging_config import logger


class PDFValidationService:
    """
    Serviço para validação de arquivos PDF.

    Centraliza todas as validações de segurança e integridade
    de arquivos PDF antes do processamento.
    """

    def __init__(self):
        self.settings = get_settings()

    def validate_file_size(self, file_size: int) -> None:
        """
        Valida se o arquivo não excede o tamanho máximo.

        Args:
            file_size: Tamanho do arquivo em bytes

        Raises:
            FileValidationError: Se exceder limite
        """
        max_bytes = self.settings.MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_bytes:
            raise FileValidationError(
                message=f"Arquivo muito grande. Máximo: {self.settings.MAX_FILE_SIZE_MB}MB",
                detail=f"Tamanho recebido: {file_size / 1024 / 1024:.2f}MB",
            )

        logger.debug(f"Tamanho válido: {file_size} bytes")

    def validate_extension(self, filename: str) -> None:
        """
        Valida se a extensão é permitida.

        Args:
            filename: Nome do arquivo

        Raises:
            FileValidationError: Se extensão inválida
        """
        extension = filename.lower().split(".")[-1] if "." in filename else ""

        if extension != "pdf":
            raise FileValidationError(
                message="Apenas arquivos PDF são permitidos",
                detail=f"Extensão recebida: .{extension}",
            )

    def validate_pdf_content(self, file_content: bytes) -> dict:
        """
        Valida se o conteúdo é um PDF válido e lê metadados.

        Args:
            file_content: Bytes do arquivo

        Returns:
            Dicionário com metadados: page_count, author, etc.

        Raises:
            InvalidPDFError: Se não for PDF válido
        """
        try:
            reader = PdfReader(io.BytesIO(file_content))

            # Lê metadados
            metadata = reader.metadata or {}

            pdf_info = {
                "page_count": len(reader.pages),
                "is_encrypted": reader.is_encrypted,
                "author": metadata.get("/Author", None),
                "creator": metadata.get("/Creator", None),
                "subject": metadata.get("/Subject", None),
                "title": metadata.get("/Title", None),
            }

            logger.info(f"PDF válido: {pdf_info['page_count']} páginas")

            return pdf_info

        except Exception as e:
            logger.error(f"Erro ao validar PDF: {e}")
            raise InvalidPDFError(
                f"Arquivo não é um PDF válido ou está corrompido: {str(e)}"
            )

    def validate_upload(self, filename: str, file_content: bytes) -> dict:
        """
        Validação completa de upload de PDF.

        Executa todas as validações em sequência.

        Args:
            filename: Nome original do arquivo
            file_content: Bytes do arquivo

        Returns:
            Metadados do PDF

        Raises:
            FileValidationError: Se qualquer validação falhar
            InvalidPDFError: Se não for PDF válido
        """
        logger.info(f"Validando upload: {filename}")

        # Valida extensão
        self.validate_extension(filename)

        # Valida tamanho
        self.validate_file_size(len(file_content))

        # Valida conteúdo
        pdf_info = self.validate_pdf_content(file_content)

        logger.info(f"Upload validado com sucesso: {filename}")

        return pdf_info
