from django.db import models

from wagtail.models import Page

from encyclopedia.views import topics_items


class HomePage(Page):
    template = "patterns/pages/home_page/home_page.html"

    def hero(self):
        return {
            'title': 'Discover the history of the Japanese American incarceration during WWII',
            'actions': [
                {'text': 'Browse by Topic', 'url': '/articles-topic/'},
                {'text': 'Browse by A-Z', 'url': '/articles-az/'},
            ],
            'image': None,  # TODO supply a wagtail Image object
        }

    def topics(self):
        return {
            'title': 'Browse Topics',
            'items': topics_items(),
        }
