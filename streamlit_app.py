"""
PDF Editor - Interface Profissional Streamlit.

Aplicação Streamlit para edição profissional de PDFs.
Integração completa com backend FastAPI.
"""

import streamlit as st
from streamlit_option_menu import option_menu

from app.ui.pages.home import render_home
from app.ui.pages.upload import render_upload
from app.ui.pages.template_view import render_template_view
from app.ui.pages.field_editor import render_field_editor
from app.ui.pages.fill_form import render_fill_form
from app.ui.pages.preview import render_preview
from app.ui.pages.version_history import render_version_history

st.set_page_config(
    page_title="PDF Editor Pro",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Inicializa estados da sessão."""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "home"

    if "selected_template_id" not in st.session_state:
        st.session_state.selected_template_id = None

    if "selected_template" not in st.session_state:
        st.session_state.selected_template = None

    if "template_fields" not in st.session_state:
        st.session_state.template_fields = []

    if "current_preview_id" not in st.session_state:
        st.session_state.current_preview_id = None

    if "field_values" not in st.session_state:
        st.session_state.field_values = {}

    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = "http://localhost:8000/api/v1"


def render_sidebar():
    """Renderiza menu lateral."""
    with st.sidebar:
        st.title("📄 PDF Editor Pro")
        st.markdown("---")

        menu_options = [
            "🏠 Início",
            "📤 Upload Template",
            "📋 Meus Templates",
            "📜 Histórico de Versões",
        ]

        selected = option_menu(
            "Menu",
            menu_options,
            icons=["house", "upload", "file-earmark-text", "clock-history"],
            menu_icon="cast",
            default_index=0,
            key="main_menu",
        )

        st.markdown("---")
        st.markdown("### ℹ️ Sobre")
        st.info(
            "Sistema profissional de edição de PDFs. "
            "Gerencie templates, crie campos editáveis, "
            "preencha formulários e mantenha histórico de versões."
        )

        return selected


def main():
    """Função principal da aplicação."""
    init_session_state()

    apply_custom_styles()

    selected_menu = render_sidebar()

    if selected_menu == "🏠 Início":
        render_home()
    elif selected_menu == "📤 Upload Template":
        render_upload()
    elif selected_menu == "📋 Meus Templates":
        render_template_list()
    elif selected_menu == "📜 Histórico de Versões":
        render_version_history()


def render_template_list():
    """Renderiza lista de templates."""
    from app.ui.pages.template_list import render_template_list as tpl_list

    tpl_list()


def apply_custom_styles():
    """Aplica estilos customizados."""
    st.markdown(
        """
        <style>
        .main {
            background-color: #f8f9fa;
        }
        .stApp {
            background-color: #ffffff;
        }
        .sidebar .sidebar-content {
            background-color: #1e293b;
            color: #ffffff;
        }
        div.stButton > button {
            background-color: #3b82f6;
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            border: none;
        }
        div.stButton > button:hover {
            background-color: #2563eb;
        }
        .success-message {
            padding: 1rem;
            background-color: #dcfce7;
            border-radius: 8px;
            border-left: 4px solid #22c55e;
        }
        .error-message {
            padding: 1rem;
            background-color: #fee2e2;
            border-radius: 8px;
            border-left: 4px solid #ef4444;
        }
        .info-message {
            padding: 1rem;
            background-color: #e0f2fe;
            border-radius: 8px;
            border-left: 4px solid #0ea5e9;
        }
        .card {
            background-color: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
        }
        .metric-card {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: white;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }
        .metric-card h3 {
            font-size: 2rem;
            margin: 0;
        }
        .metric-card p {
            margin: 0;
            opacity: 0.9;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
