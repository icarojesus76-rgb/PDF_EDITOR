"""Página de histórico de versões."""

import streamlit as st
from datetime import datetime


def render_version_history():
    """Renderiza a página de histórico de versões."""
    template_id = st.session_state.get("selected_template_id")

    st.title("📜 Histórico de Versões")

    if not template_id:
        st.markdown("""
        Selecione um template para ver seu histórico de versões.
        """)

        try:
            from app.ui.api_client import APIClient

            client = APIClient(
                st.session_state.get("api_base_url", "http://localhost:8000/api/v1")
            )
            templates = client.get_templates(limit=100)

            if templates.get("items"):
                template_options = {
                    t.get("name"): t.get("id") for t in templates["items"]
                }

                selected = st.selectbox(
                    "Selecione um Template:", options=list(template_options.keys())
                )

                if selected:
                    template_id = template_options[selected]
                    st.session_state.selected_template_id = template_id
        except Exception as e:
            st.error(f"Erro ao carregar templates: {str(e)}")
            return

    if template_id:
        try:
            from app.ui.api_client import APIClient

            client = APIClient(
                st.session_state.get("api_base_url", "http://localhost:8000/api/v1")
            )

            template = client.get_template(template_id)
            versions = client.get_all_versions(template_id)
            stats = client.get_version_statistics(template_id)

            st.markdown("---")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total de Versões", stats.get("total_versions", 0))

            with col2:
                st.metric("Versões Ativas", stats.get("active_versions", 0))

            with col3:
                st.metric("Arquivadas", stats.get("archived_versions", 0))

            with col4:
                latest = stats.get("latest_version")
                st.metric("Última Versão", f"v{latest}" if latest else "N/A")

            st.markdown("---")

            st.markdown(f"### 📋 Versões de: *{template.get('name')}*")

            if versions:
                for version in versions:
                    render_version_card(version, client)
            else:
                st.info("Nenhuma versão encontrada para este template.")
                st.info("Preencha o formulário e gere uma versão para começar.")
                if st.button("Ir para Preencher"):
                    st.session_state.current_page = "fill_form"
                    st.rerun()

        except Exception as e:
            st.error(f"Erro ao carregar histórico: {str(e)}")
            import traceback

            st.code(traceback.format_exc())


def render_version_card(version: dict, client):
    """Renderiza um card de versão."""
    version_id = version.get("id")
    version_number = version.get("version_number")
    name = version.get("name")
    description = version.get("description")
    status = version.get("status")
    created_at = version.get("created_at", "")
    created_by = version.get("created_by")
    file_size = version.get("file_size", 0)
    field_data = version.get("field_data", {})

    status_icons = {"active": "✅", "draft": "📝", "archived": "📦", "superseded": "🔄"}

    status_icon = status_icons.get(status, "❓")

    with st.container():
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            st.markdown(f"### {status_icon} **v{version_number}** - {name}")
            if description:
                st.caption(description)

        with col2:
            size_mb = file_size / (1024 * 1024)
            st.metric("Tamanho", f"{size_mb:.2f} MB")

        with col3:
            if created_at:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                st.caption(f"Criado em: {dt.strftime('%d/%m/%Y %H:%M')}")

        with col4:
            st.caption(f"**Status:** {status.upper()}")

        col_btns = st.columns(3)

        with col_btns[0]:
            try:
                pdf_bytes = client.get_version_pdf(version_id)
                st.download_button(
                    "📥 Baixar",
                    data=pdf_bytes,
                    file_name=f"{name}_v{version_number}.pdf",
                    mime="application/pdf",
                    key=f"download_{version_id}",
                    use_container_width=True,
                )
            except Exception as e:
                st.warning("PDF não disponível")

        with col_btns[1]:
            if st.button("👁️ Visualizar", key=f"view_version_{version_id}"):
                pass

        with col_btns[2]:
            if st.button("📊 Detalhes", key=f"details_{version_id}"):
                pass

        if field_data:
            with st.expander("Ver dados preenchidos"):
                st.json(field_data)

        if created_by:
            st.caption(f"Criado por: {created_by}")

        st.markdown("---")


if __name__ == "__main__":
    render_version_history()
