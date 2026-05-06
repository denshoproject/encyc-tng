from datetime import datetime

from django.db import models
from django.utils import timezone

from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.images.models import Image
from wagtail.models import Page
from wagtail.models.media import Collection
from wagtail.search import index

from encyclopedia.topics import topics_items
from .blocks import HomepageCarouselImageBlock


class HomePage(Page):
    template = "patterns/pages/home_page/home_page.html"

    def hero(self):
        context = {
            'title': 'Discover the history of the Japanese American incarceration during WWII',
            'actions': [
                {'text': 'Browse by Topic', 'url': '/articles-topic/'},
                {'text': 'Browse by A-Z', 'url': '/articles-az/'},
            ],
            'image': latest_homepage_image(),
            'carousel': {},
        }
        carousel = HomePageCarousel()
        if carousel:
            context['carousel'] = {
                'publish_date': carousel.publish_date,
                'title': carousel.title,
                'description': carousel.description,
                'items': [
                    {
                        'image': block.value['image'],
                        'url': block.value['article_url'],
                        'title': block.value['article_title'],
                        'description': block.value['description'],
                    }
                    for block in carousel.images
                ],
            }
        return context

    def topics(self):
        return {
            'title': 'Browse Topics',
            'items': topics_items(),
        }


def latest_homepage_image():
    # TODO cache
    try:
        carousel = HomePageCarousel.objects.live().order_by('-publish_date')
        carousel = carousel.filter(
            publish_date__lte=timezone.localtime(timezone.now())
        )[0]
        images = [image.value['image'] for image in carousel.images]
        return images[0]
    except IndexError:
        return None


class HomePageCarouselIndexPage(Page):
    content_panels = Page.content_panels + []
    subpage_types = ['home.HomePageCarousel']


class HomePageCarousel(Page):
    publish_date = models.DateTimeField()
    description = RichTextField(blank=True)
    images = StreamField([
            ('imageblock', HomepageCarouselImageBlock()),
        ],
        blank=True,
        use_json_field=True,
        help_text='Add one or more Image objects.',
    )

    search_fields = Page.search_fields + [
        index.SearchField('description'),
        index.SearchField('images'),
    ]
    content_panels = Page.content_panels + [
        FieldPanel('publish_date'),
        FieldPanel('description'),
        FieldPanel('images'),
    ]
    promote_panels = []
    settings_panels = []

    parent_page_types = ['home.HomePageCarouselIndexPage']
    subpage_types = []
    template = 'patterns/pages/article/article.html'

    class Meta:
        ordering = ['title']
        verbose_name = "Home Page Carousel"
        verbose_name_plural = "Home Page Carousels"

    @staticmethod
    def latest():
        try:
            carousel = HomePageCarousel.objects.live().order_by('-publish_date')
            carousel = carousel.filter(
                publish_date__lte=timezone.localtime(timezone.now())
            )[0]
            return carousel
        except IndexError:
            return None
