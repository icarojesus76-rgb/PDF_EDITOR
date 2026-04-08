"""
Modelo de domínio para Campos Editáveis (Field).

Representa um campo editável posicionado sobre um PDF template.
Cada campo é uma camada lógica que não altera o arquivo original,
mas define onde e como o usuário pode inserir dados.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship, validates

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.models.template import Template


class FieldType(str, Enum):
    """Tipos de campos editáveis suportados."""

    TEXT = "text"  # Texto simples (uma linha)
    NUMBER = "number"  # Números
    DATE = "date"  # Data
    MULTILINE = "multiline"  # Texto multi-linha
    CHECKBOX = "checkbox"  # Checkbox booleano


class FieldAlignment(str, Enum):
    """Opções de alinhamento de texto."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class Field(Base):
    """
    Entidade Field - Campo editável sobre PDF template.

    Cada campo define uma área retangular sobre o PDF onde o usuário
    pode inserir dados. As coordenadas são em pontos (1/72 polegada)
    com origem no canto superior esquerdo da página.

    O campo é uma entidade lógica - não modifica o PDF original,
    apenas mapeia posições para futura renderização ou geração de
    documentos preenchidos.

    Attributes:
        id: Identificador único
        template_id: FK para o template associado
        name: Nome único do campo (para referência)
        page: Número da página (0-indexed)
        x: Posição X (canto superior esquerdo)
        y: Posição Y (canto superior esquerdo)
        width: Largura do campo
        height: Altura do campo
        field_type: Tipo de dado (text, number, date, multiline, checkbox)
        font_family: Família da fonte
        font_size: Tamanho da fonte em pontos
        alignment: Alinhamento do texto
        color: Cor em hexadecimal (ex: #000000)
        required: Se o campo é obrigatório
        default_value: Valor padrão pré-preenchido
        placeholder: Texto de ajuda quando vazio
        max_length: Limite máximo de caracteres
        order: Ordem de exibição/navegação
        created_at: Data de criação
        updated_at: Data de atualização
    """

    __tablename__ = "fields"

    # Identificação
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Nome e identificação
    name = Column(String(100), nullable=False, comment="Nome único do campo")
    label = Column(String(255), nullable=True, comment="Label exibido ao usuário")
    description = Column(Text, nullable=True, comment="Descrição/ajuda do campo")

    # Posicionamento (coordenadas em pontos, origem: canto superior esquerdo)
    page = Column(
        Integer, nullable=False, default=0, comment="Número da página (0-indexed)"
    )
    x = Column(Float, nullable=False, comment="Posição X (esquerda)")
    y = Column(Float, nullable=False, comment="Posição Y (topo)")
    width = Column(Float, nullable=False, comment="Largura do campo")
    height = Column(Float, nullable=False, comment="Altura do campo")

    # Configurações de aparência
    field_type = Column(
        String(20),
        nullable=False,
        default=FieldType.TEXT.value,
        comment="Tipo do campo: text, number, date, multiline, checkbox",
    )
    font_family = Column(
        String(100), nullable=True, default="Helvetica", comment="Família da fonte"
    )
    font_size = Column(
        Float, nullable=True, default=12.0, comment="Tamanho da fonte em pontos"
    )
    alignment = Column(
        String(10),
        nullable=True,
        default=FieldAlignment.LEFT.value,
        comment="Alinhamento: left, center, right",
    )
    color = Column(
        String(7), nullable=True, default="#000000", comment="Cor em hexadecimal"
    )
    background_color = Column(
        String(7), nullable=True, comment="Cor de fundo (opcional)"
    )

    # Validações e comportamento
    required = Column(
        Boolean, nullable=False, default=False, comment="Campo obrigatório"
    )
    default_value = Column(String(500), nullable=True, comment="Valor padrão")
    placeholder = Column(String(255), nullable=True, comment="Texto de placeholder")
    max_length = Column(Integer, nullable=True, comment="Máximo de caracteres")

    # Ordenação
    order = Column(Integer, nullable=False, default=0, comment="Ordem de exibição")

    # Controle
    is_active = Column(
        Boolean, nullable=False, default=True, comment="Campo ativo/inativo"
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    template = relationship("Template", back_populates="fields")

    # Índices compostos para otimização
    __table_args__ = (
        Index("idx_field_template_page", "template_id", "page"),
        Index("idx_field_template_name", "template_id", "name", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Field(id={self.id}, name='{self.name}', page={self.page}, type={self.field_type})>"

    # Validações SQLAlchemy
    @validates("width", "height")
    def validate_positive_dimension(self, key, value):
        """Valida que dimensões são positivas."""
        if value is not None and value <= 0:
            raise ValueError(f"{key} deve ser maior que zero")
        return value

    @validates("page")
    def validate_page(self, key, value):
        """Valida que página é não-negativa."""
        if value is not None and value < 0:
            raise ValueError("Página não pode ser negativa")
        return value

    @validates("x", "y")
    def validate_position(self, key, value):
        """Valida que posições são não-negativas."""
        if value is not None and value < 0:
            raise ValueError(f"{key} não pode ser negativo")
        return value

    @property
    def bounds(self) -> dict:
        """Retorna limites do campo como dicionário."""
        return {
            "x": self.x,
            "y": self.y,
            "x2": self.x + self.width,
            "y2": self.y + self.height,
            "width": self.width,
            "height": self.height,
        }

    @property
    def center(self) -> tuple[float, float]:
        """Retorna coordenadas do centro do campo."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    def intersects(self, other: "Field", tolerance: float = 0.0) -> bool:
        """
        Verifica se este campo intersecta com outro.

        Args:
            other: Outro campo para verificar interseção
            tolerance: Margem de tolerância em pontos

        Returns:
            True se há interseção
        """
        if self.page != other.page:
            return False

        # Ajusta com tolerância
        self_x1 = self.x - tolerance
        self_y1 = self.y - tolerance
        self_x2 = self.x + self.width + tolerance
        self_y2 = self.y + self.height + tolerance

        other_x1 = other.x - tolerance
        other_y1 = other.y - tolerance
        other_x2 = other.x + other.width + tolerance
        other_y2 = other.y + other.height + tolerance

        # Verifica não-interseção
        if self_x2 <= other_x1 or other_x2 <= self_x1:
            return False
        if self_y2 <= other_y1 or other_y2 <= self_y1:
            return False

        return True

    def to_dict(self, include_template: bool = False) -> dict:
        """
        Serializa o campo para dicionário.

        Args:
            include_template: Se deve incluir dados do template

        Returns:
            Dicionário com dados do campo
        """
        result = {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "page": self.page,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "field_type": self.field_type,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "alignment": self.alignment,
            "color": self.color,
            "background_color": self.background_color,
            "required": self.required,
            "default_value": self.default_value,
            "placeholder": self.placeholder,
            "max_length": self.max_length,
            "order": self.order,
            "is_active": self.is_active,
            "bounds": self.bounds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_template and self.template:
            result["template"] = {"id": self.template.id, "name": self.template.name}

        return result
