from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from post.models import Post

User = get_user_model()

POST_LIST_URL = reverse("post:post-list")
FEED_URL = reverse("post:post-feed")


def detail_url(post_id):
    return reverse("post:post-detail", args=[post_id])


def like_url(post_id):
    return reverse("post:post-like", args=[post_id])


class PublicPostApiTests(APITestCase):
    def test_login_required(self):
        response = self.client.get(POST_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivatePostApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="author@example.com",
            password="password123",
            username="author_user",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
            username="other_user",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_post_success(self):
        payload = {
            "text": "Test content description.",
        }
        response = self.client.post(POST_LIST_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.get(id=response.data["id"])
        self.assertEqual(post.text, payload["text"])
        self.assertEqual(post.author, self.user)

    def test_retrieve_post_list(self):
        Post.objects.create(author=self.user, text="Content 1")
        Post.objects.create(author=self.other_user, text="Content 2")

        response = self.client.get(POST_LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        self.assertGreaterEqual(len(results), 2)

    def test_update_own_post_success(self):
        post = Post.objects.create(author=self.user, text="Old Content")
        payload = {"text": "Updated Content"}

        response = self.client.patch(detail_url(post.id), payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.text, payload["text"])

    def test_update_other_user_post_forbidden(self):
        post = Post.objects.create(author=self.other_user, text="Other User Content")
        payload = {"text": "Malicious Update"}

        response = self.client.patch(detail_url(post.id), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        post.refresh_from_db()
        self.assertNotEqual(post.text, payload["text"])

    def test_delete_other_user_post_forbidden(self):
        post = Post.objects.create(author=self.other_user, text="Other User Content")

        response = self.client.delete(detail_url(post.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Post.objects.filter(id=post.id).exists())

    def test_like_and_unlike_post(self):
        post = Post.objects.create(author=self.other_user, text="Post for likes")

        like_res = self.client.post(like_url(post.id))
        self.assertIn(
            like_res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED]
        )

        like_model = post.likes.model
        if hasattr(like_model, "author"):
            is_liked = post.likes.filter(author=self.user).exists()
        elif hasattr(like_model, "user"):
            is_liked = post.likes.filter(user=self.user).exists()
        else:
            is_liked = post.likes.filter(id=self.user.id).exists()

        self.assertTrue(is_liked)

        toggle_res = self.client.post(like_url(post.id))
        self.assertIn(
            toggle_res.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        )

    def test_feed_shows_only_followed_users_posts(self):
        not_following_user = User.objects.create_user(
            email="stranger@example.com",
            password="password123",
            username="stranger",
        )
        post_stranger = Post.objects.create(
            author=not_following_user,
            text="Invisible content",
        )

        self.user.following.add(self.other_user)
        post_followed = Post.objects.create(
            author=self.other_user,
            text="Visible content",
        )

        response = self.client.get(FEED_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        post_ids = [p["id"] for p in results]

        self.assertIn(post_followed.id, post_ids)
        self.assertNotIn(post_stranger.id, post_ids)
