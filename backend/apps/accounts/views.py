from rest_framework import generics, mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import TokenError

from apps.audit.models import AuditLog
from .models import ServiceCredential, User
from .serializers import RegisterSerializer, ServiceCredentialSerializer, UserSerializer
from .throttles import LoginThrottle


class LoginView(TokenObtainPairView):
    """POST /api/auth/token/ — login, agora com throttle anti força bruta.

    Retorna os mesmos tokens JWT do SimpleJWT (access + refresh rotativo).
    """

    throttle_classes = [LoginThrottle]


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutView(APIView):
    """POST /api/auth/logout/ — revoga o refresh token (blacklist).

    Requer o refresh token no corpo. O access token atual expira
    naturalmente em ACCESS_TOKEN_MINUTES (padrão 60min).
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except (TokenError, serializers.ValidationError):
            return Response(
                {"detail": "Refresh token inválido ou já revogado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class ServiceCredentialViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Gestão de credenciais de serviço (integração serviço→serviço, Fase 10).

    - GET  /api/accounts/service-credentials/       (lista)
    - POST /api/accounts/service-credentials/        (cria; retorna a chave UMA vez)
    - POST /api/accounts/service-credentials/:id/rotate/  (nova chave UMA vez)
    - POST /api/accounts/service-credentials/:id/revoke/  (revoga)

    A chave em texto puro é exibida apenas na criação/rotação. Nunca é
    armazenada em claro e nunca é retornada de novo pelo GET.
    """

    serializer_class = ServiceCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ServiceCredential.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = ServiceCredential.generate_key()
        credential = serializer.save(
            user=request.user,
            key_hash=ServiceCredential._hash(key),
            key_hint=ServiceCredential._hint(key),
        )
        AuditLog.log(
            user=request.user,
            action="SERVICE_CREDENTIAL_CREATE",
            entity_type="accounts.ServiceCredential",
            entity_id=str(credential.pk),
            summary=f"Criação de credencial de serviço '{credential.name}'.",
        )
        data = serializer.data.copy()
        data["key"] = key  # única oportunidade de ver a chave original
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="rotate")
    def rotate(self, request, pk=None):
        credential = self.get_object()
        new_key = ServiceCredential.generate_key()
        credential.rotate(new_key)
        AuditLog.log(
            user=request.user,
            action="SERVICE_CREDENTIAL_ROTATE",
            entity_type="accounts.ServiceCredential",
            entity_id=str(credential.pk),
            summary=f"Rotação de credencial de serviço '{credential.name}'.",
        )
        data = ServiceCredentialSerializer(credential).data
        data["key"] = new_key  # única oportunidade de ver a nova chave
        return Response(data)

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk=None):
        credential = self.get_object()
        if credential.is_active:
            credential.revoke()
            AuditLog.log(
                user=request.user,
                action="SERVICE_CREDENTIAL_REVOKE",
                entity_type="accounts.ServiceCredential",
                entity_id=str(credential.pk),
                summary=f"Revogação de credencial de serviço '{credential.name}'.",
            )
        return Response(ServiceCredentialSerializer(credential).data)
