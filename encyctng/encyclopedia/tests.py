from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page, Site
from wagtail.test.utils import WagtailPageTestCase

from .models import ArticlesIndexPage, Article
from editors.models import Author


class BrowseView(TestCase):
    def test_browse(self):
        response = self.client.get(reverse('encyc-browse'))
        self.assertEqual(response.status_code, 200)


class ArticlesTopicView(TestCase):
    def test_articles_topic(self):
        response = self.client.get(reverse('encyc-articles-topic'))
        self.assertEqual(response.status_code, 200)


class ArticlesAZView(TestCase):
    def test_articles_az(self):
        response = self.client.get(reverse('encyc-articles-az'))
        self.assertEqual(response.status_code, 200)


class AuthorsListView(TestCase):
    def test_authors(self):
        response = self.client.get(reverse('encyc-authors'))
        self.assertEqual(response.status_code, 200)


class AuthorDetailView(TestCase):
    def setUp(self):
        Author.objects.create(
            family_name='Niiya',
            given_name='Brian',
            display_name='Brian Niiya',
            description='The GOAT.',
        )

    def test_author(self):
        url = reverse('encyc-author', kwargs={'slug': 'brian-niiya'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class SearchView(TestCase):
    @classmethod
    def setUp(cls):
        root = Page.get_first_root_node()
        Site.objects.create(
            hostname='testserver',
            site_name='testserver',
            root_page=root,
            is_default_site=True,
        )
        index_page = ArticlesIndexPage(title='Articles')
        root.add_child(instance=index_page)
        cls.page = Article(
            title='Aki Kurose',
            description='Nothing here yet.',
            body='Not a real article.',
        )
        index_page.add_child(instance=cls.page)

    def test_articles_search_empty(self):
        url = reverse('encyc-articles-search')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_articles_search_minidoka(self):
        url = reverse('encyc-articles-search') + "?query=kurose"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ArticleView(WagtailPageTestCase):
    @classmethod
    def setUp(cls):
        root = Page.get_first_root_node()
        Site.objects.create(
            hostname='testserver',
            site_name='testserver',
            root_page=root,
            is_default_site=True,
        )
        index_page = ArticlesIndexPage(title='Articles')
        root.add_child(instance=index_page)
        cls.page = Article(
            title='Aki Kurose',
            description='Nothing here yet.',
            body='Not a real article.',
        )
        index_page.add_child(instance=cls.page)

    def test_default_route(self):
        self.assertPageIsRoutable(self.page)

    #def test_article(self):
    #    url = f"/{self.page.slug}/"
    #    response = self.client.get(url)
    #    self.assertEqual(response.status_code, 200)

    def test_default_route_rendering(self):
        self.assertPageIsRenderable(self.page)


class ArticleRelatedView(TestCase):
    @classmethod
    def setUp(cls):
        root = Page.get_first_root_node()
        Site.objects.create(
            hostname='testserver',
            site_name='testserver',
            root_page=root,
            is_default_site=True,
        )
        index_page = ArticlesIndexPage(title='Articles')
        root.add_child(instance=index_page)
        cls.page = Article(
            title='Aki Kurose',
            description='Nothing here yet.',
            body='Not a real article.',
        )
        index_page.add_child(instance=cls.page)

    def test_article_related(self):
        url = reverse('encyc-related', kwargs={'article_id': self.page.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
