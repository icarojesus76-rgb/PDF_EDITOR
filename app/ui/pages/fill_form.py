"""Página de preenchimento de formulário."""

import streamlit as st


def render_fill_form():
    """Renderiza a página de preenchimento de formulário."""
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

        st.title(f"📝 Preencher: {template.get('name')}")

        st.markdown("---")

        fields_data = client.get_fields(template_id)
        fields = fields_data.get("fields", []) if fields_data else []

        if not fields:
            st.warning("Nenhum campo configurado neste template.")
            st.info("Vá para 'Editar Campos' para criar campos editáveis.")
            if st.button("Ir para Editor de Campos"):
                st.session_state.current_page = "field_editor"
                st.rerun()
            return

        st.write(f"**Campos disponíveis:** {len(fields)}")

        st.markdown("---")

        if "field_values" not in st.session_state:
            st.session_state.field_values = {}

        field_values = st.session_state.field_values

        with st.form("preenchimento_form"):
            submitted = False

            for field in fields:
                if not field.get("is_active", True):
                    continue

                field_name = field.get("name")
                field_label = field.get("label") or field_name
                field_type = field.get("field_type", "text")
                required = field.get("required", False)
                default_value = field.get("default_value", "")
                placeholder = field.get("placeholder", "")
                max_length = field.get("max_length")

                current_value = field_values.get(field_name, default_value or "")

                required_mark = " *" if required else ""
                help_text = f"{field_label}{required_mark}"

                if field_type == "text":
                    value = st.text_input(
                        help_text,
                        value=current_value,
                        placeholder=placeholder,
                        key=f"field_{field_name}",
                        max_chars=max_length,
                    )
                    field_values[field_name] = value

                elif field_type == "number":
                    value = st.number_input(
                        help_text,
                        value=float(current_value) if current_value else 0.0,
                        key=f"field_{field_name}",
                        step=1.0,
                    )
                    field_values[field_name] = str(value)

                elif field_type == "date":
                    from datetime import datetime

                    if current_value:
                        try:
                            dt = datetime.strptime(current_value, "%Y-%m-%d")
                            default_date = dt.date()
                        except:
                            default_date = None
                    else:
                        default_date = None

                    value = st.date_input(
                        help_text, value=default_date, key=f"field_{field_name}"
                    )
                    field_values[field_name] = str(value) if value else ""

                elif field_type == "multiline":
                    value = st.text_area(
                        help_text,
                        value=current_value,
                        placeholder=placeholder,
                        key=f"field_{field_name}",
                        max_chars=max_length,
                    )
                    field_values[field_name] = value

                elif field_type == "checkbox":
                    value = st.checkbox(
                        help_text,
                        value=bool(current_value) if current_value else False,
                        key=f"field_{field_name}",
                    )
                    field_values[field_name] = "true" if value else "false"

            st.markdown("---")

            col_submit, col_preview = st.columns([1, 2])

            with col_submit:
                submit_btn = st.form_submit_button(
                    "🎯 Gerar Preview", type="primary", use_container_width=True
                )

            with col_preview:
                clear_btn = st.form_submit_button(
                    "🧹 Limpar Campos", use_container_width=True
                )

            if submit_btn:
                st.session_state.field_values = field_values
                submitted = True

            if clear_btn:
                st.session_state.field_values = {}
                st.rerun()

        if submitted:
            valid_fields = {k: v for k, v in field_values.items() if v}

            if not valid_fields:
                st.warning("Preenha pelo menos um campo para gerar o preview.")
            else:
                with st.spinner("Gerando preview..."):
                    try:
                        preview = client.create_preview(template_id, valid_fields)
                        st.session_state.current_preview_id = preview.get("id")
                        st.session_state.current_preview = preview

                        st.success("✅ Preview gerado com sucesso!")

                        if st.button("Ir para Preview"):
                            st.session_state.current_page = "preview"
                            st.rerun()

                    except Exception as e:
                        st.error(f"Erro ao gerar preview: {str(e)}")

        st.markdown("---")

        st.markdown("### 📋 Valores Atuais")

        if field_values:
            import json

            st.json(field_values)
        else:
            st.info("Nenhum valor preenchido ainda.")

    except Exception as e:
        st.error(f"Erro ao carregar formulário: {str(e)}")
        import traceback

        st.code(traceback.format_exc())


if __name__ == "__main__":
    render_fill_form()
