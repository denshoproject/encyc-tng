from django.test import TestCase
from django.urls import reverse

from . import models


class BrowseView(TestCase):
    def test_browse(self):
        response = self.client.get(reverse('encyc-browse'))
        self.assertEqual(response.status_code, 200)
