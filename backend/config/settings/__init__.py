"""
Seletor de configurações do Django.

Escolhe o módulo de settings com base na variável de ambiente DJANGO_ENV:
  - development (padrão) -> settings_local
  - production           -> settings_production
"""

import os

ENV = os.environ.get("DJANGO_ENV", "development").strip().lower()

if ENV == "production":
    from .settings_production import *  # noqa: F401,F403,E402
else:
    from .settings_local import *  # noqa: F401,F403,E402
