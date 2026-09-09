from rest_framework import serializers

from post.models import Comment, Hashtag, Like, Post, PostImage


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hashtag
        fields = ("id", "name")


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ("id", "image")


class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "author_username", "text", "date_created")
        read_only_fields = ("id", "author_username", "date_created")


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "post", "text", "date_created")
        read_only_fields = ("id", "date_created")


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ("id", "author", "post", "created_at")
        read_only_fields = ("id", "author", "created_at")


class PostListSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    hashtags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    images = PostImageSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    comments_count = serializers.IntegerField(source="comments.count", read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "author_username",
            "text",
            "hashtags",
            "images",
            "likes_count",
            "comments_count",
            "date_created",
        )


class PostDetailSerializer(PostListSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ("comments",)


class PostCreateSerializer(serializers.ModelSerializer):
    hashtags = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        queryset=Hashtag.objects.all(),
        required=False,
    )

    class Meta:
        model = Post
        fields = ("id", "text", "hashtags", "scheduled_time")

    def create(self, validated_data):
        # Якщо вказано scheduled_time в майбутньому — приховуємо пост до публікації
        scheduled_time = validated_data.get("scheduled_time")
        if scheduled_time:
            validated_data["is_published"] = False
        return super().create(validated_data)
