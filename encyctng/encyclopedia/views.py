from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.cache import cache_page

from wagtail.admin.auth import permission_denied
from wagtail.admin.views.reports import ReportView, PageReportView
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtailmedia.models import Media
from wagtail.models.media import Collection
from wagtail.search.utils import parse_query_string

from editors.models import Author
from encyclopedia.models import Article, ArticleSources
from encyclopedia.topics import topics_items
from sources.models import Source

PAGINATOR_ON_EACH_SIDE = 2
PAGINATOR_ON_ENDS = 1


# CMS / Editors' UI

class UnpublishedChangesReportView(PageReportView):
    index_url_name = 'unpublished_changes_report'
    index_results_url_name = 'unpublished_changes_report_results'
    results_template_name = 'reports/unpublished_changes_report_results.html'
    header_icon = 'doc-empty-inverse'
    page_title = 'Pages with unpublished changes'
    list_export = PageReportView.list_export + ['last_published_at']
    export_headings = dict(
        last_published_at='Last Published',
        **PageReportView.export_headings
    )

    def get_queryset(self):
        return Article.objects.filter(has_unpublished_changes=True)

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            return permission_denied(request)
        return super().dispatch(request, *args, **kwargs)

class ComingSoonReportView(PageReportView):
    index_url_name = 'coming_soon_report'
    index_results_url_name = 'coming_soon_report_results'
    results_template_name = 'reports/coming_soon_report_results.html'
    header_icon = 'doc-empty-inverse'
    page_title = 'Coming Soon'

    def get_queryset(self):
        return Article.objects.filter(tags__name='comingsoon')

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            return permission_denied(request)
        return super().dispatch(request, *args, **kwargs)

class NeedsEditorReportView(PageReportView):
    index_url_name = 'needs_editor_report'
    index_results_url_name = 'needs_editor_report_results'
    results_template_name = 'reports/needs_editor_report_results.html'
    header_icon = 'doc-empty-inverse'
    page_title = 'Needs Editor Attention'

    def get_queryset(self):
        return Article.objects.filter(tags__name='needseditor')

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            return permission_denied(request)
        return super().dispatch(request, *args, **kwargs)


# Public UI

# home/index page comes from home.models.HomePage

@cache_page(settings.CACHE_TIMEOUT)
def browse(request):
    topics = {
        'title': 'Browse Topics',
        'items': topics_items(),
    }
    return render(request, 'patterns/pages/topic_listing/topic_listing.html', {
        'topics': topics,
    })

def articles_base_query():
    """Base query used by all the list views
    """
    articles = Article.objects.live().order_by('title_sort') \
                .defer("body") \
                .prefetch_related('tags')
    # TODO Prefetching image renditions
    # https://docs.wagtail.org/en/stable/advanced_topics/images/renditions.html
    return articles

@cache_page(settings.CACHE_TIMEOUT)
def articles_topic(request, topic=None):
    if topic:
        topic = topic.lower()
        if topic == 'all':
            topic = None
    page_size = int(request.GET.get('pagesize', 30))
    page_number = int(request.GET.get('page', 1))

    articles = articles_base_query()
    if topic:
        articles = Article.objects.filter(tags__name__in=[topic])
    Article.remove_description_footnotes(articles)

    paginator = Paginator(articles, page_size)
    page_obj = paginator.get_page(page_number)
    page_range = page_obj.paginator.get_elided_page_range(
        page_number, on_each_side=PAGINATOR_ON_EACH_SIDE, on_ends=PAGINATOR_ON_ENDS,
    )
    page_range_bottom = page_obj.paginator.get_elided_page_range(
        page_number, on_each_side=PAGINATOR_ON_EACH_SIDE, on_ends=PAGINATOR_ON_ENDS,
    )
    return render(request, 'patterns/pages/collections/collections.html', {
        'tabs': collections_authors_tabs(url=reverse('encyc-articles-topic')),
        'tags': tags_collections_topics(topic),
        'page_obj': page_obj,
        'page_range': page_range,
        'page_range_bottom': page_range_bottom,
    })

