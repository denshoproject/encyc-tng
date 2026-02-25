from datetime import datetime
from typing import Literal

from django.http import Http404, HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify

from ninja import Field, ModelSchema, NinjaAPI, Router

from editors.models import Author
from .models import Article
from .topics import topics_items


class BaseArticleSchema(ModelSchema):
    url: str = Field(None, alias="get_url")

    class Meta:
        model = Article
        fields = [
            "title",
            "slug",
        ]


class BaseAuthorSchema(ModelSchema):
    url: str = Field(None, alias="get_absolute_url")

    class Meta:
        model = Author
        fields = [
            "display_name",
            #"slug",
        ]


def api_stub(request):
    return HttpResponseRedirect(reverse_lazy('api-1.0.0:api-root'))

router = Router()

@router.get("/")
def index(request: "HttpRequest"):
    return {
        "docs": request.build_absolute_uri(reverse_lazy('api-1.0.0:openapi-view')),
        "articles": request.build_absolute_uri(reverse_lazy('api-1.0.0:articles-list')),
        "topics": request.build_absolute_uri(reverse_lazy('api-1.0.0:topics-list')),
        "authors": request.build_absolute_uri(reverse_lazy('api-1.0.0:authors-list')),
        #"events": "http://encyclopedia.densho.org/api/0.1/events/"
    }

@router.get("/topics/", url_name='topics-list')
def topics_list(request: "HttpRequest"):
    return [
        {
            'url': request.build_absolute_uri(
                reverse_lazy("api-1.0.0:topics-detail", args=[slugify(topic['title'])])
            ),
            'title': topic['title'],
        }
        for topic in topics_items()
    ]

@router.get("/topics/{slug}", url_name='topics-detail')
def topic(request, slug: str):
    articles = Article.objects.live().public().exclude(id=1).order_by('title')
    articles = articles.filter(tags__name__in=[slug])
    return [
        {
            "url": request.build_absolute_uri(
                reverse_lazy("api-1.0.0:article-detail", args=[article.slug])
            ),
            "title": article.title,
        }
        for article in articles
    ]

@router.get("/articles/", url_name='articles-list')
def articles_list(request: "HttpRequest"):
    articles = Article.objects.live().public().exclude(id=1).order_by('title')
    return [
        {
            "url": request.build_absolute_uri(
                reverse_lazy("api-1.0.0:article-detail", args=[article.slug])
            ),
            "title": article.title,
        }
        for article in articles
    ]

@router.get("/articles/{slug}", url_name='article-detail')
def article(request, slug: str):
    try:
        article = Article.objects.get(slug=slug, live=True)
    except Article.DoesNotExist:
        raise Http404('Article matching query does not exist.')
    return {
        "url_title": article.slug,
        "title_sort": None,
        "links": {
            "json": request.build_absolute_uri(
                reverse_lazy("api-1.0.0:article-detail", args=[article.slug])
            ),
            "html": article.url,
        },
        "modified": article.last_published_at,
        "title": article.title,
        "topics": [
            tag.name for tag in article.tags.all()
        ],
        "sources": [],
        "coordinates": {},
        "ddr_topic_terms": article.related_media()[:3],
        "authors": [
            request.build_absolute_uri(author.get_absolute_url())
            for author in article.authors_all()
        ],
        #"description": article.description,
    }

@router.get("/authors/", url_name='authors-list')
def authors_list(request: "HttpRequest"):
    return [
        {
            'url': request.build_absolute_uri(
                reverse_lazy("api-1.0.0:author-detail", args=[author.slug])
            ),
            'title': author.title(),
        }
        for author in Author.objects.all()
    ]

@router.get("/authors/{slug}", url_name='author-detail')
def author(request, slug: str):
    author = Author.objects.get(slug=slug)
    data = {
        "title_sort": author.title_sort(),
        "links": {
            "json": request.build_absolute_uri(
                reverse_lazy("api-1.0.0:author-detail", args=[author.slug])
            ),
            "html": request.build_absolute_uri(
                author.get_absolute_url()
            ),
        },
        #"modified": "2014-09-22T18:35:18",
        "title": author.title(),
        "description": author.description,
        "articles": [
            {
                'url': request.build_absolute_uri(
                    reverse_lazy("api-1.0.0:article-detail", args=[article.slug])
                ),
                'title': article.title,
            }
            for article in author.article_set.all()
        ]
    }
    return data
