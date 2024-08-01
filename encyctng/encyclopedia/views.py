from django.http import Http404
from django.shortcuts import render

from editors.models import Author
from encyclopedia.models import Article


def contents(request):
    return render(request,  'encyclopedia/contents.html', {
        'articles': Article.objects.filter(live=True).order_by('title'),
    })

def authors(request, template_name='encyclopedia/authors.html'):
    return render(request, template_name, {
        'authors': Author.objects.all().order_by('family_name','given_name'),
    })

def author(request, author_id):
    # TODO use slug instead of author_id
    author = Author.objects.get(id=author_id)
    articles = author.article_set.all()
    return render(request, 'encyclopedia/author-detail.html', {
        'author': author,
        'articles': articles,
    })
