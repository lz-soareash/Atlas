"""Testes de credenciais de serviço e autenticação por API key (Fase 10)."""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import ServiceCredential, User, UserType


def _list_url():
    return reverse("service-credential-list")


def _rotate_url(pk):
    return reverse("service-credential-rotate", args=[pk])


def _revoke_url(pk):
    return reverse("service-credential-revoke", args=[pk])


class ServiceCredentialModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="svc-owner@atlas.test", password="senha-forte-123"
        )

    def test_generate_key_format_and_hash(self):
        key = ServiceCredential.generate_key()
        self.assertTrue(key.startswith("svc_"))
        cred = ServiceCredential.objects.create(
            user=self.user,
            name="Jarvis",
            scopes=["cognitive"],
            key_hash=ServiceCredential._hash(key),
            key_hint=ServiceCredential._hint(key),
        )
        self.assertTrue(cred.check_key(key))
        self.assertIn(key[-8:], cred.key_hint)
        # chave em texto puro NÃO fica armazenada
        self.assertNotIn(key, cred.key_hash)

    def test_check_key_rejects_wrong_key(self):
        key = ServiceCredential.generate_key()
        cred = ServiceCredential.objects.create(
            user=self.user,
            name="Jarvis",
            key_hash=ServiceCredential._hash(key),
            key_hint=ServiceCredential._hint(key),
        )
        self.assertFalse(cred.check_key(key + "x"))
        self.assertFalse(cred.check_key(""))

    def test_check_key_false_when_no_hash(self):
        cred = ServiceCredential.objects.create(user=self.user, name="vazia")
        self.assertFalse(cred.check_key("qualquer-coisa"))

    def test_rotate_changes_hash(self):
        key = ServiceCredential.generate_key()
        cred = ServiceCredential.objects.create(
            user=self.user,
            name="Jarvis",
            key_hash=ServiceCredential._hash(key),
            key_hint=ServiceCredential._hint(key),
        )
        old_hash = cred.key_hash
        new_key = ServiceCredential.generate_key()
        cred.rotate(new_key)
        cred.refresh_from_db()
        self.assertNotEqual(cred.key_hash, old_hash)
        self.assertTrue(cred.check_key(new_key))
        self.assertFalse(cred.check_key(key))

    def test_revoke_deactivates(self):
        key = ServiceCredential.generate_key()
        cred = ServiceCredential.objects.create(
            user=self.user,
            name="Jarvis",
            key_hash=ServiceCredential._hash(key),
        )
        cred.revoke()
        cred.refresh_from_db()
        self.assertFalse(cred.is_active)
        self.assertIsNotNone(cred.revoked_at)


class ServiceCredentialAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="svc-owner@atlas.test", password="senha-forte-123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _create(self, **overrides):
        payload = {"name": "Jarvis", "scopes": ["cognitive"]}
        payload.update(overrides)
        resp = self.client.post(_list_url(), payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp

    def test_create_returns_key_once_and_not_in_listing(self):
        key = self._create().data["key"]
        self.assertTrue(key.startswith("svc_"))
        # O GET da lista NÃO devolve a chave original.
        listing = self.client.get(_list_url()).data
        self.assertNotIn("key", listing["results"][0])

    def test_requires_authentication(self):
        anon = APIClient()
        resp = anon.get(_list_url())
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rotate_returns_new_key(self):
        created = self._create()
        cred_id = created.data["id"]
        old_hint = created.data["key_hint"]
        resp = self.client.post(_rotate_url(cred_id), format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["key"].startswith("svc_"))
        # hint mudou porque a chave mudou.
        self.assertNotEqual(resp.data["key_hint"], old_hint)

    def test_revoke_deactivates(self):
        created = self._create()
        cred_id = created.data["id"]
        resp = self.client.post(_revoke_url(cred_id), format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cred = ServiceCredential.objects.get(pk=cred_id)
        self.assertFalse(cred.is_active)

    def test_anti_idor_other_user_cannot_touch(self):
        other = User.objects.create_user(
            email="outro@atlas.test", password="senha-forte-123"
        )
        key = ServiceCredential.generate_key()
        cred = ServiceCredential.objects.create(
            user=other,
            name="Outro",
            key_hash=ServiceCredential._hash(key),
        )
        # rotate/revoke de credencial de OUTRO usuário → 404
        self.assertEqual(
            self.client.post(_rotate_url(cred.pk), format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(_revoke_url(cred.pk), format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )


class ServiceKeyAuthTests(TestCase):
    def setUp(self):
        self.service_user = User.objects.create_user(
            email="svc@atlas.test", password="senha-forte-123"
        )
        self.service_user.type = UserType.SERVICE
        self.service_user.save(update_fields=["type"])
        self.raw_key = ServiceCredential.generate_key()
        self.cred = ServiceCredential.objects.create(
            user=self.service_user,
            name="Jarvis",
            scopes=["cognitive"],
            key_hash=ServiceCredential._hash(self.raw_key),
            key_hint=ServiceCredential._hint(self.raw_key),
        )

    def test_valid_api_key_authenticates(self):
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=self.raw_key)
        resp = client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "svc@atlas.test")

    def test_invalid_api_key_rejected(self):
        client = APIClient()
        client.credentials(HTTP_X_API_KEY="svc_nao-existe")
        resp = client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revoked_key_rejected(self):
        self.cred.revoke()
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=self.raw_key)
        resp = client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rotated_old_key_rejected(self):
        self.cred.rotate(ServiceCredential.generate_key())
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=self.raw_key)
        resp = client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rotated_new_key_works(self):
        new_key = ServiceCredential.generate_key()
        self.cred.rotate(new_key)
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=new_key)
        resp = client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_missing_key_falls_back_to_jwt(self):
        # Sem X-API-Key e sem token → 401; via JWT funciona normalmente.
        self.assertEqual(
            APIClient().get(reverse("me")).status_code, status.HTTP_401_UNAUTHORIZED
        )
        client = APIClient()
        client.force_authenticate(user=self.service_user)
        self.assertEqual(client.get(reverse("me")).status_code, status.HTTP_200_OK)
