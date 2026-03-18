from pathlib import Path
import random
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django import forms
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import httpx
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from taggit.models import TaggedItemBase
from wagtail.admin.panels import (
    FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel)
from wagtail.admin.panels import TabbedInterface, ObjectList
from wagtail.blocks import CharBlock, RichTextBlock
from wagtail.fields import RichTextField, StreamField
from wagtail import hooks
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.contrib.typed_table_block.blocks import TypedTableBlock
from wagtail.images.models import Image
from wagtail.models import Page, Orderable
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from encyc import wiki
from editors.models import Author
from encyclopedia.blocks import (
    ArticleTextBlock, EncycStreamBlock, HeadingBlock, QuoteBlock,
    ImageBlock, VideoBlock, DocumentBlock,
)
from encyclopedia.citations import Citation
from encyclopedia import databoxes
from encyclopedia import ddr
from encyclopedia import footnotes
from encyclopedia.topics import topics_items
from home.models import HomePage


def load_mediawiki_titles():
    """Map MediaWiki titles to original title text and to Wagtail slug titles
    """
    key = 'mediawiki-titles'
    results = cache.get(key)
    if not results:
        try:
            mw = wiki.MediaWiki()
            allpages = mw.mw.allpages()
        except:
            allpages = []
        results = {
            page.normalize_title(page.page_title): {
                'title': page.page_title,
                'slug': slugify(page.page_title)
            }
            for page in [page for page in allpages]
        }
        cache.set(key, results, settings.CACHE_TIMEOUT)
    return results


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
    title_sort = models.CharField(max_length=255, blank=True, null=True)
    description = StreamField([
            ('paragraph', ArticleTextBlock()),
        ],
        blank=False,
        use_json_field=True,
        help_text='Description should only be one paragraph.',
    )
    signature_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
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
    footnotes = RichTextField(blank=True, null=True, editable=False)
    authors = ParentalManyToManyField('editors.Author', blank=True)
    tags = ClusterTaggableManager(through=ArticleTag, blank=True)
    mw_url = models.CharField(max_length=255, blank=True, null=True)

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
    promote_panels = [
        MultiFieldPanel([
            FieldPanel('title_sort'),
            FieldPanel('authors', widget=forms.SelectMultiple),
            FieldPanel('tags'),
        ], heading='Metadata'),
    ]
    settings_panels = []

    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    subpage_types = []
    template = 'patterns/pages/article/article.html'

    class Meta:
        ordering = ['title_sort','title']
        verbose_name = "Basic Article"
        verbose_name_plural = "Basic Articles"

    def save(self, *args, **kwargs):
        if not self.title_sort:
            self.title_sort = slugify(self.title)
        self.slug = slugify(self.slug)  # force slug/url to be all-ASCII
        self.signature_image = self.get_signature_image()
        super(Article, self).save(*args, **kwargs)

    def initial(self):
        return self.title[0].upper()

    def citation(self):
        try:
            last_published_at = self.last_published_at.strftime('%c %Z')
        except:
            last_published_at = None
        c = Citation(self)
        return {
            'title': self.title,
            'meta': [
                {'label': 'Page name', 'value': self.title},
                {'label': 'Author(s)', 'value': 'Densho Encyclopedia contributors'},
                {'label': 'Publisher', 'value': 'Densho Encyclopedia'},
                {'label': 'Date of last revision', 'value': last_published_at},
                {'label': 'Date retrieved',
                 'value': timezone.now().strftime('%c %Z')},
                {'label': 'Permanent URL',
                 'value': f"{self.url}"},
            ],
            'apa':     c.apa,
            'bibtex':  c.bibtex,
            'chicago': c.chicago,
            'cse':     c.cse,
            'mhra':    c.mhra,
            'mla':     c.mla,
    }

    def comingsoon(self):
        return 'comingsoon' in [t.name for t in self.tags.all()]

    def hero(self):
        return {
            'title': self.title,
            'type': 'article',
            'introduction': self.description,
            'meta': [],
        }

    def contents(self):
        """Generate Table-of-Contents block from article headings"""
        return [
            {
                'title': block.value['heading_text'],
                'url': f"#{slugify(block.value['heading_text'])}"
            }
            for block in self.body if block.block_type in ['heading']
        ]

    def list_footnotes(self):
        return []

    def authors_all(self):
        return [a for a in self.authors.all()]

    def media_blocks(self):
        """Generator that returns only Article's media blocks
        """
        MEDIA_BLOCK_TYPES = ['imageblock','videoblock','documentblock']
        for block in self.body:
            if block.block_type in MEDIA_BLOCK_TYPES:
                yield block

    def get_signature_image(self, force=False):
        """Scans media blocks and returns the signature image

        Article.signature_image is the image that is shown in lists.

        This function
        - Iterates through article.body blocks
        - Gets the first Image/Video/DocumentBlock where signature is checked.
        - If Block has an 'image' or 'display', set article.signature_image and break.
        - If no blocks are selected
        - iterate through article.body blocks
        - select the first Block with an 'image' or 'display' and set.
        There might be multiple media Blocks with checkboxes but that's the
        author's problem.
        """
        if self.signature_image and not force:
            return self.signature_image
        # placeholder if no media blocks
        if len([b for b in self.media_blocks()]) == 0:
            return placeholder_image()
        # Get the first ImageBlock where signature is checked
        # If it has an image, that's the signature image
        for block in self.media_blocks():
            if block.value.get('signature', None):
                if block.value.get('image', None):
                    return block.value['image']
                elif block.value.get('display', None):
                    return block.value['display']
        # Didn't find one, so just get the first image
        for block in self.media_blocks():
            if block.value.get('image', None):
                return block.value['image']
            elif block.value.get('display', None):
                return block.value['display']
        # We want to know if images are missing from media blocks
        # If signature is still blank at this point just return None
        #return placeholder_image()
        return None

    def carousel(self):
        """Image blocks at the top of self.body are gathered into carousel
        """
        items = []
        for n,block in enumerate(self.carousel_blocks()):
            if block.block_type == 'imageblock':
                #assert 0
                # TODO this looks like encyclopedia.blocks.ImageBlockStructValue.modal
                caption = ' '.join([
                    block.value['caption'], block.value['caption2'],
                    block.value['courtesy']
                ])
                ddr_id = ''
                if 'ddr-' in block.value['ext_url']:
                    ddr_id = urlparse(block.value['ext_url']).path.replace('/','')
                source_type = 'image'
                source = block.value[source_type]
                filename = Path(source.file.name).name
                encyclopedia_id = filename
                items.append({
                    'type': 'Image',
                    'image': source,
                    'caption': block.value['caption'],
                    'url': '#',
                    'modal': {
                        'id': f"modal-{n}",
                        'open': False,
                        'media_type': 'Image',
                        'image': source,
                        'title': block.value['caption'],
                        'content': caption,
                        'caption': caption,
                        'densho_id': ddr_id,
                        'download_url': source.file.url,
                        'cite_url': f"/cite/{source.title}/",
                        'view_url': f"/sources/{source_type}/{source.title}/",
                        'creative_commons': block.value['creative_commons'],
                    }
                })
        return items

    def carousel_blocks(self):
        """Pulls out top-of-article media blocks for the top-of-article carousel

        In more detail, this function
        - collects media objects that appear before the first header/paragraph
        - out of these, selects only the images
        - pops these out into a separate self.carousel_blocks list
        - leaving the rest of the media objects where they were
        It should *not* touch any media objects that appear *after* the
        first header/paragraph/etc.

        History lesson: The article carousel started off as me not knowing
        what to do with Primary Sources when I'd migrated them.  The old
        Encyclopedia had them in a sidebar so there was no way to place them
        within te article text, which is an editorial decision, so I just
        stuck them at the top and figured the editors would take care of it.
        The Torchbox people saw media at the top and made this carousel thing,
        and here we are.
        Primary sources can be Images, Videos (and audio) or Documents,
        but the carousel template they gave us only displays *images*.
        """
        if hasattr(self, '_carousel_blocks') and self._carousel_blocks:
            return self._carousel_blocks
        MEDIA_BLOCK_TYPES = ['imageblock', 'videoblock', 'documentblock']
        CAROUSEL_BLOCK_TYPES = ['imageblock']
        self._carousel_blocks = []
        # we only want media blocks that appear at the beginning of Article.body,
        # before the text
        carousel_blocks_range = 0
        for block in self.body:
            if block.block_type not in MEDIA_BLOCK_TYPES:
                # this is a non-media block, like a header or paragraph
                # we've started the article now so stop
                break
            carousel_blocks_range += 1
        # list *indices* of CAROUSEL_BLOCK_TYPES blocks in carousel_blocks_range
        blocks_for_carousel = [
            n for n in range(0, carousel_blocks_range)
            if self.body[n].block_type in CAROUSEL_BLOCK_TYPES
        ]
        # reverse the list bc we can't start popping at zero
        blocks_for_carousel = [n for n in reversed([n for n in blocks_for_carousel])]
        ## pop CAROUSEL_BLOCK_TYPES blocks out of page body into separate list
        carousel_blocks = [
            self.body.pop(n)
            for n in blocks_for_carousel
        ]
        # and restore to original order
        self._carousel_blocks = [b for b in reversed(carousel_blocks)]
        return self._carousel_blocks

    def related_links(self):
        return [
            {
                'title': 'Guide to the Mike Lowry Congressional Papers, 1978–1988',
                'source': 'University of Washington Libraries',
                'url': '#',
            },
            {
                'title': 'Shimabukuro, Robert Sadamu. Born in Seattle: The Campaign for Japanese American Redress',
                'source': 'Seattle: University of Washington Press, 2001',
                'url': '#',
            },
            {
                'title': 'Guide to the Mike Lowry Congressional Papers, 1978–1988',
                'source': 'University of Washington Libraries',
                'url': '#',
            },
        ]

    def related_media(self):
        if not hasattr(self, 'related_ddr'):
            # only load once
            self.related_ddr = [
                {
                    'url':o['links']['html'],
                    'image':o['links']['img'],
                    'title':o['title'],
                }
                for o in ddr.ddr_objects(self.title)
            ]
        return self.related_ddr

    @staticmethod
    def articles_by_author():
        """List of Articles grouped by author"""
        def format_name(author):
            return f"{author.family_name},{author.given_name}"
        authors_articles = {
            f"{author.family_name},{author.given_name}": {
                'author_id': author.id,
                'display_name': author.display_name,
                'articles': [],
            }
            for author in Author.objects.all().order_by('family_name','given_name')
        }
        for article in Article.objects.filter(live=True).order_by('title'):
            for author in article.authors.all():
                authors_articles[format_name(author)]['articles'].append(
                    article.title
                )
        return authors_articles

    @staticmethod
    def articles_by_initial():
        """List of Articles grouped by initial letter of title"""
        import string
        tags_initials = {
            '1-10': [],
        }
        for initial in string.ascii_lowercase:
            tags_initials[initial.upper()] = []
        for article in Article.objects.filter(live=True).order_by('title'):
            initial = article.title[0].upper()
            if initial.isalpha():
                tags_initials[initial].append( (article.url,article.title) )
            else:
                tags_initials['1-10'].append( (article.url,article.title) )
        return tags_initials

    @staticmethod
    def articles_by_tag():
        """Dict of Articles grouped by tag"""
        topic_ids = [topic['id'] for topic in topics_items()]
        tags_articles = {tag: [] for tag in topic_ids}
        for article in Article.objects.filter(live=True).order_by('title'):
            for tag in article.tags.all():
                if str(tag) in topic_ids:
                    tags_articles[str(tag)].append(
                        (article.url, article.title)
                    )
        return tags_articles

    @staticmethod
    def article_ids_by_title():
        """Return dict of Wagtail Article IDs by title"""
        return {a['title']: a['id'] for a in Article.objects.values('title','id')}

    @staticmethod
    def _rewrite_article_urls(article, article_ids_by_url):
        for block in article.description:
            Article._rewrite_block_urls(article, block, article_ids_by_url)
        for block in article.body:
            Article._rewrite_block_urls(article, block, article_ids_by_url)

    @staticmethod
    def _rewrite_block_urls(article, block, article_ids_by_url):
        """Rewrite internal links in a block to Wagtail format

        Migration format: <a href="/wiki/title-here">Title Here</a>
        Wagtail format:   <a linktype="page" id="1234">Title Here</a>
        Wagtail Article.url: /title-here/
        """
        if block.block_type == 'paragraph':
            block_source = block.value.source
        elif block.block_type == 'quotation':
            block_source = block.value['quotation']
        else:
            return block
        soup = BeautifulSoup(block_source, 'lxml')
        for a in soup.find_all('a'):
            # skip already converted links
            if a.get('linktype') and a.get('id'):
                continue
            schema_domain = 'https://encyclopedia.densho.org/'
            if a.get('href') and schema_domain in a['href']:
                url_title = a['href'][:a['href'].rindex('/')].replace(schema_domain, '')
            # convert from migration format
            #     '/wiki/title-here'
            # to Wagtail Article.url format
            #     '/title-here/'
            # so we can get Article.id
            url = a.get('href').replace('/wiki', '') + '/'
            target_id = article_ids_by_url.get(url, None)
            #if (not target_id) and redirects.get(article.title, None):
            #    # this might be a redirect
            #    slug = slugify(article.title)
            #    url = f"/{slug}/"
            #    target_id = article_ids_by_url.get(url, None)
            if target_id:
                # rewrite link
                a['linktype'] = 'page'
                a['id'] = target_id
                del a['href']
        html = str(soup)
        # remove the wrapper that BeautifulSoup adds
        html = html.replace('<html><body>','').replace('</body></html>','')
        # replace original value
        if block.block_type == 'paragraph':
            block.value.source = html
        elif block.block_type == 'quotation':
            block.value['quotation'] = html
        return block


