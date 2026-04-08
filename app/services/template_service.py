"""
Serviço de gestão de Templates.

Contém a lógica de negócio para operações com templates:
- Criação
- Consulta
- Listagem
- Soft delete
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.template import Template, TemplateStatus
from app.services.file_storage import FileStorageService
from app.services.pdf_validation import PDFValidationService
from app.core.exceptions import TemplateNotFoundError, TemplateAlreadyExistsError
from app.core.logging_config import logger


class TemplateService:
    """
    Serviço para gerenciamento de Templates PDF.

    Implementa as operações CRUD e regras de negócio específicas
    do domínio de templates. Cada template é imutável após upload.
    """

    def __init__(
        self,
        db: Session,
        file_storage: FileStorageService,
        pdf_validator: PDFValidationService,
    ):
        self.db = db
        self.file_storage = file_storage
        self.pdf_validator = pdf_validator

    def create_template(
        self, filename: str, file_content: bytes, custom_name: str | None = None
    ) -> Template:
        """
        Cria um novo template a partir de upload de PDF.

        Fluxo:
        1. Valida o PDF (extensão, tamanho, integridade)
        2. Salva o arquivo no storage (TEMPLATES_PATH)
        3. Cria registro no banco de dados

        Args:
            filename: Nome original do arquivo
            file_content: Bytes do arquivo PDF
            custom_name: Nome customizado (opcional)

        Returns:
            Template criado

        Raises:
            FileValidationError: Se validação falhar
            FileStorageError: Se não conseguir salvar arquivo
        """
        logger.info(f"Iniciando criação de template: {filename}")

        # 1. Valida o PDF
        pdf_info = self.pdf_validator.validate_upload(filename, file_content)

        # 2. Salva no storage
        relative_path, checksum, file_size = self.file_storage.save_template(
            file_content=file_content, original_filename=filename
        )

        # 3. Cria registro no banco
        template_name = custom_name or filename

        db_template = Template(
            name=template_name,
            original_filename=filename,
            file_path=relative_path,
            file_size=file_size,
            checksum=checksum,
            status=TemplateStatus.ACTIVE,
        )

        self.db.add(db_template)
        self.db.commit()
        self.db.refresh(db_template)

        logger.info(f"Template criado com sucesso: ID={db_template.id}")

        return db_template

    def get_template(self, template_id: int) -> Template:
        """
        Busca um template pelo ID.

        Args:
            template_id: ID do template

        Returns:
            Template encontrado

        Raises:
            TemplateNotFoundError: Se não encontrar
        """
        template = self.db.query(Template).filter(Template.id == template_id).first()

        if not template:
            logger.warning(f"Template não encontrado: {template_id}")
            raise TemplateNotFoundError(template_id)

        return template

    def list_templates(
        self, skip: int = 0, limit: int = 20, status: TemplateStatus | None = None
    ) -> tuple[list[Template], int]:
        """
        Lista templates com paginação.

        Args:
            skip: Quantos registros pular (offset)
            limit: Máximo de registros
            status: Filtrar por status (opcional)

        Returns:
            Tupla (lista de templates, total de registros)
        """
        query = self.db.query(Template)

        if status:
            query = query.filter(Template.status == status)

        # Conta total
        total = query.count()

        # Ordena por mais recentes
        templates = (
            query.order_by(desc(Template.created_at)).offset(skip).limit(limit).all()
        )

        return templates, total

    def archive_template(self, template_id: int) -> Template:
        """
        Arquiva um template (soft delete).

        O template não é removido do storage, apenas marcado como arquivado.

        Args:
            template_id: ID do template

        Returns:
            Template arquivado
        """
        template = self.get_template(template_id)
        template.status = TemplateStatus.ARCHIVED

        self.db.commit()
        self.db.refresh(template)

        logger.info(f"Template arquivado: {template_id}")

        return template

    def delete_template(self, template_id: int) -> None:
        """
        Deleta um template permanentemente.

        ATENÇÃO: Isso deleta o arquivo do storage.
        Use com cuidado.

        Args:
            template_id: ID do template
        """
        template = self.get_template(template_id)

        # Deleta arquivo do storage
        self.file_storage.delete_file(template.file_path)

        # Deleta do banco
        self.db.delete(template)
        self.db.commit()

        logger.info(f"Template deletado permanentemente: {template_id}")
