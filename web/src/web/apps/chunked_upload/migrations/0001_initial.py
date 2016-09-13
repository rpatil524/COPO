# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import web.apps.chunked_upload.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChunkedUpload',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('upload_id', models.CharField(max_length=32, default=web.apps.chunked_upload.models.generate_upload_id, unique=True, editable=False)),
                ('file', models.FileField(upload_to=web.apps.chunked_upload.models.generate_filename, max_length=255)),
                ('filename', models.CharField(max_length=255)),
                ('hash', models.CharField(default='', max_length=255)),
                ('type', models.CharField(default='', max_length=255)),
                ('offset', models.PositiveIntegerField(default=0)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('status', models.PositiveSmallIntegerField(choices=[(1, 'Uploading'), (2, 'Complete'), (3, 'Failed')], default=1)),
                ('completed_on', models.DateTimeField(null=True, blank=True)),
                ('user', models.ForeignKey(related_name='chunked_uploads', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
