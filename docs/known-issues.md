# Known Issues and Current Changes

## Middleware Updates - Media Wiki Error

File: `encyctng/encyclopedia/middleware.py`

1. Comment out line 5:

```python
# from encyclopedia.models import load_mediawiki_titles
```

2. Update line 27:

```python
legacy_page = None
```

File: `encyctng/encyclopedia/models.py`

1. Remove line 24:

```python
from encyc import wiki
```

2. Update MediaWiki titles function to:

```python
def load_mediawiki_titles():
    """Map MediaWiki titles to original title text and to Wagtail slug titles"""
    key = 'mediawiki-titles'
    results = cache.get(key)
    if not results:
        from encyc import wiki
        mw = wiki.MediaWiki()
        results = {
            page.normalize_title(page.page_title): {
                'title': page.page_title,
                'slug': slugify(page.page_title)
            }
            for page in [page for page in mw.mw.allpages()]
        }
        cache.set(key, results, settings.CACHE_TIMEOUT)
    return results
```
