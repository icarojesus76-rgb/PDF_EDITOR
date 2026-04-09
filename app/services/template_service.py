"""
Serviço de gestão de Templates.

Contém a lógica de negócio para operações com templates:
- Criação (com extração de metadados)
- Consulta
- Listagem
- Soft delete
- Gestão de metadados
"""

from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.template import Template, TemplateStatus
from app.domain.models.pdf_metadata import PDFMetadata, PDFPageMetadata
from app.services.file_storage import FileStorageService
from app.services.pdf_validation import PDFValidationService
from app.services.pdf_loader import PDFLoaderService
from app.core.exceptions import TemplateNotFoundError, TemplateAlreadyExistsError
from app.core.logging_config import logger

if TYPE_CHECKING:
    from app.services.audit_service import AuditService


class TemplateService:
    """
    Serviço para gerenciamento de Templates PDF.

    Implementa as operações CRUD e regras de negócio específicas
    do domínio de templates. Cada template é imutável após upload.

    Na criação, automaticamente extrai metadados detalhados usando
    PyMuPDF para análise do layout e conteúdo.
    """

    def __init__(
        self,
        db: Session,
        file_storage: FileStorageService,
        pdf_validator: PDFValidationService,
        pdf_loader: PDFLoaderService | None = None,
        audit_service: Optional["AuditService"] = None,
    ):
        self.db = db
        self.file_storage = file_storage
        self.pdf_validator = pdf_validator
        self.pdf_loader = pdf_loader or PDFLoaderService()
        self.audit_service = audit_service

    def create_template(
        self, filename: str, file_content: bytes, custom_name: str | None = None
    ) -> Template:
        """
        Cria um novo template a partir de upload de PDF.

        Fluxo:
        1. Valida o PDF (extensão, tamanho, integridade)
        2. Salva o arquivo no storage (TEMPLATES_PATH)
        3. Cria registro no banco de dados
        4. Extrai metadados detalhados com PyMuPDF
        5. Salva metadados em JSON e no banco

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

        logger.info(f"Template criado: ID={db_template.id}")

        if self.audit_service:
            try:
                self.audit_service.log_template_upload(
                    template_id=db_template.id,
                    template_name=db_template.name,
                    file_size=db_template.file_size,
                )
            except Exception as e:
                logger.warning(f"Failed to log audit: {e}")

        # 4. Extrai metadados detalhados
        try:
            self._extract_and_save_metadata(db_template, file_content)
        except Exception as e:
            logger.error(f"Erro ao extrair metadados: {e}")
            # Não falha o upload se metad der erro, apenas loga
            # Em produção, pode querer retry ou queue

        return db_template

    def _extract_and_save_metadata(
        self, template: Template, file_content: bytes
    ) -> PDFMetadata:
        """
        Extrai e salva metadados detalhados do PDF.

        Args:
            template: Template criado
            file_content: Bytes do PDF

        Returns:
            PDFMetadata criado
        """
        logger.info(f"Extraindo metadados do template: {template.id}")

        # Extrai metadados com PyMuPDF
        doc_metadata = self.pdf_loader.extract_metadata(
            file_content=file_content, filename=template.original_filename
        )

        # Salva JSON
        json_path = self.pdf_loader.save_metadata_json(
            metadata=doc_metadata, template_id=template.id
        )

        # Prepara dimensões das páginas
        page_dimensions = [
            {"page": i, "width": page["width"], "height": page["height"]}
            for i, page in enumerate(doc_metadata.pages)
        ]

        # Cria registro de metadados no banco
        db_metadata = PDFMetadata(
            template_id=template.id,
            page_count=doc_metadata.page_count,
            pdf_version=doc_metadata.pdf_version,
            title=doc_metadata.title,
            author=doc_metadata.author,
            creator=doc_metadata.creator,
            producer=doc_metadata.producer,
            metadata_json_path=json_path,
            page_dimensions=page_dimensions,
            total_text_blocks=doc_metadata.total_text_blocks,
            total_images=doc_metadata.total_images,
            total_forms=doc_metadata.total_forms,
        )

        self.db.add(db_metadata)
        self.db.commit()
        self.db.refresh(db_metadata)

        # Cria registros de páginas
        for page_data in doc_metadata.pages:
            page_meta = PDFPageMetadata(
                pdf_metadata_id=db_metadata.id,
                page_number=page_data["page_number"],
                width=page_data["width"],
                height=page_data["height"],
                rotation=page_data["rotation"],
                text_blocks=page_data["text_blocks"],
                images=page_data["images"],
                form_fields=page_data["form_fields"],
            )
            self.db.add(page_meta)

        self.db.commit()

        logger.info(
            f"Metadados salvos: {db_metadata.id}, {doc_metadata.page_count} páginas"
        )

        return db_metadata

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

    def get_template_metadata(self, template_id: int) -> PDFMetadata:
        """
        Busca metadados de um template.

        Args:
            template_id: ID do template

        Returns:
            PDFMetadata do template

        Raises:
            TemplateNotFoundError: Se template não existir
        """
        from app.domain.models.pdf_metadata import PDFMetadata

        # Verifica se template existe
        self.get_template(template_id)

        metadata = (
            self.db.query(PDFMetadata)
            .filter(PDFMetadata.template_id == template_id)
            .first()
        )

        if not metadata:
            logger.warning(f"Metadados não encontrados para template: {template_id}")
            raise TemplateNotFoundError(
                template_id=template_id  # Reutiliza erro, mas é metadados
            )

        return metadata

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

        total = query.count()

        templates = (
            query.order_by(desc(Template.created_at)).offset(skip).limit(limit).all()
        )

        return templates, total

    def archive_template(self, template_id: int) -> Template:
        """
        Arquiva um template (soft delete).

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

        if self.audit_service:
            try:
                from app.domain.models.audit_log import AuditAction

                self.audit_service.log(
                    action=AuditAction.TEMPLATE_ARCHIVE,
                    template_id=template.id,
                    template_name=template.name,
                    payload={"status": "archived"},
                )
            except Exception as e:
                logger.warning(f"Failed to log audit: {e}")

        return template

    def delete_template(self, template_id: int) -> None:
        """
        Deleta um template permanentemente.

        ATENÇÃO: Deleta arquivo e metadados.

        Args:
            template_id: ID do template
        """
        template = self.get_template(template_id)

        # Deleta arquivo do storage
        self.file_storage.delete_file(template.file_path)

        # Deleta metadados JSON se existir
        if template.pdf_metadata:
            try:
                self.pdf_loader.load_metadata_json(
                    template.pdf_metadata.metadata_json_path
                )
                # Não precisa deletar manualmente, cascade do SQLAlchemy
                # cuida dos registros no banco
            except:
                pass

        # Deleta do banco (cascade remove metadados)
        self.db.delete(template)
        self.db.commit()

        logger.info(f"Template deletado permanentemente: {template_id}")

        if self.audit_service:
            try:
                from app.domain.models.audit_log import AuditAction

                self.audit_service.log(
                    action=AuditAction.TEMPLATE_DELETE,
                    template_id=template_id,
                    template_name=template.name,
                    payload={"file_path": template.file_path},
                )
            except Exception as e:
                logger.warning(f"Failed to log audit: {e}")
