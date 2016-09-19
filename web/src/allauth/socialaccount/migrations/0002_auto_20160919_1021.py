# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socialaccount', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socialaccount',
            name='provider',
            field=models.CharField(max_length=30, verbose_name='provider', choices=[('orcid', 'Orcid.org'), ('google', 'Google')]),
        ),
        migrations.AlterField(
            model_name='socialapp',
            name='provider',
            field=models.CharField(max_length=30, verbose_name='provider', choices=[('orcid', 'Orcid.org'), ('google', 'Google')]),
        ),
    ]
