"""Views base reutilizadas pelas entidades do Knowledge Core."""

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsOwner


class OwnerModelViewSet(viewsets.ModelViewSet):
    """ViewSet com isolamento por owner e suporte a soft delete.

    - `get_queryset`: retorna apenas registros não removidos do usuário.
    - `perform_create`: define `owner = request.user` automaticamente.
    - `destroy`: faz soft delete (marca `deleted_at`) em vez de apagar.
    - Permissão por objeto: `IsOwner` (anti-IDOR).
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.for_owner(self.request.user).active()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
