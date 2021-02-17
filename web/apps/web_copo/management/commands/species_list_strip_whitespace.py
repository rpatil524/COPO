from django.core.management import BaseCommand

from dal import copo_da as da
from tools import resolve_env


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    # Show this when the user types help
    help = "strip white space from dtol species list entries in given manifest id"

    def __init__(self):
        super.__init__(self)
        self.pass_word = resolve_env('WEBIN_USER_PASSWORD')
        self.user_token = resolve_env('WEBIN_USER').split("@")[0]
        self.ena_service = resolve_env('ENA_SERVICE')  # 'https://wwwdev.ebi.ac.uk/ena/submit/drop-box/submit/'
        self.ena_sample_retrieval = self.ena_service[:-len('submit/')] + "samples/"  # https://devwww.ebi.ac.uk/ena
        # /submit/drop-box/samples/" \

    def add_arguments(self, parser):
        parser.add_argument('manifest_id', type=str)

    # A command must define handle()
    def handle(self, *args, **options):
        manifest_id = options["manifest_id"]
        fromdb = da.handle_dict["sample"].find({"manifest_id": manifest_id})
        fromdb = da.cursor_to_list(fromdb)
        for s in fromdb:
            print(s)