@cache_page(settings.CACHE_TIMEOUT)
def articles_az(request):
    initial = request.GET.get('initial', None)
    if initial and initial.lower() == 'all':
        initial = None
    page_size = int(request.GET.get('pagesize', 30))
    page_number = int(request.GET.get('page', 1))

    articles = articles_base_query()
    if initial and initial[0].isalpha():
        articles = articles.filter(title_sort__istartswith=initial)
    elif initial and initial[0].isdigit():
        articles = articles.filter(title_sort__regex=r"^(\d)")
    Article.remove_description_footnotes(articles)

    paginator = Paginator(articles, page_size)
    page_obj = paginator.get_page(page_number)
    page_range = page_obj.paginator.get_elided_page_range(
        page_number, on_each_side=PAGINATOR_ON_EACH_SIDE, on_ends=PAGINATOR_ON_ENDS,
    )
    page_range_bottom = page_obj.paginator.get_elided_page_range(
        page_number, on_each_side=PAGINATOR_ON_EACH_SIDE, on_ends=PAGINATOR_ON_ENDS,
    )
    return render(request, 'patterns/pages/collections/collections--a-z.html', {
        'tabs': collections_authors_tabs(url=reverse('encyc-articles-az')),
        'tags': tags_collections_az(initial),
        'page_obj': page_obj,
        'page_range': page_range,
        'page_range_bottom': page_range_bottom,
    })

@cache_page(settings.CACHE_TIMEOUT)
def articles_search(request, topic=None):
    query_string = request.GET.get('query', None)
    page_size = int(request.GET.get('pagesize', 30))
    page_number = int(request.GET.get('page', 1))

    if query_string:
        articles = articles_base_query()
        filters, query = parse_query_string(query_string, operator='and')
        articles = articles.filter(live=True).search(query)
        # Log the query so Wagtail can suggest promoted results
        #from wagtail.contrib.search_promotions.models import Query
        #Query.get(query).add_hit()
    else:
        articles = Article.objects.none()
    Article.remove_description_footnotes(articles)

    paginator = Paginator(articles, page_size)
    page_obj = paginator.get_page(page_number)
    page_range = page_obj.paginator.get_elided_page_range(
        page_number, on_each_side=PAGINATOR_ON_EACH_SIDE, on_ends=PAGINATOR_ON_ENDS,
    )
    page_range_bottom = page_obj.paginator.get_elided_page_range(
        page_number, on_each_side=PAGINATOR_ON_EACH_SIDE, on_ends=PAGINATOR_ON_ENDS,
    )
    return render(request, 'patterns/pages/collections/collections-search.html', {
        'query': query_string,
        'tabs': collections_authors_tabs(url=reverse('encyc-articles-topic')),
        'tags': tags_collections_topics(topic),
        'page_obj': page_obj,
        'page_range': page_range,
        'page_range_bottom': page_range_bottom,
    })

"""
from django.db.models.functions import Left
from encyclopedia.models import Article
for a in Article.objects.order_by('title').annotate(initial=Left('title', 1)).prefetch_related('tags').values('initial','title','description','tags').all():
    a

TODO only get published Articles
TODO prefetch_related() to get tags?
TODO optimize image query https://docs.wagtail.org/en/stable/advanced_topics/images/renditions.html
"""

