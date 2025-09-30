"""
URL configuration for encyctng project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from ninja import NinjaAPI
from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from encyclopedia import urls as encyclopedia_urls

urlpatterns = []

api = NinjaAPI(
    title='Densho Encyclopedia',
    description='DESCRIPTION TEXT GOES HERE',
    openapi_extra={
        "info": {
            "termsOfService": "https://example.com/terms/",
        }
    },
)
api.add_router('/', 'encyclopedia.api.router')

# Disable this in production!
if apps.is_installed("pattern_library"):
    urlpatterns += [
        path("pattern-library/", include("pattern_library.urls")),
    ]

urlpatterns += [
    path("api/1.0/", api.urls),
    path('admin/', admin.site.urls),
    path('cms/', include(wagtailadmin_urls)),
    path('sitemap.xml', sitemap),
    path('documents/', include(wagtaildocs_urls)),
    path('', include(encyclopedia_urls)), # match encyc URLs before wagtail ones
    path('', include(wagtail_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
