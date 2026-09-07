from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from post.models import Comment, Hashtag, Like, Post
from post.permissions import IsAuthorOrReadOnly
from post.serializers import (
    CommentCreateSerializer,
    CommentSerializer,
    HashtagSerializer,
    PostCreateSerializer,
    PostDetailSerializer,
    PostImageSerializer,
    PostListSerializer,
)


class HashtagViewSet(viewsets.ModelViewSet):
    queryset = Hashtag.objects.all()
    serializer_class = HashtagSerializer
    permission_classes = [IsAuthenticated]


class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["text", "hashtags__name"]

    def get_queryset(self):
        queryset = (
            Post.objects.filter(is_published=True)
            .select_related("author")
            .prefetch_related("hashtags", "images", "likes", "comments__author")
        )

        # Фільтрація за авторами або хештегом через query params
        author_id = self.request.query_params.get("author")
        hashtag = self.request.query_params.get("hashtag")

        if author_id:
            queryset = queryset.filter(author_id=author_id)
        if hashtag:
            queryset = queryset.filter(hashtags__name__iexact=hashtag)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return PostCreateSerializer
        if self.action == "upload_image":
            return PostImageSerializer
        return PostListSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthorOrReadOnly()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=False, methods=["GET"], url_path="feed")
    def feed(self, request):
        """Стрічка постів тільки тих користувачів, на яких підписаний юзер."""
        following_users = request.user.following.all()
        posts = self.get_queryset().filter(author__in=following_users)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["POST"], url_path="like")
    def like(self, request, pk=None):
        """Поставити лайк посту."""
        post = self.get_object()
        like, created = Like.objects.get_or_create(author=request.user, post=post)
        if not created:
            return Response(
                {"detail": "You already liked this post."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"detail": "Post liked successfully."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["POST"], url_path="unlike")
    def unlike(self, request, pk=None):
        """Прибрати лайк з поста."""
        post = self.get_object()
        like = Like.objects.filter(author=request.user, post=post).first()
        if not like:
            return Response(
                {"detail": "You have not liked this post."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        like.delete()
        return Response(
            {"detail": "Post unliked successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["POST"], url_path="upload-image")
    def upload_image(self, request, pk=None):
        """Завантаження зображення до конкретного поста."""
        post = self.get_object()
        if post.author != request.user and not request.user.is_staff:
            return Response(
                {"detail": "You cannot upload images to someone else's post."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = PostImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(post=post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CommentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Comment.objects.select_related("author", "post")
        post_id = self.request.query_params.get("post")
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        return queryset

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CommentCreateSerializer
        return CommentSerializer

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [IsAuthorOrReadOnly()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
