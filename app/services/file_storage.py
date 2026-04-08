"""
Serviço de armazenamento de arquivos.

Responsável por todas as operações de I/O com arquivos.
Separa lógica de storage do resto da aplicação.
"""

import hashlib
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.core.exceptions import FileStorageError, FileValidationError
from app.core.logging_config import logger


class FileStorageService:
    """
    Serviço para gerenciamento de arquivos no storage.

    Centraliza todas as operações de leitura/escrita de arquivos.
    Implementa validações e tratamento de erros consistente.
    """

    def __init__(self):
        self.settings = get_settings()
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Garante que todos os diretórios de storage existam."""
        self.settings.TEMPLATES_PATH.mkdir(parents=True, exist_ok=True)
        self.settings.VERSIONS_PATH.mkdir(parents=True, exist_ok=True)

    def _calculate_checksum(self, file_content: bytes) -> str:
        """
        Calcula hash SHA256 do conteúdo do arquivo.

        Args:
            file_content: Bytes do arquivo

        Returns:
            String hex com hash SHA256
        """
        return hashlib.sha256(file_content).hexdigest()

    def save_template(
        self, file_content: bytes, original_filename: str
    ) -> tuple[str, str, int]:
        """
        Salva um arquivo de template no storage.

        O arquivo é salvo com nome único (UUID) para evitar colisões
        e preservar o nome original para referência.

        Args:
            file_content: Bytes do arquivo PDF
            original_filename: Nome original do arquivo

        Returns:
            Tupla (caminho_relative, checksum, tamanho)

        Raises:
            FileStorageError: Se houver erro ao salvar
        """
        try:
            # Gera nome único para o arquivo
            unique_id = uuid.uuid4().hex
            extension = Path(original_filename).suffix.lower()

            # Nome do arquivo no storage: uuid_original.pdf
            stored_filename = f"{unique_id}_{original_filename}"
            relative_path = f"templates/{stored_filename}"
            full_path = self.settings.STORAGE_PATH / relative_path

            # Salva o arquivo
            with open(full_path, "wb") as f:
                f.write(file_content)

            # Calcula checksum
            checksum = self._calculate_checksum(file_content)
            file_size = len(file_content)

            logger.info(f"Template salvo: {relative_path} ({file_size} bytes)")

            return relative_path, checksum, file_size

        except Exception as e:
            logger.error(f"Erro ao salvar template: {e}")
            raise FileStorageError(
                message="Falha ao salvar arquivo no storage", detail=str(e)
            )

    def file_exists(self, relative_path: str) -> bool:
        """
        Verifica se um arquivo existe no storage.

        Args:
            relative_path: Caminho relativo ao storage

        Returns:
            True se existir, False caso contrário
        """
        full_path = self.settings.STORAGE_PATH / relative_path
        return full_path.exists()

    def get_file_path(self, relative_path: str) -> Path:
        """
        Retorna caminho completo de um arquivo.

        Args:
            relative_path: Caminho relativo ao storage

        Returns:
            Path absoluto do arquivo
        """
        return self.settings.STORAGE_PATH / relative_path

    def delete_file(self, relative_path: str) -> None:
        """
        Deleta um arquivo do storage.

        Args:
            relative_path: Caminho relativo ao storage

        Raises:
            FileStorageError: Se o arquivo não existir ou não puder ser deletado
        """
        full_path = self.settings.STORAGE_PATH / relative_path

        if not full_path.exists():
            raise FileStorageError(message=f"Arquivo não encontrado: {relative_path}")

        try:
            full_path.unlink()
            logger.info(f"Arquivo deletado: {relative_path}")
        except Exception as e:
            raise FileStorageError(message="Falha ao deletar arquivo", detail=str(e))

    def copy_file(self, source_path: str, dest_path: str) -> None:
        """
        Copia um arquivo dentro do storage.

        Útil para criar versões a partir do template.

        Args:
            source_path: Caminho de origem (relativo)
            dest_path: Caminho de destino (relativo)
        """
        source = self.settings.STORAGE_PATH / source_path
        dest = self.settings.STORAGE_PATH / dest_path

        if not source.exists():
            raise FileStorageError(
                message=f"Arquivo de origem não encontrado: {source_path}"
            )

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        logger.info(f"Arquivo copiado: {source_path} -> {dest_path}")
