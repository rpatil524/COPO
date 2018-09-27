__author__ = 'etuka'

import os
import json
import numpy as np
import pandas as pd
from web.apps.web_copo.lookup.resolver import RESOLVER
import web.apps.web_copo.schemas.utils.data_utils as d_utils


class CgCoreSchemas:
    def __init__(self):
        self.resource_path = RESOLVER['cg_core_schemas']
        self.schemas_utils_paths = RESOLVER["cg_core_utils"]
        self.path_to_json = os.path.join(self.resource_path, 'cg_core.json')
        self.type_field_status_path = os.path.join(self.schemas_utils_paths, 'type_field_STATUS.csv')
        self.map_type_subtype_path = os.path.join(self.schemas_utils_paths, 'mapTypeSubtype.csv')
        self.copo_schema_spec_path = os.path.join(self.schemas_utils_paths, 'copo_schema.csv')

    def retrieve_schema_specs(self, path_to_spec):
        """
        function retrieves csv, returns dataframe
        :param path_to_spec:
        :return:
        """

        df = pd.read_csv(path_to_spec)

        # set index using 'type' column
        df.index = df['harmonized labeling']
        df = df.drop(['harmonized labeling'], axis='columns')

        # drop null index
        df = df[df.index.notnull()]

        return df

    def get_type_field_matrix(self):
        """
        function returns cg core fields and corresponding constraints as a dataframe
        :return: dataframe
        """

        df = self.retrieve_schema_specs(self.type_field_status_path)

        # filter valid types and subtypes
        df['match_type_subtype_x'] = df['in cgc2 typelist'].astype(str) + df['in cgc2 subtypelist'].astype(str)
        df = df[(df['match_type_subtype_x'] == '01') | (df['match_type_subtype_x'] == '10')]

        # # substitute value todo: might have to revisit this - for now user gets to decide
        # df = df.replace('required if applicable', 'required')
        df = df.replace('required if applicable', 'required-if-applicable')

        # drop noisy columns - that do not define any constraint
        constraints = ['required', 'recommended', 'optional', 'not applicable', 'required-if-applicable']

        # filter out noisy columns
        df = df.T
        df = df[df.isin(constraints)]
        df = df.dropna(how='all')

        # filter out noisy rows
        df = df.T
        df = df.dropna()

        return df

    def get_type_constraints(self, type_name):
        """
        given a type (or a subtype) function returns participating schemas and constraints
        :param type_name:
        :return:
        """

        df = self.get_type_field_matrix()
        df.index = df.index.str.lower()
        df_type_series = df.loc[type_name.lower()]
        df_type_series = df_type_series[df_type_series != 'not applicable']
        df_type_series.index = df_type_series.index.str.lower()

        from dal.copo_base_da import DataSchemas
        schema_fields = DataSchemas("COPO").get_ui_template_node('cgCore')

        schemas_df = pd.DataFrame(schema_fields)
        schemas_df.index = schemas_df.ref.str.lower()
        schemas_df = schemas_df[schemas_df.index.isin(df_type_series.index)]

        # set constraints
        schemas_df.loc[schemas_df.index, 'required'] = df_type_series
        schemas_df.loc[schemas_df.index, 'field_constraint'] = df_type_series

        schemas_df["required"] = schemas_df["required"].replace(
            {'required': True, 'recommended': False, 'optional': False, 'required-if-applicable': False})

        # rank fields by constraints
        constraint_to_rank = {
            'required': 1,
            'required-if-applicable': 2,
            'recommended': 3,
            'optional': 4
        }

        lowercased = schemas_df['field_constraint'].str.lower()
        schemas_df['field_constraint_rank'] = lowercased.map(constraint_to_rank)

        schemas_df['option_values'] = schemas_df['option_values'].fillna(False)

        return schemas_df

    def get_type_subtype_map(self):
        """
        function returns type-subtype mapping
        :return:
        """

        path_to_spec = self.map_type_subtype_path
        df = pd.read_csv(path_to_spec)

        df = df[['type collection character', 'type', 'subtype', 'remark']]

        return df

    def get_required_types(self, type_class):
        """
        function returns items matching required type_class
        :param type_class:
        :return:
        """

        type_map_df = self.get_type_subtype_map()
        df = type_map_df[type_map_df['type collection character'] == type_class]

        all_types_index = self.get_type_field_matrix().index

        df_series = pd.Series(list(df['type'].str.strip().str.lower().dropna().unique()))
        all_types_series = pd.Series(all_types_index.str.strip().str.lower())

        qualified_types = list(df_series[df_series.isin(all_types_series)])

        all_types_series = pd.Series(all_types_index)

        qualified_types = list(all_types_series[all_types_series.str.strip().str.lower().isin(qualified_types)])

        return qualified_types

    def get_required_subtype(self, type_class, type_name):
        """
        function returns items matching required type_class and type
        :param type_class:
        :param type_name:
        :return:
        """

        qualified_types = list()

        type_map_df = self.get_type_subtype_map()

        df = type_map_df[type_map_df['type collection character'] == type_class]

        # filter by type
        df = df[df['type'].str.strip().str.lower() == type_name.strip().lower()]

        all_types_index = self.get_type_field_matrix().index

        all_types_series = pd.Series(all_types_index.str.strip().str.lower())
        subtypes = list(df['subtype'].str.strip().str.lower().dropna().unique())

        if subtypes:
            df_series = pd.Series(subtypes)
            qualified_types = list(df_series[df_series.isin(all_types_series)])
        else:
            remarks = list(df['remark'].str.strip().str.lower().dropna().unique())
            if remarks and remarks[0] == 'can contain any type or subtype':
                qualified_types = list(all_types_series)

        all_types_series = pd.Series(all_types_index)
        qualified_types = list(all_types_series[all_types_series.str.strip().str.lower().isin(qualified_types)])

        return qualified_types

    def get_singular_types(self):
        """
        function returns relevant types for single item description
        :return:
        """

        return self.get_required_types('as singular types')

    def get_multiple_types(self):
        """
        function returns relevant types for multiple item description
        :return:
        """

        return self.get_required_types('multiple item types')

    def extract_dublin_core(self, datafile_id=str()):
        """
        given a datafile id, function returns a list of dictionaries of dublin-core fields
        :param datafile_id:
        :return:
        """
        from dal.copo_da import DataFile

        record = DataFile().get_record(datafile_id)
        description = record.get("description", dict())

        attributes = description.get("attributes", dict())
        stages = description.get("stages", list())

        items_list = list()

        for st in stages:
            for item in st.get("items", list()):
                item['stage_ref'] = st["ref"]
                items_list.append(item)

        items_df = pd.DataFrame(items_list)
        items_df.index = items_df['id']
        items_df = items_df[['ref', 'id', 'stage_ref']]
        items_df = items_df[~items_df['ref'].isna()]
        items_df['dc'] = items_df['ref'].str.split(".").str.get(0)
        items_df = items_df[items_df['dc'] == 'dc']

        target_stages = list(items_df['stage_ref'].unique())

        # first level filter - participating stages
        datafile_attributes = [v for k, v in attributes.items() if k in target_stages]
        new_dict = dict()

        for d in datafile_attributes:
            new_dict.update(d)

        new_dict_series = pd.Series(new_dict)
        items_df['vals'] = new_dict_series

        items_df = items_df[['ref', 'id', 'vals']]

        items_df.rename(index=str, columns={"ref": "dc", "id": "copo_id"}, inplace=True)

        dc_list = items_df.to_dict('records')

        return dc_list

    def get_singular_subtypes(self, type_name):
        """
        function returns relevant subtypes for type
        :param type_name:
        :return:
        """

        return self.get_required_subtype('as singular types', type_name)

    def get_multiple_subtypes(self, type_name):
        """
        function returns relevant subtypes for type
        :param type_name:
        :return:
        """

        return self.get_required_subtype('multiple item types', type_name)

    def controls_mapping(self):
        """
        function maps to COPO controls
        :return:
        """

        control = 'text'

        return control

    def get_schema_spec(self):
        """
        function returns cg core field specifications e.g., field id, field type, field label
        :return:
        """

        df = self.retrieve_schema_specs(self.copo_schema_spec_path)

        # filter out columns not found in type-field matrix
        df_spec_col_series = pd.Series(df.columns)
        type_field_series = pd.Series(self.get_type_field_matrix().columns)
        spec_qualified_cols = df_spec_col_series[df_spec_col_series.isin(type_field_series)]

        df = df[spec_qualified_cols]

        # filter out columns with no copo id
        cid_series = df.loc['COPO_ID']
        df = df[cid_series[~cid_series.isna()].index]

        # substitute for NANs
        df.loc['LABEL'] = df.loc['LABEL'].fillna('**No label**')
        df.loc['HELP_TIP'] = df.loc['HELP_TIP'].fillna('n/a')
        df.loc['COPO_CONTROL'] = df.loc['COPO_CONTROL'].fillna('text')
        df.loc['TYPE'] = df.loc['TYPE'].fillna('string')
        df.loc['COPO_DATA_SOURCE'] = df.loc['COPO_DATA_SOURCE'].fillna('')
        df.loc['Wizard_Stage_ID'] = df.loc['Wizard_Stage_ID'].fillna('-1')

        return df

    def process_schema(self):
        """
        function builds schema fragments to file, which is later called to generate the complete schema in db
        :return:
        """

        specs_df = self.get_schema_spec()

        # compose copo schema fragment from cg-core spec
        df = specs_df.T.copy()
        df["ref"] = list(df.index)

        df["id"] = df['COPO_ID'].apply(lambda x: ".".join(("copo", "cgCore", x)))
        df["label"] = df['LABEL']
        df["help_tip"] = df['HELP_TIP']
        df["control"] = df['COPO_CONTROL']
        df["stage_id"] = df['Wizard_Stage_ID']

        # set cardinality
        df["type"] = df['TYPE'].replace({'1': 'string', 'm': 'array'})

        # set data source for relevant controls
        df['data_source'] = np.where(df['control'].isin(['copo-lookup', 'copo-multi-select', 'copo-button-list']), df['COPO_DATA_SOURCE'],
                                     '')
        df['data_maxItems'] = np.where(df['control'] == 'copo-multi-select', 1, '')

        df = df.loc[:,
             ["ref", "id", "label", "help_tip", "control", "type", "stage_id", "data_source", "data_maxItems"]]

        df["required"] = False
        df["field_constraint"] = "optional"

        schema_list = df.to_dict('records')

        # update schema in file
        cg_schema = d_utils.json_to_pytype(self.path_to_json)
        cg_schema['properties'] = schema_list

        with open(self.path_to_json, 'w') as fout:
            json.dump(cg_schema, fout)

        return True
