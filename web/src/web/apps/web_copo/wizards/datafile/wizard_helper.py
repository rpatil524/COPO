__author__ = 'etuka'

from bson import ObjectId
from dal import cursor_to_list

import difflib
from operator import itemgetter
import web.apps.web_copo.lookup.lookup as lkup
import web.apps.web_copo.schemas.utils.data_utils as d_utils
import web.apps.web_copo.templatetags.html_tags as htags
from converters.ena.copo_isa_ena import ISAHelpers
from dal.copo_base_da import DataSchemas
from dal.copo_da import DataFile, Description
from dal.figshare_da import Figshare
from web.apps.web_copo.schemas.utils.data_utils import DecoupleFormSubmission
from web.apps.web_copo.schemas.utils import data_utils


class WizardHelper:
    def __init__(self, description_token=str(), description_targets=list()):
        self.datafile_id = str()
        self.description_token = description_token
        self.description_targets = description_targets
        self.targets_datafiles = self.set_targets_datafiles()
        self.profile_id = data_utils.get_current_request().session['profile_id']
        self.rendered_stages = list()

    def set_rendered_stages(self, rendered_stages=list()):
        """
        sets stages rendered on the UI
        :param rendered_stages:
        :return:
        """
        self.rendered_stages = rendered_stages

    def get_rendered_stages(self):
        return self.rendered_stages

    def set_targets_datafiles(self):
        targets_datafiles = dict()

        object_list = list()
        for target in self.description_targets:
            object_list.append(ObjectId(target["recordID"]))

        datafiles = cursor_to_list(DataFile().get_collection_handle().find({"_id": {"$in": object_list}}))

        for df in datafiles:
            targets_datafiles[str(df["_id"])] = df

        return targets_datafiles

    def update_targets_datafiles(self):
        bulk = DataFile().get_collection_handle().initialize_unordered_bulk_op()
        for k, v in self.targets_datafiles.items():
            bulk.find({'_id': ObjectId(k)}).update({'$set': {"description": v.get("description", dict())}})
        bulk.execute()

    def set_datafile_id(self, datafile_id):
        self.datafile_id = datafile_id

    def set_description_targets(self, description_targets):
        self.description_targets = description_targets
        self.targets_datafiles = self.set_targets_datafiles()

    def get_description_token(self):
        return self.description_token

    def get_datafile_description(self):
        description = self.targets_datafiles.get(self.datafile_id, dict()).get("description", dict())

        for k in [dict(key="stages", type=list()), dict(key="attributes", type=dict())]:
            if k["key"] not in description:
                description[k["key"]] = k["type"]

        return description

    def get_datafile_attributes(self):
        return self.get_datafile_description().get("attributes")

    def get_datafile_stages(self):
        return self.get_datafile_description().get("stages")

    def get_datafile_stage(self, ref):
        stage = dict()
        stages = [x for x in self.get_datafile_stages() if x['ref'] == ref]
        if stages:
            stage = stages[0]

        return stage

    def get_batch_attributes(self):
        return Description().GET(self.description_token).get("attributes", dict())

    def set_batch_attributes(self, attributes):
        Description().edit_description(self.description_token, dict(attributes=attributes))

    def get_batch_stages(self):
        return Description().GET(self.description_token).get("stages", list())

    def set_batch_stages(self, stages):
        fields = dict(stages=list())

        # one or two other housekeeping tasks before saving stage

        # set default type, if not already set on stage items
        for stage in stages:
            stage = self.set_items_type(stage)
            fields.get("stages").append(stage)

        Description().edit_description(self.description_token, fields)

    def get_batch_stage(self, ref):
        stages = self.get_batch_stages()
        listed_stage = [indx for indx, stage in enumerate(stages) if stage['ref'] == ref]

        return stages[listed_stage[0]]

    def update_description(self, description):
        if self.datafile_id in self.targets_datafiles:
            self.targets_datafiles[self.datafile_id]["description"] = description

        return

    def activate_stage(self, elem):
        """
        function indicates that stage has been treated for rendering (by the wizard)
        :param elem: stage to be activated
        :return:
        """
        stages = self.get_batch_stages()
        listed_stage = [indx for indx, stage in enumerate(stages) if stage['ref'] == elem['ref']]

        elem['activated'] = True
        stages[listed_stage[0]] = elem
        self.set_batch_stages(stages)

    def deactivate_stage(self, elem):
        """
        function indicates that stage has been treated for rendering (by the wizard)
        :param elem: stage to be activated
        :return:
        """
        stages = self.get_batch_stages()
        listed_stage = [indx for indx, stage in enumerate(stages) if stage['ref'] == elem['ref']]

        if 'activated' in elem:
            del elem['activated']

        stages[listed_stage[0]] = elem
        self.set_batch_stages(stages)

    def is_activated(self, elem):
        """
        function checks if stage has previously been activated
        :param elem: the stage dictionary
        :return: boolean
        """

        return elem.get("activated", False)

    def is_stage_stub(self, elem):
        """
        function checks if stage (i.e. elem) is a stub (i.e. metadata for generating actual stages)
        :param elem: the stage dictionary
        :return:
        """

        return elem.get("is_stage_stub", False)

    def is_conditional_stage(self, elem):
        """
        function checks if the presentation of a stage (i.e. elem) is conditioned in some manner
        :param elem: the stage dictionary
        :return:
        """

        return elem.get("is_conditional_stage", False)

    def get_stage_data(self, stage_id):
        return self.get_datafile_attributes().get(stage_id, None)

    def refresh_targets_data(self):
        for indx, target in enumerate(self.description_targets):
            self.set_datafile_id(target["recordID"])
            self.description_targets[indx]["attributes"] = self.get_datafile_attributes()

        return self.description_targets

    def get_stage_display(self, stage):
        """
        function resolve UI components for stage
        :param stage: is the dictionary that captures the stage metadata
        :return: stage, with UI-ready components set
        """

        if "data" not in stage:
            stage['data'] = self.get_stage_data(stage['ref'])

        # resolve other html components

        if "items" in stage:
            for st in stage['items']:

                # resolve option_values for select-type controls,
                if "option_values" in st:
                    st["option_values"] = htags.get_control_options(st)

        stage_dict = dict(stage=stage)

        return stage_dict

    def display_stage(self, elem):
        """
        function decides if a stage should be displayed or not. it assumes that conditional stages have
        callbacks defined in order to resolve the validity of the condition.
        however, if no callback is defined, function defaults to a decision
        to display the stage (i.e., True), except in the case where the said stage is a 'stub' (stage used
        to generate other stages, but not themselves displayable), in that case function
        will always default to a False.
        :param elem: is the dictionary that captures the stage metadata
        :return: is a boolean; if true stage is displayed
        """

        display = True

        # define a parameter dictionary and collect any required parameter value here...
        # or elsewhere before before the actual call to the callback function
        param_dict = dict()

        # any restrictions imposed?
        if self.is_conditional_stage(elem):
            call_back_function = elem.get("callback", dict()).get("function", str())
            call_back_parameter = elem.get("callback", dict()).get("parameter", str())

            args = d_utils.get_args_from_parameter(call_back_parameter, param_dict)
            try:
                display = getattr(WizardHelper, call_back_function)(self, *args)
            except:
                pass

        # stage_stub are non-displayable
        if self.is_stage_stub(elem):
            display = False

        return display

    def fire_on_create_triggers(self, stage):
        """
        functions fires defined triggers, where requested, to set initial values and/or controls.
        NB:this should only be needed the first time the stage is activated for display, as the display agent (UI)
        takes care of firing the trigger after display
        :param elem: stage dictionary
        :return:
        """

        # define param dictionary and collect relevant parameter values for callback functions
        param_dict = dict()

        param_dict["stage"] = stage  # parameter value
        param_dict["stage_ref"] = stage.get("ref", str())  # parameter value

        for sti in stage.get("items", list()):
            param_dict["item_id"] = sti['id']  # parameter value

            trigger_elem = sti.get("trigger", dict())
            if trigger_elem and trigger_elem.get("fire_on_create", False):
                param_dict["new_value"] = None  # parameter value
                param_dict["old_value"] = None  # parameter value

                # get callback function
                call_back_function = trigger_elem.get("callback", dict()).get("function", str())

                # get callback parameters and sort out callback function arguments
                call_back_parameter = trigger_elem.get("callback", dict()).get("parameter", str())

                # resolve relevant arguments for this call
                args = d_utils.get_args_from_parameter(call_back_parameter, param_dict)

                try:
                    getattr(WizardHelper, call_back_function)(self, *args)
                except:
                    pass

    def get_stages_display(self):
        """
        function displays all previously activated stages
        :return: stages to be displayed
        """
        stages = list()
        batch_stages = self.get_batch_stages()

        for sta in batch_stages:
            if self.display_stage(sta) and self.is_activated(sta):
                stages.append(self.get_stage_display(sta))

        return stages

    def get_item_stage_display(self, stage_id, target_id=str()):
        """
        function resolves a 'localised' stage display for an item in the description batch
        if a target_id isn't supplied, then a 'default' form (i.e., without user-specified data) is returned
        :param stage_id: id of the requested stage
        :param target_id: id of the item for which the stage html is requested
        :return: stage html
        """
        # get target stage dictionary
        stage = self.get_batch_stage(stage_id)

        if target_id:
            self.set_datafile_id(target_id)

        stage_html = None
        if self.display_stage(stage) and self.is_activated(stage):
            if not target_id:
                stage["data"] = None
            stage_html = self.get_stage_display(stage)

        return stage_html

    def resolve_deposition_context(self):
        """
        this returns an inferred deposition destination for a datafile.
        we assume here that the target destination of the file can be inferred based on its type
        :param:
        :return string destination:
        """

        # get file details
        datafile = DataFile().get_record(self.datafile_id)
        ft = datafile.get("file_type", "unknown")

        if ft == '':
            ft = 'unknown'

        deposition_context = 'default'

        # match against documented destinations
        for k, v in lkup.REPO_FILE_EXTENSIONS.items():
            if ft in v:
                deposition_context = k
                break

        return deposition_context

    def update_datafile_attributes(self, stage_description):
        if stage_description:
            description = self.get_datafile_description()

            # soft validation...only allow stage attribute entry if there is an actual value assigned
            save_stage = False
            for k, v in stage_description['data'].items():
                if v:
                    save_stage = True
                    break

            if save_stage:
                description['attributes'][stage_description['ref']] = stage_description['data']

            self.update_description(description)

    def update_datafile_stage(self, stages):
        if stages:
            description = self.get_datafile_description()
            description['stages'] = stages

            self.update_description(description)

    def initiate_process(self):
        process = dict()

        """
        In initiating a description process, it may well be the case that the target items (to be described) already
        have metadata recorded (from a previous description session). Try bootstrapping the
        current description using available metadata. Specifically, the target (item in description bundle)
        with the highest number of (recorded) stages takes precedence over others, and, thus is used for initiating
        the current description. Of course, there are obvious implications to this. For instance, do we assume
        other (potentially less described) items in the current bundle adopt the 'difference' in the metadata? Also,
        we poll the attributes metadata from every target, the result of which might be used in making suggestions
        for new items added to the bundle at a later stage in the current description pipeline.
        """

        batch_stages = list()
        targets_attributes = list()
        for target in self.description_targets:
            self.set_datafile_id(target["recordID"])

            datafile_attributes = self.get_datafile_attributes()
            if datafile_attributes:
                targets_attributes.append(datafile_attributes)

            if len(self.get_datafile_stages()) > len(batch_stages):
                batch_stages = self.get_datafile_stages()

        # create a description instance, hence token
        # but first, sort out the pooled attributes

        batch_attributes = dict()
        for attribute in targets_attributes:
            for key, value in attribute.items():
                if not key in batch_attributes:
                    batch_attributes[key] = list()

                batch_attributes[key].append(value)

        description_token = self.get_description_token()  # if there is a valid description token, use it -
        # ...it might well be a call to re-invalidate displayed stages

        if description_token:
            Description().edit_description(self.description_token, dict(attributes=batch_attributes))
            Description().edit_description(self.description_token, dict(stages=batch_stages))
        else:
            self.description_token = str(
                Description(self.profile_id).create_description(batch_stages, batch_attributes)['_id'])

        self.refresh_description_stages()  # refresh previously stored stages to pick up any schema changes

        current_stage = str()

        # load all previously activated stages to determine UI display 'take-off' point
        stages = self.get_stages_display()
        if stages:
            current_stage = stages[-1].get("stage", dict()).get("ref", str())

        self.stage_description(current_stage)
        process['process_name'] = 'stages'
        process['process_data'] = self.get_stages_display()

        return process

    def resolve_stage_stub(self, elem):
        """
        function allows new stages to be realised from a stub
        :param elem: the stub stage that holds the metadata for resolving the new stages
        :return: new stages realised
        """

        stub_ref = elem['ref']
        new_stages = list()

        # define a parameter dictionary and collect any required parameter value here...
        # or elsewhere before before the actual call to the callback function
        param_dict = dict()
        param_dict["stub_ref"] = stub_ref

        if self.is_stage_stub(elem):
            call_back_function = elem.get("callback", dict()).get("function", str())
            call_back_parameter = elem.get("callback", dict()).get("parameter", str())

            args = d_utils.get_args_from_parameter(call_back_parameter, param_dict)
            try:
                new_stages = getattr(WizardHelper, call_back_function)(self, *args)
            except:
                pass

        return new_stages

    def stage_description(self, current_stage):
        # get current stage, output next-in-line
        stage_dict = dict()

        if current_stage:
            stage_list = self.get_batch_stages()
        else:
            # likely no recorded stage
            stage_list = d_utils.json_to_pytype(lkup.WIZARD_FILES["start"])['properties']
            self.set_batch_stages(stage_list)

        # next, determine the stage in line to be rendered
        next_stage_indx = 0
        listed_stage = [indx for indx, elem in enumerate(stage_list) if elem['ref'] == current_stage]
        if listed_stage:
            next_stage_indx = listed_stage[0] + 1

        if next_stage_indx < len(stage_list):  # given a valid index, there is a stage to render!
            elem = stage_list[next_stage_indx]

            if not self.is_activated(elem):  # stage not previously activated

                # now, the retrieved stage may very well be a stage_stub (metadata for bootstrapping actual stage(s))
                # check for stage stubs and resolve accordingly
                new_stages = self.resolve_stage_stub(elem)
                if new_stages:
                    self.activate_stage(elem)
                    # insert generated stages into the stage list
                    stage_gap = next_stage_indx + 1
                    stage_list = stage_list[:stage_gap] + new_stages + stage_list[stage_gap:]
                    self.set_batch_stages(stage_list)
                    elem = stage_list[stage_gap]  # refresh elem

                # determine whether stage should be displayed based on satisfaction of defined constraints
                if self.display_stage(elem):
                    self.activate_stage(elem)
                    stage_dict = self.get_stage_display(elem)

                    # any fire_on_create trigger?
                    self.fire_on_create_triggers(elem)

        return stage_dict

    def refresh_description_stages(self):
        """
        function refreshes description stages in order to pick up eventual schema updates
        :return:
        """

        batch_stages = self.get_batch_stages()

        if not batch_stages:
            return

        # update the start stages
        new_stage_list = d_utils.json_to_pytype(lkup.WIZARD_FILES["start"])['properties']

        for update_stage in new_stage_list:
            listed_stage = [indx for indx, stage in enumerate(batch_stages) if stage['ref'] == update_stage['ref']]

            if listed_stage:
                temp_stage = update_stage
                temp_stage["activated"] = batch_stages[listed_stage[0]].get("activated", False)
                batch_stages[listed_stage[0]] = update_stage

        # update other stages that may be resolved
        for elem in list(batch_stages):
            new_stage_list = self.resolve_stage_stub(elem)
            for update_stage in new_stage_list:
                listed_stage = [indx for indx, stage in enumerate(batch_stages) if stage['ref'] == update_stage['ref']]

                if listed_stage:
                    temp_stage = update_stage
                    temp_stage["activated"] = batch_stages[listed_stage[0]].get("activated", False)
                    batch_stages[listed_stage[0]] = update_stage

        self.set_batch_stages(batch_stages)

        return

    def revalidate_stage_display(self):
        """
        function re-validates stage to verify front-end to backend description stages alignment
        :param elem: the requested stage to be displayed
        :return:
        """

        is_valid_stage_sequence = True

        validation_dict = dict()

        rendered_stages = self.get_rendered_stages()
        display_stages = list()

        for stage in list(self.get_stages_display()):
            stage_ref = stage.get("stage", dict()).get("ref", str())
            stage_items = stage.get("stage", dict()).get("items", list())

            items = list()

            for item in stage_items:
                items.append(item.get("id", str()))

            display_stages.append(dict(ref=stage_ref, items=items))

        # first check, are the lengths same? - if not, it reflects a non-synchronisation between backend and frontend?
        is_valid_stage_sequence = len(rendered_stages) == len(display_stages)

        if is_valid_stage_sequence:
            # todo: other tests here...for instance, are the actual stages the same? -
            # todo: examine the stage refs; activation status; items list etc.
            pass

        if not is_valid_stage_sequence:
            # resolve valid stage sequence
            process = self.initiate_process()
            validation_dict["stages"] = process['process_data']

        validation_dict["is_valid_stage_sequence"] = is_valid_stage_sequence

        return validation_dict

    def save_stage_data(self, auto_fields):
        """
        function saves stage data
        auto_fields: data to be applied to description targets
        :return:
        """

        # get target stage reference
        current_stage = auto_fields.get("current_stage", str())

        # get target stage dictionary
        stage = self.get_batch_stage(current_stage)

        # extract and save values for items in the description target

        # build data dictionary and apply to all targets
        data = DecoupleFormSubmission(auto_fields, d_utils.json_to_object(stage).items).get_schema_fields_updated()

        for target in self.description_targets:
            # 'focus' on target
            self.set_datafile_id(target["recordID"])

            # use batch stages to update targets
            self.update_datafile_stage(self.get_batch_stages())

            # retrieve previously saved data for the stage
            old_stage_data = self.get_stage_data(stage['ref']) or dict()

            # call to handle triggers defined on items
            triggers_kwargs = dict(old_data=old_stage_data,
                                   new_data=data,
                                   stage=self.get_datafile_stage(stage['ref']))
            self.handle_save_triggers(**triggers_kwargs)

            # update attribute given data. Note: this does not actually commit to the db yet.
            # a bulk commit of all description target's attributes to the db is done at a later stage
            self.update_datafile_attributes({'ref': stage["ref"], 'data': data})

        # get batch attributes
        batch_attributes = self.get_batch_attributes()
        if not stage["ref"] in batch_attributes:
            batch_attributes[stage["ref"]] = list()

        # append targets' data to the batch aggregate
        batch_attributes[stage['ref']].append(data)

        # update batch description
        self.set_batch_attributes(batch_attributes)

        # update description targets
        self.update_targets_datafiles()

        return True

    def target_repo_change(self, old_value, new_value):
        """
        function checks if the target repository value has changed and clears up the description metadata accordingly

        :param old_value: value before the trigger was fired
        :param new_value: new target repository value giving rise to the trigger
        :return:
        """

        if old_value == new_value or not old_value or not new_value:  # no change in target repository
            return False

        description = self.get_datafile_description()

        # reset batch stages
        Description().edit_description(self.description_token, dict(attributes=dict()))
        Description().edit_description(self.description_token, dict(stages=list()))

        stage_list = d_utils.json_to_pytype(lkup.WIZARD_FILES["start"])['properties']

        # activate the target repository stage
        listed_stage = [indx for indx, stage in enumerate(stage_list) if stage['ref'] == "target_repository"]
        stage_list[listed_stage[0]]['activated'] = True

        description['stages'] = stage_list
        retained_attributes = dict()

        for stage in list(description['stages']):
            if stage['ref'] in description['attributes']:
                retained_attributes[stage['ref']] = description['attributes'][stage['ref']]
                del description['attributes'][stage['ref']]

        description['attributes'] = retained_attributes
        self.update_description(description)

    def growth_facility_change(self, item_id, new_value, stage):
        """
        function refreshes the stage items in response to a value change
        :param item_id: item or control that originated the trigger
        :param new_value: the new value that led to the trigger, if none is provided, then we might be dealing
                            an initial instantiation of the stage
        :param stage: parent stage of the trigger element
        :return:
        """

        # remove potentially obsolete items from the stage items list
        for schema_name in [x['schema'] for x in lkup.DROP_DOWNS['GROWTH_AREAS'] if x.get('schema', str())]:
            target_schema = d_utils.get_copo_schema(schema_name)

            for f in target_schema:
                stage["items"] = [item for item in stage.get("items", list()) if
                                  not item["id"].split(".")[-1] == f["id"].split(".")[-1]]

        # now get the required schema name
        if not new_value:
            # possibly an initial stage setting, set new value to the first value of the drop down
            new_value = lkup.DROP_DOWNS['GROWTH_AREAS'][0]['value']

        growth_areas = [x for x in lkup.DROP_DOWNS['GROWTH_AREAS'] if
                        x['value'] == new_value and x.get("schema", str())]

        if not growth_areas:  # no associated schema, nothing to do!
            return
        else:
            # resolve actual schema to be inserted given the schema name or reference
            insert_schema = d_utils.get_copo_schema(growth_areas[0]['schema'])

            # get the index of the reference item (trigger originator) from the stage dictionary,
            # and use this to inform the insertion of the new items.
            # it is assumed that the new items will be inserted just after the trigger originator.
            # feel free, however, to change the position (index) accordingly to reflect
            # what is required on the rendering agent
            item_indx = [indx for indx, item in enumerate(stage.get("items", list())) if
                         item["id"].split(".")[-1] == item_id.split(".")[-1]]
            if item_indx:
                insert_indx = item_indx[0]
                stage["items"][insert_indx + 1:insert_indx + 1] = insert_schema[:]

                # and finally...a little stage housekeeping...and we are good!
                self.set_items_type(stage)

    def get_nutrient_controls(self, item_id, new_value, stage):
        """
        function refreshes the stage items in response to a value change
        :param item_id: item or control that originated the trigger
        :param new_value: the new value that led to the trigger, if none is provided, then we might be dealing
                            an initial instantiation of the stage
        :param stage: parent stage of the trigger element
        :return:
        """

        # remove potentially obsolete items from the stage items list
        for schema_name in [x['schema'] for x in lkup.DROP_DOWNS['GROWTH_NUTRIENTS'] if x.get('schema', str())]:
            target_schema = d_utils.get_copo_schema(schema_name)

            for f in target_schema:
                stage["items"] = [item for item in stage.get("items", list()) if
                                  not item["id"].split(".")[-1] == f["id"].split(".")[-1]]

        # now get the required schema name
        if not new_value:
            # possibly an initial stage setting, set new value to the first value of the drop down
            new_value = lkup.DROP_DOWNS['GROWTH_NUTRIENTS'][0]['value']

        growth_areas = [x for x in lkup.DROP_DOWNS['GROWTH_NUTRIENTS'] if
                        x['value'] == new_value and x.get("schema", str())]

        if not growth_areas:  # no associated schema, nothing to do!
            return
        else:
            # resolve actual schema to be inserted given the schema name or reference
            insert_schema = d_utils.get_copo_schema(growth_areas[0]['schema'])

            # get the index of the reference item (trigger originator) from the stage dictionary,
            # and use this to inform the insertion of the new items.
            # it is assumed that the new items will be inserted just after the trigger originator.
            # feel free, however, to change the position (index) accordingly to reflect
            # what is required on the rendering agent
            item_indx = [indx for indx, item in enumerate(stage.get("items", list())) if
                         item["id"].split(".")[-1] == item_id.split(".")[-1]]
            if item_indx:
                insert_indx = item_indx[0]
                stage["items"][insert_indx + 1:insert_indx + 1] = insert_schema[:]

                # and finally...a little stage housekeeping...and we are good!
                self.set_items_type(stage)

    def confirm_pairing(self):
        """
        function determines if the pairing of datafiles should be performed given the 'library_layout' value
        also function has the task of cleaning up unpaired targets with dangling metadata (from previous description)
        :return:
        """

        # the test to be carried out will return True, if at least one of the description targets has a value 'PAIRED'
        do_pairing = False

        # if no accompanying description targets, then we can't do a confirmatory test.
        # if len(self.description_targets) == 0:
        #     return True # need to think through this again!!!

        self.refresh_targets_data()
        for target in self.description_targets:
            if target.get('attributes', dict()).get('library_construction', dict()).get('library_layout',
                                                                                        str()).upper() == 'PAIRED':
                do_pairing = True
                break

        # deactivate dependent stage if not pairing
        if not do_pairing:
            stages = self.get_batch_stages()
            elem = [stage for stage in self.get_batch_stages() if stage['ref'] == "datafiles_pairing"]

        return do_pairing

    def study_type_change(self, item_id, old_value, new_value):
        """
        function reacts to a change in the study type (ENA repo-specific), and alters the stages accordingly
        :param item_id: the item giving rise to the trigger
        :param old_value:
        :param new_value:
        :return:
        """

        if old_value == new_value or not old_value or not new_value:  # no change in target repository
            return False

        description = self.get_datafile_description()

        # now let's deal with changes pertaining to specific items
        if item_id:
            blacklist = list()  # list of stages to discard
            stubs = list()  # the stub that initiated creation of the elements
            for stage in self.get_datafile_stages():
                if stage.get("dependent_on", str()) == item_id:
                    blacklist.append(stage['ref'])
                    if 'stub_ref' in stage:
                        stubs.append(stage['stub_ref'])

            # remove blacklisted elements from description stages...
            description['stages'] = [stage for stage in description['stages'] if stage['ref'] not in blacklist]

            # also, update the batch stages
            batch_stages = [stage for stage in description['stages'] if stage['ref'] not in blacklist]

            # ...and from description
            for bkl in blacklist:
                if bkl in description['attributes']:
                    del description['attributes'][bkl]

            # reset batch description object
            Description().edit_description(self.description_token, dict(attributes=dict()))
            Description().edit_description(self.description_token, dict(stages=list()))

            # reset from the first stage stub onward to force re-entry into stage activation process
            stubs = set(stubs)
            for stage_ref in stubs:
                listed_stage = [indx for indx, stage in enumerate(description['stages']) if stage['ref'] == stage_ref]
                if listed_stage:
                    for i in range(listed_stage[0], len(description['stages'])):
                        description['stages'][i]['activated'] = False

            # ...and update the db
            self.update_description(description)

    def library_layout_change(self, item_id, old_value, new_value):
        """
        function reacts to a change in the library layout: basically to clean up metadata
        :param item_id: the item giving rise to the trigger
        :param old_value:
        :param new_value:
        :return:
        """

        if old_value == new_value or not old_value or not new_value:  # no change in library layout
            return False

        if new_value.upper() == 'SINGLE':
            description = self.get_datafile_description()
            if "datafiles_pairing" in description.get("attributes", dict()):
                del description['attributes']["datafiles_pairing"]
                self.update_description(description)

        return

    def discard_description(self):
        object_list = [ObjectId(target["recordID"]) for target in self.description_targets]

        DataFile().get_collection_handle().update_many(
            {"_id": {"$in": object_list}}, {"$set": {"description": dict()}}
        )

    def get_description_stages(self):
        stages = list()
        target_repository = self.get_batch_attributes()["target_repository"][0]
        if target_repository:
            stages = d_utils.json_to_pytype(lkup.WIZARD_FILES[target_repository['deposition_context']])['properties']

        return stages

    def is_same_metadata(self, stage_ref):
        """
        function checks if same metadata is shared by the description targets in a given description stage
        :param stage_ref: reference of the target stage
        :return: boolean; True if same metadata is shared
        """
        same_metadata = True
        targets_data = list()
        for target in self.description_targets:
            self.set_datafile_id(target["recordID"])
            target_description = self.get_datafile_description()['attributes']
            if stage_ref in target_description:
                targets_data.append(target_description[stage_ref])
            else:
                targets_data.append(dict())

        for td in targets_data[1:]:
            if td != targets_data[0]:
                same_metadata = False
                break

        return same_metadata

    def inherit_metadata(self, reference_target_id):
        """
        using reference_target as the basis, copy metadata across to description targets
        :param reference_target_id:
        :return:
        """

        reference_description = DataFile().get_record(reference_target_id).get("description", dict())
        reference_description = self.remove_suppressed_stages(reference_description)

        reference_attributes = reference_description.get("attributes", dict())
        reference_stages = reference_description.get("stages", list())

        for target in self.description_targets:
            # 'focus' on target
            self.set_datafile_id(target["recordID"])

            # use batch stages to update targets
            self.update_datafile_stage(reference_stages)

            # add attributes from the reference datafile
            for k, v in reference_attributes.items():
                if k not in self.get_datafile_attributes():
                    self.update_datafile_attributes({'ref': k, 'data': v})

        self.update_targets_datafiles()
        return

    def datafile_pairing(self):
        """
        pair datafiles - in the context of an ENA description. file to be paired must
        satisfy the following constraints:
            1. mutually exclusive - isn't already paired to another file
            2. symmetric - given two files 'file1', 'file2'. if file1 is paired to file2, file2 must be paired to file1
            3. must have the same metadata
        :return:
        """

        paired_list = list()
        for pairing_target in self.description_targets:
            paired_list.append(pairing_target)
            if len(paired_list) == 2:
                # first test - are both files unpaired?
                paired_files = list()
                for target in paired_list:
                    # set 'focus' to target
                    self.set_datafile_id(target["recordID"])

                    paired_file = self.get_datafile_attributes().get("datafiles_pairing", dict()).get("paired_file", str())
                    paired_files.append(paired_file)

                if len(set(paired_files)) == 1 and list(set(paired_files))[0] == str():  # i.e., no previous pairing
                    # do pairing
                    self.set_datafile_id(paired_list[0]["recordID"])
                    description = self.get_datafile_description()

                    description['attributes']["datafiles_pairing"] = dict(paired_file=paired_list[1]["recordID"])
                    self.update_description(description)

                    self.set_datafile_id(paired_list[1]["recordID"])
                    description = self.get_datafile_description()

                    description['attributes']["datafiles_pairing"] = dict(paired_file=paired_list[0]["recordID"])
                    self.update_description(description)

                    # paired files must have the same metadata too...

                paired_list = list()

        self.update_targets_datafiles()

        return True

    def datafile_unpairing(self):
        """
        performs unpairing of datafiles in the context of an ENA description.
        :return:
        """

        unpaired = True

        # first test, are both files free of previous pairing?
        paired_files = list()
        for target in self.description_targets:
            # set 'focus' to target
            self.set_datafile_id(target["recordID"])
            description = self.get_datafile_description()
            del description['attributes']["datafiles_pairing"]

            self.update_description(description)

        self.update_targets_datafiles()

        return unpaired

    def validate_bundle_candidates(self, description_bundle):
        """
        validates candidates to be added to description bundle to ascertain 'compatibility' between
        new description targets and already existing items in the description bundle
        :param description_bundle:
        :return: validation result
        """

        # maintain a copy of the original targets
        original_targets = list(self.description_targets)

        # validate targets against one another
        result_dict = self.validate_prospective_targets()

        if description_bundle:
            # validate targets against one another as well as existing items in the bundle
            validation_code = result_dict["validation_code"]
            if validation_code in ["100", "101"]:
                # targets are compatible with one another, also there may be some datafiles ahead
                # in description metadata,
                # it should now be sufficient only to verify that
                # at least one of the targets is compatible with at least one item in the bundle

                selected_bundle_item = description_bundle[0]
                selected_target = self.description_targets[0]

                if validation_code == "101":
                    # "101": "Some targets are ahead of others! Inherit metadata?"
                    # item with the most metadata is preferred here for obvious reason

                    selected_target = result_dict["extra_information"]["target"]

                description_targets = [selected_bundle_item, selected_target]
                self.set_description_targets(description_targets)

                result_dict = self.validate_prospective_targets()

                # resolve results
                if result_dict["validation_code"] == "100" and validation_code == "101":
                    result_dict = self.get_validation_result("101")
                    self.set_datafile_id(selected_target["recordID"])

                    reference_description = self.remove_suppressed_stages(self.get_datafile_description())
                    summary = htags.resolve_description_data(reference_description, dict())

                    result_dict["extra_information"] = dict(summary=summary, target=selected_target)
                elif result_dict["validation_code"] == "101":
                    local_target = result_dict["extra_information"]["target"]
                    if local_target["recordID"] == selected_target["recordID"]:
                        result_dict = self.get_validation_result("103")
                    elif local_target["recordID"] == selected_bundle_item["recordID"]:
                        result_dict = self.get_validation_result("101")

                    self.set_datafile_id(local_target["recordID"])

                    reference_description = self.remove_suppressed_stages(self.get_datafile_description())
                    summary = htags.resolve_description_data(reference_description, dict())

                    result_dict["extra_information"] = dict(summary=summary, target=local_target)

        # set data for candidates
        self.set_description_targets(original_targets)
        self.refresh_targets_data()
        result_dict["extra_information"]["candidates_data"] = self.description_targets

        return result_dict

    def remove_suppressed_stages(self, description_object):
        """
        function removes stage data, not to be cloned, from description_object
        :param description_object: description dictionary comprising of stages and attributes
        :return:
        """
        stages = list(description_object.get("stages", list()))

        for indx, stage in enumerate(stages):
            ref = stage.get("ref", str())
            if not stage.get("is_clonable", True):
                description_object.get("attributes", dict()).pop(ref, None)

        return description_object

    def get_validation_result(self, code):
        validation_codes = {
            "100": "Targets are compatible, and may be described as a bundle!",
            "101": "Some targets are ahead of others! Inherit metadata?",
            "102": "Targets have incompatible metadata!",
            "103": "Some targets are ahead of bundle items! Inherit metadata?",
        }

        result_dict = dict(
            validation_code=code,
            validation_message=validation_codes.get(code),
            extra_information=dict()
        )

        return result_dict

    def validate_prospective_targets(self):
        """
        validates candidates to be added to description bundle to ascertain compatibility
        :return: validation result
        """

        result_dict = self.get_validation_result("100")

        # extract useful attributes for validation
        stages_union = dict()
        attributes_counts = list()
        benchmark_target = None
        benchmark_count = -1

        for target in self.description_targets:
            # 'focus' on target
            self.set_datafile_id(target["recordID"])

            target["attributes"] = self.get_datafile_attributes()

            # store count of attributes
            if len(target["attributes"]) not in attributes_counts:
                attributes_counts.append(len(target["attributes"]))

            if len(target["attributes"]) > benchmark_count:
                benchmark_target = target
                benchmark_count = len(target["attributes"])

            for stage in self.get_datafile_stages():
                if stage.get("is_singular_stage", False) and stage.get("ref") not in stages_union.keys():
                    stages_union[stage.get("ref")] = list()

            for su in stages_union:
                if su in target["attributes"]:
                    stages_union[su].append(target["attributes"].get(su))

        # perform metadata compatibility test
        compatible = True
        for k, v in stages_union.items():
            if len(v) > 1 and not all(x == v[0] for x in v):
                compatible = False
                result_dict = self.get_validation_result("102")
                break

        if compatible:
            # perform metadata alignment test
            if len(attributes_counts) > 1 and benchmark_target:
                # there is at least one target with metadata ahead of the rest
                result_dict = self.get_validation_result("101")
                self.set_datafile_id(benchmark_target["recordID"])

                reference_description = self.remove_suppressed_stages(self.get_datafile_description())
                summary = htags.resolve_description_data(reference_description, dict())

                result_dict["extra_information"] = dict(summary=summary, target=benchmark_target)

        return result_dict

    def is_target_member(self, datafile_id):
        """
        function checks if datafile_id is in the description target
        :param datafile_id:
        :return:
        """

        in_target = False

        l = [x for x in self.description_targets if x["recordID"] == datafile_id]

        if len(l) != 0:
            in_target = True

        return in_target

    def negotiate_datafile_pairing(self):
        """
        separate description targets groups of into paired, need to be paired, don't pair
        :return:
        """
        unpaired_list = list()  # datafiles that need to be paired
        paired_in_bundle_list = list()  # already paired and the pair is in bundle
        paired_not_in_bundle_list = list()  # paired, but one of the pair isn't in the bundle
        do_not_pair_list = list()  # not to be paired
        targets_record_ids = list()
        add_to_bundle = list()  # will be used to dynamically update bundle
        self.refresh_targets_data()  # update with current db state
        for target in self.description_targets:
            targets_record_ids.append(target.get('recordID'))
            if target.get('attributes', dict()).get('library_construction', dict()).get('library_layout',
                                                                                        str()) != 'PAIRED':
                do_not_pair_list.append(target)
            else:
                # paired or needs to be paired
                paired_file = target.get('attributes', dict()).get('datafiles_pairing', dict()).get('paired_file',
                                                                                                    str())
                if paired_file == str():
                    # not yet paired, needs to be paired
                    unpaired_list.append(target.get('recordID'))
                else:
                    # paired...keep unique pairs (pairing is commutative)
                    temp_list = [target.get('recordID'), paired_file]

                    if self.is_target_member(paired_file):
                        temp_list.sort()  # sort here for uniqueness test
                        paired_in_bundle_list.append(temp_list) if temp_list not in paired_in_bundle_list else ''
                    else:
                        paired_not_in_bundle_list.append(temp_list)

        # are there any paired but not in bundle?
        if paired_not_in_bundle_list:
            pass
            # here we will attempt to validate pairs in the list:
            # i.e., where possible, add missing pair member to the bundle
            # (if they can be found, and are not paired to another file).
            # where we can't validate a pair, we unpair the member which is part of the description target.

            for pnb in paired_not_in_bundle_list:
                paired_member_0_id = pnb[0]  # datafile in description targets
                paired_member_1_id = pnb[1]  # datafile not in description targets, needs to be resolved
                try:
                    paired_member_1 = DataFile().get_record(paired_member_1_id)
                    paired_file = paired_member_1.get("description", dict()).get('attributes', dict()).get(
                        'datafiles_pairing', dict()).get('paired_file',
                                                         str())
                    if paired_file and paired_file == paired_member_0_id:  # paired, add to description bundle
                        option = dict(recordLabel=paired_member_1.get("name", str()),
                                      recordID=str(paired_member_1.get("_id", str())),
                                      attributes=paired_member_1.get("description", dict()).get("attributes", dict())
                                      )
                        add_to_bundle.append(option)
                        # also, add to paired list
                        pnb.sort()
                        paired_in_bundle_list.append(pnb) if pnb not in paired_in_bundle_list else ''
                    else:  # paired to another, or not at all
                        #  add the file to unpaired list, making it available for pairing
                        unpaired_list.append(paired_member_0_id)
                except:
                    # can't resolve, add member to unpaired list
                    unpaired_list.append(paired_member_0_id)

        self.description_targets.extend(add_to_bundle)  # update description targets with new members
        self.set_description_targets(list(self.description_targets))  # set and refresh targets data
        self.refresh_targets_data()
        pairing_dict = dict(
            unpaired_list=[x for x in self.description_targets if x["recordID"] in unpaired_list],
            paired_list=[[y for y in self.description_targets if y["recordID"] in x] for x in paired_in_bundle_list],
            add_to_bundle=add_to_bundle,
            do_not_pair_list=do_not_pair_list
        )

        # can we try to suggest potential pairings for files in the unpaired list?

        suggested_pairings = list()
        copied_unpaired_list = list(pairing_dict["unpaired_list"])

        #  let's assume 'R1.fastq.gz' and 'R2.fastq.gz' naming convention, then ordinary 'sort' should suffice
        new_sorted_list = sorted(copied_unpaired_list, key=itemgetter('recordLabel'))

        if len(new_sorted_list) > 1:
            if len(new_sorted_list) % 2 != 0:
                # uneven number of files to be paired
                # we might have to remove a file from the start or end of the list before suggesting pairing
                # to do that, we compute how similar the top three files are and use that metric to decide
                d01 = difflib.SequenceMatcher(None, new_sorted_list[0]["recordLabel"], new_sorted_list[1]["recordLabel"]).ratio()
                d12 = difflib.SequenceMatcher(None, new_sorted_list[1]["recordLabel"], new_sorted_list[2]["recordLabel"]).ratio()
                if d01 > d12:
                    new_sorted_list = new_sorted_list[:-1]
                else:
                    new_sorted_list = new_sorted_list[1:]

            while len(new_sorted_list) >= 2:
                suggested_pairings.append([new_sorted_list.pop(0), new_sorted_list.pop(0)])

        pairing_dict["suggested_pairings"] = suggested_pairings

        return pairing_dict

    def is_description_mismatch(self, auto_fields):
        """
        function verifies if description targets have any mismatch with submitted stage description
        :param auto_fields: form entries
        :return: boolean; True if there is a mismatch
        """
        # get target stage reference
        current_stage = auto_fields["current_stage"]

        # get target stage dictionary
        stage = self.get_batch_stage(current_stage)

        # build data dictionary
        data = DecoupleFormSubmission(auto_fields, d_utils.json_to_object(stage).items).get_schema_fields_updated()

        description_mismatch = False
        for target in self.description_targets:
            self.set_datafile_id(target["recordID"])
            target_description = self.get_datafile_description()['attributes']
            if current_stage in target_description:
                if data != target_description[current_stage]:
                    description_mismatch = True
                    break

        return description_mismatch

    def get_dynamic_elements_ena(self, stub_ref):
        """
        function generates dynamic stages for ENA based on the study type
        :param stub_ref: the reference of the stub stage
        :return:
        """

        study_type = self.get_batch_attributes()["study_type"][0]
        if not study_type:
            return list()

        study_type = study_type['study_type']

        # get protocols
        protocols = ISAHelpers().get_protocols_parameter_values(study_type)

        # get study assay schema
        schema_fields = getattr(DataSchemas("COPO").get_ui_template_as_obj().copo, study_type).fields

        # generate dynamic stages from protocols
        dynamic_stages = list()

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
                                  dependent_on=str("study_type"),
                                  stub_ref=stub_ref,
                                  items=list()
                                  )

                for f in schema_fields:
                    if f.ref in pr.get("parameterValues", list()):
                        if f.show_in_form:
                            elem = htags.get_element_by_id(f.id)
                            elem["id"] = elem['id'].strip(".").rsplit(".", 1)[1]
                            del elem['ref']
                            stage_dict.get("items").append(elem)

                            # define trigger for library layout: better to maintain in here than in multiple assay files
                            if elem["id"] == "library_layout":
                                elem["trigger"] = {
                                    "type": "change",
                                    "message": "Changing the library layout will lead to some adjustments in the wizard to reflect update to the metadata requirements. <br/><br/>Please note that previous entries may be lost as a result of the change.",
                                    "callback": {
                                        "function": "library_layout_change",
                                        "parameter": "item_id,old_value,new_value"
                                    }
                                }

                dynamic_stages.append(stage_dict)

        return dynamic_stages

    def validate_figshare_token(self):
        t = Figshare().get_token_for_user(user_id=data_utils.get_current_user().id)
        if t:
            return False
        else:
            return True

    def set_items_type(self, stage):
        for item in stage.get("items", list()):
            if not item.get("type"):
                item["type"] = "string"

            # also get id in the desired order
            item["id"] = item["id"].split(".")[-1]

        return stage

    def handle_save_triggers(self, **param_dict):
        """
        takes care of dispatching calls to trigger functions
        :param param_dict:
        :return:
        """

        # use param dictionary to collect relevant parameter values for callback functions
        stage = param_dict.get("stage", dict())
        old_data = param_dict.get("old_data", dict())
        new_data = param_dict.get("new_data", dict())

        stage_ref = stage.get("ref", str())

        param_dict["stage_ref"] = stage_ref

        # go through all items in the stage and fire any defined triggers
        for sti in stage.get("items", list()):
            param_dict["item_id"] = sti['id']  # parameter value

            trigger_elem = sti.get("trigger", dict())
            if trigger_elem:
                param_dict["new_value"] = new_data[sti['id']]  # parameter value
                param_dict["old_value"] = str()  # parameter value
                if old_data.get(sti['id'], str()):
                    param_dict["old_value"] = old_data[sti['id']]  # parameter value

                # get callback function
                call_back_function = trigger_elem.get("callback", dict()).get("function", str())

                # get callback parameters and sort out callback function arguments
                call_back_parameter = trigger_elem.get("callback", dict()).get("parameter", str())

                # resolve relevant arguments for this call
                args = d_utils.get_args_from_parameter(call_back_parameter, param_dict)

                try:
                    getattr(WizardHelper, call_back_function)(self, *args)
                except:
                    pass

        return