ARTICLE_FOOTNOTE_FIELDS = {
    'richtextfields': [],
    'streamfields': ['description', 'body'],
}

ARTICLE_FOOTNOTE_BLOCK_TYPES = [
    'paragraph',
    'quote',
]

@hooks.register('after_create_page')
def do_after_page_create(request, page):
    # TODO save first Image to self.image
    if isinstance(page, Article):
        return footnotes.Footnotary.update_footnotes(
            page, request=request,
            fields=ARTICLE_FOOTNOTE_FIELDS,
            block_types=ARTICLE_FOOTNOTE_BLOCK_TYPES,
        )

@hooks.register('after_edit_page')
def do_after_page_edit(request, page):
    # TODO save first Image to self.image
    if isinstance(page, Article):
        return footnotes.Footnotary.update_footnotes(
            page, request=request,
            fields=ARTICLE_FOOTNOTE_FIELDS,
            block_types=ARTICLE_FOOTNOTE_BLOCK_TYPES,
        )

@hooks.register('before_serve_page')
def prep_footnotes(page, request, serve_args, serve_kwargs):
    if isinstance(page, Article):
        # uses BeautifulSoup to rewrite paragraph blocks with links to footnotes
        # TODO this should happen BEFORE page is cached
        return footnotes.Footnotary.prep_footnotes(
            page, request=request,
            fields=ARTICLE_FOOTNOTE_FIELDS,
            block_types=ARTICLE_FOOTNOTE_BLOCK_TYPES,
        )

