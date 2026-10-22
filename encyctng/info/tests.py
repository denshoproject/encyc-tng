from django.test import TestCase
from django.urls import reverse

from .models import SitePage


class AboutView(TestCase):
    def test_about(self):
        response = self.client.get(reverse('encyc-about'))
        self.assertEqual(response.status_code, 200)


class HistoryView(TestCase):
    def test_history(self):
        response = self.client.get(reverse('encyc-history'))
        self.assertEqual(response.status_code, 200)


class TerminologyView(TestCase):
    def test_terminology(self):
        response = self.client.get(reverse('encyc-terminology'))
        self.assertEqual(response.status_code, 200)


class TimelineView(TestCase):
    def test_timeline(self):
        response = self.client.get(reverse('encyc-timeline'))
        self.assertEqual(response.status_code, 200)
