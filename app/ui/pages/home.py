"""Página inicial do PDF Editor."""

import streamlit as st


def render_home():
    """Renderiza a página inicial."""
    st.title("🏠 Bem-vindo ao PDF Editor Pro")

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            """
        <div class="metric-card">
            <h3>📤</h3>
            <p>Upload de Template</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown("Envie um PDF base como template para começar.")
        if st.button("Fazer Upload", key="home_upload"):
            st.session_state.current_page = "upload"
            st.rerun()

    with col2:
        st.markdown(
            """
        <div class="metric-card">
            <h3>📋</h3>
            <p>Meus Templates</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown("Gerencie seus templates PDF existentes.")
        if st.button("Ver Templates", key="home_templates"):
            st.session_state.current_page = "templates"
            st.rerun()

    with col3:
        st.markdown(
            """
        <div class="metric-card">
            <h3>✏️</h3>
            <p>Editar Campos</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown("Crie campos editáveis nos seus templates.")
        if st.button("Editar Campos", key="home_edit"):
            st.session_state.current_page = "field_editor"
            st.rerun()

    with col4:
        st.markdown(
            """
        <div class="metric-card">
            <h3>📜</h3>
            <p>Histórico</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.markdown("Consulte versões geradas anteriormente.")
        if st.button("Ver Histórico", key="home_history"):
            st.session_state.current_page = "version_history"
            st.rerun()

    st.markdown("---")

    st.markdown("### 🔄 Fluxo de Trabalho")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("""
        **1. Upload**
        
        Envie seu PDF modelo e ele será
        armazena de forma imutável.
        """)

    with col2:
        st.info("""
        **2. Criar Campos**
        
        Defina campos editáveis nas
        posições desejadas no documento.
        """)

    with col3:
        st.info("""
        **3. Gerar Versões**
        
        Preencha os campos, gere um
        preview e confirme para criar
        uma versão final.
        """)

    st.markdown("---")

    st.markdown("### 📊 Estatísticas")

    try:
        from app.ui.api_client import APIClient

        client = APIClient(
            st.session_state.get("api_base_url", "http://localhost:8000/api/v1")
        )
        templates = client.get_templates(limit=100)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de Templates", templates.get("total", 0))
        with col2:
            st.metric("Templates na Página", len(templates.get("items", [])))
    except Exception as e:
        st.warning(f"Não foi possível carregar estatísticas: {str(e)}")
        st.info(
            "Certifique-se de que o servidor FastAPI está rodando em http://localhost:8000"
        )


if __name__ == "__main__":
    render_home()
