# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socialaccount', '0003_auto_20160921_0951'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socialaccount',
            name='provider',
            field=models.CharField(verbose_name='provider', choices=[('orcid', 'Orcid.org'), ('google', 'Google')], max_length=30),
        ),
        migrations.AlterField(
            model_name='socialapp',
            name='provider',
            field=models.CharField(verbose_name='provider', choices=[('orcid', 'Orcid.org'), ('google', 'Google')], max_length=30),
        ),
    ]
