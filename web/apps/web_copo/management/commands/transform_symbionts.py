from django.core.management import BaseCommand
from dal.copo_da import Sample


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):

    # A command must define handle()
    def handle(self, *args, **options):
        s_list = Sample().get_collection_handle().find({"sample_type": "asg"})
        for s in s_list:
            print(s["_id"])
