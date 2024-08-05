from django import template
from django.conf import settings
from django.utils.text import slugify

register = template.Library()


@register.simple_tag
def article_toc(article):
    """Generate Table-of-Contents block from article headings"""
    headings = [
        block.value for block in article.body if block.block_type in ['heading']
    ]
    for heading in headings:
        heading['url'] = f"#{slugify(heading['heading_text'])}"
    return template.loader.get_template('encyclopedia/article-toc.html').render({
        'headings': headings,
    })
