from django.urls import include, path
from rest_framework.routers import DefaultRouter

from post.views import CommentViewSet, HashtagViewSet, PostViewSet

router = DefaultRouter()
router.register("hashtags", HashtagViewSet, basename="hashtag")
router.register("posts", PostViewSet, basename="post")
router.register("comments", CommentViewSet, basename="comment")

app_name = "post"

urlpatterns = [
    path("", include(router.urls)),
]
