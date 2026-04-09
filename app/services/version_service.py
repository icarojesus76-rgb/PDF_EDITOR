"""
Serviço de versionamento de PDF.

Gerencia o ciclo de vida completo das versões de documentos PDF,
incluindo criação, listagem, download e manipulação de versões.
"""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import VersionNotFoundError, TemplateNotFoundError
from app.core.logging_config import logger
from app.domain.models.template import Template
from app.domain.models.version import Version, VersionStatus


class VersionService:
    """
    Serviço para gerenciamento de versões de PDF.

    Responsabilidades:
    - Criação de novas versões
    - Listagem de histórico de versões
    - Download de versões específicas
    - Validação de integridade via checksum
    - Rastreamento de usuário responsável
    """

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def create_version(
        self,
        template_id: int,
        pdf_bytes: bytes,
        name: str,
        field_data: dict,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
        observation: Optional[str] = None,
        parent_version_id: Optional[int] = None,
    ) -> Version:
        """
        Cria uma nova versão de um template.

        Args:
            template_id: ID do template base
            pdf_bytes: Bytes do PDF gerado
            name: Nome da versão
            field_data: Dados usados no preenchimento
            created_by: Usuário responsável
            description: Descrição da versão
            observation: Observação opcional
            parent_version_id: Versão pai (para versionamento hierárquico)

        Returns:
            Versão criada

        Raises:
            TemplateNotFoundError: Se template não existir
        """
        template = self.db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise TemplateNotFoundError(template_id)

        version_number = self._get_next_version_number(template_id, parent_version_id)

        unique_id = uuid.uuid4().hex
        filename = f"{unique_id}_v{version_number}_{template.id}.pdf"
        relative_path = f"versions/{filename}"

        full_path = self.settings.STORAGE_PATH / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(pdf_bytes)

        checksum = self._calculate_checksum(pdf_bytes)
        changes_summary = self._generate_changes_summary(field_data)

        version = Version(
            template_id=template_id,
            parent_version_id=parent_version_id,
            version_number=version_number,
            name=name,
            description=description,
            file_path=relative_path,
            file_size=len(pdf_bytes),
            checksum=checksum,
            field_data=field_data,
            created_by=created_by,
            observation=observation,
            changes_summary=changes_summary,
            status=VersionStatus.ACTIVE.value,
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        logger.info(
            f"Versão criada: ID={version.id}, v{version_number}, "
            f"template={template_id}, user={created_by}"
        )

        return version

    def get_version(self, version_id: int) -> Version:
        """
        Busca uma versão pelo ID.

        Args:
            version_id: ID da versão

        Returns:
            Versão encontrada

        Raises:
            VersionNotFoundError: Se versão não existir
        """
        version = self.db.query(Version).filter(Version.id == version_id).first()
        if not version:
            raise VersionNotFoundError(version_id)
        return version

    def get_version_by_number(self, template_id: int, version_number: int) -> Version:
        """
        Busca uma versão pelo número.

        Args:
            template_id: ID do template
            version_number: Número da versão

        Returns:
            Versão encontrada

        Raises:
            VersionNotFoundError: Se versão não existir
        """
        version = (
            self.db.query(Version)
            .filter(
                Version.template_id == template_id,
                Version.version_number == version_number,
            )
            .first()
        )
        if not version:
            raise VersionNotFoundError(f"{template_id}-{version_number}")
        return version

    def list_versions(
        self,
        template_id: int,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Version], int]:
        """
        Lista versões de um template com paginação.

        Args:
            template_id: ID do template
            status: Filtrar por status (opcional)
            limit: Limite de resultados
            offset: Offset para paginação

        Returns:
            Tupla (lista de versões, total)
        """
        query = self.db.query(Version).filter(Version.template_id == template_id)

        if status:
            query = query.filter(Version.status == status)

        total = query.count()

        versions = (
            query.order_by(Version.version_number.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return versions, total

    def list_all_versions(self, template_id: int) -> list[Version]:
        """
        Lista todas as versões de um template (sem paginação).

        Args:
            template_id: ID do template

        Returns:
            Lista de versões
        """
        return (
            self.db.query(Version)
            .filter(Version.template_id == template_id)
            .order_by(Version.version_number.desc())
            .all()
        )

    def get_latest_version(self, template_id: int) -> Optional[Version]:
        """
        Retorna a versão mais recente de um template.

        Args:
            template_id: ID do template

        Returns:
            Versão mais recente ou None
        """
        return (
            self.db.query(Version)
            .filter(
                Version.template_id == template_id,
                Version.status == VersionStatus.ACTIVE.value,
            )
            .order_by(Version.version_number.desc())
            .first()
        )

    def get_version_pdf_bytes(self, version_id: int) -> bytes:
        """
        Retorna os bytes do PDF de uma versão.

        Args:
            version_id: ID da versão

        Returns:
            Bytes do PDF

        Raises:
            VersionNotFoundError: Se versão não existir
            FileNotFoundError: Se arquivo físico não existir
        """
        version = self.get_version(version_id)
        full_path = self.settings.STORAGE_PATH / version.file_path

        if not full_path.exists():
            logger.error(f"Arquivo não encontrado: {full_path}")
            raise FileNotFoundError(f"Arquivo da versão {version_id} não encontrado")

        return full_path.read_bytes()

    def verify_checksum(self, version_id: int) -> bool:
        """
        Verifica integridade do arquivo via checksum.

        Args:
            version_id: ID da versão

        Returns:
            True sechecksum coincidir
        """
        version = self.get_version(version_id)
        full_path = self.settings.STORAGE_PATH / version.file_path

        if not full_path.exists():
            return False

        current_checksum = self._calculate_checksum(full_path.read_bytes())
        return current_checksum == version.checksum

    def update_version_status(
        self,
        version_id: int,
        status: VersionStatus,
    ) -> Version:
        """
        Atualiza o status de uma versão.

        Args:
            version_id: ID da versão
            status: Novo status

        Returns:
            Versão atualizada
        """
        version = self.get_version(version_id)
        version.status = status.value

        self.db.commit()
        self.db.refresh(version)

        logger.info(f"Status da versão {version_id} atualizado para {status.value}")

        return version

    def archive_version(
        self, version_id: int, observation: Optional[str] = None
    ) -> Version:
        """
        Arquiva uma versão.

        Args:
            version_id: ID da versão
            observation: Observação sobre o arquivamento

        Returns:
            Versão arquivada
        """
        version = self.update_version_status(version_id, VersionStatus.ARCHIVED)
        if observation:
            version.observation = observation
            self.db.commit()
            self.db.refresh(version)

        return version

    def supersede_version(self, version_id: int, new_version_id: int) -> Version:
        """
        Marca uma versão como substituída por outra.

        Args:
            version_id: ID da versão a ser substituída
            new_version_id: ID da nova versão

        Returns:
            Versão marcada como superseded
        """
        version = self.update_version_status(version_id, VersionStatus.SUPERSEDED)

        new_version = self.get_version(new_version_id)
        version.observation = f"Substituída pela versão {new_version.version_number}"

        self.db.commit()
        self.db.refresh(version)

        return version

    def delete_version(self, version_id: int, hard_delete: bool = False) -> None:
        """
        Deleta uma versão.

        Args:
            version_id: ID da versão
            hard_delete: Se True, deleta o arquivo físico também
        """
        version = self.get_version(version_id)

        if hard_delete:
            full_path = self.settings.STORAGE_PATH / version.file_path
            if full_path.exists():
                full_path.unlink()
                logger.info(f"Arquivo físico deletado: {version.file_path}")

        self.db.delete(version)
        self.db.commit()

        logger.info(f"Versão {version_id} deletada")

    def get_version_lineage(self, version_id: int) -> list[Version]:
        """
        Retorna a linhagem completa de uma versão (do ancestral ao descendente).

        Args:
            version_id: ID da versão

        Returns:
            Lista de versões da mais antiga à mais recente
        """
        version = self.get_version(version_id)
        lineage = [version]

        while version.parent_version_id:
            version = version.parent_version
            lineage.insert(0, version)

        return lineage

    def get_template_statistics(self, template_id: int) -> dict:
        """
        Retorna estatísticas de versionamento de um template.

        Args:
            template_id: ID do template

        Returns:
            Dicionário com estatísticas
        """
        versions = self.list_all_versions(template_id)

        total_versions = len(versions)
        active_versions = sum(
            1 for v in versions if v.status == VersionStatus.ACTIVE.value
        )
        archived_versions = sum(
            1 for v in versions if v.status == VersionStatus.ARCHIVED.value
        )
        superseded_versions = sum(
            1 for v in versions if v.status == VersionStatus.SUPERSEDED.value
        )

        total_size = sum(v.file_size for v in versions)

        return {
            "template_id": template_id,
            "total_versions": total_versions,
            "active_versions": active_versions,
            "archived_versions": archived_versions,
            "superseded_versions": superseded_versions,
            "total_size_bytes": total_size,
            "latest_version": versions[0].version_number if versions else None,
        }

    def _get_next_version_number(
        self, template_id: int, parent_version_id: Optional[int]
    ) -> int:
        """Calcula o próximo número de versão."""
        if parent_version_id:
            parent = (
                self.db.query(Version).filter(Version.id == parent_version_id).first()
            )
            if parent:
                return parent.version_number + 1

        max_version = (
            self.db.query(Version)
            .filter(Version.template_id == template_id)
            .order_by(Version.version_number.desc())
            .first()
        )

        return (max_version.version_number + 1) if max_version else 1

    def _calculate_checksum(self, data: bytes) -> str:
        """Calcula hash SHA256 dos dados."""
        return hashlib.sha256(data).hexdigest()

    def _generate_changes_summary(self, field_data: dict) -> str:
        """Gera resumo das alterações."""
        if not field_data:
            return "Versão inicial"

        changed_fields = list(field_data.keys())
        if len(changed_fields) <= 5:
            return f"Campos preenchidos: {', '.join(changed_fields)}"
        else:
            return f"Campos preenchidos: {', '.join(changed_fields[:5])} (+{len(changed_fields) - 5} mais)"
