from bs4 import BeautifulSoup
from bs4.formatter import HTMLFormatter
from wagtail.models.sites import Site

from encyclopedia.models import Article
from encyclopedia import footnotes

FORMATTER = HTMLFormatter(indent=4)


class ArticleMiddleware:
    SITE_DOMAINS = []

    def __init__(self, get_response):
        self.get_response = get_response
        self.SITE_DOMAINS = [
            s.hostname for s in Site.objects.all() if s.hostname != 'localhost'
        ]

    def __call__(self, request):
        response = self.get_response(request)
        # ignore anything that is not an Article
        if request.META['PATH_INFO'].startswith('/cms/'):
            return response
        if request.META['PATH_INFO'].startswith('/api/'):
            return response
        try:
            assert isinstance(response.context_data['page'], Article)
        except AttributeError:
            return response
        except AssertionError:
            return response

        html = footnotes.fix_ref_tags(response.rendered_content)
        soup = BeautifulSoup(html, 'lxml')
        # make internal URLs /relative/
        soup = Article.rewrite_internal_urls(soup, self.SITE_DOMAINS)
        # do footnotes
        soup = footnotes.rewrite_body(soup)
        response.content = soup.prettify(formatter=FORMATTER)

        return response
