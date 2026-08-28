"""Configurações de desenvolvimento (DJANGO_ENV=development)."""

from .settings_base import *  # noqa: F401,F403
from .settings_base import BASE_DIR, DEBUG, env_bool, env_str

# Desenvolvimento usa SQLite por padrão (ver DB_ENGINE em settings_base).
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0"]

# SQLite não suporta concorrência; aumentar timeout evita erros em dev.
if "sqlite" in env_str("DB_ENGINE", "sqlite"):
    DATABASES["default"]["OPTIONS"] = {"timeout": 20}

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
