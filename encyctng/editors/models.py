from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField
from wagtail.images.models import Image
from wagtail.models.media import Collection
from wagtail.snippets.models import register_snippet


@register_snippet
class Author(models.Model):
    slug = models.CharField(max_length=255, blank=True, null=True)
    family_name = models.CharField(max_length=255)
    given_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    description = RichTextField(blank=True, null=True)
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    panels = [
        FieldPanel('family_name'),
        FieldPanel('given_name'),
        FieldPanel('display_name'),
        FieldPanel('description'),
        FieldPanel('image'),
    ]

    class Meta:
        verbose_name_plural = 'Authors'

    def __str__(self):
        return self.slug

    def get_absolute_url(self):
        return reverse('encyc-author', args=[self.slug])

    def title(self):
        return self.display_name

    def title_sort(self):
        return slugify(f"{self.family_name} {self.given_name}")

    def save(self, *args, **kwargs):
        self.slug = slugify(self.display_name)
        super(Author, self).save(*args, **kwargs)
