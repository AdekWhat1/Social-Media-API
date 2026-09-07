from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from user.permissions import IsUserOrReadOnly
from user.serializers import (
    UserCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)

User = get_user_model()


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"


class UserViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
    viewsets.mixins.UpdateModelMixin,
):
    queryset = User.objects.all().prefetch_related("followers", "following")
    filter_backends = [SearchFilter]
    search_fields = ["username", "email"]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        return UserDetailSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return [IsUserOrReadOnly()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["GET", "PATCH"], url_path="me")
    def me(self, request):
        """Ендпоінт для перегляду та редагування власного профілю."""
        user = request.user
        if request.method == "PATCH":
            serializer = UserDetailSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = UserDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"], url_path="follow")
    def follow(self, request, pk=None):
        """Підписатися на користувача."""
        target_user = self.get_object()
        if target_user == request.user:
            return Response(
                {"detail": "You cannot follow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.user.following.filter(id=target_user.id).exists():
            return Response(
                {"detail": "You are already following this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.following.add(target_user)
        return Response(
            {
                "detail": f"Successfully followed {target_user.username or target_user.email}."
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["POST"], url_path="unfollow")
    def unfollow(self, request, pk=None):
        """Відписатися від користувача."""
        target_user = self.get_object()
        if target_user == request.user:
            return Response(
                {"detail": "You cannot unfollow yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.following.filter(id=target_user.id).exists():
            return Response(
                {"detail": "You are not following this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.following.remove(target_user)
        return Response(
            {
                "detail": f"Successfully unfollowed {target_user.username or target_user.email}."
            },
            status=status.HTTP_200_OK,
        )
