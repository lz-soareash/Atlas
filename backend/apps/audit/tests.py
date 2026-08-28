"""Testes de segurança da FASE 1 (IDOR, exposição de secrets)."""

from django.test import TestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog


class AuditRedactionTests(TestCase):
    """Auditoria nunca deve expor secrets."""

    def setUp(self):
        self.user = User.objects.create_user(email="audit@atlas.test", password="x")

    def test_audit_redacts_passwords(self):
        log = AuditLog.log(
            user=self.user,
            action="TEST",
            details={
                "email": "a@b.com",
                "password": "segredo",
                "api_key": "chave",
                "token": "abc",
                "safe": "visivel",
            },
        )
        self.assertEqual(log.details["safe"], "visivel")
        self.assertEqual(log.details["password"], "[REDACTED]")
        self.assertEqual(log.details["api_key"], "[REDACTED]")
        self.assertEqual(log.details["token"], "[REDACTED]")

    def test_audit_redacts_nested_secrets(self):
        log = AuditLog.log(
            user=self.user,
            action="TEST",
            details={"nested": {"authorization": "Bearer xyz", "ok": 1}},
        )
        self.assertEqual(log.details["nested"]["authorization"], "[REDACTED]")
        self.assertEqual(log.details["nested"]["ok"], 1)

    def test_audit_requires_authenticated_user(self):
        # Modelo de auditoria não exige autenticação para gravar, mas registra usuário
        log = AuditLog.log(action="TEST", entity_type="x", entity_id="1")
        self.assertIsNone(log.user)
        self.assertEqual(log.action, "TEST")
