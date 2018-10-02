""" module defines callbacks for wizard stages """
__author__ = 'etuka'

import pandas as pd

from dal.copo_da import Description
from dal.copo_base_da import DataSchemas
from converters.ena.copo_isa_ena import ISAHelpers
import web.apps.web_copo.templatetags.html_tags as htags
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
