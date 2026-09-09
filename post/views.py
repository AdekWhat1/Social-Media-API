from django.utils import timezone
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)
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


@extend_schema_view(
    list=extend_schema(
        summary="List published posts",
        description="Retrieve a paginated list of all published posts. Supports filtering by author, hashtag, or keyword search.",
        parameters=[
            OpenApiParameter(
                name="author",
                description="Filter posts by author ID",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="hashtag",
                description="Filter posts by hashtag name (case-insensitive, omit the '#' symbol)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="search",
                description="Search across post text and hashtags",
                required=False,
                type=str,
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve post details",
        description="Retrieve complete details for a specific post, including its comments and media attachments.",
        responses={200: PostDetailSerializer},
    ),
    create=extend_schema(
        summary="Create a new post",
        description="Create a post authored by the currently authenticated user. An optional scheduled_time can be supplied for deferred publishing.",
        responses={201: PostDetailSerializer},
    ),
    update=extend_schema(
        summary="Update a post",
        description="Completely update an existing post. Restricted to the post's author.",
    ),
    partial_update=extend_schema(
        summary="Partially update a post",
        description="Partially update an existing post. Restricted to the post's author.",
    ),
    destroy=extend_schema(
        summary="Delete a post",
        description="Delete a post. Restricted to the post's author or staff administrators.",
    ),
)
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
        scheduled_time = serializer.validated_data.get("scheduled_time")
        if scheduled_time and scheduled_time > timezone.now():
            serializer.save(author=self.request.user, is_published=False)
        else:
            serializer.save(author=self.request.user, is_published=True)

    @extend_schema(
        summary="Retrieve following feed",
        description="Retrieve a paginated list of posts authored exclusively by users the current account follows.",
        responses={200: PostListSerializer(many=True)},
    )
    @action(detail=False, methods=["GET"], url_path="feed")
    def feed(self, request):
        following_users = request.user.following.all()
        posts = self.get_queryset().filter(author__in=following_users)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Like a post",
        description="Add a like to a post on behalf of the authenticated user.",
        request=None,
        responses={
            201: OpenApiResponse(
                description="Post liked successfully",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"detail": "Post liked successfully."},
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Conflict - post already liked",
                examples=[
                    OpenApiExample(
                        "Duplicate",
                        value={"detail": "You already liked this post."},
                    )
                ],
            ),
        },
    )
    @action(detail=True, methods=["POST"], url_path="like")
    def like(self, request, pk=None):
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

    @extend_schema(
        summary="List liked posts",
        description="Retrieve a paginated list of posts liked by the authenticated user.",
        responses={200: PostListSerializer(many=True)},
    )
    @action(detail=False, methods=["GET"], url_path="liked")
    def liked(self, request):
        posts = self.get_queryset().filter(likes__author=request.user)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PostListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Unlike a post",
        description="Remove an existing like from a post.",
        request=None,
        responses={
            200: OpenApiResponse(
                description="Post unliked successfully",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={"detail": "Post unliked successfully."},
                    )
                ],
            ),
            400: OpenApiResponse(
                description="Bad Request - like does not exist",
                examples=[
                    OpenApiExample(
                        "Not found",
                        value={"detail": "You have not liked this post."},
                    )
                ],
            ),
        },
    )
    @action(detail=True, methods=["POST"], url_path="unlike")
    def unlike(self, request, pk=None):
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

    @extend_schema(
        summary="Upload an image to a post",
        description="Upload an image attachment using multipart/form-data and attach it to the post. Restricted to the post's author.",
        request=PostImageSerializer,
        responses={201: PostImageSerializer},
    )
    @action(detail=True, methods=["POST"], url_path="upload-image")
    def upload_image(self, request, pk=None):

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
