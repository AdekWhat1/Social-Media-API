import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from post.models import Comment, Hashtag, Like, Post

User = get_user_model()


class Command(BaseCommand):
    help = "Populates the database with realistic fake data for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=10,
            help="Number of users to create (default: 10)",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=25,
            help="Number of posts to create (default: 25)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        fake = Faker()
        num_users = options["users"]
        num_posts = options["posts"]

        self.stdout.write(self.style.NOTICE("Starting database population..."))

        users = []
        for _ in range(num_users):
            email = fake.unique.email()
            user = User.objects.create_user(
                email=email,
                password="testpassword123",
                bio=fake.paragraph(nb_sentences=2),
                birthday=fake.date_of_birth(minimum_age=16, maximum_age=65),
            )

            if hasattr(user, "username"):
                user.username = fake.unique.user_name()
                user.save()
            users.append(user)

        self.stdout.write(self.style.SUCCESS(f"Created {len(users)} users."))

        for user in users:
            possible_targets = [u for u in users if u != user]
            sample_size = min(len(possible_targets), random.randint(1, 5))
            targets = random.sample(possible_targets, sample_size)
            user.following.set(targets)

        self.stdout.write(self.style.SUCCESS("Generated user follow relationships."))

        hashtag_words = [
            "django",
            "python",
            "backend",
            "webdev",
            "api",
            "rest",
            "tech",
            "coding",
            "software",
            "opensource",
        ]
        hashtags = []
        for word in hashtag_words:
            tag, _ = Hashtag.objects.get_or_create(name=word)
            hashtags.append(tag)

        self.stdout.write(self.style.SUCCESS(f"Created {len(hashtags)} hashtags."))

        posts = []
        for _ in range(num_posts):
            author = random.choice(users)
            post = Post.objects.create(
                author=author,
                text=fake.text(max_nb_chars=300),
                is_published=True,
            )
            post.hashtags.set(random.sample(hashtags, random.randint(1, 3)))
            posts.append(post)

        self.stdout.write(self.style.SUCCESS(f"Created {len(posts)} posts."))

        likes_count = 0
        comments_count = 0

        for post in posts:
            for _ in range(random.randint(0, 4)):
                Comment.objects.create(
                    post=post,
                    author=random.choice(users),
                    text=fake.sentence(),
                )
                comments_count += 1

            likers = random.sample(users, random.randint(0, min(len(users), 6)))
            for liker in likers:
                Like.objects.get_or_create(author=liker, post=post)
                likes_count += 1

        self.stdout.write(self.style.SUCCESS(f"Created {comments_count} comments."))
        self.stdout.write(self.style.SUCCESS(f"Created {likes_count} likes."))

        self.stdout.write(
            self.style.SUCCESS(
                "\nDatabase successfully populated! All test users have password: 'testpassword123'"
            )
        )
