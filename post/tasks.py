from celery import shared_task
from django.utils import timezone

from post.models import Post


@shared_task
def publish_scheduled_posts():
    now = timezone.now()
    posts_to_publish = Post.objects.filter(
        is_published=False,
        scheduled_time__lte=now,
    )
    updated_count = posts_to_publish.update(is_published=True)
    return f"Successfully published {updated_count} scheduled posts."
