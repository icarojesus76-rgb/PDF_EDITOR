"""Página de editor de campos."""

import base64
import fitz
import streamlit as st
from datetime import datetime


def render_field_editor():
    """Renderiza a página de edição de campos."""
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

        st.title(f"✏️ Editar Campos: {template.get('name')}")

        st.markdown("---")

        tab1, tab2 = st.tabs(["🖱️ Adicionar Campo", "📋 Lista de Campos"])

        with tab1:
            render_add_field_tab(client, template_id, metadata)

        with tab2:
            render_fields_list_tab(client, template_id)

    except Exception as e:
        st.error(f"Erro ao carregar editor de campos: {str(e)}")
        import traceback

        st.code(traceback.format_exc())


def render_add_field_tab(client, template_id: int, metadata: dict):
    """Renderiza a aba de adição de campo."""
    page_count = metadata.get("page_count", 1)
    page_options = [f"Página {i + 1}" for i in range(page_count)]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Configurações do Campo")

        selected_page_str = st.selectbox(
            "Página", options=page_options, index=0, key="field_page"
        )
        page_index = page_options.index(selected_page_str)

        field_name = st.text_input(
            "Nome do Campo *",
            placeholder="nome_campo",
            help="Identificador único do campo",
        )

        field_label = st.text_input("Label (nome exibido)", placeholder="Nome do Campo")

        field_type = st.selectbox(
            "Tipo de Campo",
            options=["text", "number", "date", "multiline", "checkbox"],
            index=0,
            format_func=lambda x: {
                "text": "Texto",
                "number": "Número",
                "date": "Data",
                "multiline": "Texto Longo",
                "checkbox": "Caixa de Seleção",
            }.get(x, x),
        )

        required = st.checkbox("Campo Obrigatório", value=False)

        default_value = st.text_input("Valor Padrão", placeholder="Valor inicial")
        placeholder = st.text_input("Placeholder", placeholder="Texto de ajuda")
        max_length = st.number_input(
            "Máximo de Caracteres", min_value=0, value=0, step=1
        )

        st.markdown("### Posição e Tamanho")

        col_pos1, col_pos2 = st.columns(2)

        with col_pos1:
            pos_x = st.number_input(
                "Posição X (pontos)", min_value=0.0, value=100.0, step=1.0
            )
            pos_y = st.number_input(
                "Posição Y (pontos)", min_value=0.0, value=100.0, step=1.0
            )

        with col_pos2:
            width = st.number_input(
                "Largura (pontos)", min_value=1.0, value=200.0, step=1.0
            )
            height = st.number_input(
                "Altura (pontos)", min_value=1.0, value=30.0, step=1.0
            )

        st.markdown("### Aparência")

        col_style1, col_style2 = st.columns(2)

        with col_style1:
            font_family = st.selectbox(
                "Fonte", options=["Helvetica", "Times", "Courier"], index=0
            )
            font_size = st.number_input(
                "Tamanho da Fonte", min_value=6.0, max_value=72.0, value=12.0, step=0.5
            )

        with col_style2:
            alignment = st.selectbox(
                "Alinhamento",
                options=["left", "center", "right"],
                index=0,
                format_func=lambda x: {
                    "left": "Esquerda",
                    "center": "Centro",
                    "right": "Direita",
                }.get(x, x),
            )
            color = st.color_picker("Cor do Texto", "#000000")

        order = st.number_input("Ordem de Exibição", min_value=0, value=0, step=1)

        if st.button("➕ Adicionar Campo", type="primary", use_container_width=True):
            if not field_name:
                st.error("Nome do campo é obrigatório!")
            else:
                try:
                    field_data = {
                        "template_id": template_id,
                        "name": field_name,
                        "label": field_label or None,
                        "page": page_index,
                        "x": pos_x,
                        "y": pos_y,
                        "width": width,
                        "height": height,
                        "field_type": field_type,
                        "font_family": font_family,
                        "font_size": font_size,
                        "alignment": alignment,
                        "color": color,
                        "required": required,
                        "default_value": default_value or None,
                        "placeholder": placeholder or None,
                        "max_length": int(max_length) if max_length > 0 else None,
                        "order": int(order),
                    }

                    field = client.create_field(field_data)
                    st.success(f"✅ Campo '{field_name}' criado com sucesso!")

                    st.session_state.template_fields = client.get_fields(template_id)

                except Exception as e:
                    st.error(f"Erro ao criar campo: {str(e)}")

    with col2:
        st.markdown("### Visualização")

        page_image = render_template_page_with_fields(template_id, page_index)

        if page_image:
            st.image(
                page_image, caption=f"Página {page_index + 1}", use_container_width=True
            )
        else:
            st.warning("Não foi possível carregar a visualização.")


def render_fields_list_tab(client, template_id: int):
    """Renderiza a aba de listagem de campos."""
    try:
        fields = client.get_fields(template_id)

        if fields and fields.get("fields"):
            field_list = fields["fields"]
            st.write(f"**Total de Campos:** {len(field_list)}")

            st.markdown("---")

            for field in field_list:
                render_field_card(field, client, template_id)
        else:
            st.info(
                "Nenhum campo encontrado. Adicione campos na aba 'Adicionar Campo'."
            )

    except Exception as e:
        st.error(f"Erro ao carregar campos: {str(e)}")


def render_field_card(field: dict, client, template_id: int):
    """Renderiza um card de campo."""
    field_id = field.get("id")
    name = field.get("name")
    label = field.get("label") or name
    field_type = field.get("field_type")
    page = field.get("page", 0) + 1
    required = field.get("required", False)
    is_active = field.get("is_active", True)

    type_labels = {
        "text": "Texto",
        "number": "Número",
        "date": "Data",
        "multiline": "Texto Longo",
        "checkbox": "Checkbox",
    }

    with st.container():
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

        with col1:
            status_icon = "✅" if is_active else "⛔"
            st.markdown(f"**{status_icon} {label}**")
            st.caption(f"ID: {field_id} | Nome: {name}")

        with col2:
            st.write(f"**Tipo:** {type_labels.get(field_type, field_type)}")

        with col3:
            st.write(f"**Página:** {page}")

        with col4:
            st.write("**Obrigatório:**" + (" Sim" if required else " Não"))

        with col5:
            col_act1, col_act2 = st.columns(2)
            with col_act1:
                if st.button("✏️", key=f"edit_field_{field_id}", help="Editar"):
                    pass
            with col_act2:
                if st.button("🗑️", key=f"del_field_{field_id}", help="Excluir"):
                    try:
                        client.delete_field(field_id)
                        st.success(f"Campo '{name}' excluído!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {str(e)}")

        with st.expander("Ver detalhes"):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.write(f"**Posição:** X={field.get('x')}, Y={field.get('y')}")
                st.write(f"**Tamanho:** {field.get('width')} x {field.get('height')}")
            with col_d2:
                st.write(f"**Fonte:** {field.get('font_family')}")
                st.write(f"**Tamanho Fonte:** {field.get('font_size')}")
                st.write(f"**Alinhamento:** {field.get('alignment')}")

            if field.get("default_value"):
                st.write(f"**Valor Padrão:** {field.get('default_value')}")
            if field.get("placeholder"):
                st.write(f"**Placeholder:** {field.get('placeholder')}")

        st.markdown("---")


def render_template_page_with_fields(template_id: int, page_index: int) -> str:
    """Renderiza a página do template com campos sobrepostos."""
    try:
        from app.services.file_storage import FileStorageService

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
        return None


if __name__ == "__main__":
    render_field_editor()
