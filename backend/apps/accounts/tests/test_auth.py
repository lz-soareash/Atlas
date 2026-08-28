"""Testes de autenticação e segurança da FASE 1 (accounts)."""

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog


class AuthTestMixin:
    def make_client(self, **kwargs):
        return APIClient(**kwargs)


class RegisterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("register")

    def test_register_creates_user_and_returns_tokens(self):
        resp = self.client.post(
            self.url,
            {
                "email": "novo@atlas.test",
                "first_name": "Novo",
                "password": "senha-forte-123",
                "password_confirmation": "senha-forte-123",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        user = User.objects.get(email="novo@atlas.test")
        self.assertEqual(user.first_name, "Novo")
        self.assertTrue(user.check_password("senha-forte-123"))
        # Auditoria registrada
        self.assertTrue(
            AuditLog.objects.filter(user=user, action="AUTH_REGISTER").exists()
        )

    def test_register_rejects_mismatched_passwords(self):
        resp = self.client.post(
            self.url,
            {
                "email": "erro@atlas.test",
                "password": "senha-forte-123",
                "password_confirmation": "diferente-456",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="erro@atlas.test").exists())

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(email="dup@atlas.test", password="senha-forte-123")
        resp = self.client.post(
            self.url,
            {
                "email": "dup@atlas.test",
                "password": "senha-forte-123",
                "password_confirmation": "senha-forte-123",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_short_password(self):
        resp = self.client.post(
            self.url,
            {
                "email": "curta@atlas.test",
                "password": "abc",
                "password_confirmation": "abc",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="login@atlas.test", password="senha-forte-123"
        )

    def test_login_returns_tokens(self):
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "login@atlas.test", "password": "senha-forte-123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_refresh_token(self):
        token = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "login@atlas.test", "password": "senha-forte-123"},
            format="json",
        ).data["refresh"]
        resp = self.client.post(reverse("token_refresh"), {"refresh": token}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

    def test_login_rejects_wrong_password(self):
        resp = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "login@atlas.test", "password": "senha-errada"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class MeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="me@atlas.test", password="senha-forte-123"
        )

    def test_me_requires_authentication(self):
        resp = APIClient().get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_profile(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], "me@atlas.test")
        # Não expõe campos sensíveis
        self.assertNotIn("password", resp.data)
        self.assertNotIn("is_superuser", resp.data)
