import random
import string
from urllib.parse import urlparse, urlunparse


def random_string(length=10):
    """Generate a random string of the requested length"""
    return ''.join(
        random.choices(string.ascii_letters + string.digits, k=length)
    )

def relativize_site_url(url, site_domains):
    """Make an absolute URL relative if domain in SITE_DOMAINS
    """
    scheme,netloc,path,params,query,fragment = urlparse(url)
    if netloc in site_domains:
        return urlunparse(('','',path,params,query,fragment))
    return url
