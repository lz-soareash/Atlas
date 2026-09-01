"""App cognitive — Fase 10.

Cognitive Engine + Integração Jarvis. Sessões persistentes, respostas
estruturadas e eventos de integração com whitelist extensível.
"""

from django.apps import AppConfig


class CognitiveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cognitive"
    verbose_name = "Cognitive Engine & Integração"
