__author__ = 'etuka'

import os
import glob
import json
import requests
import pandas as pd
from dal.copo_da import Sample
from web.apps.web_copo.lookup.resolver import RESOLVER
import web.apps.web_copo.schemas.utils.data_utils as d_utils

"""
class is a service for the resolution of search terms to local objects in COPO. 
Each resolver should provide a mechanism for:
1. resolving a search term to valid objects
2. resolving accessions (i.e., id, values, etc.) to obtain matching or corresponding objects
"""


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
            'agrovoclabels': self.get_agrovoclabels,
            'countrieslist': self.get_countrieslist,
            'mediatypelabels': self.get_mediatypelabels,
            'fundingbodies': self.get_fundingbodies,
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

    def get_agrovoclabels(self):
        data = d_utils.json_to_pytype(os.path.join(self.drop_downs_pth, 'agrovocLabels.json'))["bindings"]
        data_df = pd.DataFrame(data)

        data_df['accession'] = data_df['uri'].apply(lambda x: x.get('value', str()))
        data_df['label'] = data_df['label'].apply(lambda x: x.get('value', str()))
        data_df['description'] = ' '

        if self.accession:
            bn = list()
            bn.append(self.accession) if isinstance(self.accession, str) else bn.extend(self.accession)
            data_df = data_df[data_df['accession'].isin(bn)]
        elif self.search_term:
            data_df = data_df[data_df['label'].str.lower().str.contains(self.search_term, regex=False)]

        data_df = data_df[['accession', 'label', 'description']]
        result = data_df.to_dict('records')

        return result

    def get_countrieslist(self):
        data = d_utils.json_to_pytype(os.path.join(self.drop_downs_pth, 'countries.json'))["bindings"]
        data_df = pd.DataFrame(data)

        if self.accession:
            bn = list()
            bn.append(self.accession) if isinstance(self.accession, str) else bn.extend(self.accession)
            data_df = data_df[data_df['iso_3166-2'].isin(bn)]
        elif self.search_term:
            data_df = data_df[data_df['name'].str.lower().str.contains(self.search_term, regex=False)]

        data_df['accession'] = data_df['iso_3166-2']
        data_df['label'] = data_df['name']
        data_df['description'] = '<table style="width:100%"><tr><td>Code</td><td>' + data_df[
            'country-code'] + '</td></tr><tr><td>Region</td><td>' + data_df[
                                     'region'] + '</td></tr><tr><td>Sub-region</td><td>' + data_df[
                                     'sub-region'] + '</td></tr></table>'

        data_df = data_df[['accession', 'label', 'description']]
        result = data_df.to_dict('records')

        return result

    def get_mediatypelabels(self):
        """
        function generates and performs lookup of media types - to regenerate, delete 'media_types/all_list.json'
        see: https://www.iana.org/assignments/media-types/media-types.xml
        :return:
        """
        if not os.path.exists(os.path.join(self.drop_downs_pth, 'media_types', 'all_list.json')):
            pth = os.path.join(self.drop_downs_pth, 'media_types')
            all_files = glob.glob(os.path.join(pth, "*.csv"))

            all_list = list()
            for f in all_files:
                df = pd.read_csv(f)
                df['type'] = df['Template'].str.split("/").str.get(0)
                stem_part = set(df['type'][~df['type'].isna()]).pop()
                df['type'] = stem_part
                vv = df['Template'][df['Template'].isna()].index
                tt = df['Name'][vv]
                df.loc[list(vv), 'Template'] = stem_part + '/' + tt
                df = df[['Name', 'Template', 'type']]
                all_list = all_list + df.to_dict('records')

                with open(os.path.join(self.drop_downs_pth, 'media_types', 'all_list.json'), 'w') as fout:
                    json.dump(all_list, fout)

        data_df = pd.read_json(os.path.join(self.drop_downs_pth, 'media_types', 'all_list.json'))

        data_df['accession'] = data_df['Template']
        data_df['label'] = data_df['Template']

        if self.accession:
            bn = list()
            bn.append(self.accession) if isinstance(self.accession, str) else bn.extend(self.accession)
            data_df = data_df[data_df['accession'].isin(bn)]
        elif self.search_term:
            data_df = data_df[data_df['label'].str.lower().str.contains(self.search_term, regex=False)]

        data_df['description'] = '<table style="width:100%"><tr><td>Category</td><td>' + data_df[
            'type'] + '</td></tr></table>'

        data_df = data_df[['accession', 'label', 'description']]
        result = data_df.to_dict('records')

        return result

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
            df['description'] = '<table style="width:100%"><tr><td>Name</td><td>' + df[
                'name'] + '</td></tr></table>'

        df = df[['accession', 'label', 'description']]
        result = df.to_dict('records')

        return result