def placeholder_image():
    """Return a placeholder Image object
    TODO cache this!
    """
    try:
        return Image.objects.filter(title='placeholder')[0]
    except Image.DoesNotExist:
        return None
    except IndexError:
        return None


class MediawikiWagtail(models.Model):
    """Map encycfront MediaWiki URLs to Article title slugs
    """
    mediawiki_url = models.CharField(max_length=255, help_text="MediaWiki title URL")
    wagtail_slug = models.CharField(max_length=255, help_text="Wagtail title slug")

    class Meta:
        verbose_name = 'Mediawiki-Wagtail'
        verbose_name_plural = 'Mediawiki-Wagtail'


# Article -> sources ---------------------------------------------------

BLOCK_TYPES = ['imageblock','documentblock','videoblock']

BLOCKTYPE_OBJECTTYPE = {
    'imageblock': 'image',
    'documentblock': 'document',
    'videoblock': 'video',
}

OBJECTTYPE_BLOCKTYPE = {
    'image': 'imageblock',
    'document': 'documentblock',
    'video': 'videoblock',
}

class ArticleSources():
    """
    """

    @staticmethod
    def source_article_blocks(source):
        articles = [page.article for page,ref in source.get_usage()]
        articles_blocks = [
            (
                article,
                ArticleSources.source_article_block(
                    source._meta.model_name, source.id, article
                ).value
            )
            for article in articles
        ]
        return articles_blocks

    @staticmethod
    def source_article_block(source_type, source_id, article):
        for block in article.body:
            if BLOCKTYPE_OBJECTTYPE.get(block.block_type) == source_type:
                obj = block.value[source_type]
                if obj.id == source_id:
                    return block
        return None


