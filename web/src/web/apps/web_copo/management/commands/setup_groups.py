# Created by fshaw at 25/06/2018

from django.core.management import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from web.apps.web_copo.models import Repository


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    # Show this when the user types help
    help = "My test command"

    # A command must define handle()
    def handle(self, *args, **options):
        self.stdout.write("Checking Groups")

        dm_group, created = Group.objects.get_or_create(name='data_managers')
        ct = ContentType.objects.get_for_model(Repository)

        Permission.objects.filter(codename="can_create_repo").delete()
        permission = Permission.objects.create(codename='can_create_repo',
                                               name='Can Create Repository',
                                               content_type=ct)
        dm_group.permissions.add(permission)
        Permission.objects.filter(codename="can_add_user_to_repo").delete()
        permission = Permission.objects.create(codename='can_add_user_to_repo',
                                           name='Can Add User to Repository',
                                           content_type=ct)
        dm_group.permissions.add(permission)
