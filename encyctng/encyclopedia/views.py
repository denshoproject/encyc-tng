from django.http import Http404
from django.shortcuts import render

from encyclopedia.models import Article


def contents(request):
    return render(request,  'encyclopedia/contents.html', {
        'articles': Article.objects.filter(live=True).order_by('title'),
    })
