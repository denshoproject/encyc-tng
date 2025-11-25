from django.db import models
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.search import index

from .blocks import (
    ArticleTextBlock, HeadingBlock, QuoteBlock,
    ImageBlock, VideoBlock, DocumentBlock,
)


class SitePagesIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]


class SitePage(Page):
    description = StreamField([
            ('paragraph', ArticleTextBlock()),
        ],
        blank=False,
        use_json_field=True,
        help_text='Description should only be one paragraph.',
    )
    body = StreamField([
            ('heading', HeadingBlock()),
            ('paragraph', ArticleTextBlock()),
            ('quote', QuoteBlock()),
            ('imageblock', ImageBlock()),
            ('videoblock', VideoBlock()),
            ('documentblock', DocumentBlock()),
        ],
        blank=True,
        use_json_field=True,
        help_text='BODY HELP TEXT GOES HERE.',
    )

    search_fields = Page.search_fields + [
        index.SearchField('description'),
        index.SearchField('body'),
        index.SearchField('footnotes'),
    ]
    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('body'),
        #FieldPanel('footnotes'),
    ]
    promote_panels = []
    settings_panels = []

    parent_page_types = ['wagtailcore.Page', 'info.SitePagesIndexPage']
    subpage_types = []
    template = 'patterns/pages/article/article.html'

    class Meta:
        verbose_name = "Site Article"
        verbose_name_plural = "Site Articles"
