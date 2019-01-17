__author__ = 'etuka'

import os
import requests
import pandas as pd
from bson import ObjectId
from dal import cursor_to_list
from dal.copo_da import Sample, Source
from dal.mongo_util import get_collection_ref
from web.apps.web_copo.lookup.resolver import RESOLVER
import web.apps.web_copo.schemas.utils.data_utils as d_utils

"""
class is a service for the resolution of search terms to local objects in COPO. 
Each resolver should provide a mechanism for:
1. resolving a search term to valid objects
2. resolving accessions (i.e., id, values, etc.) to obtain matching or corresponding objects
"""

Lookups = get_collection_ref("Lookups")


class COPOLookup:
    def __init__(self, **kwargs):
        self.param_dict = kwargs
        self.search_term = self.param_dict.get("search_term", str()).lower()
        self.accession = self.param_dict.get("accession", dict())
        self.data_source = self.param_dict.get("data_source", str())
        self.profile_id = self.param_dict.get("profile_id", str())
        self.drop_downs_pth = RESOLVER['copo_drop_downs']

    def broker_component_search(self):
        dispatcher = {
            'agrovoclabels': self.get_lookup_type,
            'countrieslist': self.get_lookup_type,
            'mediatypelabels': self.get_lookup_type,
            'fundingbodies': self.get_lookup_type,
            'isa_samples_lookup': self.get_isasamples,
            'sample_source_lookup': self.get_samplesource,
            'all_samples_lookup': self.get_allsamples
        }

        result = []
        message = 'error'

        if self.data_source in dispatcher:
            try:
                result = dispatcher[self.data_source]()
                message = 'success'
            except Exception as e:
                message = 'error'
                print(e)

        return dict(result=result, message=message)

    def broker_data_source(self):
        """
        function resolves dropdown list given a data source handle
        :return:
        """

        pths_map = dict(
            select_yes_no=os.path.join(self.drop_downs_pth, 'select_yes_no.json'),
            select_start_end=os.path.join(self.drop_downs_pth, 'select_start_end.json'),
            cgiar_centres=os.path.join(self.drop_downs_pth, 'cgiar_centres.json'),
            languagelist=os.path.join(self.drop_downs_pth, 'language_list.json'),
            figshare_category_options=d_utils.get_figshare_category_options(),
            figshare_article_options=d_utils.get_figshare_article_options(),
            figshare_publish_options=d_utils.get_figshare_publish_options(),
            figshare_license_options=d_utils.get_figshare_license_options(),
            study_type_options=d_utils.get_study_type_options(),
            rooting_medium_options=d_utils.get_rooting_medium_options(),
            growth_area_options=d_utils.get_growth_area_options(),
            nutrient_control_options=d_utils.get_nutrient_control_options(),
            watering_control_options=d_utils.get_watering_control_options(),
            dataverse_subject_dropdown=d_utils.get_dataverse_subject_dropdown(),
            repository_options=d_utils.get_repository_options()
        )

        data = pths_map.get(self.data_source, str())

        if isinstance(data, str):  # it's only a path, resolve to get actual data
            data = d_utils.json_to_pytype(data)

        return data

    def get_lookup_type(self):
        projection = dict(label=1, accession=1, description=1)
        filter_by = dict(type=self.data_source)

        records = list()

        if self.accession or self.search_term:
            if self.accession:
                bn = list()
                bn.append(self.accession) if isinstance(self.accession, str) else bn.extend(self.accession)
                filter_by["accession"] = {'$in': bn}

            elif self.search_term:
                filter_by["label"] = {'$regex': self.search_term, "$options": 'i'}

            records = cursor_to_list(Lookups.find(filter_by, projection))

        return records

    def get_fundingbodies(self):
        """
        function performs a lookup on funding bodies'
        see: https://www.crossref.org/services/funder-registry/; https://github.com/CrossRef/rest-api-doc
        :return:
        """

        REQUEST_BASE_URL = 'https://api.crossref.org/funders'
        BASE_HEADERS = {'Accept': 'application/json'}

        all_list = list()

        if self.accession:
            bn = list()
            bn.append(self.accession) if isinstance(self.accession, str) else bn.extend(self.accession)

            for acc in bn:
                resp = requests.get(acc)
                json_body = resp.json()
                label = json_body.get("prefLabel", dict()).get("Label", dict()).get("literalForm", dict()).get(
                    "content",
                    "n/a")
                all_list.append(dict(accession=acc, label=label, description=''))
        elif self.search_term:
            resp = requests.get(REQUEST_BASE_URL, params={'query': str(self.search_term)}, headers=BASE_HEADERS)
            json_body = resp.json()

            resolved_items = json_body['message'].get('items', list())
            for item in resolved_items:
                all_list.append(dict(accession=item["uri"], label=item["name"], description=''))

        return all_list

    def get_samplesource(self):
        """
        lookup sources related to a sample
        :return:
        """
        import web.apps.web_copo.templatetags.html_tags as htags

        df = pd.DataFrame()

        if self.accession:
            if isinstance(self.accession, str):
                self.accession = self.accession.split(",")

            object_ids = [ObjectId(x) for x in self.accession]
            records = cursor_to_list(Source().get_collection_handle().find({"_id": {"$in": object_ids}}))

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['desc'] = df['accession'].apply(lambda x: htags.generate_attributes("source", x))
                df['description'] = df['desc'].apply(lambda x: self.format_description(x))
                df['server-side'] = True  # ...to request callback to server for resolving item description
        elif self.search_term:
            projection = dict(name=1)
            filter_by = dict()
            filter_by["name"] = {'$regex': self.search_term, "$options": 'i'}

            sort_by = 'name'
            sort_direction = -1

            records = Source(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                 projection=projection,
                                                                                 sort_by=sort_by,
                                                                                 sort_direction=sort_direction)

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['description'] = ''
                df['server-side'] = True  # ...to request callback to server for resolving item description

        result = list()

        if not df.empty:
            df = df[['accession', 'label', 'description', 'server-side']]
            result = df.to_dict('records')

        return result

    def get_isasamples(self):
        """
        lookup for ISA-based (COPO standard) samples
        :return:
        """

        import web.apps.web_copo.templatetags.html_tags as htags

        df = pd.DataFrame()

        if self.accession:
            if isinstance(self.accession, str):
                self.accession = self.accession.split(",")

            object_ids = [ObjectId(x) for x in self.accession]
            records = cursor_to_list(Sample().get_collection_handle().find({"_id": {"$in": object_ids}}))

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['desc'] = df['accession'].apply(lambda x: htags.generate_attributes("sample", x))
                df['description'] = df['desc'].apply(lambda x: self.format_description(x))
                df['server-side'] = True  # ...to request callback to server for resolving item description

        elif self.search_term:
            projection = dict(name=1)
            filter_by = dict(sample_type="isasample")
            filter_by["name"] = {'$regex': self.search_term, "$options": 'i'}

            sort_by = 'name'
            sort_direction = -1

            records = Sample(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                 projection=projection,
                                                                                 sort_by=sort_by,
                                                                                 sort_direction=sort_direction)
            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['description'] = ''
                df['server-side'] = True  # ...to request callback to server for resolving item description

        result = list()

        if not df.empty:
            df = df[['accession', 'label', 'description', 'server-side']]
            result = df.to_dict('records')

        return result

    def get_allsamples(self):
        """
        lookup for all samples irrespective of sample type
        :return:
        """

        import web.apps.web_copo.templatetags.html_tags as htags

        df = pd.DataFrame()

        if self.accession:
            if isinstance(self.accession, str):
                self.accession = self.accession.split(",")

            object_ids = [ObjectId(x) for x in self.accession]
            records = cursor_to_list(Sample().get_collection_handle().find({"_id": {"$in": object_ids}}))

            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['desc'] = df['accession'].apply(lambda x: htags.generate_attributes("sample", x))
                df['description'] = df['desc'].apply(lambda x: self.format_description(x))
                df['server-side'] = True  # ...to request callback to server for resolving item description
        elif self.search_term:
            projection = dict(name=1)
            filter_by = dict()
            filter_by["name"] = {'$regex': self.search_term, "$options": 'i'}

            sort_by = 'name'
            sort_direction = -1

            records = Sample(profile_id=self.profile_id).get_all_records_columns(filter_by=filter_by,
                                                                                 projection=projection,
                                                                                 sort_by=sort_by,
                                                                                 sort_direction=sort_direction)
            if records:
                df = pd.DataFrame(records)
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                df['description'] = ''
                df['server-side'] = True  # ...to request callback to server for resolving item description

        result = list()

        if not df.empty:
            df = df[['accession', 'label', 'description', 'server-side']]
            result = df.to_dict('records')

        return result

    def format_description(self, desc):
        html = """<table style="width:100%">"""
        for col in desc['columns']:
            html += "<tr><td>{}</td>".format(col['title'])
            html += "<td>{}</td>".format(desc['data_set'][col['data']])
            html += "</tr>"
        html += "</table>"

        return html
