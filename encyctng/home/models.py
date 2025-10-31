from django.db import models

from wagtail.images.models import Image
from wagtail.models import Page
from wagtail.models.media import Collection

from encyclopedia.topics import topics_items


class HomePage(Page):
    template = "patterns/pages/home_page/home_page.html"

    def hero(self):
        return {
            'title': 'Discover the history of the Japanese American incarceration during WWII',
            'actions': [
                {'text': 'Browse by Topic', 'url': '/articles-topic/'},
                {'text': 'Browse by A-Z', 'url': '/articles-az/'},
            ],
            'image': latest_homepage_image(),
        }

    def topics(self):
        return {
            'title': 'Browse Topics',
            'items': topics_items(),
        }


def latest_homepage_image():
    c = Collection.objects.get(name='Home page')
    try:
        return Image.objects.filter(collection=c)[0]
    except:
        return None


class HomePageCarouselIndexPage(Page):
    content_panels = Page.content_panels + []
