from urllib.parse import urlparse, urlunparse


def relativize_site_url(url, site_domains):
    """Make an absolute URL relative if domain in SITE_DOMAINS
    """
    scheme,netloc,path,params,query,fragment = urlparse(url)
    if netloc in site_domains:
        return urlunparse(('','',path,params,query,fragment))
    return url
