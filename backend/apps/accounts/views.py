from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import TokenError

from apps.audit.models import AuditLog
from .models import User
from .serializers import RegisterSerializer, UserSerializer
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
