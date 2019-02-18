__author__ = 'etuka'

import os
import json
import numpy as np
import pandas as pd
import web.apps.web_copo.lookup.lookup as lkup
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
        self.dataverse_dataset_template = os.path.join(self.schemas_utils_paths, 'dataverse_dataset_template.json')

    def get_dv_dataset_template(self):
        try:
            return d_utils.json_to_pytype(self.dataverse_dataset_template)
        except Exception as e:
            print("Couldn't retrieve Dataverse template" + str(e))
            return False

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

        # # substitute value
        # todo: example dc.creator affiliation depends on dc.creator use this infer dependency
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
        given a type (or a subtype) function returns relevant schemas and constraints
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

    def extract_repo_fields(self, datafile_id=str(), repo=str()):
        """
        given a datafile id, and repository type function returns a list of dictionaries of fields matching the repo
        :param datafile_id:
        :param repo:
        :return:
        """

        from dal.copo_da import DataFile
        from dal.copo_base_da import DataSchemas

        if not repo:  # no repository to filter by
            return list()

        repo_type_option = lkup.DROP_DOWNS["REPO_TYPE_OPTIONS"]
        repo_type_option = [x for x in repo_type_option if x["value"].lower() == repo.lower()]

        if not repo_type_option:
            return list()

        repo_type_option = repo_type_option[0]

        cg_schema = DataSchemas("COPO").get_ui_template_node('cgCore')

        # filter by 'repo'
        cg_schema = [x for x in cg_schema if
                     x.get("target_repo", str()).strip() != str() and
                     repo_type_option.get("abbreviation", str()) in [y.strip() for y in
                                                                     x.get("target_repo").split(',')]]

        record = DataFile().get_record(datafile_id)
        description = record.get("description", dict())

        attributes = description.get("attributes", dict())
        stages = description.get("stages", list())

        items_list = list()
        stage_ref_list = list()

        # get fields for target repo
        for st in stages:
            for item in st.get("items", list()):
                new_item = [x for x in cg_schema if
                            x["id"].lower().split(".")[-1] == item.get("id", str()).lower().split(".")[-1]]
                if new_item:
                    stage_ref_list.append(st["ref"].lower())
                    new_item[0]['id'] = new_item[0]['id'].lower().split(".")[-1]
                    items_list.append(new_item[0])

        items_df = pd.DataFrame(items_list)
        items_df.index = items_df['id'].str.lower()
        items_df = items_df[['ref', 'id', 'prefix']]
        items_df = items_df[~items_df['ref'].isna()]

        # first level filter - relevant stages
        target_stages = list(set(stage_ref_list))
        datafile_attributes = [v for k, v in attributes.items() if k in target_stages]

        new_dict = dict()
        for d in datafile_attributes:
            new_dict.update(d)

        new_dict_series = pd.Series(new_dict)
        new_dict_series.index = new_dict_series.index.str.lower()
        items_df['vals'] = new_dict_series
        items_df['vals'] = items_df['vals'].fillna('')

        items_df = items_df[['ref', 'id', 'vals', 'prefix']]

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
        df.loc['DEPENDENCY'] = df.loc['DEPENDENCY'].fillna('')
        df.loc['COPO_DATA_SOURCE'] = df.loc['COPO_DATA_SOURCE'].fillna('')
        df.loc['REPO'] = df.loc['REPO'].fillna('')
        df.loc['REPO_PREFIX'] = df.loc['REPO_PREFIX'].fillna('')
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
        df["dependency"] = df['DEPENDENCY']
        df["control"] = df['COPO_CONTROL']
        df["stage_id"] = df['Wizard_Stage_ID']
        df["target_repo"] = df['REPO']
        df["prefix"] = df['REPO_PREFIX']
        df["data_maxItems"] = -1

        # set max item for lookup control
        temp_df_1 = df[(df['control'] == 'copo-lookup2') & (df['TYPE'] == '1')]
        if len(temp_df_1):
            df.loc[temp_df_1.index, 'data_maxItems'] = 1

        # set cardinality
        df["type"] = df['TYPE'].replace({'1': 'string', 'm': 'array'})

        # set data source for relevant controls
        df['data_source'] = np.where(
            df['control'].isin(['copo-lookup2', 'copo-multi-select2', 'copo-button-list', 'copo-single-select']),
            df['COPO_DATA_SOURCE'],
            '')

        # reset 'type' to string for select2 controls
        temp_df_1 = df[df['control'].isin(['copo-lookup2', 'copo-multi-select2', 'copo-single-select', 'copo-select2'])]
        df.loc[temp_df_1.index, 'type'] = 'string'

        filtered_columns = ["ref", "id", "label", "help_tip", "control", "type", "stage_id", "data_source",
                            "data_maxItems", "dependency", "target_repo", "prefix"]

        df = df.loc[:, filtered_columns]

        df["required"] = False  # this will be set later
        df["field_constraint"] = "optional"  # this will be set later

        schema_list = df.to_dict('records')

        # update schema in file
        cg_schema = d_utils.json_to_pytype(self.path_to_json)
        cg_schema['properties'] = schema_list

        with open(self.path_to_json, 'w') as fout:
            json.dump(cg_schema, fout)

        return True
