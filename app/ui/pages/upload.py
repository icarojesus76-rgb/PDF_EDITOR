"""Página de upload de template."""

import streamlit as st
from datetime import datetime


def render_upload():
    """Renderiza a página de upload de template."""
    st.title("📤 Upload de Template")

    st.markdown("""
    Envie um arquivo PDF para ser usado como template. O arquivo será
    armazenado de forma imutável e servir como base para criação de versões.
    """)

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Selecione um arquivo PDF",
            type=["pdf"],
            help="Apenas arquivos PDF são aceitos",
        )

    with col2:
        custom_name = st.text_input(
            "Nome personalizado (opcional)",
            placeholder="Meu Template",
            help="Deixe vazio para usar o nome do arquivo",
        )

    if uploaded_file is not None:
        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.metric("Tamanho", f"{file_size_mb:.2f} MB")

        with col2:
            st.metric("Tipo", uploaded_file.type or "application/pdf")

        with col3:
            st.metric("Nome", uploaded_file.name)

        if st.button("✅ Enviar Template", type="primary", use_container_width=True):
            try:
                from app.ui.api_client import APIClient

                client = APIClient(
                    st.session_state.get("api_base_url", "http://localhost:8000/api/v1")
                )

                name = custom_name if custom_name else None
                template = client.upload_template(uploaded_file, name)

                st.success(f"✅ Template '{template.get('name')}' enviado com sucesso!")
                st.info(f"ID do Template: {template.get('id')}")

                st.session_state.selected_template_id = template.get("id")
                st.session_state.selected_template = template

                st.markdown("### Próximos Passos")
                st.markdown("""
                - Visualize o template
                - Crie campos editáveis
                - Gere sua primeira versão
                """)

                if st.button("Ir para Visualização"):
                    st.session_state.current_page = "template_view"
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Erro ao enviar template: {str(e)}")
                st.info("Certifique-se de que o servidor FastAPI está rodando.")

    st.markdown("---")

    st.markdown("### 📋 Templates Recentes")

    try:
        from app.ui.api_client import APIClient

        client = APIClient(
            st.session_state.get("api_base_url", "http://localhost:8000/api/v1")
        )
        templates = client.get_templates(limit=5)

        if templates.get("items"):
            for tmpl in templates["items"]:
                with st.expander(f"📄 {tmpl.get('name')} (ID: {tmpl.get('id')})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Arquivo:** {tmpl.get('original_filename')}")
                        st.write(f"**Status:** {tmpl.get('status')}")
                    with col2:
                        created = tmpl.get("created_at", "")
                        if created:
                            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            st.write(f"**Criado em:** {dt.strftime('%d/%m/%Y %H:%M')}")
                        st.write(f"**Versões:** {tmpl.get('version_count', 0)}")
        else:
            st.info("Nenhum template encontrado.")
    except Exception as e:
        st.warning(f"Não foi possível carregar templates: {str(e)}")


if __name__ == "__main__":
    render_upload()
