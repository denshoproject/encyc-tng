from django.conf import settings

def sitewide(request):
    return {
        'request': request,
        'MEDIA_URL': settings.MEDIA_URL,
        'STATIC_URL': settings.STATIC_URL,
    }
