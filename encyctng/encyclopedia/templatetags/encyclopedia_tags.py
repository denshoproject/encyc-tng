from django import template
from django.conf import settings
from django.utils.text import slugify

from encyclopedia import databoxes

register = template.Library()


@register.simple_tag
def article_table_of_contents(article):
    """Generate Table-of-Contents block from article headings"""
    template_name = 'patterns/components/table_of_contents/table_of_contents.html'
    return template.loader.get_template(template_name).render({
        'table_of_contents': article.table_of_contents(),
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
