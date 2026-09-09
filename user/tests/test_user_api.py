from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

REGISTER_URL = reverse("user:register")
TOKEN_URL = reverse("user:token_obtain_pair")
ME_URL = reverse("user:user-me")
LOGOUT_URL = reverse("user:logout")


class PublicUserApiTests(APITestCase):
    def test_create_user_success(self):
        payload = {
            "email": "test@example.com",
            "password": "strong_password123",
            "username": "testuser",
        }
        response = self.client.post(REGISTER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", response.data)

    def test_obtain_jwt_token(self):
        User.objects.create_user(
            email="token_test@example.com",
            password="testpassword123",
        )
        payload = {
            "email": "token_test@example.com",
            "password": "testpassword123",
        }
        response = self.client.post(TOKEN_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_auth_required_for_me_endpoint(self):
        response = self.client.get(ME_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="me@example.com",
            password="password123",
            username="main_user",
            bio="Initial bio",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
            username="other_user",
        )
        self.client.force_authenticate(user=self.user)

    def test_user_logout_blacklists_token(self):
        token_res = self.client.post(
            TOKEN_URL,
            {"email": "me@example.com", "password": "password123"},
        )
        refresh_token = token_res.data["refresh"]

        response = self.client.post(LOGOUT_URL, {"refresh": refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        refresh_res = self.client.post(
            reverse("user:token_refresh"),
            {"refresh": refresh_token},
        )
        self.assertEqual(refresh_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_current_user_profile(self):
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["username"], self.user.username)

    def test_update_current_user_profile(self):
        payload = {"bio": "Updated bio text"}
        response = self.client.patch(ME_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, payload["bio"])

    def test_follow_user_success(self):
        url = reverse("user:user-follow", args=[self.other_user.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.following.filter(id=self.other_user.id).exists())

    def test_follow_self_fails(self):
        url = reverse("user:user-follow", args=[self.user.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(self.user.following.filter(id=self.user.id).exists())

    def test_duplicate_follow_fails(self):
        self.user.following.add(self.other_user)
        url = reverse("user:user-follow", args=[self.other_user.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unfollow_user_success(self):
        self.user.following.add(self.other_user)
        url = reverse("user:user-unfollow", args=[self.other_user.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.user.following.filter(id=self.other_user.id).exists())

    def test_followers_list_endpoint(self):
        self.other_user.following.add(self.user)
        url = reverse("user:user-followers", args=[self.user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.other_user.id)

    def test_following_list_endpoint(self):
        self.user.following.add(self.other_user)
        url = reverse("user:user-following", args=[self.user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.other_user.id)