@cache_page(settings.CACHE_TIMEOUT)
def authors(request, template_name='encyclopedia/authors.html'):
    initial = request.GET.get('initial', None)
    if initial and initial.lower() == 'all':
        initial = None
    page_size = int(request.GET.get('pagesize', 30))
    page_number = int(request.GET.get('page', 1))

    if initial:
        authors = Author.objects.filter(family_name__istartswith=initial)
    else:
        authors = Author.objects.all()
    authors = authors.order_by('family_name','given_name')

    paginator = Paginator(authors, page_size)
    page_obj = paginator.get_page(page_number)
    page_range = page_obj.paginator.get_elided_page_range(
        page_number, on_each_side=PAGINATOR_ON_EACH_SIDE, on_ends=PAGINATOR_ON_ENDS,
    )
    page_range_bottom = page_obj.paginator.get_elided_page_range(
        page_number, on_each_side=PAGINATOR_ON_EACH_SIDE, on_ends=PAGINATOR_ON_ENDS,
    )
    return render(request, 'patterns/pages/collections/collections--authors.html', {
        'tabs': collections_authors_tabs(url=reverse('encyc-authors')),
        'tags': tags_authors_az(initial),
        'page_obj': page_obj,
        'page_range': page_range,
        'page_range_bottom': page_range_bottom,
    })

@cache_page(settings.CACHE_TIMEOUT)
def author(request, slug):
    author = Author.objects.get(slug=slug)
    # TODO optimize query (restrict fields)
    articles = author.article_set.live()
    Article.remove_description_footnotes(articles)
    return render(request, 'patterns/pages/collections/collections--author.html', {
        'tabs': collections_authors_tabs(url=reverse('encyc-authors')),
        'author': author,
        'collections': articles,
    })


def collections_authors_tabs(url):
    """Return tabs for collection navigation pages
    """
    tabs = [
        {'label': 'Articles by Topic', 'url': reverse('encyc-articles-topic')},
        {'label': 'Articles by A-Z',   'url': reverse('encyc-articles-az')},
        {'label': 'Authors by A-Z',    'url': reverse('encyc-authors')},
    ]
    for tab in tabs:
        if tab['url'] == url:
            tab['active'] = True
    return tabs

def tags_collections_topics(topic=None):
    """
    [
        {'id':'all', 'name':'All'}, {'id':'arts', 'name':'Arts'}, {'id':'camps', 'name':'Camps'}, ...
    ]
    """
    tags = topics_items()
    tags.insert(0, {
        'id':'all', 'title':'All', 'url':reverse('encyc-articles-topic'), 'active':True
    })
    if topic:
        topic = slugify(topic)
        for tag in tags:
            if tag['id'] == topic:
                tag['active'] = True
                tags[0].pop('active')
    return tags

def tags_collections_az(initial=None):
    """
    [
        {'name': 'All'}, {'name': '1-10'}, {'name': 'A'}, {'name': 'B'}, ...
    ]
    """
    tags = [
        {'name':'All', 'active':True},
        {'name':'1-10'},
    ]
    [tags.append({'name':char}) for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
    if initial:
        if initial.isdigit():
            tags[1]['active'] = True
            tags[0].pop('active')
        else:
            initial = initial.upper()
            for tag in tags:
                if tag['name'].upper() == initial:
                    tag['active'] = True
                    tags[0].pop('active')
    return tags

def tags_authors_az(initial=None):
    """
    [
        {'name': 'All'}, {'name': '1-10'}, {'name': 'A'}, {'name': 'B'}, ...
    ]
    """
    tags = [
        {'name':'All', 'active':True},
    ]
    [tags.append({'name':char}) for char in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
    if initial:
        initial = initial.upper()
        for tag in tags:
            if tag['name'].upper() == initial:
                tag['active'] = True
                tags[0].pop('active')
    return tags

def author_images():
    c = Collection.objects.get(name='Authors')
    images = {
        image.title: image
        for image in Image.objects.filter(collection=c)
    }
    return images


def redirect_wiki(request, title):
    """Redirect links between articles TEMPORARY
    TODO get links right in migration so we don't need this
    """
    url = f"/encyclopedia/{title}/"
    return HttpResponseRedirect(url, preserve_request=True)

def redirect_source(request, encyclopedia_id):
    """Redirect old PSMS Source links to the Article they appear in
    """
    source = get_object_or_404(Source, encyclopedia_id=encyclopedia_id)
    # TODO redirection may not if Source.headword differs from Article.title
    # TODO example: Miné Okubo
    article = get_object_or_404(Article, title=source.headword)
    return HttpResponseRedirect(article.url, preserve_request=True)
