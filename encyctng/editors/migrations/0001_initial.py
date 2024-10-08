# Generated by Django 5.0.7 on 2024-07-31 20:17

import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('family_name', models.CharField(max_length=255)),
                ('given_name', models.CharField(max_length=255)),
                ('display_name', models.CharField(max_length=255)),
                ('description', wagtail.fields.RichTextField(blank=True, null=True)),
            ],
            options={
                'verbose_name_plural': 'Authors',
            },
        ),
    ]
