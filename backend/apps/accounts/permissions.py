"""Permissões customizadas do Atlas.

A base de todas as entidades do Knowledge Core é isolada por 'owner'.
Estas permissões garantem que um usuário autenticado nunca acesse ou
modifique objetos de terceiros (proteção contra IDOR).
"""

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsOwner(BasePermission):
    """Permite acesso apenas ao proprietário do objeto.

    Requer que o objeto possua um atributo 'owner' (apontando para o usuário)
    ou uma FK 'user'/'owning_user' comparável.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return obj.owner_id == request.user.id
