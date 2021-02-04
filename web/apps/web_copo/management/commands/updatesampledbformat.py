from django.core.management import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from web.apps.web_copo.models import Repository
import os
import subprocess
import xml.etree.ElementTree as ET
import sys
import pymongo
from pymongo import MongoClient
import datetime

import sys

from dal.copo_da import Source, Sample
from dal import cursor_to_list, cursor_to_list_str, cursor_to_list_no_ids
from tools import resolve_env
from web.apps.web_copo.lookup.dtol_lookups import DTOL_ENA_MAPPINGS, DTOL_UNITS, PUBLIC_NAME_SERVICE, \
    API_KEY


# The class must be named Command, and subclass BaseCommand
class Command(BaseCommand):
    help="update old DTOL samples in db to move taxonomy metadata intospecies_list"

    def __init__(self):
        self.TAXONOMY_FIELDS = ["TAXON_ID", "ORDER_OR_GROUP", "FAMILY", "GENUS",
                               "SCIENTIFIC_NAME", "INFRASPECIFIC_EPITHET", "CULTURE_OR_STRAIN_ID",
                               "COMMON_NAME", "TAXON_REMARKS"]

    def handle(self, *args, **options):
        samples_to_update = self.identify_old_dtol_samples()
        for sample in samples_to_update:
            self.move_taxonomy_information(sample)

    def identify_old_dtol_samples(self):
        '''identify DTOL samples in the old format
        look for sample_type dtol and no species_list'''
        listtoupdate = []
        for dtolsample in Sample().get_all_dtol_samples():
            if "species_list" not in Sample().get_record(dtolsample['_id']):
                #print("missing field")
                listtoupdate.append(dtolsample['_id'])
        return listtoupdate

    def move_taxonomy_information(self, oid):
        '''create species_list field in database and
        add all taxonomic field in the first item of the list
        then remove the same field from the root'''
        print(oid)
        sam = Sample().get_record(oid)
        #Sample().add_field("species_list", [], oid)
        out = dict()
        out["SYMBIONT"] = "target"
        for field in self.TAXONOMY_FIELDS:
            out[field] = sam[field]
        topass = []
        topass.append(out)
        Sample().add_field("species_list", topass, oid)
        #now remove field from outside species_list
        for field in self.TAXONOMY_FIELDS:
            Sample().remove_field(field, oid)
        return


