from django.conf import settings
from django.contrib import admin

from .models import MediawikiWagtail


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
