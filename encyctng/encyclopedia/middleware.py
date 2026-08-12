from encyclopedia.models import Article


class ArticleMiddleware:
    SITE_DOMAINS = []

    def __init__(self, get_response):
        self.get_response = get_response
        self.SITE_DOMAINS = ['encyctng.lan']

    def __call__(self, request):
        response = self.get_response(request)
        # ignore anything that is not an Article
        try:
            assert isinstance(response.context_data['page'], Article)
        except AttributeError:
            return response
        except AssertionError:
            return response

        return response