# databox articles -----------------------------------------------------

DATABOX_MAX = 1024

def databox_hero_meta(article, hero):
    """Adds Article's databox fields to hero['meta'] for hero_split template
    """
    class_name = article.__class__.__name__
    key = f"databox-{article._meta.verbose_name_plural}"
    fields_labels = {
        f['tng']: f['label'] for f in databoxes.DATABOXES[key]['fields']
    }
    fieldnames = databoxes.ARTICLE_CLASS_FIELDNAMES.get(class_name, [])
    for fieldname in fieldnames:
        value = getattr(article, fieldname, None)
        if value:
            hero['meta'].append({
                'label':fields_labels[fieldname],
                'value':value,
            })
    return hero


class ArticleAlbum(Article):
    album_title = models.CharField(blank=True, max_length=DATABOX_MAX)
    artist = models.CharField(blank=True, max_length=DATABOX_MAX)
    album_type = models.CharField(blank=True, max_length=DATABOX_MAX)
    recorded = models.CharField(blank=True, max_length=DATABOX_MAX)
    released = models.CharField(blank=True, max_length=DATABOX_MAX)
    genre = models.CharField(blank=True, max_length=DATABOX_MAX)
    length = models.CharField(blank=True, max_length=DATABOX_MAX)
    label = models.CharField(blank=True, max_length=DATABOX_MAX)
    producer = models.CharField(blank=True, max_length=DATABOX_MAX)
    official_url = models.CharField(blank=True, max_length=DATABOX_MAX)
    musicbrainz_url = models.CharField(blank=True, max_length=DATABOX_MAX)
    discogs_url = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleAlbum']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_albums"
        verbose_name = "Album"
        verbose_name_plural = "Albums"

    def hero(self):
        return databox_hero_meta(self, super(ArticleAlbum, self).hero())


