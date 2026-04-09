"""Página de listagem de templates."""

import streamlit as st
from datetime import datetime


def render_template_list():
    """Renderiza a página de listagem de templates."""
    st.title("📋 Meus Templates")

    st.markdown(
        "Gerencie seus templates PDF. Selecione um template para visualizar, editar campos ou gerar versões."
    )

    st.markdown("---")

    try:
        from app.ui.api_client import APIClient

        client = APIClient(
            st.session_state.get("api_base_url", "http://localhost:8000/api/v1")
        )
        templates = client.get_templates(limit=100)

        if templates.get("items"):
            st.write(f"**Total de Templates:** {templates.get('total', 0)}")

            for tmpl in templates["items"]:
                render_template_card(tmpl, client)
        else:
            st.info(
                "Nenhum template encontrado. Faça o upload de um template para começar."
            )
            if st.button("Fazer Upload"):
                st.session_state.current_page = "upload"
                st.rerun()

    except Exception as e:
        st.error(f"Erro ao carregar templates: {str(e)}")
        st.info("Certifique-se de que o servidor FastAPI está rodando.")


def render_template_card(template: dict, client):
    """Renderiza um card de template."""
    template_id = template.get("id")
    name = template.get("name")
    original_filename = template.get("original_filename")
    status = template.get("status")
    version_count = template.get("version_count", 0)
    created_at = template.get("created_at", "")
    file_size = template.get("file_size", 0)

    with st.container():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            status_emoji = (
                "✅" if status == "active" else "⏸️" if status == "archived" else "❌"
            )
            st.markdown(f"### {status_emoji} **{name}**")
            st.caption(f"Arquivo: {original_filename}")

        with col2:
            st.metric("Versões", version_count)

        with col3:
            size_mb = file_size / (1024 * 1024)
            st.metric("Tamanho", f"{size_mb:.2f} MB")

        with col4:
            if created_at:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                st.caption(f"Criado em: {dt.strftime('%d/%m/%Y')}")

        col_btns = st.columns(4)

        with col_btns[0]:
            if st.button("👁️ Visualizar", key=f"view_{template_id}"):
                st.session_state.selected_template_id = template_id
                st.session_state.selected_template = template
                st.session_state.current_page = "template_view"
                st.rerun()

        with col_btns[1]:
            if st.button("✏️ Editar Campos", key=f"edit_{template_id}"):
                st.session_state.selected_template_id = template_id
                st.session_state.selected_template = template
                st.session_state.current_page = "field_editor"
                st.rerun()

        with col_btns[2]:
            if st.button("📝 Preencher", key=f"fill_{template_id}"):
                st.session_state.selected_template_id = template_id
                st.session_state.selected_template = template
                st.session_state.current_page = "fill_form"
                st.rerun()

        with col_btns[3]:
            if st.button("📜 Versões", key=f"versions_{template_id}"):
                st.session_state.selected_template_id = template_id
                st.session_state.selected_template = template
                st.session_state.current_page = "version_history"
                st.rerun()

        st.markdown("---")


if __name__ == "__main__":
    render_template_list()
