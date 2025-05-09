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
def articles(request):
    return render(request,  'encyclopedia/articles.html', {
        'initials_articles': Article.articles_by_initial(),
    })

#@cache_page(settings.CACHE_TIMEOUT)
def topics(request):
    return render(request,  'encyclopedia/topics.html', {
        'tags_articles': Article.articles_by_tag(),
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
        'collections': authors,
        'tags': collect_tags(authors),
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


def collect_tags(items):
    """
    [
        {'name': 'All'}, {'name': '1-10'}, {'name': 'A'}, {'name': 'B'}, ...
    ]
    """
    initials = sorted(set([item['initial'] for item in items]))
    # TODO replace all digits with '1-10'
    initials.insert(0, 'All')
    return [{'name':initial} for initial in initials]
