"""Página de preview e confirmação."""

import base64
import fitz
import io
import streamlit as st
from datetime import datetime


def render_preview():
    """Renderiza a página de preview."""
    preview_id = st.session_state.get("current_preview_id")
    template_id = st.session_state.get("selected_template_id")

    if not preview_id:
        st.warning("Nenhum preview disponível.")
        if st.button("Ir para Preencher Formulário"):
            st.session_state.current_page = "fill_form"
            st.rerun()
        return

    try:
        from app.ui.api_client import APIClient

        client = APIClient(
            st.session_state.get("api_base_url", "http://localhost:8000/api/v1")
        )

        template = st.session_state.get("selected_template")
        preview = st.session_state.get("current_preview")

        if not preview:
            preview = client.get_preview(preview_id)
            st.session_state.current_preview = preview

        st.title("🎯 Preview do Documento")

        st.markdown("---")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("ID do Preview", preview_id)

        with col2:
            st.metric("Status", preview.get("status", "N/A").upper())

        with col3:
            created = preview.get("created_at", "")
            if created:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                st.metric("Criado em", dt.strftime("%d/%m/%Y %H:%M"))

        with col4:
            file_size = preview.get("file_size", 0) / (1024 * 1024)
            st.metric("Tamanho", f"{file_size:.2f} MB")

        st.markdown("---")

        st.markdown("### 📝 Dados Preenchidos")

        field_data = preview.get("field_data", {})
        if field_data:
            st.json(field_data)
        else:
            st.info("Nenhum dado preenchido.")

        st.markdown("---")

        st.markdown("### 📄 Visualização do Documento")

        pdf_bytes = client.get_preview_pdf(preview_id)

        if pdf_bytes:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            doc.close()

            page_options = [f"Página {i + 1}" for i in range(page_count)]

            selected_page = st.selectbox(
                "Selecione a página:",
                options=page_options,
                index=0,
                key="preview_page_selector",
            )

            page_index = page_options.index(selected_page)

            page_image = render_preview_page(pdf_bytes, page_index)

            if page_image:
                st.image(
                    page_image,
                    caption=f"Preview - {selected_page}",
                    use_container_width=True,
                )

                st.download_button(
                    label="📥 Baixar Preview PDF",
                    data=pdf_bytes,
                    file_name="preview.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.warning("Não foi possível gerar a visualização.")
        else:
            st.error("Não foi possível carregar o PDF do preview.")

        st.markdown("---")

        st.markdown("### ✅ Confirmar Geração")

        col_confirm, col_cancel = st.columns([2, 1])

        with col_confirm:
            with st.form("confirm_form"):
                version_name = st.text_input(
                    "Nome da Versão *",
                    placeholder="Versão Final",
                    help="Nome que será dado à versão gerada",
                )

                description = st.text_area(
                    "Descrição (opcional)",
                    placeholder="Descrição da versão...",
                    height=3,
                )

                confirm_btn = st.form_submit_button(
                    "✅ Confirmar e Gerar Versão",
                    type="primary",
                    use_container_width=True,
                )

                if confirm_btn:
                    if not version_name:
                        st.error("Nome da versão é obrigatório!")
                    else:
                        try:
                            version = client.confirm_preview(
                                preview_id=preview_id,
                                version_name=version_name,
                                description=description,
                            )

                            st.success(
                                f"✅ Versão '{version_name}' criada com sucesso!"
                            )
                            st.info(f"ID da Versão: {version.get('id')}")
                            st.info(
                                f"Número da Versão: v{version.get('version_number')}"
                            )

                            st.session_state.current_preview_id = None
                            st.session_state.current_preview = None
                            st.session_state.field_values = {}

                            if st.button("Ver Histórico de Versões"):
                                st.session_state.current_page = "version_history"
                                st.rerun()

                        except Exception as e:
                            st.error(f"Erro ao confirmar preview: {str(e)}")

        with col_cancel:
            st.markdown("### ou")

            cancel_btn = st.button("❌ Cancelar Preview", use_container_width=True)

            if cancel_btn:
                try:
                    client.cancel_preview(preview_id)
                    st.warning("Preview cancelado.")
                    st.session_state.current_preview_id = None
                    st.session_state.current_preview = None
                    st.session_state.field_values = {}
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao cancelar preview: {str(e)}")

    except Exception as e:
        st.error(f"Erro ao carregar preview: {str(e)}")
        import traceback

        st.code(traceback.format_exc())


def render_preview_page(pdf_bytes: bytes, page_index: int) -> str:
    """Renderiza uma página do PDF de preview como imagem."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

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
    render_preview()
