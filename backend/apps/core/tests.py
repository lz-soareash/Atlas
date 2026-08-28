"""Testes do modelo base (soft delete, timestamps) da FASE 1.

Valida o AtlasModel abstrato através de um modelo concreto de teste,
criando a tabela dinamicamente (padrão para testar modelos abstratos).
"""

from django.db import connection, models
from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.core.models import AtlasModel, OwnerMixin


class Entry(AtlasModel, OwnerMixin):
    """Modelo concreto apenas para os testes da FASE 1."""

    title = models.CharField(max_length=120)

    class Meta:
        app_label = "core"
        db_table = "test_core_entry"

    def __str__(self):
        return self.title


class SoftDeleteTests(TransactionTestCase):
    # Cria/remove a tabela de teste. TransactionTestCase não abre transação
    # ao redor do setUpClass, permitindo o schema_editor no SQLite.
    @staticmethod
    def _create_table():
        with connection.schema_editor() as editor:
            editor.execute("DROP TABLE IF EXISTS test_core_entry")
            editor.create_model(Entry)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._create_table()

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(Entry)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(email="soft@atlas.test", password="x")
        self.entry = Entry.objects.create(owner=self.user, title="Nota de teste")

    def test_soft_delete_sets_deleted_at(self):
        self.assertIsNone(self.entry.deleted_at)
        self.entry.soft_delete()
        self.assertTrue(self.entry.is_deleted)
        self.assertIsNotNone(self.entry.deleted_at)
        # Permanece no banco (não é apagado fisicamente)
        self.assertTrue(Entry.objects.filter(pk=self.entry.pk).exists())

    def test_restore_clears_deleted_at(self):
        self.entry.soft_delete()
        self.entry.restore()
        self.assertFalse(self.entry.is_deleted)
        self.assertIsNone(self.entry.deleted_at)

    def test_timestamps_automatic(self):
        self.assertIsNotNone(self.entry.created_at)
        self.assertIsNotNone(self.entry.updated_at)

    def test_owner_isolated_by_user(self):
        other = User.objects.create_user(email="other@atlas.test", password="x")
        self.assertEqual(Entry.objects.filter(owner=self.user).count(), 1)
        self.assertEqual(Entry.objects.filter(owner=other).count(), 0)

    def test_uuid_pk_not_predictable(self):
        self.assertNotEqual(str(self.entry.id), "1")
        self.assertGreater(len(str(self.entry.id)), 8)
