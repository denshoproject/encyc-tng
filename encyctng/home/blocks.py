from wagtail.blocks import (
    CharBlock, TextBlock, URLBlock, StructBlock, StructValue,
)
from wagtail.images.blocks import ImageBlock as WagtailImageBlock


class HomepageCarouselImageBlockStructValue(StructValue):
    def modal(self):
        return {
            'image': self.get('image'),
            'id': self.get('id'),
            'url': 'article_url',
            'title': self.get('article_title'),
            'description': self.get('description'),
        }

class HomepageCarouselImageBlock(StructBlock):
    image = WagtailImageBlock(required=True)
    article_title = CharBlock(required=False)
    article_url = URLBlock(required=False)
    description = TextBlock(required=False)

    class Meta:
        icon = 'image'
        label = 'Image'
        template = 'patterns/components/full_width_image/full_width_image.html'
        value_class = HomepageCarouselImageBlockStructValue
