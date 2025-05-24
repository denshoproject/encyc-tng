from django.db import models
from django.urls import reverse
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.images.models import Image
from wagtail.models.media import Collection
from wagtail.snippets.models import register_snippet


@register_snippet
class Author(models.Model):
    family_name = models.CharField(max_length=255)
    given_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    description = RichTextField(blank=True, null=True)

    panels = [
        FieldPanel('family_name'),
        FieldPanel('given_name'),
        FieldPanel('display_name'),
        FieldPanel('description'),
    ]

    class Meta:
        verbose_name_plural = 'Authors'

    def __str__(self):
        return f"{self.display_name}"

    def get_absolute_url(self):
        return reverse('encyc-author', args=[self.id])

    def image(self):
        c = Collection.objects.get(name='Authors')
        try:
            i = Image.objects.get(collection=c, title=self.display_name)
        except:
            i = None
        return i
