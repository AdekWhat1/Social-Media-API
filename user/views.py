from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
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

    @extend_schema(
        summary="List user followers",
        description="Retrieve a paginated list of users following the specified user.",
        responses={200: UserListSerializer(many=True)},
    )
    @action(detail=True, methods=["GET"], url_path="followers")
    def followers(self, request, pk=None):
        user = self.get_object()
        followers = user.followers.all()
        page = self.paginate_queryset(followers)
        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = UserListSerializer(followers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="List user following",
        description="Retrieve a paginated list of users that the specified user is following.",
        responses={200: UserListSerializer(many=True)},
    )
    @action(detail=True, methods=["GET"], url_path="following")
    def following(self, request, pk=None):
        user = self.get_object()
        following = user.following.all()
        page = self.paginate_queryset(following)
        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = UserListSerializer(following, many=True)
        return Response(serializer.data)
