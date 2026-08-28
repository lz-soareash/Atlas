"""Configurações de produção (DJANGO_ENV=production).

Exige PostgreSQL + pgvector (busca semântica). Secrets via variáveis de
ambiente do host (nunca versionadas).
"""

from .settings_base import *  # noqa: F401,F403
from .settings_base import DEBUG, env_bool, env_str

DEBUG = env_bool("DEBUG", False)

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Garante, por segurança, que produção rode sobre PostgreSQL.
assert env_str("DB_ENGINE", "sqlite") == "postgres", (
    "ATLAS PRODUCTION: DB_ENGINE deve ser 'postgres'."
)
