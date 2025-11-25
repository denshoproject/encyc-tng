from django.shortcuts import render

from .models import SitePage


#@cache_page(settings.CACHE_TIMEOUT)
def about(request):
    page = SitePage.objects.get(title='About the Encyclopedia')
    return render(request, page.template, {'page':page})

def history(request):
    page = SitePage.objects.get(title='About the Incarceration')
    return render(request, page.template, {'page':page})

def terminology(request):
    page = SitePage.objects.get(title='Do Words Matter?')
    return render(request, page.template, {'page':page})

def timeline(request):
    page = SitePage.objects.get(title='Timeline')
    return render(request, page.template, {'page':page})
