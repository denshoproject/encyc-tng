from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render
from django.urls import reverse

from encyclopedia.models import load_mediawiki_titles


class RedirectLegacyURLsMiddleware:
    """Try to redirect legacy URLs to new ones
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404:
            
            # get what might be an article title
            title = request.META['PATH_INFO']
            # shave off preceding and trailing slashes, if any
            if title[0] == '/':
                title = title[1:]
            if title[-1] == '/':
                title = title[:-1]
            # redirec if it matches a legacy page
            legacy_page = load_mediawiki_titles().get(title)
            if legacy_page:
                return HttpResponsePermanentRedirect(
                    f"/wiki/{legacy_page['slug']}/"
                )

        # not a 404 or not a legacy page
        return response
