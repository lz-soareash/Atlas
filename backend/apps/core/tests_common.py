"""Mixin de teste reutilizável para as entidades do Knowledge Core.

Cada app define um `tests.py` que herda `EntityCrudTestMixin` e informa
`model`, `list_url`, `create_payload` (e opcionalmente `detail_route_url`).
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


class EntityCrudTestMixin:
    """Casos de teste comuns a todas as entidades do Knowledge Core."""

    # Campos opcionais a preencher na criação (default usa title/summary/status).
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.other = User.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    # Helpers
    def list_url(self):
        return reverse(f"{self.basename}-list")

    def detail_url(self, obj_id):
        return reverse(f"{self.basename}-detail", args=[obj_id])

    def _create(self, **overrides):
        payload = {**self.create_payload, **overrides}
        return self.client.post(self.list_url(), payload, format="json")

    def _make_obj_for(self, owner, **overrides):
        return self.model.objects.create(
            owner=owner,
            **{**self.create_payload, **overrides},
        )

    # --- Criação ---
    def test_create_sets_owner(self):
        resp = self._create()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(self.model.objects.get(pk=resp.data["id"]).owner, self.user)
        self.assertNotIn("deleted_at", resp.data)

    def test_create_requires_auth(self):
        anon = APIClient()
        resp = anon.post(self.list_url(), self.create_payload, format="json")
        self.assertEqual(resp.status_code, 401)

    # --- Listagem / isolamento ---
    def test_list_returns_only_own(self):
        self._create()
        self._make_obj_for(self.other)
        resp = self.client.get(self.list_url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)

    # --- Recuperação / IDOR ---
    def test_retrieve_own(self):
        obj = self._create().data
        resp = self.client.get(self.detail_url(obj["id"]))
        self.assertEqual(resp.status_code, 200)

    def test_retrieve_other_returns_404(self):
        other_obj = self._make_obj_for(self.other)
        resp = self.client.get(self.detail_url(other_obj.pk))
        self.assertEqual(resp.status_code, 404)

    # --- Atualização ---
    def test_update_own(self):
        obj = self._create().data
        resp = self.client.patch(self.detail_url(obj["id"]), {"title": "Atualizado"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "Atualizado")

    def test_update_other_returns_404(self):
        other_obj = self._make_obj_for(self.other)
        resp = self.client.patch(self.detail_url(other_obj.pk), {"title": "Hack"}, format="json")
        self.assertEqual(resp.status_code, 404)

    # --- Soft delete ---
    def test_delete_is_soft(self):
        obj = self._create().data
        resp = self.client.delete(self.detail_url(obj["id"]))
        self.assertEqual(resp.status_code, 204)
        self.assertTrue(self.model.objects.get(pk=obj["id"]).is_deleted)
        self.assertEqual(self.client.get(self.list_url()).data["count"], 0)
        self.assertEqual(self.client.get(self.detail_url(obj["id"])).status_code, 404)
