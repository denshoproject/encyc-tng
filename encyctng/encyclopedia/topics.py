import json
from pathlib import Path

from django.conf import settings
from django.urls import reverse

from wagtail.images.models import Image
from wagtail.models.media import Collection


def topics_items():
    c = Collection.objects.get(name='Topics')
    images = {
        image.title: image
        for image in Image.objects.filter(collection=c)
    }
    # TODO cache this
    # TODO store in database instead?
    path = Path(settings.ENCYC_TOPICS_PATH)
    if not path.exists():
        raise Exception(f"Cannot read topics data file {path}.")
    with path.open('r') as f:
        topics = json.loads(f.read())
    for topic in topics:
        topic_id = topic['id']
        if images.get(topic['title']):
            topic['image'] = images.pop(topic['title'])
        topic['url'] = reverse('encyc-articles-topic',args=[topic_id])
        topic['articles'] = 123
    return topics
