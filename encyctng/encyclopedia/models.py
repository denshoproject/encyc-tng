from bs4 import BeautifulSoup
from django import forms
from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from taggit.models import TaggedItemBase
from wagtail.admin.panels import (
    FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel)
from wagtail.blocks import CharBlock, RichTextBlock
from wagtail.fields import RichTextField, StreamField
from wagtail import hooks
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.contrib.typed_table_block.blocks import TypedTableBlock
from wagtail.models import Page, Orderable
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from encyclopedia.blocks import (
    ArticleTextBlock, EncycStreamBlock, HeadingBlock, QuoteBlock,
    ImageBlock, VideoBlock, DocumentBlock,
)


class ArticlesIndexPage(Page):
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    def get_context(self, request):
        """Override context: only published posts in reverse-chrono order
        """
        context = super().get_context(request)
        articles = self.get_children().live().order_by('-first_published_at')
        context['articles'] = articles
        return context


class ArticleTag(TaggedItemBase):
    content_object = ParentalKey(
        'Article',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )


class ArticleTagPage(Page):
    def get_context(self, request):
        # filter by tag
        tag = request.GET.get('tag')
        articles = Article.objects.filter(tags__name=tag)
        # update template content
        context = super().get_context(request)
        context['articles'] = articles
        return context


class Article(Page):
    description = RichTextField(blank=True)
    body = StreamField([
            ('heading', HeadingBlock()),
            ('paragraph', ArticleTextBlock()),
            ('embed', EncycStreamBlock()),
            ('quote', QuoteBlock()),
            ('imageblock', ImageBlock()),
            ('videoblock', VideoBlock()),
            ('documentblock', DocumentBlock()),
        ],
        blank=True,
        use_json_field=True,
        help_text='BODY HELP TEXT GOES HERE.',
    )
    footnotes = RichTextField(blank=True, null=True)
    authors = ParentalManyToManyField('editors.Author', blank=True)
    tags = ClusterTaggableManager(through=ArticleTag, blank=True)

    search_fields = Page.search_fields + [
        index.SearchField('description'),
        index.SearchField('body'),
        index.SearchField('footnotes'),
    ]
    content_panels = Page.content_panels + [
        FieldPanel('description'),
        FieldPanel('body'),
        FieldPanel('footnotes'),
    ]
    promote_panels = [
        MultiFieldPanel([
            FieldPanel('authors', widget=forms.SelectMultiple),
            FieldPanel('tags'),
        ], heading='Metadata'),
    ]
    settings_panels = []

    parent_page_types = ['encyclopedia.ArticlesIndexPage']
    subpage_types = []

ARTICLE_FOOTNOTE_FIELDS = {
    'richtextfields': ['description'],
    'streamfields': ['body'],
}

@hooks.register('after_create_page')
def do_after_page_create(request, page):
    if type(page) == Article:
        return Footnotary.update_footnotes(page, ARTICLE_FOOTNOTE_FIELDS)

@hooks.register('after_edit_page')
def do_after_page_edit(request, page):
    if type(page) == Article:
        return Footnotary.update_footnotes(page, ARTICLE_FOOTNOTE_FIELDS)

@hooks.register('before_serve_page')
def prep_footnotes(page, request, serve_args, serve_kwargs):
    return Footnotary.prep_footnotes(page, ARTICLE_FOOTNOTE_FIELDS, request)


# footnote tags - see docstring for Footnotary
REF_TAGS = [
    ('&lt;ref&gt;','<ref>'),
    ('&lt;/ref&gt;','</ref>')
]

