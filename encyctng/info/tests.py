from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from .models import SitePagesIndexPage, SitePage


class SiteViews(TestCase):
    @classmethod
    def setUp(cls):
        root = Page.get_first_root_node()
        Site.objects.create(
            hostname='testserver',
            site_name='testserver',
            root_page=root,
            is_default_site=True,
        )
        index_page = SitePagesIndexPage(title='Site Pages')
        root.add_child(instance=index_page)

        page = SitePage(
            title='About the Encyclopedia',
            description='Nothing here yet.',
            body='Not a real article.',
        )
        index_page.add_child(instance=page)
        page = SitePage(
            title='About the Incarceration',
            description='Nothing here yet.',
            body='Not a real article.',
        )
        index_page.add_child(instance=page)
        page = SitePage(
            title='Do Words Matter?',
            description='Nothing here yet.',
            body='Not a real article.',
        )
        index_page.add_child(instance=page)
        page = SitePage(
            title='Timeline',
            description='Nothing here yet.',
            body='Not a real article.',
        )
        index_page.add_child(instance=page)

    def test_about(self):
        response = self.client.get(reverse('encyc-about'))
        self.assertEqual(response.status_code, 200)

    def test_history(self):
        response = self.client.get(reverse('encyc-history'))
        self.assertEqual(response.status_code, 200)

    def test_terminology(self):
        response = self.client.get(reverse('encyc-terminology'))
        self.assertEqual(response.status_code, 200)

    def test_timeline(self):
        response = self.client.get(reverse('encyc-timeline'))
        self.assertEqual(response.status_code, 200)
