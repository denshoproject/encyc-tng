from django.http import Http404
from django.shortcuts import render
from wagtail.documents.models import Document
from wagtail.images.models import Image
from wagtailmedia.models import Media

from editors.models import Author
from encyclopedia.models import Article


def articles(request):
    return render(request,  'encyclopedia/articles.html', {
        'articles': Article.objects.filter(live=True).order_by('title'),
    })

BLOCK_TYPES = ['imageblock','documentblock','videoblock']
BLOCKTYPE_OBJECTTYPE = {
    'imageblock': 'image',
    'documentblock': 'document',
    'videoblock': 'video',
}
OBJECTTYPE_BLOCKTYPE = {
    'image': 'imageblock',
    'document': 'documentblock',
    'video': 'videoblock',
}

def link_sources_articles():
    sources_articles = {'image': {}, 'document': {}, 'video': {}}
    from encyclopedia.models import Article
    for article in Article.objects.all():
        blocks = list(filter(lambda b: b.block_type in BLOCK_TYPES, article.body))
        for block in blocks:
            object_type = BLOCKTYPE_OBJECTTYPE[block.block_type]
            obj = block.value[object_type]
            sources_articles[object_type][str(obj.id)] = article.id
            #if block.block_type == 'imageblock':
            #    image = block.value['image']
            #    sources_articles['image'][str(image.id)] = article.id
            #elif block.block_type == 'documentblock':
            #    document = block.value['document']
            #    sources_articles['document'][str(document.id)] = article.id
            #elif block.block_type == 'videoblock':
            #    video = block.value['video']
            #    sources_articles['video'][str(video.id)] = article.id
    return sources_articles

def source_article_block(source_type, source_id, article):
    for block in article.body:
        if BLOCKTYPE_OBJECTTYPE[block.block_type] == source_type:
            obj = block.value[source_type]
            if obj.id == source_id:
                return block
    return None

def source(request, source_type, source_id):
    """
    # cannot search for source_id in Article.body (only stores pk)
    # Instead search for Image,Media,Document with title containing source_id
    # then get Article from that

from wagtail.images.models import Image
from encyclopedia.models import Article
source_id = 'en-denshopd-i93-00023-1'
images = Image.objects.filter(title__contains=source_id)
source = images[0]

    """
    if   source_type == 'image':    source = Image.objects.get(id=source_id)
    elif source_type == 'document': source = Document.objects.get(id=source_id)
    elif source_type == 'video':    source = Media.objects.get(id=source_id)
    article_id = link_sources_articles()[source_type][str(source.id)]
    article = Article.objects.get(id=article_id)
    block = source_article_block(source_type, source_id, article)
    # IDEA ArticleMedia.metadata(source)
    template = f"encyclopedia/source-{source_type}.html"
    #assert 0
    return render(request, template, {
        'source_type': source_type,
        #'source': source,
        'article': article,
        'source': block.value,
    })

def authors(request, template_name='encyclopedia/authors.html'):
    return render(request, template_name, {
        'authors': Author.objects.all().order_by('family_name','given_name'),
    })

def author(request, author_id):
    # TODO use slug instead of author_id
    author = Author.objects.get(id=author_id)
    articles = author.article_set.all()
    return render(request, 'encyclopedia/author-detail.html', {
        'author': author,
        'articles': articles,
    })
