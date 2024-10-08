# Generated by Django 5.0.7 on 2024-07-31 20:17

import django.db.models.deletion
import encyclopedia.blocks
import modelcluster.contrib.taggit
import modelcluster.fields
import wagtail.blocks
import wagtail.documents.blocks
import wagtail.embeds.blocks
import wagtail.fields
import wagtail.images.blocks
import wagtailmedia.blocks
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('editors', '0001_initial'),
        ('taggit', '0006_rename_taggeditem_content_type_object_id_taggit_tagg_content_8fc721_idx'),
        ('wagtailcore', '0091_remove_revision_submitted_for_moderation'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticlesIndexPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('intro', wagtail.fields.RichTextField(blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='ArticleTagPage',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.page')),
                ('description', wagtail.fields.RichTextField(blank=True)),
                ('body', wagtail.fields.StreamField([('heading', wagtail.blocks.StructBlock([('heading_text', wagtail.blocks.CharBlock(form_classname='title', required=True)), ('size', wagtail.blocks.ChoiceBlock(blank=True, choices=[('', 'Select a heading size'), ('h2', 'H2'), ('h3', 'H3'), ('h4', 'H4')], required=False))])), ('paragraph', encyclopedia.blocks.ArticleTextBlock()), ('embed', wagtail.blocks.StreamBlock([('heading_block', wagtail.blocks.StructBlock([('heading_text', wagtail.blocks.CharBlock(form_classname='title', required=True)), ('size', wagtail.blocks.ChoiceBlock(blank=True, choices=[('', 'Select a heading size'), ('h2', 'H2'), ('h3', 'H3'), ('h4', 'H4')], required=False))])), ('paragraph_block', wagtail.blocks.RichTextBlock(icon='pilcrow')), ('image_block', wagtail.blocks.StructBlock([('image', wagtail.images.blocks.ImageChooserBlock(required=True)), ('caption', wagtail.blocks.TextBlock(required=False)), ('caption2', wagtail.blocks.TextBlock(required=False)), ('courtesy', wagtail.blocks.CharBlock(required=False)), ('creative_commons', wagtail.blocks.BooleanBlock(required=False)), ('ext_url', wagtail.blocks.URLBlock(required=False))])), ('embed_block', wagtail.embeds.blocks.EmbedBlock(help_text='Insert a URL to embed. For example, https://youtu.be/sWqDIZxO-nU', icon='media'))])), ('quote', wagtail.blocks.StructBlock([('quotation', wagtail.blocks.RichTextBlock(icon='pilcrow')), ('attribution', wagtail.blocks.CharBlock(required=False))])), ('imageblock', wagtail.blocks.StructBlock([('image', wagtail.images.blocks.ImageChooserBlock(required=True)), ('caption', wagtail.blocks.TextBlock(required=False)), ('caption2', wagtail.blocks.TextBlock(required=False)), ('courtesy', wagtail.blocks.CharBlock(required=False)), ('creative_commons', wagtail.blocks.BooleanBlock(required=False)), ('ext_url', wagtail.blocks.URLBlock(required=False))])), ('videoblock', wagtail.blocks.StructBlock([('video', wagtailmedia.blocks.VideoChooserBlock(required=False)), ('transcript', wagtail.documents.blocks.DocumentChooserBlock(required=False)), ('caption', wagtail.blocks.TextBlock(required=False)), ('caption2', wagtail.blocks.TextBlock(required=False)), ('courtesy', wagtail.blocks.CharBlock(required=False)), ('creative_commons', wagtail.blocks.BooleanBlock(required=False))])), ('documentblock', wagtail.blocks.StructBlock([('document', wagtail.documents.blocks.DocumentChooserBlock(required=True)), ('display', wagtail.images.blocks.ImageChooserBlock(required=False)), ('caption', wagtail.blocks.TextBlock(required=False)), ('caption2', wagtail.blocks.TextBlock(required=False)), ('courtesy', wagtail.blocks.CharBlock(required=False)), ('creative_commons', wagtail.blocks.BooleanBlock(required=False)), ('ext_url', wagtail.blocks.URLBlock(required=False))]))], blank=True, help_text='BODY HELP TEXT GOES HERE.')),
                ('footnotes', wagtail.fields.RichTextField(blank=True, null=True)),
                ('authors', modelcluster.fields.ParentalManyToManyField(blank=True, to='editors.author')),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
        migrations.CreateModel(
            name='ArticleTag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content_object', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='tagged_items', to='encyclopedia.article')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(app_label)s_%(class)s_items', to='taggit.tag')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='article',
            name='tags',
            field=modelcluster.contrib.taggit.ClusterTaggableManager(blank=True, help_text='A comma-separated list of tags.', through='encyclopedia.ArticleTag', to='taggit.Tag', verbose_name='Tags'),
        ),
    ]
