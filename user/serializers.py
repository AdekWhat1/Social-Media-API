from django.contrib.auth import get_user_model
from rest_framework import serializers


class UserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
    )

    class Meta:
        model = get_user_model()
        fields = ("id", "email", "username", "password")

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)


class UserListSerializer(serializers.ModelSerializer):

    followers_count = serializers.IntegerField(source="followers.count", read_only=True)
    following_count = serializers.IntegerField(source="following.count", read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "email",
            "username",
            "photo_profile",
            "followers_count",
            "following_count",
        )


class UserDetailSerializer(serializers.ModelSerializer):

    followers_count = serializers.IntegerField(source="followers.count", read_only=True)
    following_count = serializers.IntegerField(source="following.count", read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "email",
            "username",
            "photo_profile",
            "bio",
            "birthday",
            "followers_count",
            "following_count",
        )
        read_only_fields = ("id", "email")
