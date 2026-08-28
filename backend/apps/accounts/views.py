from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditLog
from .models import User
from .serializers import RegisterSerializer, UserSerializer
from .throttles import LoginThrottle


class RegisterView(generics.CreateAPIView):
    """Cria um novo usuário e retorna os tokens JWT (login automático)."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        AuditLog.log(
            user=user,
            action="AUTH_REGISTER",
            entity_type="accounts.User",
            entity_id=str(user.pk),
            summary=f"Registro de conta para {user.email}.",
        )
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """Perfil do usuário autenticado."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
