from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtailmedia.models import Media

from editors.models import Author
from encyclopedia.models import Article, ArticleSources


#@cache_page(settings.CACHE_TIMEOUT)
def index(request):
    hero = {
        'title': 'Discover the history of the Japanese American incarceration during WWII',
        'actions': [
            {'text': 'Browse by Topic', 'url': '/articles-topic/'},
            {'text': 'Browse by A-Z', 'url': '/articles-az/'},
        ]
    }
    topics = {
        'title': 'Browse Topics',
        'items': topics_items(),
    }
    return render(request, 'patterns/pages/home_page/home_page.html', {
        'hero': hero,
        'topics': topics,
    })

#@cache_page(settings.CACHE_TIMEOUT)
def articles_topic(request):
    articles = [
        {
            #'image': None,
            'type': 'Article',
            'initial': article.title[0].upper(),
            'title': article.title,
            'url': article.url,
            'description': article.description,
            'tags': [
                {'name': tag.name, 'url': f"/tags/{tag.name}/"}
                for tag in article.tags.all()
            ]
        }
        # TODO optimize query (restrict fields)
        for article in Article.objects.all()[:25]
        if getattr(article, 'description')
    ]
    return render(request, 'patterns/pages/collections/collections.html', {
        'tabs': collections_authors_tabs(url='/articles-topic/'),
        'collections': articles,
        'tags': tags_collections_topics(articles),
    })

#@cache_page(settings.CACHE_TIMEOUT)
def articles_az(request):
    articles = [
        {
            #'image': None,
            'type': 'Article',
            'initial': article.title[0].upper(),
            'title': article.title,
            'url': article.url,
            'description': article.description,
            'tags': [
                {'name': tag.name, 'url': f"/tags/{tag.name}/"}
                for tag in article.tags.all()
            ]
        }
        # TODO optimize query (restrict fields)
        for article in Article.objects.all()[:25]
        if getattr(article, 'description')
    ]
    return render(request, 'patterns/pages/collections/collections--a-z.html', {
        'tabs': collections_authors_tabs(url='/articles-az/'),
        'collections': articles,
        'tags': tags_collections_az(articles),
    })

#@cache_page(settings.CACHE_TIMEOUT)
def authors(request, template_name='encyclopedia/authors.html'):
    authors = [
        {
            #'image': None,
            'initial': author.family_name[0],
            'title': author.display_name,
            'url': author.get_absolute_url(),
            'role': 'ROLE',
        }
        # TODO optimize query (restrict fields)
        for author in Author.objects.all()
    ]
    return render(request, 'patterns/pages/collections/collections--authors.html', {
        'tabs': collections_authors_tabs(url='/authors/'),
        'collections': authors,
        'tags': tags_authors_az(authors),
    })

#@cache_page(settings.CACHE_TIMEOUT)
def author(request, author_id):
    # TODO use slug instead of author_id
    author = Author.objects.get(id=author_id)
    # TODO optimize query (restrict fields)
    articles = author.article_set.all()
    return render(request, 'encyclopedia/author-detail.html', {
        'author': author,
        'articles': articles,
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
    return [
        {'articles': 453, 'image': '', 'title': 'Arts'},
        {'articles': 453, 'image': '', 'title': 'Camps'},
        {'articles': 453, 'image': '', 'title': 'Chroniclers'},
        {'articles': 453, 'image': '', 'title': 'Communities'},
        {'articles': 453, 'image': '', 'title': 'Definitions'},
        {'articles': 453, 'image': '', 'title': 'Events'},
        {'articles': 453, 'image': '', 'title': 'Legal'},
        {'articles': 453, 'image': '', 'title': 'Military'},
        {'articles': 453, 'image': '', 'title': 'Newspapers'},
        {'articles': 453, 'image': '', 'title': 'Organizations'},
        {'articles': 453, 'image': '', 'title': 'People'},
        {'articles': 453, 'image': '', 'title': 'Postwar'},
        {'articles': 453, 'image': '', 'title': 'Prewar'},
        {'articles': 453, 'image': '', 'title': 'Redress'},
        {'articles': 453, 'image': '', 'title': 'Resettlement'},
    ]

def tags_collections_topics(items):
    """
    [
        {'name': 'All'}, {'name': 'Arts'}, {'name': 'Camps'}, ...
    ]
    """
    tags = [
        {'name': item['title']}
        for item in topics_items()
    ]
    return tags

def tags_collections_az(items):
    """
    [
        {'name': 'All'}, {'name': '1-10'}, {'name': 'A'}, {'name': 'B'}, ...
    ]
    """
    initials = sorted(set([item['initial'] for item in items]))
    # TODO replace all digits with '1-10'
    return [{'name':initial} for initial in initials]

def tags_authors_az(items):
    """
    [
        {'name': 'All'}, {'name': '1-10'}, {'name': 'A'}, {'name': 'B'}, ...
    ]
    """
    initials = sorted(set([item['initial'] for item in items]))
    # TODO replace all digits with '1-10'
    return [{'name':initial} for initial in initials]
