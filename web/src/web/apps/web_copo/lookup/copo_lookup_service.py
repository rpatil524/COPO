__author__ = 'etuka'

import os
import pandas as pd
from web.apps.web_copo.lookup.resolver import RESOLVER
import web.apps.web_copo.schemas.utils.data_utils as d_utils

"""
class is a service for the resolution of search terms to local objects in COPO. 
Each resolver should provide a mechanism for:
1. resolving a search term to valid objects
2. resolving accessions (i.e., id, values, etc.) to obtain matching or corresponding objects
"""


class COPOLookup:
    def __init__(self, search_term=str(), component=str(), accession=str()):
        self.search_term = search_term.lower()
        self.accession = accession
        self.component = component

        self.drop_downs_pth = RESOLVER['copo_drop_downs']

    def broker_component_search(self):
        dispatcher = {
            'agrovoclabels': self.get_agrovoclabels,
            'countrieslist': self.get_countrieslist
        }

        result = []
        message = 'error'

        if self.component in dispatcher:
            try:
                result = dispatcher[self.component]()
                message = 'success'
            except Exception as e:
                message = 'error'

        return dict(result=result, message=message)

    def get_agrovoclabels(self):
        data = d_utils.json_to_pytype(os.path.join(self.drop_downs_pth, 'agrovocLabels.json'))["bindings"]
        data_df = pd.DataFrame(data)

        data_df['accession'] = data_df['uri'].apply(lambda x: x['value'])
        data_df['label'] = data_df['label'].apply(lambda x: x['value'])
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

        data_df['accession'] = data_df['iso_3166-2']
        data_df['label'] = data_df['name']
        data_df['description'] = '<table style="width:100%"><tr><td>Code</td><td>'+data_df['country-code']+'</td></tr><tr><td>Region</td><td>'+data_df['region']+'</td></tr><tr><td>Sub-region</td><td>'+data_df['sub-region']+'</td></tr></table>'

        if self.accession:
            bn = list()
            bn.append(self.accession) if isinstance(self.accession, str) else bn.extend(self.accession)
            data_df = data_df[data_df['accession'].isin(bn)]
        elif self.search_term:
            data_df = data_df[data_df['label'].str.lower().str.contains(self.search_term, regex=False)]

        data_df = data_df[['accession', 'label', 'description']]
        result = data_df.to_dict('records')

        return result
