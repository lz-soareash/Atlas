"""Usuário do Atlas.

Autenticação por e-mail + senha (sem username), com UUID como PK.

A partir da Fase 10, contas podem ser de tipo `human` (pessoa, com login por
senha) ou `service` (cliente de integração, ex.: Jarvis — sem senha de interação
humana; autentica via ServiceCredential / API key).
"""

import hashlib
import hmac
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager que autentica por e-mail."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser precisa de is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser precisa de is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class UserType(models.TextChoices):
    HUMAN = "human", "Humano"
    SERVICE = "service", "Serviço"


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.HUMAN,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["email"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self):
        return self.first_name or self.email


class ServiceCredential(models.Model):
    """Credencial de API para integração serviço→serviço (ex.: Jarvis).

    A chave em texto puro é exibida apenas UMA vez, na criação/rotação, e é
    armazenada apenas como HASH. Suporta escopo, rotação e revogação.
    NUNCA retornar a chave original depois de criada. NUNCA logar secrets.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_credentials",
    )
    # Conta de serviço associada (owner) — human opcional para impressubility.
    name = models.CharField(max_length=120)
    scopes = models.JSONField(default=list, blank=True, help_text="Escopos ('cognitive', 'events', ...).")
    key_hash = models.CharField(max_length=128, editable=False)
    # Últimos 8 caracteres da chave, para identificação sem expor o valor completo.
    key_hint = models.CharField(max_length=16, blank=True)
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Credencial de serviço"
        verbose_name_plural = "Credenciais de serviço"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["key_hash"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.key_hint})"

    def rotate(self, new_key: str) -> "ServiceCredential":
        """Rotaciona a chave: atualiza o hash preservando a vida da credencial."""
        self.key_hash = self._hash(new_key)
        self.key_hint = self._hint(new_key)
        self.save(update_fields=["key_hash", "key_hint", "updated_at"])
        return self

    def revoke(self) -> None:
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=["is_active", "revoked_at", "updated_at"])

    def check_key(self, raw_key: str) -> bool:
        """Compara a chave fornecida com o hash armazenado (tempo constante)."""
        if not self.key_hash:
            return False
        expected = self._hash(raw_key)
        return hmac.compare_digest(expected, self.key_hash)

    @staticmethod
    def _hash(raw_key: str) -> str:
        # HMAC SHA-256 com SECRET_KEY como pepper — nunca armazena a chave pura.
        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            raw_key.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _hint(raw_key: str) -> str:
        return f"…{raw_key[-8:]}" if raw_key else ""

    @classmethod
    def generate_key(cls) -> str:
        """Gera uma nova chave aleatória forte na forma svc_<token>."""
        import secrets as _secrets

        return f"svc_{_secrets.token_urlsafe(43)}"
