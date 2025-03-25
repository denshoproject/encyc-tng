from django.db import models

from wagtail.models import Page


class HomePage(Page):
    template = "patterns/pages/home_page/home_page.html"
    pass
