from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    orcid_id = models.TextField(max_length=40, blank=True)
    repo_manager = ArrayField(
        models.CharField(max_length=100, blank=True),
        blank=True,
        null=True,
    )
    repo_submitter = ArrayField(
        models.CharField(max_length=100, blank=True),
        blank=True,
        null=True,
    )

    #class Meta:
        #app_label = 'django.contrib.auth'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserDetails.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_details(sender, instance, **kwargs):
    instance.userdetails.save()


class Repository(models.Model):
    class Meta:
        managed = False  # No database table creation or deletion operations \
        # will be performed for this model.

        permissions = (
            ('customer_rigths', 'Global customer rights'),
            ('vendor_rights', 'Global vendor rights'),
            ('any_rights', 'Global any rights'),
        )
