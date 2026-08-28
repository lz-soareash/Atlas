from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.audit.models import AuditLog
from .models import User


@receiver(post_save, sender=User)
def audit_user_event(sender, instance, created, **kwargs):
    """Registra criação/atualização de usuários na auditoria."""
    if instance.pk is None:
        return
    AuditLog.log(
        user=instance,
        action="USER_CREATED" if created else "USER_UPDATED",
        entity_type="accounts.User",
        entity_id=str(instance.pk),
        summary=f"Usuário {instance.email} {'criado' if created else 'atualizado'}.",
    )
