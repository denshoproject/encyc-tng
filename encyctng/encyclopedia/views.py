from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import cache_page

from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtailmedia.models import Media
from wagtail.models.media import Collection

from editors.models import Author
from encyclopedia.models import Article, ArticleSources


# home/index page comes from home.models.HomePage

#@cache_page(settings.CACHE_TIMEOUT)
def browse(request):
    topics = {
        'title': 'Browse Topics',
        'items': topics_items(),
    }
    return render(request, 'patterns/pages/topic_listing/topic_listing.html', {
        'topics': topics,
    })

#@cache_page(settings.CACHE_TIMEOUT)
def articles_topic(request, topic=None):
    topic = request.GET.get('topic')
    page_size = int(request.GET.get('pagesize', 30))
    page_number = int(request.GET.get('page', 1))
    # TODO order by topic, then title
    if topic:
        articles = Article.objects.order_by('title').all()
    else:
        articles = Article.objects.order_by('title').all()
    paginator = Paginator(articles, page_size)
    page_obj = paginator.get_page(page_number)
    page_range = page_obj.paginator.get_elided_page_range(page_number)
    return render(request, 'patterns/pages/collections/collections.html', {
        'tabs': collections_authors_tabs(url='/articles-topic/'),
        'tags': tags_collections_topics(topic),
        'page_obj': page_obj,
        'page_range': page_range,
    })

#@cache_page(settings.CACHE_TIMEOUT)
def articles_az(request):
    initial = request.GET.get('initial')
    page_size = int(request.GET.get('pagesize', 30))
    page_number = int(request.GET.get('page', 1))
    if initial:
        articles = Article.objects.order_by('title').filter(title__istartswith=initial)
    else:
        articles = Article.objects.order_by('title').all()
    paginator = Paginator(articles, page_size)
    page_obj = paginator.get_page(page_number)
    page_range = page_obj.paginator.get_elided_page_range(page_number)
    return render(request, 'patterns/pages/collections/collections--a-z.html', {
        'tabs': collections_authors_tabs(url='/articles-az/'),
        'tags': tags_collections_az(initial),
        'page_obj': page_obj,
        'page_range': page_range,
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

#@cache_page(settings.CACHE_TIMEOUT)
def authors(request, template_name='encyclopedia/authors.html'):
    initial = request.GET.get('initial')
    page_size = int(request.GET.get('pagesize', 30))
    page_number = int(request.GET.get('page', 1))
    if initial:
        authors = Author.objects.order_by('family_name','given_name').filter(family_name__istartswith=initial)
    else:
        authors = Author.objects.order_by('family_name','given_name').all()
    paginator = Paginator(authors, page_size)
    page_obj = paginator.get_page(page_number)
    page_range = page_obj.paginator.get_elided_page_range(page_number)
    return render(request, 'patterns/pages/collections/collections--authors.html', {
        'tabs': collections_authors_tabs(url='/authors/'),
        'tags': tags_authors_az(initial),
        'page_obj': page_obj,
        'page_range': page_range,
    })

#@cache_page(settings.CACHE_TIMEOUT)
def author(request, author_id):
    # TODO use slug instead of author_id
    author = Author.objects.get(id=author_id)
    # TODO optimize query (restrict fields)
    articles = author.article_set.all()
    return render(request, 'patterns/pages/collections/collections--author.html', {
        'tabs': collections_authors_tabs(url='/authors/'),
        'author': author,
        'collections': articles,
    })

def source(request, source_type, source_id):
    """Display Primary Source with captions from Article(s) it appears in
    """
    if   source_type == 'image':    source = Image.objects.get(id=source_id)
    elif source_type == 'document': source = Document.objects.get(id=source_id)
    elif source_type == 'video':    source = Media.objects.get(id=source_id)
    articles_blocks = ArticleSources.source_article_blocks(source)
    # IDEA ArticleMedia.metadata(source)
    template = f"encyclopedia/source-{source_type}.html"
    return render(request, template, {
        'source_type': source_type,
        #'source': source,
        'source': source,
        'articles_blocks': articles_blocks,
    })


def collections_authors_tabs(url):
    """Return tabs for collection navigation pages
    """
    tabs = [
        {'label': 'Articles by Topic', 'url': '/articles-topic/'},
        {'label': 'Articles by A-Z',   'url': '/articles-az/'},
        {'label': 'Authors by A-Z',    'url': '/authors/'},
    ]
    for tab in tabs:
        if tab['url'] == url:
            tab['active'] = True
    return tabs

def topics_items():
    from wagtail.images.models import Image
    from wagtail.models.media import Collection
    c = Collection.objects.get(name='Topics')
    images = {
        image.title: image
        for image in Image.objects.filter(collection=c)
    }
    topics = [
        {'articles': 453, 'image': '', 'url': '/articles-topic/arts/',         'title': 'Arts'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/camps/',        'title': 'Camps'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/chroniclers/',  'title': 'Chroniclers'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/communities/',  'title': 'Communities'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/definitions/',  'title': 'Definitions'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/events/',       'title': 'Events'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/legal/',        'title': 'Legal'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/military/',     'title': 'Military'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/newspapers/',   'title': 'Newspapers'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/organizations/','title': 'Organizations'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/people/',       'title': 'People'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/post-war/',     'title': 'Post-War'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/pre-war/',      'title': 'Pre-War'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/redress/',      'title': 'Redress'},
        {'articles': 453, 'image': '', 'url': '/articles-topic/resettlement/', 'title': 'Resettlement'},
    ]
    for topic in topics:
        if images.get(topic['title']):
            topic['image'] = images.pop(topic['title'])
    return topics

def tags_collections_topics(topic=None):
    """
    [
        {'name': 'All'}, {'name': 'Arts'}, {'name': 'Camps'}, ...
    ]
    """
    tags = [
        {'name': item['title']}
        for item in topics_items()
    ]
    tags.insert(0, {'name':'All', 'active':True})
    if topic:
        topic = topic.capitalize()
        for tag in tags:
            if tag['name'].capitalize() == topic:
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
