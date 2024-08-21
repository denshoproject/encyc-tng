from django import template
from django.conf import settings
from django.utils.text import slugify

from encyclopedia import databoxes

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

@register.simple_tag
def databox(article):
    if databoxes.ARTICLE_CLASS_DATABOX.get(article.__class__.__name__):
        databox_name = databoxes.ARTICLE_CLASS_DATABOX[article.__class__.__name__]
        template_name = databoxes.DATABOXES[databox_name]['templatetag']
        return template.loader.get_template(template_name).render({
            'article': article,
        })
    return ''
