"""
Configurações base do Atlas (backend).

As configurações são divididas em:
  - settings_base.py     : compartilhadas por todos os ambientes
  - settings_local.py    : DJANGO_ENV=development  (SQLite + DEBUG)
  - settings_production.py: DJANGO_ENV=production   (PostgreSQL + pgvector)

O seletor é feito em config/settings/__init__.py a partir da variável
de ambiente DJANGO_ENV.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Carrega variáveis de ambiente a partir do .env (na raiz backend) se existir.
load_dotenv(BASE_DIR / ".env")


def env_str(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=None):
    val = os.environ.get(name)
    if not val:
        return default or []
    return [item.strip() for item in val.split(",") if item.strip()]


SECRET_KEY = env_str("SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", env_bool("DEBUG", False))
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["127.0.0.1", "localhost"])

# --- Aplicações ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.audit",
    "apps.core",
    # Fase 2 — Knowledge Core
    "apps.knowledge",
    "apps.ideas",
    "apps.projects",
    "apps.questions",
    "apps.decisions",
    "apps.experiences",
    # Dashboard / visão agregada
    "apps.dashboard",
    # Fase 3 — Relacionamentos + Grafo
    "apps.relationships",
]

# Entidades aptas a participar de relacionamentos (app_label, model_name).
# Extensível: basta adicionar pares aqui para habilitar novas entidades.
RELATIONSHIP_MODELS = [
    ("knowledge", "knowledge"),
    ("ideas", "idea"),
    ("projects", "project"),
    ("questions", "question"),
    ("decisions", "decision"),
    ("experiences", "experience"),
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

# Frontend separado do backend em <repo>/frontend (servido pelo Django).
FRONTEND_DIR = BASE_DIR.parent / "frontend"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [FRONTEND_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Banco de dados ---
# DB_ENGINE=sqlite (padrão local) | DB_ENGINE=postgres (produção, pgvector)
DB_ENGINE = env_str("DB_ENGINE", "sqlite").lower()

if DB_ENGINE == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env_str("DB_NAME", "atlas"),
            "USER": env_str("DB_USER", "atlas"),
            "PASSWORD": env_str("DB_PASSWORD", "atlas"),
            "HOST": env_str("DB_HOST", "127.0.0.1"),
            "PORT": env_str("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

# --- Autenticação (JWT) ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env_str("ACCESS_TOKEN_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env_str("REFRESH_TOKEN_DAYS", "1"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env_str("THROTTLE_ANON", "20/min"),
        "user": env_str("THROTTLE_USER", "100/min"),
    },
}

# --- CORS ---
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://127.0.0.1:8000", "http://localhost:8000"],
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    ["http://127.0.0.1:8000", "http://localhost:8000"],
)

# --- Segurança (ajustado por ambiente) ---
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)

# --- Internacionalização ---
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# --- Estáticos / mídia ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Diretório de estáticos da aplicação Atlas (CSS/JS servidos sem build step),
# agora em <repo>/frontend/static.
STATICFILES_DIRS = [FRONTEND_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": env_str("LOG_LEVEL", "INFO"),
    },
}
