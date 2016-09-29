# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socialaccount', '0002_auto_20160919_1021'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socialaccount',
            name='provider',
            field=models.CharField(choices=[('google', 'Google'), ('orcid', 'Orcid.org')], verbose_name='provider', max_length=30),
        ),
        migrations.AlterField(
            model_name='socialapp',
            name='provider',
            field=models.CharField(choices=[('google', 'Google'), ('orcid', 'Orcid.org')], verbose_name='provider', max_length=30),
        ),
    ]
