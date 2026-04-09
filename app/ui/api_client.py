"""Módulo de API Client para comunicação com backend."""

import base64
import requests
from typing import Optional


class APIClient:
    """Cliente HTTP para comunicação com a API FastAPI."""

    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_templates(self, skip: int = 0, limit: int = 20):
        """Lista templates."""
        response = self.session.get(
            f"{self.base_url}/templates/", params={"skip": skip, "limit": limit}
        )
        response.raise_for_status()
        return response.json()

    def get_template(self, template_id: int):
        """Busca template por ID."""
        response = self.session.get(f"{self.base_url}/templates/{template_id}")
        response.raise_for_status()
        return response.json()

    def get_template_metadata(self, template_id: int):
        """Busca metadados do template."""
        response = self.session.get(f"{self.base_url}/templates/{template_id}/metadata")
        response.raise_for_status()
        return response.json()

    def upload_template(self, file, name: Optional[str] = None):
        """Faz upload de template."""
        files = {"file": file}
        data = {"name": name} if name else {}
        response = self.session.post(
            f"{self.base_url}/templates/upload", files=files, data=data
        )
        response.raise_for_status()
        return response.json()

    def get_fields(self, template_id: int):
        """Lista campos de um template."""
        response = self.session.get(f"{self.base_url}/fields/template/{template_id}")
        response.raise_for_status()
        return response.json()

    def create_field(self, field_data: dict):
        """Cria um novo campo."""
        response = self.session.post(f"{self.base_url}/fields/", json=field_data)
        response.raise_for_status()
        return response.json()

    def update_field(self, field_id: int, field_data: dict):
        """Atualiza um campo."""
        response = self.session.put(
            f"{self.base_url}/fields/{field_id}", json=field_data
        )
        response.raise_for_status()
        return response.json()

    def delete_field(self, field_id: int):
        """Deleta um campo."""
        response = self.session.delete(f"{self.base_url}/fields/{field_id}")
        response.raise_for_status()
        return response.json()

    def create_preview(self, template_id: int, field_values: dict):
        """Cria preview."""
        response = self.session.post(
            f"{self.base_url}/previews/",
            json={
                "template_id": template_id,
                "field_values": field_values,
            },
        )
        response.raise_for_status()
        return response.json()

    def get_preview(self, preview_id: int):
        """Busca preview por ID."""
        response = self.session.get(f"{self.base_url}/previews/{preview_id}")
        response.raise_for_status()
        return response.json()

    def get_preview_pdf(self, preview_id: int):
        """Busca PDF do preview."""
        response = self.session.get(f"{self.base_url}/previews/{preview_id}/download")
        response.raise_for_status()
        return response.content

    def get_preview_images(self, preview_id: int):
        """Busca imagens do preview."""
        response = self.session.get(f"{self.base_url}/previews/{preview_id}/images")
        response.raise_for_status()
        return response.json()

    def confirm_preview(
        self, preview_id: int, version_name: str, description: Optional[str] = None
    ):
        """Confirma preview e gera versão."""
        response = self.session.post(
            f"{self.base_url}/previews/{preview_id}/confirm",
            json={
                "version_name": version_name,
                "description": description,
            },
        )
        response.raise_for_status()
        return response.json()

    def cancel_preview(self, preview_id: int):
        """Cancela preview."""
        response = self.session.post(f"{self.base_url}/previews/{preview_id}/cancel")
        response.raise_for_status()
        return response.json()

    def get_versions(self, template_id: int, limit: int = 50, offset: int = 0):
        """Lista versões de um template."""
        response = self.session.get(
            f"{self.base_url}/versions/template/{template_id}",
            params={"limit": limit, "offset": offset},
        )
        response.raise_for_status()
        return response.json()

    def get_all_versions(self, template_id: int):
        """Lista todas as versões de um template."""
        response = self.session.get(
            f"{self.base_url}/versions/template/{template_id}/all"
        )
        response.raise_for_status()
        return response.json()

    def get_version(self, version_id: int):
        """Busca versão por ID."""
        response = self.session.get(f"{self.base_url}/versions/{version_id}")
        response.raise_for_status()
        return response.json()

    def get_version_pdf(self, version_id: int):
        """Busca PDF de uma versão."""
        response = self.session.get(f"{self.base_url}/versions/{version_id}/download")
        response.raise_for_status()
        return response.content

    def get_version_statistics(self, template_id: int):
        """Busca estatísticas de versões."""
        response = self.session.get(
            f"{self.base_url}/versions/template/{template_id}/statistics"
        )
        response.raise_for_status()
        return response.json()

    def get_template_image(self, template_id: int, page: int = 0):
        """Gera imagem de uma página do template."""
        response = self.session.get(
            f"{self.base_url}/templates/{template_id}/page/{page}/image"
        )
        if response.status_code == 200:
            return base64.b64encode(response.content).decode()
        return None

    def get_template_page_image(self, template_id: int, page: int = 0):
        """Retorna URL da imagem de uma página."""
        return f"{self.base_url}/templates/{template_id}/page/{page}/image"
