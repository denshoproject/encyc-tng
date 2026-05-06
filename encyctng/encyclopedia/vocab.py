import json
from pathlib import Path
import random
from urllib.parse import unquote

from django.conf import settings
from django.utils.text import slugify


class Topics():
    """Topic terms from densho-vocab/api/0.2/topics.json

    TODO needs caching and optimization!
    """
    ids_terms = {}
    slugs_termids = {}

    def __init__(self):
        topics = _load_topics(path=settings.DDR_VOCAB_TOPICS_PATH)
        self.ids_terms = _terms_by_id(topics)
        self.slugs_termids = _term_ids_by_slug(topics)

    def term(self, id: int) -> dict:
        return self.ids_terms[id]

    def article_terms(self, title: str) -> int:
        slug = slugify(title)
        try:
            term_ids = self.slugs_termids[slug]
        except KeyError:
            return []
        terms = []
        for tid in term_ids:
            try:
                term = self.ids_terms[tid]
                terms.append(term)
            except KeyError:
                pass
        return terms


def _load_topics(path):
    with Path(path).open('r') as f:
        topics = json.loads(f.read())
    return topics

def _terms_by_id(topics) -> dict:
    return {term['id']: term for term in topics['terms']}

def _term_ids_by_slug(topics) -> dict:
    slugs_termids = {}
    for term in topics['terms']:
        for url in term['encyc_urls']:
            slug = slugify(unquote(url))
            if not slugs_termids.get(slug):
                slugs_termids[slug] = []
            slugs_termids[slug].append(term['id'])
    return slugs_termids