class ArticleArticle(Article):
    author = models.CharField(blank=True, max_length=DATABOX_MAX)
    article_title = models.CharField(blank=True, max_length=DATABOX_MAX)
    pubname = models.CharField(blank=True, max_length=DATABOX_MAX)
    pubdate = models.CharField(blank=True, max_length=DATABOX_MAX)
    pubdetails = models.CharField(blank=True, max_length=DATABOX_MAX)
    doi_url = models.CharField(blank=True, max_length=DATABOX_MAX)
    url = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleArticle']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_articles"
        verbose_name = "Article/essay/story/etc"
        verbose_name_plural = "Articles/essays/stories/etc"

    def hero(self):
        return databox_hero_meta(self, super(ArticleArticle, self).hero())


class ArticleBook(Article):
    book_title = models.CharField(blank=True, max_length=DATABOX_MAX)
    author = models.CharField(blank=True, max_length=DATABOX_MAX)
    illustrator = models.CharField(blank=True, max_length=DATABOX_MAX)
    title_orig = models.CharField(blank=True, max_length=DATABOX_MAX)
    country = models.CharField(blank=True, max_length=DATABOX_MAX)
    language = models.CharField(blank=True, max_length=DATABOX_MAX)
    series = models.CharField(blank=True, max_length=DATABOX_MAX)
    genre = models.CharField(blank=True, max_length=DATABOX_MAX)
    publisher = models.CharField(blank=True, max_length=DATABOX_MAX)
    pubdate = models.CharField(blank=True, max_length=DATABOX_MAX)
    publisher_current = models.CharField(blank=True, max_length=DATABOX_MAX)
    pubdate_current = models.CharField(blank=True, max_length=DATABOX_MAX)
    media_type = models.CharField(blank=True, max_length=DATABOX_MAX)
    pages = models.CharField(blank=True, max_length=DATABOX_MAX)
    awards = models.CharField(blank=True, max_length=DATABOX_MAX)
    isbn = models.CharField(blank=True, max_length=DATABOX_MAX)
    worldcat_url = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleBook']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_books"
        verbose_name = "Book"
        verbose_name_plural = "Books"

    def hero(self):
        return databox_hero_meta(self, super(ArticleBook, self).hero())


