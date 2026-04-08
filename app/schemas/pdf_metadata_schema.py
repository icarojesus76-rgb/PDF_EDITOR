"""
Schemas Pydantic para Metadados de PDF.

Define os schemas de entrada/saída para operações com metadados.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class TextBlockSchema(BaseModel):
    """Schema para bloco de texto."""

    text: str = Field(..., description="Conteúdo do texto")
    x0: float = Field(..., description="Coordenada X inicial")
    y0: float = Field(..., description="Coordenada Y inicial")
    x1: float = Field(..., description="Coordenada X final")
    y1: float = Field(..., description="Coordenada Y final")
    font: Optional[str] = Field(None, description="Nome da fonte")
    size: Optional[float] = Field(None, description="Tamanho da fonte")
    flags: Optional[int] = Field(None, description="Flags da fonte")


class ImageInfoSchema(BaseModel):
    """Schema para informações de imagem."""

    xref: int = Field(..., description="Referência da imagem no PDF")
    x0: float = Field(..., description="Coordenada X inicial")
    y0: float = Field(..., description="Coordenada Y inicial")
    x1: float = Field(..., description="Coordenada X final")
    y1: float = Field(..., description="Coordenada Y final")
    width: int = Field(..., description="Largura em pixels")
    height: int = Field(..., description="Altura em pixels")
    ext: str = Field(..., description="Extensão do arquivo (png/jpeg)")


class FormFieldSchema(BaseModel):
    """Schema para campo de formulário."""

    field_name: str = Field(..., description="Nome do campo")
    field_type: str = Field(..., description="Tipo do campo (text, checkbox, etc)")
    x0: float = Field(..., description="Coordenada X inicial")
    y0: float = Field(..., description="Coordenada Y inicial")
    x1: float = Field(..., description="Coordenada X final")
    y1: float = Field(..., description="Coordenada Y final")
    page: int = Field(..., description="Número da página (0-indexed)")
    value: Optional[str] = Field(None, description="Valor atual do campo")


class PageMetadataSchema(BaseModel):
    """Schema para metadados de uma página."""

    page_number: int = Field(..., description="Número da página (0-indexed)")
    width: float = Field(..., description="Largura da página em pontos")
    height: float = Field(..., description="Altura da página em pontos")
    rotation: int = Field(..., description="Rotação da página em graus")
    text_blocks: List[TextBlockSchema] = Field(
        default=[], description="Blocos de texto"
    )
    images: List[ImageInfoSchema] = Field(default=[], description="Imagens na página")
    form_fields: List[FormFieldSchema] = Field(
        default=[], description="Campos de formulário"
    )


class PageDimensionsSchema(BaseModel):
    """Schema simplificado para dimensões de página."""

    page: int = Field(..., description="Número da página")
    width: float = Field(..., description="Largura em pontos")
    height: float = Field(..., description="Altura em pontos")


class PDFMetadataResponse(BaseModel):
    """Schema completo para metadados do PDF."""

    id: int = Field(..., description="ID dos metadados")
    template_id: int = Field(..., description="ID do template associado")

    # Informações gerais
    page_count: int = Field(..., description="Quantidade de páginas")
    pdf_version: Optional[str] = Field(None, description="Versão do PDF")
    title: Optional[str] = Field(None, description="Título do documento")
    author: Optional[str] = Field(None, description="Autor")
    creator: Optional[str] = Field(None, description="Criador do PDF")
    producer: Optional[str] = Field(None, description="Produtor do PDF")

    # Caminhos
    metadata_json_path: str = Field(..., description="Caminho do arquivo JSON")

    # Dimensões
    page_dimensions: List[PageDimensionsSchema] = Field(
        ..., description="Dimensões de cada página"
    )
    pages: List[PageMetadataSchema] = Field(
        default=[], description="Metadados detalhados por página"
    )

    # Estatísticas
    total_text_blocks: int = Field(default=0, description="Total de blocos de texto")
    total_images: int = Field(default=0, description="Total de imagens")
    total_forms: int = Field(default=0, description="Total de campos de formulário")

    # Timestamps
    extracted_at: datetime = Field(..., description="Data da extração")
    updated_at: Optional[datetime] = Field(
        None, description="Data da última atualização"
    )

    class Config:
        from_attributes = True


class PDFMetadataSummarySchema(BaseModel):
    """Schema resumido para listagens."""

    id: int
    template_id: int
    page_count: int
    total_text_blocks: int
    total_images: int
    total_forms: int
    extracted_at: datetime

    class Config:
        from_attributes = True


class PDFMetadataCreate(BaseModel):
    """Schema para criação de metadados."""

    template_id: int = Field(..., description="ID do template")
    metadata_dict: Dict[str, Any] = Field(
        ..., description="Dicionário com metadados extraídos"
    )
