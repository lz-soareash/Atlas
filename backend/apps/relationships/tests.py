"""Testes do app relationships (CRUD, validações, grafo)."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.knowledge.models import Knowledge
from apps.projects.models import Project
from .models import Relationship


def endpoint_for(instance):
    from django.contrib.contenttypes.models import ContentType

    ct = ContentType.objects.get_for_model(instance)
    return {"model": f"{ct.app_label}.{ct.model}", "id": str(instance.pk)}


class RelationshipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.other = User.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.base = reverse("relationships-list")
        self.k = Knowledge.objects.create(owner=self.user, title="Django")
        self.p = Project.objects.create(owner=self.user, name="Atlas")

    def _create(self, origin=None, target=None, type="USA", **kw):
        data = {
            "type": type,
            "origin": endpoint_for(origin or self.k),
            "target": endpoint_for(target or self.p),
        }
        data.update(kw)
        return self.client.post(self.base, data, format="json")

    def _other_endpoints(self):
        ok = Knowledge.objects.create(owner=self.other, title="Outro")
        op = Project.objects.create(owner=self.other, name="Outro projeto")
        return ok, op

    # --- Criação ---
    def test_create_relationship(self):
        resp = self._create()
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Relationship.objects.get(pk=resp.data["id"]).owner, self.user)

    def test_create_requires_auth(self):
        anon = APIClient()
        resp = anon.post(self.base, self._create().data, format="json")
        self.assertEqual(resp.status_code, 401)

    # --- Listagem / isolamento ---
    def test_list_only_own(self):
        self._create()
        ok, op = self._other_endpoints()
        Relationship.objects.create(owner=self.other, type="USA", origin=ok, target=op)
        resp = self.client.get(self.base)
        self.assertEqual(resp.data["count"], 1)

    # --- IDOR: não permite relacionar entidade de outro usuário ---
    def test_reject_other_owner_endpoint(self):
        other_k = Knowledge.objects.create(owner=self.other, title="Privado")
        resp = self._create(origin=other_k)
        self.assertEqual(resp.status_code, 400)

    # --- Validações ---
    def test_reject_self_loop(self):
        resp = self._create(origin=self.k, target=self.k)
        self.assertEqual(resp.status_code, 400)

    def test_reject_duplicate(self):
        self._create()
        resp = self._create()
        self.assertEqual(resp.status_code, 400)

    def test_retrieve_other_returns_404(self):
        ok, op = self._other_endpoints()
        rel = Relationship.objects.create(owner=self.other, type="USA", origin=ok, target=op)
        resp = self.client.get(reverse("relationships-detail", args=[rel.pk]))
        self.assertEqual(resp.status_code, 404)

    # --- Soft delete ---
    def test_delete_is_soft(self):
        rel = self._create().data
        resp = self.client.delete(reverse("relationships-detail", args=[rel["id"]]))
        self.assertEqual(resp.status_code, 204)
        self.assertTrue(Relationship.objects.get(pk=rel["id"]).is_deleted)

    def test_invalid_type(self):
        resp = self._create(type="INEXISTENTE")
        self.assertEqual(resp.status_code, 400)


class GraphTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@atlas.test", password="senha-forte-123")
        self.other = User.objects.create_user(email="b@atlas.test", password="senha-forte-123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = reverse("graph")
        self.k = Knowledge.objects.create(owner=self.user, title="Django")
        self.p = Project.objects.create(owner=self.user, name="Atlas")

    def test_empty_graph(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["nodes"], [])
        self.assertEqual(resp.data["edges"], [])

    def test_graph_with_relationship(self):
        Relationship.objects.create(owner=self.user, type="USA", origin=self.k, target=self.p)
        resp = self.client.get(self.url)
        self.assertEqual(len(resp.data["edges"]), 1)
        self.assertEqual(len(resp.data["nodes"]), 2)
        labels = {n["label"] for n in resp.data["nodes"]}
        self.assertEqual(labels, {"Conhecimento", "Projeto"})

    def test_graph_isolated_by_owner(self):
        ok = Knowledge.objects.create(owner=self.other, title="Outro")
        op = Project.objects.create(owner=self.other, name="Outro projeto")
        Relationship.objects.create(owner=self.other, type="USA", origin=ok, target=op)
        resp = self.client.get(self.url)
        self.assertEqual(resp.data["edges"], [])
        self.assertEqual(resp.data["nodes"], [])

    def test_graph_excludes_soft_deleted_entities(self):
        Relationship.objects.create(owner=self.user, type="USA", origin=self.k, target=self.p)
        self.k.soft_delete()
        resp = self.client.get(self.url)
        # Projeto é a única entidade viva, mas a aresta não pode ser desenhada
        # porque exige as duas pontas presentes. Nenhum nó/aresta:
        self.assertEqual(resp.data["nodes"], [])
        self.assertEqual(resp.data["edges"], [])

    def test_requires_auth(self):
        anon = APIClient()
        resp = anon.get(self.url)
        self.assertEqual(resp.status_code, 401)
