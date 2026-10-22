from django.test import TestCase
from django.urls import reverse

from .models import Article


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
    def test_author(self):
        url = reverse('encyc-author', kwargs={'slug': 'brian-niiya'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class SearchView(TestCase):

    def test_articles_search_empty(self):
        url = reverse('encyc-articles-search')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_articles_search_minidoka(self):
        url = reverse('encyc-articles-search') + "?query=minidoka"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ArticleView(TestCase):
    def test_article(self):
        url = '/aki-kurose/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ArticleRelatedView(TestCase):
    def test_article(self):
        url = reverse('encyc-related', kwargs={'article_id': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
