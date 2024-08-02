from django.http import Http404
from django.shortcuts import render
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtailmedia.models import Media

from editors.models import Author
from encyclopedia.models import Article, ArticleSources


def articles(request):
    return render(request,  'encyclopedia/articles.html', {
        'initials_articles': Article.articles_by_initial(),
    })

def topics(request):
    return render(request,  'encyclopedia/topics.html', {
        'tags_articles': Article.articles_by_tag(),
    })

def source(request, source_type, source_id):
    """
    # cannot search for source_id in Article.body (only stores pk)
    # Instead search for Image,Media,Document with title containing source_id
    # then get Article from that

from wagtail.images.models import Image
from encyclopedia.models import Article
source_id = 'en-denshopd-i93-00023-1'
images = Image.objects.filter(title__contains=source_id)
source = images[0]

    """
    if   source_type == 'image':    source = Image.objects.get(id=source_id)
    elif source_type == 'document': source = Document.objects.get(id=source_id)
    elif source_type == 'video':    source = Media.objects.get(id=source_id)
    article_id = ArticleSources.link_sources_articles()[source_type][str(source.id)]
    article = Article.objects.get(id=article_id)
    block = ArticleSources.source_article_block(source_type, source_id, article)
    # IDEA ArticleMedia.metadata(source)
    template = f"encyclopedia/source-{source_type}.html"
    #assert 0
    return render(request, template, {
        'source_type': source_type,
        #'source': source,
        'article': article,
        'source': block.value,
    })

def authors(request, template_name='encyclopedia/authors.html'):
    return render(request, template_name, {
        'authors_articles': Article.articles_by_author(),
    })

def author(request, author_id):
    # TODO use slug instead of author_id
    author = Author.objects.get(id=author_id)
    articles = author.article_set.all()
    return render(request, 'encyclopedia/author-detail.html', {
        'author': author,
        'articles': articles,
    })
