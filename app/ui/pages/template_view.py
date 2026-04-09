"""Página de visualização de template."""

import base64
import fitz
import io
import streamlit as st
from datetime import datetime


def render_template_view():
    """Renderiza a página de visualização de template."""
    template_id = st.session_state.get("selected_template_id")

    if not template_id:
        st.warning("Nenhum template selecionado.")
        if st.button("Ver Templates"):
            st.session_state.current_page = "templates"
            st.rerun()
        return

    try:
        from app.ui.api_client import APIClient

        client = APIClient(
            st.session_state.get("api_base_url", "http://localhost:8000/api/v1")
        )

        template = st.session_state.get("selected_template")
        if not template:
            template = client.get_template(template_id)
            st.session_state.selected_template = template

        metadata = client.get_template_metadata(template_id)

        st.title(f"👁️ Visualizar: {template.get('name')}")

        st.markdown("---")

        col_info1, col_info2, col_info3, col_info4 = st.columns(4)

        with col_info1:
            st.metric("Páginas", metadata.get("page_count", 0))

        with col_info2:
            file_size = template.get("file_size", 0) / (1024 * 1024)
            st.metric("Tamanho", f"{file_size:.2f} MB")

        with col_info3:
            st.metric("Versões", template.get("version_count", 0))

        with col_info4:
            status = template.get("status", "unknown")
            st.metric("Status", status.upper())

        st.markdown("### 📄 Metadados")

        with st.expander("Ver metadados detalhados"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Título:** {metadata.get('title', 'N/A')}")
                st.write(f"**Autor:** {metadata.get('author', 'N/A')}")
                st.write(f"**Criado por:** {metadata.get('creator', 'N/A')}")
            with col2:
                st.write(f"**Producer:** {metadata.get('producer', 'N/A')}")
                st.write(f"**Versão PDF:** {metadata.get('pdf_version', 'N/A')}")
                st.write(f"**Data Extração:** {metadata.get('extracted_at', 'N/A')}")

            st.write(f"**Blocos de Texto:** {metadata.get('total_text_blocks', 0)}")
            st.write(f"**Imagens:** {metadata.get('total_images', 0)}")
            st.write(f"**Formulários:** {metadata.get('total_forms', 0)}")

        st.markdown("---")

        page_count = metadata.get("page_count", 1)
        page_options = [f"Página {i + 1}" for i in range(page_count)]

        selected_page = st.selectbox(
            "Selecione a página para visualizar:",
            options=page_options,
            index=0,
            key="page_selector",
        )

        page_index = page_options.index(selected_page)

        st.markdown(f"### 📄 {selected_page}")

        page_dims = metadata.get("page_dimensions", [])
        if page_index < len(page_dims):
            page_info = page_dims[page_index]
            st.caption(
                f"Dimensões: {page_info.get('width', 0):.1f} x {page_info.get('height', 0):.1f} pontos"
            )

        page_image = render_pdf_page(template_id, page_index)

        if page_image:
            st.image(
                page_image,
                caption=f"Preview da {selected_page}",
                use_container_width=True,
            )
        else:
            st.warning("Não foi possível gerar a imagem desta página.")

        st.markdown("---")

        col_actions1, col_actions2 = st.columns(2)

        with col_actions1:
            if st.button("✏️ Editar Campos", use_container_width=True):
                st.session_state.current_page = "field_editor"
                st.rerun()

        with col_actions2:
            if st.button("📝 Preencher Formulário", use_container_width=True):
                st.session_state.current_page = "fill_form"
                st.rerun()

    except Exception as e:
        st.error(f"Erro ao carregar template: {str(e)}")
        import traceback

        st.code(traceback.format_exc())


def render_pdf_page(template_id: int, page_index: int) -> str:
    """Renderiza uma página do PDF como imagem base64."""
    try:
        from app.core.config import get_settings
        from app.services.file_storage import FileStorageService

        settings = get_settings()
        storage = FileStorageService()

        template = st.session_state.get("selected_template")
        if template:
            file_path = template.get("file_path")
            full_path = storage.get_file_path(file_path)

            if full_path.exists():
                doc = fitz.open(str(full_path))

                if page_index < len(doc):
                    page = doc[page_index]

                    zoom = 1.5
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)

                    img_data = pix.tobytes("png")
                    img_base64 = base64.b64encode(img_data).decode()

                    doc.close()

                    return f"data:image/png;base64,{img_base64}"

                doc.close()

        return None
    except Exception as e:
        st.error(f"Erro ao renderizar página: {str(e)}")
        return None


if __name__ == "__main__":
    render_template_view()