class ArticleCamp(Article):
    sos_uid = models.CharField(blank=True, max_length=DATABOX_MAX)
    densho_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    usg_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    facility_type = models.CharField(blank=True, max_length=DATABOX_MAX)
    admin_agency = models.CharField(blank=True, max_length=DATABOX_MAX)
    date_opened = models.CharField(blank=True, max_length=DATABOX_MAX)
    date_closed = models.CharField(blank=True, max_length=DATABOX_MAX)
    location_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    city_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    state_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    facility_descr = models.CharField(blank=True, max_length=DATABOX_MAX)
    gis_lat = models.CharField(blank=True, max_length=DATABOX_MAX)
    gis_long = models.CharField(blank=True, max_length=DATABOX_MAX)
    gis_tgn_id = models.CharField(blank=True, max_length=DATABOX_MAX)
    current_disposition = models.CharField(blank=True, max_length=DATABOX_MAX)
    population_descr = models.CharField(blank=True, max_length=DATABOX_MAX)
    exit_destination = models.CharField(blank=True, max_length=DATABOX_MAX)
    peak_population = models.CharField(blank=True, max_length=DATABOX_MAX)
    peak_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    nps_link = models.CharField(blank=True, max_length=DATABOX_MAX)
    official_link = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleCamp']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_camps"
        verbose_name = "Camp"
        verbose_name_plural = "Camps"

    def hero(self):
        return databox_hero_meta(self, super(ArticleCamp, self).hero())


class ArticleExhibition(Article):
    first_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    final_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    location = models.CharField(blank=True, max_length=DATABOX_MAX)
    organization = models.CharField(blank=True, max_length=DATABOX_MAX)
    curator = models.CharField(blank=True, max_length=DATABOX_MAX)
    producer = models.CharField(blank=True, max_length=DATABOX_MAX)
    key_staff = models.CharField(blank=True, max_length=DATABOX_MAX)
    url = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleExhibition']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_exhibitions"
        verbose_name = "Exhibition"
        verbose_name_plural = "Exhibitions"

    def hero(self):
        return databox_hero_meta(self, super(ArticleExhibition, self).hero())


