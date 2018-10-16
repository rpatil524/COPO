__author__ = 'etuka'

import os
import glob
import json
import requests
import pandas as pd
from dal import cursor_to_list
from dal.copo_da import Sample
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
            'isa_samples_lookup': self.get_isasamples
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
            languagelist=os.path.join(self.drop_downs_pth, 'language_list.json')
        )

        data = list()

        try:
            data = d_utils.json_to_pytype(pths_map.get(self.data_source, str()))
        except:
            pass

        return data

    def get_lookup_type(self):
        projection = dict(label=1, accession=1, description=1)
        filter_by = dict(type=self.data_source)

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

    def get_isasamples(self):
        """
        lookup for ISA-based (COPO standard) samples
        :return:
        """

        import web.apps.web_copo.templatetags.html_tags as htags

        df = pd.DataFrame()

        if self.accession:
            record = Sample().get_record(self.accession)
            if record:
                df = pd.DataFrame([record])
                df['accession'] = df._id.astype(str)
                df['label'] = df['name']
                desc = df['accession'].apply(lambda x: htags.generate_attributes("sample", x))
                desc = list(desc)[0]
                html = """<table style="width:100%">"""
                for col in desc['columns']:
                    html += "<tr><td>{}</td>".format(col['title'])
                    html += "<td>{}</td>".format(desc['data_set'][col['data']])
                    html += "</tr>"
                html += "</table>"
                df['description'] = html
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

            df = pd.DataFrame(records)
            df['accession'] = df._id.astype(str)
            df['label'] = df['name']
            df['description'] = ''
            df['server-side'] = True  # ...to request callback to server for resolving item description

        df = df[['accession', 'label', 'description', 'server-side']]
        result = df.to_dict('records')

        return result
