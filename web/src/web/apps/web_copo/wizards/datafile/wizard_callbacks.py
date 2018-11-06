""" module defines callbacks for wizard stages """
__author__ = 'etuka'

import numpy as np
import pandas as pd
from dal import cursor_to_list

from dal.copo_da import Description, DataFile
from dal.copo_base_da import DataSchemas
from converters.ena.copo_isa_ena import ISAHelpers
import web.apps.web_copo.templatetags.html_tags as htags
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.wizards.utils.process_wizard_schemas import WizardSchemas
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas


class WizardCallbacks:
    def __init__(self, wzh):
        self.__wzh = wzh

    def get_cg_type(self, next_stage_index):
        """
        stage callback function to resolve type list for cg core description
        :param next_stage_index:
        :return:
        """
        stage = dict()

        description = Description().GET(self.__wzh.description_token)
        stages = description["stages"]
        attributes = description["attributes"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

            count_bundle_items = len(self.__wzh.get_description_bundle())

            item = [x for x in stage.get('items', list()) if x['id'] == 'type']

            item = item[0] if item else dict()

            if count_bundle_items <= 1:
                item['option_values'] = CgCoreSchemas().get_singular_types()
            else:
                item['option_values'] = CgCoreSchemas().get_multiple_types()

            save_dict = dict(attributes=attributes, stages=stages)
            Description().edit_description(self.__wzh.description_token, save_dict)

        return stage

    def get_cg_subtype(self, next_stage_index):
        """
        stage callback function to resolve type list for cg core description
        :param next_stage_index:
        :return:
        """
        stage = dict()

        description = Description().GET(self.__wzh.description_token)
        stages = description["stages"]
        attributes = description["attributes"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

            count_bundle_items = len(self.__wzh.get_description_bundle())

            item = [x for x in stage.get('items', list()) if x['id'] == 'subtype']

            item = item[0] if item else dict()

            type = attributes.get("cg_type", dict()).get("type", str())

            if count_bundle_items <= 1:
                item['option_values'] = CgCoreSchemas().get_singular_subtypes(type)
            else:
                item['option_values'] = CgCoreSchemas().get_multiple_subtypes(type)

            save_dict = dict(attributes=attributes, stages=stages)
            Description().edit_description(self.__wzh.description_token, save_dict)

        return stage

    def get_unique_bundle_names(self, next_stage_index):
        """
        stage callback function: sets unique_items list for bundle names
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.__wzh.description_token)
        stages = description["stages"]

        # get existing names to form unique list
        unique_list = list()
        projection = dict(name=1)
        filter_by = dict(profile_id=self.__wzh.profile_id, component=self.__wzh.component)
        records = Description().get_all_records_columns(projection=projection,
                                                        filter_by=filter_by)

        records_df = pd.DataFrame(records).dropna()

        if len(records_df):
            records_df["_id2"] = records_df._id.astype(str)
            records_df = records_df[records_df._id2 != self.__wzh.description_token]
            records_df = records_df[records_df.name != str()]
            unique_list = list(records_df.name)

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

            for item in stage["items"]:
                if "unique_items" in item:
                    item["unique_items"] = unique_list

        return stage

    def get_description_stages(self, next_stage_index):
        """
        stage callback function: resolves stages based on repository value
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.__wzh.description_token)

        stages = description["stages"]
        attributes = description["attributes"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        target_repository = attributes.get("target_repository", dict()).get("deposition_context", str())

        if not target_repository:
            # no target repository specified, we can't really do anything but signal abort
            return dict()

        # re-validate dependency if necessary

        meta = description.get("meta", dict())
        target_repository_old = meta.get(stage["ref"] + "_target_repository", None)

        # remove dependency - remove resolved stages preceding target_repository
        if not target_repository_old == target_repository:
            cleared_stages = self.__wzh.remove_stage_dependency(next_stage_index)

            # get new dynamic stages based on user current choice
            new_stages = WizardSchemas().get_wizard_template(target_repository)

            # retain user choice for future reference
            meta[stage["ref"] + "_target_repository"] = target_repository

            # save meta
            Description().edit_description(self.__wzh.description_token, dict(meta=meta))

            if not new_stages:
                # no resolved stages; signal abort
                return dict()

            # resolve type and data source for generated stages
            self.__wzh.sanitise_stages(new_stages)

            # register dependency
            self.__wzh.set_stage_dependency(new_stages)

            # insert new stages to stage list
            stage_gap = next_stage_index + 1
            stages = cleared_stages[:stage_gap] + new_stages + cleared_stages[stage_gap:]

            # update description record
            Description().edit_description(self.__wzh.description_token, dict(stages=stages))

        return False

    def get_cg_dynamic_stages(self, next_stage_index):
        """
        stage callback function: resolves stages for cg core based on type/subtype
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.__wzh.description_token)

        stages = description["stages"]
        attributes = description["attributes"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        # get type and subtype
        cg_type = attributes.get("cg_type", dict()).get("type", str())
        cg_subtype = attributes.get("cg_subtype", dict()).get("subtype", str())

        if cg_subtype:  # if there's a subtype defined, use that to resolve the stages
            cg_type = cg_subtype

        if not cg_type:
            # no type specified, we can't really do anything but signal abort
            return dict()

        # re-validate dependency if necessary
        meta = description.get("meta", dict())
        cg_type_old = meta.get(stage["ref"] + "_cg_type", None)

        # remove stages dependent on 'cg_type' - remove resolved stages preceding cg_type
        if not cg_type_old == cg_type:
            cleared_stages = self.__wzh.remove_stage_dependency(next_stage_index)

            # get new dynamic stages based on user current choice
            new_stages = list()

            # get fields schema
            schema_df = CgCoreSchemas().get_type_constraints(cg_type)

            # get dependencies
            # todo: revisit this once there is more clarification from the CG Core folks
            dependencies = schema_df[~schema_df['dependency'].isin([''])]['dependency'].unique()
            #
            # # filter out dependants - these are fields that are to be displayed via their parent field
            schema_df = schema_df[schema_df['dependency'].isin([''])]
            schema_df["show_create_button"] = False

            composite_field_df = schema_df[schema_df['ref'].isin(dependencies)]
            schema_df.loc[composite_field_df.index, "show_create_button"] = True
            schema_df.loc[composite_field_df.index, "control"] = "copo-select"

            # get stage id groups
            stage_ids = list(schema_df.stage_id.unique())

            stage_ids = pd.Series(stage_ids)
            stage_ids = stage_ids.astype(int).sort_values()
            stage_ids = stage_ids[stage_ids >= 0]
            stage_ids = stage_ids.astype(str)

            for s_id in stage_ids:
                title = "Stage - " + s_id

                ref = "cg_stage_" + s_id
                # todo: get message for stage, and an appropriate title
                message = "Dynamically generated stage - still needs appropriate message!"

                stage_dict = dict(title=title,
                                  ref=ref,
                                  message=message,
                                  items=schema_df[schema_df.stage_id == s_id].sort_values(
                                      by=['field_constraint_rank']).to_dict('records')
                                  )

                new_stages.append(stage_dict)

            # retain user choice for future reference
            meta[stage["ref"] + "_cg_type"] = cg_type

            # save meta
            Description().edit_description(self.__wzh.description_token, dict(meta=meta))

            if not new_stages:
                # no resolved stages; signal abort
                return dict()

            # resolve type and data source for generated stages
            self.__wzh.sanitise_stages(new_stages)

            # register dependency
            self.__wzh.set_stage_dependency(new_stages)

            # insert new stages to stage list
            stage_gap = next_stage_index + 1
            stages = cleared_stages[:stage_gap] + new_stages + cleared_stages[stage_gap:]

            # update description record
            Description().edit_description(self.__wzh.description_token, dict(stages=stages))

        return False

    def get_ena_sequence_stages(self, next_stage_index):
        """
        stage callback function: resolves stages based on study type value
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.__wzh.description_token)

        stages = description["stages"]
        attributes = description["attributes"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        study_type = attributes.get("study_type", dict()).get("study_type", str())

        if not study_type:
            # no study type specified, we can't really do anything but signal abort
            return dict()

        # re-validate dependency if necessary

        meta = description.get("meta", dict())
        study_type_old = meta.get(stage["ref"] + "_study_type", None)

        # remove stages dependent on 'study_type' - remove resolved stages preceding study_type
        if not study_type_old == study_type:
            cleared_stages = self.__wzh.remove_stage_dependency(next_stage_index)

            # get new dynamic stages based on user current choice
            new_stages = list()

            # get protocols
            protocols = ISAHelpers().get_protocols_parameter_values(study_type)

            # get study assay schema
            schema_fields = DataSchemas("COPO").get_ui_template_node(study_type)

            # get message dictionary
            message_dict = self.__wzh.wiz_message

            for pr in protocols:
                if len(pr.get("parameterValues", list())) > 0:

                    title = pr.get("name", str()).title()
                    ref = pr.get("name", str()).replace(" ", "_")
                    message = message_dict.get(ref + "_message", dict()).get("text", str())

                    stage_dict = dict(title=title,
                                      ref=ref,
                                      message=message,
                                      items=list()
                                      )

                    for f in schema_fields:
                        if f['ref'] in pr.get("parameterValues", list()):
                            if f.get('show_in_form', False):
                                f["id"] = f['id'].strip(".").rsplit(".", 1)[1]
                                f["label"] = htags.trim_parameter_value_label(f["label"])

                                # convert select type controls to copo custom select
                                if f.get("control", str()) == "select":
                                    f["control"] = "copo-multi-select"
                                    f["data_maxItems"] = 1

                                stage_dict.get("items").append(f)

                    new_stages.append(stage_dict)

            # retain user choice for future reference
            meta[stage["ref"] + "_study_type"] = study_type

            # save meta
            Description().edit_description(self.__wzh.description_token, dict(meta=meta))

            if not new_stages:
                # no resolved stages; signal abort
                return dict()

            # resolve type and data source for generated stages
            self.__wzh.sanitise_stages(new_stages)

            # register dependency
            self.__wzh.set_stage_dependency(new_stages)

            # insert new stages to stage list
            stage_gap = next_stage_index + 1
            stages = cleared_stages[:stage_gap] + new_stages + cleared_stages[stage_gap:]

            # update description record
            Description().edit_description(self.__wzh.description_token, dict(stages=stages))

        return False

    def perform_datafile_generation(self, next_stage_index):
        """
        stage callback function: to initiate display of attributes for files in bundle
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.__wzh.description_token)
        stages = description["stages"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        return stage

    def perform_datafile_pairing(self, next_stage_index):
        """
        stage callback function: determines if the pairing of datafiles should be performed given the 'library_layout'
        :param next_stage_index:
        :return:
        """

        description = Description().GET(self.__wzh.description_token)
        stages = description["stages"]
        attributes = description["attributes"]
        meta = description.get("meta", dict())

        # validate stage
        stage = dict()

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        # first, target repository
        relevant_repos = ["ena"]  # add a repo to this list if it requires datafile pairing

        target_repository = attributes.get("target_repository", dict()).get("deposition_context", str())

        if target_repository not in relevant_repos:
            # no items to pair, clear any previous pairing information
            self.remove_pairing_info(stage["ref"], attributes, meta)

            return False

        # get records in bundle
        records = cursor_to_list(DataFile().get_collection_handle().find({"$and": [
            {"description_token": self.__wzh.description_token, 'deleted': d_utils.get_not_deleted_flag()},
            {'description.attributes.library_construction': {"$exists": True}}]},
            {'description.attributes.library_construction': 1, 'name': 1}))

        if not records:
            # no items to pair, clear any previous pairing information
            self.remove_pairing_info(stage["ref"], attributes, meta)

            return False

        df = pd.DataFrame(records)
        df._id = df['_id'].astype(str)
        df.index = df._id

        df['pairing'] = df['description'].apply(
            lambda x: x.get('attributes', dict()).get('library_construction', dict()).get('library_layout', np.nan))

        df = df.dropna()
        df['pairing'] = df.pairing.str.upper()

        df = df[df['pairing'] == 'PAIRED']

        if not len(df):
            # no items to pair, clear any previous pairing information
            self.remove_pairing_info(stage["ref"], attributes, meta)

            return False

        # remove extraneous columns
        df = df.drop(columns=['description'])

        if not len(df) % 2 == 0:
            stage["error"] = "Pairing requires even number of datafiles!"
            stage["refresh_wizard"] = True
        else:
            # get previously pairing candidates
            paired_candidates_old = meta.get(stage["ref"] + "_paired_candidates", list())
            paired_candidates = list(df.index)

            paired_candidates_old.sort()
            paired_candidates.sort()

            if not paired_candidates_old == paired_candidates:
                stage["refresh_wizard"] = True

            # if there's a valid stored map, use it
            stage_data = list()
            saved_copy = attributes.get(stage["ref"], list())

            if saved_copy:
                stored_pairs_df = pd.DataFrame(saved_copy)
                stored_pairs_list = list(stored_pairs_df._id) + list(stored_pairs_df._id2)
                stored_pairs_list.sort()

                if stored_pairs_list == paired_candidates:
                    df_dict = df.to_dict()
                    df_dict = df_dict["name"]

                    stored_pairs_df["name"] = stored_pairs_df['_id'].apply(lambda x: str(df_dict[x]))
                    stored_pairs_df["name2"] = stored_pairs_df['_id2'].apply(lambda x: str(df_dict[x]))

                    df_result = stored_pairs_df[['name', 'name2']]
                    df_result.columns = ['file1', 'file2']

                    stage_data = df_result.to_dict('records')

            if not stage_data:
                # define fresh pairing map

                # sort by file name to reflect pairing
                df = df.sort_values(by=['name'])

                s_even = df._id.iloc[1::2]
                s_odd = df._id.iloc[::2]
                df_odd = df[df.index.isin(s_odd)].copy()
                df_even = df[df.index.isin(s_even)].copy()
                df_even['_id2'] = df_even['_id']
                df_even['name2'] = df_even['name']
                df_even = df_even[['_id2', 'name2']]
                df_odd = df_odd[['_id', 'name']]
                df_odd.index = range(0, len(df_odd))
                df_even.index = range(0, len(df_even))
                df_result = pd.concat([df_odd, df_even], axis=1, join_axes=[df_odd.index])
                saved_copy = df_result[['_id', '_id2']].to_dict('records')
                df_result = df_result[['name', 'name2']]
                df_result.columns = ['file1', 'file2']

                stage_data = df_result.to_dict('records')

            stage["data"] = stage_data

            # save state
            attributes[stage["ref"]] = saved_copy
            meta[stage["ref"] + "_paired_candidates"] = paired_candidates

            save_dict = dict(attributes=attributes, meta=meta)
            Description().edit_description(self.__wzh.description_token, save_dict)

            stage["message"] = self.__wzh.wiz_message["datafiles_pairing_message"]["text"]

        return stage

    def remove_pairing_info(self, stage_ref, attributes, meta):
        attributes[stage_ref] = list()
        meta[stage_ref + "_paired_candidates"] = list()
        save_dict = dict(attributes=attributes, meta=meta)

        Description().edit_description(self.__wzh.description_token, save_dict)
