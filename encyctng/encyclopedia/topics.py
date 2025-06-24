from django.urls import reverse

from wagtail.images.models import Image
from wagtail.models.media import Collection


def topics_items():
    c = Collection.objects.get(name='Topics')
    images = {
        image.title: image
        for image in Image.objects.filter(collection=c)
    }
    topics = [
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['arts']),         'title': 'Arts'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['camps']),        'title': 'Camps'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['chroniclers']),  'title': 'Chroniclers'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['communities']),  'title': 'Communities'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['definitions']),  'title': 'Definitions'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['events']),       'title': 'Events'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['legal']),        'title': 'Legal'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['military']),     'title': 'Military'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['newspapers']),   'title': 'Newspapers'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['organizations']),'title': 'Organizations'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['people']),       'title': 'People'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['post-war']),     'title': 'Post-War'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['pre-war']),      'title': 'Pre-War'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['redress']),      'title': 'Redress'},
        {'articles': 453, 'image': '', 'url': reverse('encyc-articles-topic',args=['resettlement']), 'title': 'Resettlement'},
    ]
    for topic in topics:
        if images.get(topic['title']):
            topic['image'] = images.pop(topic['title'])
    return topics