class ArticleFilm(Article):
    film_title = models.CharField(blank=True, max_length=DATABOX_MAX)
    film_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    genre = models.CharField(blank=True, max_length=DATABOX_MAX)
    released = models.CharField(blank=True, max_length=DATABOX_MAX)
    director = models.CharField(blank=True, max_length=DATABOX_MAX)
    producer = models.CharField(blank=True, max_length=DATABOX_MAX)
    writer = models.CharField(blank=True, max_length=DATABOX_MAX)
    screenplay = models.CharField(blank=True, max_length=DATABOX_MAX)
    story = models.CharField(blank=True, max_length=DATABOX_MAX)
    based_on = models.CharField(blank=True, max_length=DATABOX_MAX)
    narrator = models.CharField(blank=True, max_length=DATABOX_MAX)
    starring = models.CharField(blank=True, max_length=DATABOX_MAX)
    music = models.CharField(blank=True, max_length=DATABOX_MAX)
    cinematography = models.CharField(blank=True, max_length=DATABOX_MAX)
    editing = models.CharField(blank=True, max_length=DATABOX_MAX)
    studio = models.CharField(blank=True, max_length=DATABOX_MAX)
    distributor = models.CharField(blank=True, max_length=DATABOX_MAX)
    runtime = models.CharField(blank=True, max_length=DATABOX_MAX)
    country = models.CharField(blank=True, max_length=DATABOX_MAX)
    language = models.CharField(blank=True, max_length=DATABOX_MAX)
    budget = models.CharField(blank=True, max_length=DATABOX_MAX)
    gross = models.CharField(blank=True, max_length=DATABOX_MAX)
    imdb_url = models.CharField(blank=True, max_length=DATABOX_MAX)
    trailer_url = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleFilm']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_films"
        verbose_name = "Film"
        verbose_name_plural = "Films"

    def hero(self):
        return databox_hero_meta(self, super(ArticleFilm, self).hero())


class ArticleMagazine(Article):
    magazine_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    year_founded = models.CharField(blank=True, max_length=DATABOX_MAX)
    first_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    final_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    final_issue = models.CharField(blank=True, max_length=DATABOX_MAX)
    frequency = models.CharField(blank=True, max_length=DATABOX_MAX)
    editor = models.CharField(blank=True, max_length=DATABOX_MAX)
    former_editors = models.CharField(blank=True, max_length=DATABOX_MAX)
    staff_writers = models.CharField(blank=True, max_length=DATABOX_MAX)
    photographers = models.CharField(blank=True, max_length=DATABOX_MAX)
    founder = models.CharField(blank=True, max_length=DATABOX_MAX)
    publisher = models.CharField(blank=True, max_length=DATABOX_MAX)
    company = models.CharField(blank=True, max_length=DATABOX_MAX)
    circulation = models.CharField(blank=True, max_length=DATABOX_MAX)
    country = models.CharField(blank=True, max_length=DATABOX_MAX)
    language = models.CharField(blank=True, max_length=DATABOX_MAX)
    issn = models.CharField(blank=True, max_length=DATABOX_MAX)
    worldcat_url = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleMagazine']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_magazines"
        verbose_name = "Magazine"
        verbose_name_plural = "Magazines"

    def hero(self):
        return databox_hero_meta(self, super(ArticleMagazine, self).hero())


class ArticleNewspaper(Article):
    peak_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    publication_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    camp_article = models.CharField(blank=True, max_length=DATABOX_MAX)
    publication_start_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    publication_end_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    predecessor_pub = models.CharField(blank=True, max_length=DATABOX_MAX)
    successor_pub = models.CharField(blank=True, max_length=DATABOX_MAX)
    mode_of_production = models.CharField(blank=True, max_length=DATABOX_MAX)
    staff = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleNewspaper']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_newspapers"
        verbose_name = "Newspaper"
        verbose_name_plural = "Newspapers"

    def hero(self):
        return databox_hero_meta(self, super(ArticleNewspaper, self).hero())