class Footnotary():
    """Turn <ref>footnotes</ref> in page.body into links and notes with backlinks
    
    IMPORTANT: Footnotes <ref> tags are stored as entity references (&lt;/ref&gt;).
    This way they are visible to the user in the UI but are hidden from Wagtail's
    RichTextBlock editor and parser.
    """

    @staticmethod
    def update_footnotes(page, fields):
        """Copy Mediawiki-style <ref> footnotes from page body to a Footnotes block
        
        Run in after_create_page and after_edit_page hooks.
        """
        # smoosh HTML from the paragraph blocks into one string
        html = '\n'.join([
            block['value']
            for block in page.body.raw_data if block['type'] == 'paragraph'
        ])
        # the <ref> tags might have been escaped so fix them
        for broken,fixed in REF_TAGS:
            html = html.replace(broken,fixed)
        # extract each <ref></ref> tag and build HTML
        footnotes = '\n'.join([
            str(ref) for ref in BeautifulSoup(html).find_all('ref')
        ])
        # replace the old footnotes block
        page.footnotes = footnotes
        # save the page
        new_revision = page.save_revision()
        if page.live:
            # page has been created and published at the same time,
            # so ensure that the updated title is on the published version too
            new_revision.publish()

    @staticmethod
    def prep_footnotes(page, fields, request):
        """Prep <ref>footnotes</ref> in the text for display
        
        Run in before_serve_page hooks.
        """
        if not type(page) == Article:
            return
        n = 1
        for block in page.body:
            if block.block_type == 'paragraph':
                html,n = Footnotary._rewrite_body_html(str(block.value), n)
                block.value.source = html
        page.footnotes = Footnotary._rewrite_footnotes_html(page.footnotes)

    @staticmethod
    def _rewrite_body_html(html, n):
        """Replace <ref>footnotes</ref> in page body with links to footnotes
        
        BEFORE
            <ref>Footnote text</ref>
        AFTER
            <sup class="reference" id="cite_ref-1">
              <a class="" href="#cite_note-1">
                [1]
              </a>
            </sup>
        """
        # <ref> tags might have been escaped so fix them
        for broken,fixed in REF_TAGS:
            html = html.replace(broken,fixed)
        soup = BeautifulSoup(html)
        # remove <head> and <body>
        soup.html.unwrap()
        soup.head.unwrap()
        soup.body.unwrap()
        # rewrite <ref> tags as <li> with backlinks
        for item in soup.find_all('ref'):
            ref_name  = f"cite_ref-{n}"
            note_name = f"cite_note-{n}"
            # insert <a name> before
            anchor = soup.new_tag('a')
            anchor['name'] = ref_name
            item.insert_before(anchor)
            # rewrite <ref> as <a href>
            item.name = 'a'
            item['href'] = f"#{note_name}"
            item.string = f"[{n}]"
            # increment
            n += 1
        return str(soup),n

    @staticmethod
    def _rewrite_footnotes_html(html):
        """Replace <refs> in footnotes field with <li>notes</li> and backlinks
        
        BEFORE
            <ref>First footnote text</ref>
            <ref>Second footnote text</ref>
        AFTER
            <ol class="references">
              <li id="cite_note-1">
                <span class="mw-cite-backlink">
                  <a class="" href="#cite_ref-1">↑</a>
                </span>
                <span class="reference-text">...</span>
              </li>
              ...
            </ol>
        """
        soup = BeautifulSoup(html)
        # remove <head> and <body>
        soup.head.unwrap()
        soup.body.unwrap()
        # rename <html> to <ol>
        soup.html.name = 'ol'
        soup.ol['class'] = 'references'
        # rewrite <ref> tags as <li> with backlinks
        for n,item in enumerate(soup.find_all('ref'), start=1):
            ref_name  = f"cite_ref-{n}"
            note_name = f"cite_note-{n}"
            # insert <a name> before
            anchor = soup.new_tag('a')
            anchor['name'] = note_name
            item.insert_before(anchor)
            # rewrite <ref> as <a href>
            item.name = 'li'
            item['id'] = note_name
            # insert backlink
            item.insert(0, ' ')
            backlink = soup.new_tag('a')
            backlink['href'] = f"#{ref_name}"
            backlink.string = '↑'
            item.insert(0, backlink)
        return str(soup)