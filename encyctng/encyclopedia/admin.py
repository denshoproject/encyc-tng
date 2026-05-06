from django.conf import settings
from django.contrib import admin

from .models import ArticleTopic, MediawikiWagtail


@admin.register(ArticleTopic)
class ArticleTopicAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': (
            'id',
            'name',
        )}),
    )
    list_display = (
        'id',
        'name',
    )
    list_display_links = ['id',]
    ordering = ['id', 'name',]
    list_filter = []
    search_fields = []


@admin.register(MediawikiWagtail)
class MediawikiWagtailAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': (
            'mediawiki_url',
            'wagtail_slug',
        )}),
    )
    list_display = (
        'mediawiki_url',
        'wagtail_slug',
    )
    list_display_links = ['mediawiki_url',]
    ordering = ['mediawiki_url', 'wagtail_slug',]
    list_filter = []
    search_fields = [
        'mediawiki_url',
        'wagtail_slug',
    ]
