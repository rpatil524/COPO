# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import allauth.socialaccount.fields


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SocialAccount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('google', 'Google'), ('orcid', 'Orcid.org')], max_length=30, verbose_name='provider')),
                ('uid', models.CharField(max_length=255, verbose_name='uid')),
                ('last_login', models.DateTimeField(auto_now=True, verbose_name='last login')),
                ('date_joined', models.DateTimeField(auto_now_add=True, verbose_name='date joined')),
                ('extra_data', allauth.socialaccount.fields.JSONField(default='{}', verbose_name='extra data')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'social accounts',
                'verbose_name': 'social account',
            },
        ),
        migrations.CreateModel(
            name='SocialApp',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('google', 'Google'), ('orcid', 'Orcid.org')], max_length=30, verbose_name='provider')),
                ('name', models.CharField(max_length=40, verbose_name='name')),
                ('client_id', models.CharField(max_length=100, verbose_name='client id', help_text='App ID, or consumer key')),
                ('secret', models.CharField(max_length=100, verbose_name='secret key', help_text='API secret, client secret, or consumer secret')),
                ('key', models.CharField(max_length=100, verbose_name='key', blank=True, help_text='Key')),
                ('sites', models.ManyToManyField(to='sites.Site', blank=True)),
            ],
            options={
                'verbose_name_plural': 'social applications',
                'verbose_name': 'social application',
            },
        ),
        migrations.CreateModel(
            name='SocialToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.TextField(verbose_name='token', help_text='"oauth_token" (OAuth1) or access token (OAuth2)')),
                ('token_secret', models.TextField(verbose_name='token secret', blank=True, help_text='"oauth_token_secret" (OAuth1) or refresh token (OAuth2)')),
                ('expires_at', models.DateTimeField(null=True, verbose_name='expires at', blank=True)),
                ('account', models.ForeignKey(to='socialaccount.SocialAccount')),
                ('app', models.ForeignKey(to='socialaccount.SocialApp')),
            ],
            options={
                'verbose_name_plural': 'social application tokens',
                'verbose_name': 'social application token',
            },
        ),
        migrations.AlterUniqueTogether(
            name='socialtoken',
            unique_together=set([('app', 'account')]),
        ),
        migrations.AlterUniqueTogether(
            name='socialaccount',
            unique_together=set([('provider', 'uid')]),
        ),
    ]