class ArticlePerson(Article):
    first_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    last_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    display_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    birth_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    death_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    birth_location = models.CharField(blank=True, max_length=DATABOX_MAX)
    gender = models.CharField(blank=True, max_length=DATABOX_MAX)
    ethnicity = models.CharField(blank=True, max_length=DATABOX_MAX)
    generation = models.CharField(blank=True, max_length=DATABOX_MAX)
    nationality = models.CharField(blank=True, max_length=DATABOX_MAX)
    external_url = models.CharField(blank=True, max_length=DATABOX_MAX)
    primary_geography = models.CharField(blank=True, max_length=DATABOX_MAX)
    religion = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticlePerson']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_people"
        verbose_name = "Person"
        verbose_name_plural = "People"

    def hero(self):
        return databox_hero_meta(self, super(ArticlePerson, self).hero())


class ArticlePlay(Article):
    play_name = models.CharField(blank=True, max_length=DATABOX_MAX)
    first_data = models.CharField(blank=True, max_length=DATABOX_MAX)
    final_date = models.CharField(blank=True, max_length=DATABOX_MAX)
    location = models.CharField(blank=True, max_length=DATABOX_MAX)
    writer = models.CharField(blank=True, max_length=DATABOX_MAX)
    director = models.CharField(blank=True, max_length=DATABOX_MAX)
    producer = models.CharField(blank=True, max_length=DATABOX_MAX)
    creative = models.CharField(blank=True, max_length=DATABOX_MAX)
    technical = models.CharField(blank=True, max_length=DATABOX_MAX)
    characters = models.CharField(blank=True, max_length=DATABOX_MAX)
    official_url = models.CharField(blank=True, max_length=DATABOX_MAX)
    playbill_url = models.CharField(blank=True, max_length=DATABOX_MAX)
    ibdb_id = models.CharField(blank=True, max_length=DATABOX_MAX)
    iodb_id = models.CharField(blank=True, max_length=DATABOX_MAX)
    theatricalia_id = models.CharField(blank=True, max_length=DATABOX_MAX)
    publisher = models.CharField(blank=True, max_length=DATABOX_MAX)
    pubdate = models.CharField(blank=True, max_length=DATABOX_MAX)
    current_publisher = models.CharField(blank=True, max_length=DATABOX_MAX)
    current_pubdate = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticlePlay']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_plays"
        verbose_name = "Play"
        verbose_name_plural = "Plays"

    def hero(self):
        return databox_hero_meta(self, super(ArticlePlay, self).hero())


class ArticleWebsite(Article):
    website_type = models.CharField(blank=True, max_length=DATABOX_MAX)
    url = models.CharField(blank=True, max_length=DATABOX_MAX)
    website_title = models.CharField(blank=True, max_length=DATABOX_MAX)
    creator = models.CharField(blank=True, max_length=DATABOX_MAX)
    active = models.CharField(blank=True, max_length=DATABOX_MAX)
    has_blog = models.CharField(blank=True, max_length=DATABOX_MAX)
    primary_sources = models.CharField(blank=True, max_length=DATABOX_MAX)

    metadata_panels = [
        FieldPanel(fieldname)
        for fieldname in databoxes.ARTICLE_CLASS_FIELDNAMES['ArticleWebsite']
    ]
    edit_handler = TabbedInterface([
        ObjectList(Article.content_panels, heading='Content'),
        ObjectList(metadata_panels, heading='Metadata'),
        ObjectList(Article.promote_panels, heading='Promote'),
        ObjectList(Article.settings_panels, heading='Settings'),
    ])
    parent_page_types = ['wagtailcore.Page', 'home.HomePage', 'encyclopedia.ArticlesIndexPage']
    template = 'patterns/pages/article/article.html'

    class Meta:
        db_table = "encyclopedia_article_website"
        verbose_name = "Web Site"
        verbose_name_plural = "Web Sites"

    def hero(self):
        return databox_hero_meta(self, super(ArticleWebsite, self).hero())
