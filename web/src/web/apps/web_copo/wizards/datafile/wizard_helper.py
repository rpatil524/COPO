__author__ = 'etuka'

import difflib
import numpy as np
import pandas as pd
from bson import ObjectId
from dal import cursor_to_list
from operator import itemgetter
from django.conf import settings

from dal.copo_base_da import DataSchemas
from dal.copo_da import DataFile, Description
import web.apps.web_copo.lookup.lookup as lkup
from converters.ena.copo_isa_ena import ISAHelpers
import web.apps.web_copo.templatetags.html_tags as htags
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.lookup.copo_enums import Loglvl, Logtype
from web.apps.web_copo.schemas.utils.data_utils import DecoupleFormSubmission

lg = settings.LOGGER


class WizardHelper:
    def __init__(self, description_token, profile_id):
        self.description_token = description_token
        self.profile_id = self.set_profile_id(profile_id)

        self.key_split = "___0___"
        self.object_key = settings.DATAFILE_OBJECT_PREFIX + self.description_token
        self.store_name = settings.DATAFILE_OBJECT_STORE

    def initiate_description(self, description_targets):
        """
        using the description targets as basis, function attempts to initiate a new description...
        :param description_targets: datafiles to be described
        :return:
        """

        initiate_result = dict(status="success", message="")
        initiate_result['wiz_message'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["datafile_wizard"])["properties"]

        if self.description_token:  # this is a call to reload an existing description; validate token

            # start by getting the description record
            description = Description().GET(self.description_token)

            if not description:
                # description record doesn't exist; flag error
                initiate_result['status'] = "error"
                initiate_result[
                    'message'] = "Couldn't reload description. " \
                                 "The description may have expired, or the associated token is invalid."
                del initiate_result['wiz_message']
            else:
                # reset timestamp, which will also reset the 'grace period' for the description
                Description().edit_description(self.description_token, dict(created_on=d_utils.get_datetime()))
                initiate_result['description_token'] = self.description_token

        else:  # this is a call to instantiate a new description; validate bundle, create record, issue token

            validation_result = self.validate_description_targets(description_targets)

            for k in validation_result.keys():
                initiate_result[k] = validation_result[k]

            if initiate_result['status'] == "success":
                # get start stages
                wizard_stages = d_utils.json_to_pytype(lkup.WIZARD_FILES["start"])['properties']

                # resolve type and data source for generated stages
                self.sanitise_stages(wizard_stages)

                meta = dict(description_targets=[x.split("row_")[-1] for x in description_targets],
                            rendered_stages=list())

                description_token = str(
                    Description().create_description(stages=wizard_stages, attributes=dict(),
                                                     profile_id=self.profile_id,
                                                     component='datafile', meta=meta)['_id'])

                initiate_result['description_token'] = description_token
            else:
                del initiate_result['wiz_message']

        return initiate_result

    def validate_description_targets(self, description_targets):
        """
        function validates targets for 'bundling' suitability
        :param description_targets:
        :return:
        """

        validation_result = dict(status="success", message="")

        # all okay with single file
        if len(description_targets) == 1:
            return validation_result

        return validation_result

        # validate multiple files - maybe no need for complex validation, just warn the user that they may be conflicting metadata, but allow the description to on
        validation_result['status'] = 'error'
        validation_result['message'] = 'Not supporting bundling at the moment!'

        return validation_result

    def resolve_select_data(self, stages):
        """
        function resolves data source for select-type controls
        :param stages:
        :return:
        """

        for stage in stages:
            for st in stage.get("items", list()):
                if "option_values" in st:
                    st["option_values"] = htags.get_control_options(st)

        return True

    def set_profile_id(self, profile_id):
        p_id = profile_id
        if not p_id and self.description_token:
            description = Description().GET(self.description_token)
            p_id = description.get("profile_id", str())

        return p_id

    def set_items_type(self, stages):
        """
        function ensures all stage controls have a type
        :param stages:
        :return:
        """

        for stage in stages:
            for st in stage.get("items", list()):
                if not st.get("type"):
                    st["type"] = "string"

                # also get id in the desired order
                st["id"] = st["id"].split(".")[-1]

        return True

    def sanitise_stages(self, stages):
        self.resolve_select_data(stages)
        self.set_items_type(stages)

        return True

    def set_stage_dependency(self, stages):
        """
        for dynamically generated stages, function sets their dependency
        :param stages:
        :return:
        """

        for stage in stages:
            stage['dependency'] = "resolved_stage"

        return True

    def remove_stage_dependency(self, indx):
        """
        function removes resolved stages preceding 'indx'
        :param stages:
        :param indx:
        :return:
        """

        description = Description().GET(self.description_token)

        stages = description["stages"]

        indx = indx + 1

        safe_stages = stages[:indx]
        targeted_stages = stages[indx:]
        cleared_stages = [st for st in targeted_stages if not st.get('dependency', str()) == 'resolved_stage']

        return safe_stages + cleared_stages

    def resolve_next_stage(self, auto_fields):
        """
        given data from a stage, function tries to resolve the next stage to be displayed to the user by the wizard
        :param auto_fields:
        :return:
        """

        next_stage_dict = dict(abort=False)
        current_stage = auto_fields.get("current_stage", str())

        if not current_stage:
            # there's no way of telling what next stage is requested; send signal to abort the wizard
            next_stage_dict["abort"] = True
            return next_stage_dict

        # get the description record
        description = Description().GET(self.description_token)

        if not description:
            # invalid description; send signal to abort the wizard
            next_stage_dict["abort"] = True
            return next_stage_dict

        stages = description["stages"]
        attributes = description["attributes"]

        # get next stage index
        next_stage_index = [indx for indx, stage in enumerate(stages) if stage['ref'] == current_stage]

        if not next_stage_index and not current_stage == 'intro':  # invalid current stage; send abort signal
            next_stage_dict["abort"] = True
            return next_stage_dict

        next_stage_index = next_stage_index[0] + 1 if len(next_stage_index) else 0

        # save in-coming stage data, check for changes, re-validate wizard, serve next stage
        previous_data = dict()
        if next_stage_index > 0:  # we don't want to save 'intro' stage attributes;
            previous_data = attributes.get(current_stage, dict())
            current_data = DecoupleFormSubmission(auto_fields,
                                                  d_utils.json_to_object(
                                                      stages[next_stage_index - 1]).items).get_schema_fields_updated()
            # save current stage data
            attributes[current_stage] = current_data

            # save attributes
            Description().edit_description(self.description_token, dict(attributes=attributes))

        # get next stage
        next_stage_dict['stage'] = self.serve_stage(next_stage_index)

        # refresh values from db after obtaining next stage, as this operation has the potential of
        # modifying things such as introducing new stages
        description = Description().GET(self.description_token)
        attributes = description["attributes"]
        meta = description.get("meta", dict())

        if not next_stage_dict['stage']:
            # no stage to retrieve, this should signal end
            return next_stage_dict

        if next_stage_index > 0 and previous_data and not (previous_data == current_data):
            # stage data has changed, refresh wizard
            next_stage_dict['refresh_wizard'] = True

            # ...also, update rendered stages list
            if current_stage in meta["rendered_stages"]:
                srch_indx = meta["rendered_stages"].index(current_stage)
                meta["rendered_stages"] = meta["rendered_stages"][:srch_indx + 1]

            # remove store object, if any, associated with this description
            Description().remove_store_object(store_name=self.store_name, object_key=self.object_key)

            # update meta
            meta["generated_columns"] = list()

        # build data dictionary for stage
        if next_stage_dict['stage']['ref'] in attributes and "data" not in next_stage_dict['stage']:
            next_stage_dict['stage']['data'] = attributes[next_stage_dict['stage']['ref']]
        # save rendered stage
        if next_stage_dict['stage']['ref']:
            meta["last_rendered_stage"] = next_stage_dict['stage']['ref']

            if not next_stage_dict['stage']['ref'] in meta["rendered_stages"]:
                meta["rendered_stages"].append(next_stage_dict['stage']['ref'])

        Description().edit_description(self.description_token, dict(meta=meta))

        return next_stage_dict

    def serve_stage(self, next_stage_index):
        """
        function determines how a given stage should be served
        :param stage:
        :return:
        """

        # start by getting the description record
        description = Description().GET(self.description_token)
        stages = description["stages"]

        stage = dict()

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        while True:
            if "callback" in stage:
                # resolve stage from callback function
                try:
                    stage = getattr(WizardHelper, stage["callback"])(self, next_stage_index)
                except:
                    stage = dict()

            # we expect a stage that cannot be directly rendered to return a False, thus prompting
            # progression to the next
            # stage in the sequence of stages (see below). Such non-renderable stages
            # may just be processes or stubs meant for resolving other dynamically culled stages
            if isinstance(stage, dict):
                break

            # refresh stages and index of the next stage - why do this? callbacks can potentially modify things
            description = Description().GET(self.description_token)
            stages = description["stages"]

            next_stage_index = next_stage_index + 1  # progress to next index in this very quest for a valid next stage

            if next_stage_index < len(stages):
                stage = stages[next_stage_index]
            else:
                stage = dict()
                break

        return stage

    def get_description_stages(self, next_stage_index):
        """
        stage callback function: resolves stages based on repository value
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.description_token)

        stages = description["stages"]
        attributes = description["attributes"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        target_repository = attributes.get("target_repository", dict()).get("target_repository", str())

        if not target_repository:
            # no target repository specified, we can't really do anything but signal abort
            return dict()

        # re-validate dependency if necessary

        meta = description.get("meta", dict())
        target_repository_old = meta.get(stage["ref"] + "_target_repository", None)

        # remove dependency - remove resolved stages preceding target_repository
        if not target_repository_old == target_repository:
            cleared_stages = self.remove_stage_dependency(next_stage_index)

            # get new dynamic stages based on user current choice
            new_stages = d_utils.json_to_pytype(lkup.WIZARD_FILES[target_repository])['properties']

            # retain user choice for future reference
            meta[stage["ref"] + "_target_repository"] = target_repository

            # save meta
            Description().edit_description(self.description_token, dict(meta=meta))

            if not new_stages:
                # no resolved stages; signal abort
                return dict()

            # resolve type and data source for generated stages
            self.sanitise_stages(new_stages)

            # register dependency
            self.set_stage_dependency(new_stages)

            # insert new stages to stage list
            stage_gap = next_stage_index + 1
            stages = cleared_stages[:stage_gap] + new_stages + cleared_stages[stage_gap:]

            # update description record
            Description().edit_description(self.description_token, dict(stages=stages))

        return False

    def get_ena_sequence_stages(self, next_stage_index):
        """
        stage callback function: resolves stages based on study type value
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.description_token)

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
            cleared_stages = self.remove_stage_dependency(next_stage_index)

            # get new dynamic stages based on user current choice
            new_stages = list()

            # get protocols
            protocols = ISAHelpers().get_protocols_parameter_values(study_type)

            # get study assay schema
            schema_fields = getattr(DataSchemas("COPO").get_ui_template_as_obj().copo, study_type).fields

            # get message dictionary
            message_dict = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["datafile_wizard"])["properties"]

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
                        if f.ref in pr.get("parameterValues", list()):
                            if f.show_in_form:
                                elem = htags.get_element_by_id(f.id)
                                elem["id"] = elem['id'].strip(".").rsplit(".", 1)[1]

                                # convert select type controls to copo custom select
                                if elem.get("control", str()) == "select":
                                    elem["control"] = "copo-multi-select"
                                    elem["data_maxItems"] = 1

                                del elem['ref']
                                stage_dict.get("items").append(elem)

                    new_stages.append(stage_dict)

            # retain user choice for future reference
            meta[stage["ref"] + "_study_type"] = study_type

            # save meta
            Description().edit_description(self.description_token, dict(meta=meta))

            if not new_stages:
                # no resolved stages; signal abort
                return dict()

            # resolve type and data source for generated stages
            self.sanitise_stages(new_stages)

            # register dependency
            self.set_stage_dependency(new_stages)

            # insert new stages to stage list
            stage_gap = next_stage_index + 1
            stages = cleared_stages[:stage_gap] + new_stages + cleared_stages[stage_gap:]

            # update description record
            Description().edit_description(self.description_token, dict(stages=stages))

        return False

    def perform_datafile_generation(self, next_stage_index):
        """
        stage callback function: to initiate display of attributes for files in bundle
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.description_token)
        stages = description["stages"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        return stage

    def get_description_bundle(self):
        """
        function returns description bundle for UI display
        :return:
        """

        data_set = list()

        description = Description().GET(self.description_token)
        bundle_ids = description.get("meta", dict()).get("description_targets", list())
        object_ids = [ObjectId(x) for x in bundle_ids]

        records = cursor_to_list(DataFile().get_collection_handle().find({"_id": {"$in": object_ids}}, {'name': 1}))

        if len(records):
            df = pd.DataFrame(records)
            df['_id'] = df._id.astype(str)
            df["DT_RowId"] = df._id
            df["chk_box"] = ''
            df.DT_RowId = 'row_' + df.DT_RowId
            df = df.drop('_id', axis='columns')
            data_set = df.to_dict('records')

        return data_set

    def generate_discrete_attributes(self):
        """
        function generate discrete attributes for individual sample editing
        :return:
        """

        # if there's stored object, use that rather than generating dataset from scratch
        # stored_data_set = list()
        # try:
        #     with pd.HDFStore(self.store_name) as store:
        #         if self.object_key in store:
        #             stored_data_set = store[self.object_key].to_dict('records')
        # except Exception as e:
        #     print('HDF5 Access Error: ' + str(e))

        description = Description().GET(self.description_token)
        stored_columns = description["meta"].get("generated_columns", list())

        # if stored_columns and stored_data_set:
        #     return dict(columns=stored_columns, rows=stored_data_set)

        # object type controls and their corresponding schemas
        object_array_controls = [
            "copo-characteristics",
            "copo-comment",
            "copo-environmental-characteristics",
            "copo-phenotypic-characteristics"
        ]
        object_array_schemas = [
            d_utils.get_copo_schema("material_attribute_value"),
            d_utils.get_copo_schema("comment"),
            d_utils.get_copo_schema("environment_variables"),
            d_utils.get_copo_schema("phenotypic_variables")
        ]

        # data and columns lists
        data = list()

        columns = [dict(title=' ', name='s_n', data="s_n", className='select-checkbox'),
                   dict(title='Name', name='name', data="name")]

        attributes = description["attributes"]
        meta = description["meta"]

        # get rendered stages
        rendered_stages_ref = meta["rendered_stages"]
        rendered_stages = [x for x in description["stages"] if x['ref'] in rendered_stages_ref]

        # aggregate items and data from all rendered stages
        datafile_items = list()
        datafile_attributes = dict()  # will be used for generating tabular data
        df_attributes = dict()  # will be copied to records with no previous description data

        for st in rendered_stages:
            apply_to_all = st.get("apply_to_all", False)
            df_attributes[st["ref"]] = attributes.get(st["ref"], dict())
            for item in st.get("items", list()):
                if str(item.get("hidden", False)).lower() == "false":
                    atrib_val = attributes.get(st["ref"], dict()).get(item["id"], str())
                    item["id"] = st["ref"] + self.key_split + item["id"]
                    item["apply_to_all"] = apply_to_all
                    datafile_attributes[item["id"]] = atrib_val
                    datafile_items.append(item)

        schema_df = pd.DataFrame(datafile_items)

        for index, row in schema_df.iterrows():
            resolved_data = htags.resolve_control_output(datafile_attributes, row)
            label = row["label"]

            # 'apply_to_all' columns are flagged as non-editable in table view
            column_class = 'locked-column' if row.get("apply_to_all") else ''

            if row['control'] in object_array_controls:
                # get object-type-control schema
                control_index = object_array_controls.index(row['control'])
                control_df = pd.DataFrame(object_array_schemas[control_index])
                control_df['id2'] = control_df['id'].apply(lambda x: x.split(".")[-1])

                if resolved_data:
                    object_array_keys = [list(x.keys())[0] for x in resolved_data[0]]
                    object_array_df = pd.DataFrame([dict(pair for d in k for pair in d.items()) for k in resolved_data])

                    for o_indx, o_row in object_array_df.iterrows():
                        # add primary header/value - first element in object_array_keys taken as header, second value
                        # e.g., category, value in material_attribute_value schema
                        # a slightly different implementation will be needed for an object-type-control
                        # that require a different display structure

                        class_name = self.key_split.join((row.id, str(o_indx), object_array_keys[1]))
                        columns.append(dict(title=label + "[{0}]".format(o_row[object_array_keys[0]]), data=class_name))
                        data.append({class_name: o_row[object_array_keys[1]]})

                        # add other headers/values e.g., unit in material_attribute_value schema
                        for subitem in object_array_keys[2:]:
                            class_name = self.key_split.join((row.id, str(o_indx), subitem))
                            columns.append(dict(
                                title=control_df[control_df.id2.str.lower() == subitem].iloc[0].label, data=class_name))
                            data.append({class_name: o_row[subitem]})
            else:
                # account for array types
                if row["type"] == "array":
                    for tt_indx, tt_val in enumerate(resolved_data):
                        shown_keys = (row["id"], str(tt_indx))
                        class_name = self.key_split.join(shown_keys)
                        columns.append(
                            dict(title=label + "[{0}]".format(str(tt_indx + 1)), data=class_name,
                                 className=column_class))

                        if isinstance(tt_val, list):
                            tt_val = ', '.join(tt_val)

                        data_attribute = dict()
                        data_attribute[class_name] = tt_val
                        data.append(data_attribute)
                else:
                    shown_keys = row["id"]
                    class_name = shown_keys
                    columns.append(dict(title=label, data=class_name, className=column_class))
                    val = resolved_data

                    if isinstance(val, list):
                        val = ', '.join(val)

                    data_attribute = dict()
                    data_attribute[class_name] = val
                    data.append(data_attribute)

        # retrieve datafiles
        bundle_ids = description.get("meta", dict()).get("description_targets", list())
        object_ids = [ObjectId(x) for x in bundle_ids]
        records = cursor_to_list(
            DataFile().get_collection_handle().find({"_id": {"$in": object_ids}}, {'name': 1, 'description': 1}))

        datafiles_df = pd.DataFrame(records)
        datafiles_df['_id'] = datafiles_df._id.astype(str)
        datafiles_df["DT_RowId"] = datafiles_df._id
        datafiles_df.DT_RowId = 'row_' + datafiles_df.DT_RowId
        datafiles_df = datafiles_df.drop(['_id', 'description'], axis='columns')

        # save description for targets
        # df_description = dict(attributes=df_attributes, stages=rendered_stages)
        # df_description = dict(description=df_description)
        # DataFile().get_collection_handle().update_many(
        #     {"_id": {"$in": object_ids}},
        #     {'$set': df_description})

        # build display dataset

        data_record = dict(pair for d in data for pair in d.items())
        for k, v in data_record.items():
            datafiles_df[k] = v

        datafiles_df.insert(loc=0, column='s_n', value=[''] * len(bundle_ids))  # - for sorting

        # override generated dataframe with record specific values, if set
        bulk = DataFile().get_collection_handle().initialize_unordered_bulk_op()
        for rec in records:
            rec_description = rec['description']
            rec_description['stages'] = rendered_stages  # refresh record's stage list

            if rec_description.get("attributes", dict()) == dict():  # record's got no description data; use wizard data
                rec_description['attributes'] = df_attributes
            else:
                for index, row in schema_df.iterrows():
                    st_key_split = row.id.split(self.key_split)  # will give [0]: stage id / [1]: control id

                    # is stage data present in record's attribute
                    if st_key_split[0] not in rec_description['attributes']:  # use wizard data
                        rec_description['attributes'][st_key_split[0]] = df_attributes[st_key_split[0]]
                        continue

                    # is control data present in stage data or is it a control whose data is shared by all?
                    if st_key_split[1] not in rec_description['attributes'][
                        st_key_split[0]] or row.apply_to_all:  # use wizard data
                        rec_description['attributes'][st_key_split[0]][st_key_split[1]] = \
                            df_attributes[st_key_split[0]][st_key_split[1]]
                        continue

                    # any discrepancy with wizard data?
                    if rec_description['attributes'][st_key_split[0]][st_key_split[1]] == \
                            df_attributes[st_key_split[0]][st_key_split[1]]:
                        continue

                    # record's got relevant data, we need to resolve it and update datafiles_df
                    retained_row_id = row.id
                    row.id = st_key_split[1]
                    rec_resolved_data = htags.resolve_control_output(rec_description['attributes'][st_key_split[0]], row)
                    df_resolved_data = htags.resolve_control_output(df_attributes[st_key_split[0]], row)

                    if row.control in object_array_controls:
                        if df_resolved_data:  # use data from wizard to refresh record's data
                            if not rec_resolved_data:  # copy across wizard's data
                                rec_description['attributes'][st_key_split[0]][st_key_split[1]] = \
                                    df_attributes[st_key_split[0]][st_key_split[1]]
                                continue

                            new_list = list()  # form a new list to align with wizard's data
                            object_array_keys = [list(x.keys())[0] for x in df_resolved_data[0]]
                            df_object_array_df = pd.DataFrame(
                                [dict(pair for d in k for pair in d.items()) for k in df_resolved_data])
                            rec_object_array_df = pd.DataFrame(
                                [dict(pair for d in k for pair in d.items()) for k in rec_resolved_data])

                            for ii, rr in df_object_array_df.iterrows():
                                new_list[ii] = df_attributes[st_key_split[0]][st_key_split[1]][ii]
                                matched_loc = list(
                                    rec_object_array_df[rec_object_array_df[object_array_keys[0]] == row[object_array_keys[0]]].index)

                                if matched_loc:
                                    # get the first element matched
                                    new_list[ii] = rec_description['attributes'][st_key_split[0]][st_key_split[1]][matched_loc[0]]
                                    class_name = self.key_split.join((row.id, str(ii), object_array_keys[1]))
                                    datafiles_df.loc[
                                        datafiles_df.loc[datafiles_df['DT_RowId'].isin(
                                            ["row_" + str(rec["_id"])])].index, class_name] = rec_object_array_df.loc[matched_loc[0], object_array_keys[1]]

                            rec_description['attributes'][st_key_split[0]][st_key_split[1]] = new_list
                    else:
                        # account for array types
                        if row.type == "array":
                            for tt_indx in range(len(df_resolved_data)):  # use wizard's length to incorporate changes
                                if tt_indx < len(rec_resolved_data):
                                    shown_keys = (retained_row_id, str(tt_indx))
                                    class_name = self.key_split.join(shown_keys)
                                    tt_val = rec_resolved_data[tt_indx]

                                    if isinstance(tt_val, list):
                                        tt_val = ', '.join(tt_val)

                                    datafiles_df.loc[
                                        datafiles_df.loc[datafiles_df['DT_RowId'].isin(
                                            ["row_" + str(rec["_id"])])].index, class_name] = tt_val
                        else:
                            class_name = retained_row_id
                            val = rec_resolved_data

                            if isinstance(val, list):
                                val = ', '.join(val)

                            datafiles_df.loc[
                                datafiles_df.loc[datafiles_df['DT_RowId'].isin(
                                    ["row_" + str(rec["_id"])])].index, class_name] = val

        # generate dataset for UI
        data_set = datafiles_df.to_dict('records')

        # save generated dataset
        # try:
        #     with pd.HDFStore(self.store_name) as store:
        #         store[self.object_key] = pd.DataFrame(data_set)
        # except Exception as e:
        #     lg.log('HDF5 Access Error: ' + str(e), level=Loglvl.ERROR, type=Logtype.FILE)

        # save generated columns
        # meta = description.get("meta", dict())
        # meta["generated_columns"] = columns

        # save meta
        # Description().edit_description(self.description_token, dict(meta=meta))

        return dict(columns=columns, rows=data_set)

    def discard_description(self, description_targets):
        object_list = [ObjectId(x.split("row_")[-1]) for x in description_targets]

        DataFile().get_collection_handle().update_many(
            {"_id": {"$in": object_list}}, {"$set": {"description": dict()}}
        )
