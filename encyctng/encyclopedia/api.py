from datetime import datetime
from typing import Literal

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify

from ninja import Field, ModelSchema, NinjaAPI, Router

from editors.models import Author
from .models import Article
from .topics import topics_items

router = Router()


@router.get("/")
def index(request: "HttpRequest"):
    return {
        "articles": reverse_lazy('api-1.0.0:articles-list'),
        "authors": reverse_lazy('api-1.0.0:authors-list'),
        "topics": reverse_lazy('api-1.0.0:topics-list'),
        #"events": "http://encyclopedia.densho.org/api/0.1/events/"
    }


class BaseArticleSchema(ModelSchema):
    url: str = Field(None, alias="get_url")

    class Meta:
        model = Article
        model_fields = [
            "title",
            "slug",
        ]

@router.get("/articles/", response=list[BaseArticleSchema], url_name='articles-list')
def articles_list(request: "HttpRequest"):
    return Article.objects.live().public().exclude(id=1)

@router.get("/articles/{slug}", url_name='article-detail')
def article(request, slug: str):
    article = Article.objects.get(slug=slug)
    return {
        "url_title": article.slug,
        "title_sort": None,
        "links": {
            "json": reverse_lazy("api-1.0.0:article-detail", args=[article.slug]),
            "html": article.url,
        },
        "modified": article.last_published_at,
        "title": article.title,
        "categories": [tag.name for tag in article.tags.all()],
        "sources": [],
        "coordinates": {},
        "ddr_topic_terms": article.related_media()[:3],
        "authors": [
            author.get_absolute_url() for author in article.authors_all()
        ],
        "description": article.description,
    }


class BaseAuthorSchema(ModelSchema):
    url: str = Field(None, alias="get_absolute_url")

    class Meta:
        model = Author
        model_fields = [
            "display_name",
            #"slug",
        ]

@router.get("/authors/", response=list[BaseAuthorSchema], url_name='authors-list')
def authors_list(request: "HttpRequest"):
    return Author.objects.all()

@router.get("/authors/{slug}", url_name='author-detail')
def author(request, slug: str):
    author = Author.objects.get(slug=slug)
    data = {
        "title_sort": author.title_sort(),
        "links": {
            "json": reverse_lazy("api-1.0.0:author-detail", args=[author.id]),
            "html": author.get_absolute_url(),
        },
        #"modified": "2014-09-22T18:35:18",
        "title": author.title(),
        "description": author.description,
        "articles": [
            {
                'url': reverse_lazy("api-1.0.0:article-detail", args=[article.slug]),
                'title': article.title,
            }
            for article in author.article_set.all()
        ]
    }
    return data

@router.get("/topics/", url_name='topics-list')
def topics_list(request: "HttpRequest"):
    data = [
        {
            'links': {
                'json': reverse_lazy(
                    "api-1.0.0:topics-detail",
                    args=[slugify(topic['title'])]
                ),
                'html': reverse('encyc-articles-topic', args=[topic['title']]),
            },
            'title': topic['title'],
        }
        for topic in topics_items()
    ]
    return data

@router.get("/topics/{slug}", response=list[BaseArticleSchema], url_name='topics-detail')
def topic(request, slug: str):
    return Article.objects.live().public().exclude(id=1).order_by('title').filter(tags__name__in=[slug])
