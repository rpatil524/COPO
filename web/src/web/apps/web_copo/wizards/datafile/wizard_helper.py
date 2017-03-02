__author__ = 'etuka'

from bson import ObjectId
from dal import cursor_to_list

from django_tools.middlewares import ThreadLocal

import web.apps.web_copo.lookup.lookup as lkup
import web.apps.web_copo.schemas.utils.data_utils as d_utils
import web.apps.web_copo.templatetags.html_tags as htags
from converters.ena.copo_isa_ena import ISAHelpers
from dal.copo_base_da import DataSchemas
from dal.copo_da import DataFile, Description
from dal.figshare_da import Figshare
from web.apps.web_copo.schemas.utils.data_utils import DecoupleFormSubmission


class WizardHelper:
    def __init__(self, description_token=str(), description_targets=list()):
        self.datafile_id = str()
        self.description_token = description_token
        self.description_targets = description_targets
        self.targets_datafiles = self.set_targets_datafiles()
        self.profile_id = ThreadLocal.get_current_request().session['profile_id']

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
        function dispatches the call to render a stage
        :param stage: is the dictionary that captures the stage metadata
        :return: is the rendered stage in its html 're-incarnation'
        """

        if "data" not in stage:
            stage['data'] = self.get_stage_data(stage['ref'])

        getattr(WizardHelper, stage['content'])(self, stage)
        stage_dict = dict(stage=stage)

        return stage_dict

    def display_stage(self, elem):
        """
        function decides if a stage should be displayed or not. it assumes that conditional stages have
        callbacks defined in order to resolve the validity of the condition.
        however, if no callback is defined, function defaults to a decision
        to display the stage (i.e., True), except in the case where the said stage is a 'stub', in that case function
        will always default to a False.
        :param elem: is the dictionary that captures the stage metadata
        :return: is a boolean; if true stage is displayed
        """

        display = True

        # any restrictions imposed?
        if self.is_conditional_stage(elem):
            call_back_function = elem.get("callback", dict()).get("function", str())
            call_back_parameter = elem.get("callback", dict()).get("parameter", str())

            if call_back_function:
                if call_back_parameter:
                    display = getattr(WizardHelper, call_back_function)(self, call_back_parameter.format(**locals()))
                else:
                    display = getattr(WizardHelper, call_back_function)(self)

        # stage_stub are non-displayable
        if self.is_stage_stub(elem):
            display = False

        return display

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
            description['attributes'][stage_description['ref']] = stage_description['data']

            # soft validation...only allow stage attribute entry, if there is an actual value assigned
            save_stage = False
            for k, v in stage_description['data'].items():
                if isinstance(v, str) and v:
                    save_stage = True
                    break

            if not save_stage:
                del description['attributes'][stage_description['ref']]

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

        self.description_token = str(
            Description(self.profile_id).create_description(batch_stages, batch_attributes)['_id'])

        if batch_stages:  # load all previously activated stages
            process['process_name'] = 'stages'
            process['process_data'] = self.get_stages_display()
        else:
            process['process_name'] = 'stage'
            process['process_data'] = self.stage_description(current_stage=str())

        return process

    def resolve_stage_stub(self, elem):
        """
        function allows new stages to be realised from a stub
        :param elem: the stub stage that holds the metadata for resolving the new stages
        :return: new stages realised
        """

        stub_ref = elem['ref']
        new_stages = list()
        if self.is_stage_stub(elem):
            call_back_function = elem.get("callback", dict()).get("function", str())
            call_back_parameter = elem.get("callback", dict()).get("parameter", str())

            if call_back_function:
                if call_back_parameter:
                    new_stages = getattr(WizardHelper, call_back_function)(self, call_back_parameter.format(**locals()))
                else:
                    new_stages = getattr(WizardHelper, call_back_function)(self)

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

                # determine whether stage should be displayed based on the satisfaction of certain condition(s)
                if self.display_stage(elem):
                    self.activate_stage(elem)
                    stage_dict = self.get_stage_display(elem)

        return stage_dict

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

        aggregate_data = list()

        # extract and save values for items in the description target

        # build data dictionary and apply to all targets
        data = DecoupleFormSubmission(auto_fields, d_utils.json_to_object(stage).items).get_schema_fields_updated()

        # aggregate target's data to aggregate
        aggregate_data.append(data)

        for target in self.description_targets:
            # 'focus' on target
            self.set_datafile_id(target["recordID"])

            # use batch stages to update targets
            self.update_datafile_stage(self.get_batch_stages())

            # retrieve previously saved data for the stage
            old_stage_data = self.get_stage_data(stage['ref']) or dict()

            # call to handle triggers defined on items
            self.handle_save_triggers(old_stage_data, data, stage)

            # update attribute, given data
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

    def target_repo_change(self, args):
        args = args.split(",")
        # args: item_id, old_value, new_value

        if args[0] == args[1] or not args[0] or not args[1]:  # no change in target repository
            return False

        # reset batch stages
        if self.get_batch_attributes():
            stage_list = d_utils.json_to_pytype(lkup.WIZARD_FILES["start"])['properties']
            self.set_batch_stages(stage_list)
            self.set_batch_attributes(dict())

        # discard description for datafile
        description = self.get_datafile_description()
        description['stages'] = list()
        description['attributes'] = dict()

        self.update_description(description)

    def study_type_change(self, args):
        args = args.split(",")
        # args: item_id, old_value, new_value

        if args[1] == args[2] or not args[1] or not args[2]:  # no change in target repository
            return False

        item_id = args[0]
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

            # ...and from description
            for bkl in blacklist:
                if bkl in description['attributes']:
                    del description['attributes'][bkl]

            # reset stubs
            stubs = set(stubs)
            for stage_ref in stubs:
                listed_stage = [indx for indx, stage in enumerate(description['stages']) if stage['ref'] == stage_ref]
                if listed_stage:
                    description['stages'][listed_stage[0]]['activated'] = False

            # ...and update the db
            self.update_description(description)

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

        reference_attributes = reference_description.get("attributes", dict())
        reference_stages = reference_description.get("stages", list())

        for target in self.description_targets:
            # 'focus' on target
            self.set_datafile_id(target["recordID"])

            # use batch stages to update targets
            self.update_datafile_stage(reference_stages)

            # find and attributes from the reference
            for k, v in reference_attributes.items():
                if k not in self.get_datafile_attributes():
                    self.update_datafile_attributes({'ref': k, 'data': v})

        self.update_targets_datafiles()
        return

    def validate_bundle_candidates(self, description_bundle):
        """
        validates candidates to be added to description bundle to ascertain compatibility between
        new description targets and already existing items in the description bundle
        :param description_bundle:
        :return: validation result
        """

        # maintain a copy of the original targets
        original_targets = list(self.description_targets)

        # validating targets against one another
        result_dict = self.validate_prospective_targets()

        if description_bundle:
            # validating targets against one another as well as existing items in the bundle
            validation_code = result_dict["validation_code"]
            if validation_code in ["100", "101"]:
                # targets are compatible with one another/there may be some ahead in description metadata,
                # it should now be sufficient only to verify that
                # at least one of the targets is compatible with at least one item in the bundle

                selected_bundle_item = description_bundle[0]
                selected_target = self.description_targets[0]

                if validation_code == "101":
                    # "101": "Some targets are ahead of others! Inherit metadata?"
                    # item with most metadata is preferred here for obvious reason

                    selected_target = result_dict["extra_information"]["target"]

                description_targets = [selected_bundle_item, selected_target]
                self.set_description_targets(description_targets)

                result_dict = self.validate_prospective_targets()

                # resolve results
                if result_dict["validation_code"] == "100" and validation_code == "101":
                    result_dict = self.get_validation_result("101")
                    self.set_datafile_id(selected_target["recordID"])
                    result_dict["extra_information"] = dict(
                        summary=htags.resolve_description_data(self.get_datafile_description(),
                                                               dict()),
                        target=selected_target)
                elif result_dict["validation_code"] == "101":
                    local_target = result_dict["extra_information"]["target"]
                    if local_target["recordID"] == selected_target["recordID"]:
                        result_dict = self.get_validation_result("103")
                    elif local_target["recordID"] == selected_bundle_item["recordID"]:
                        result_dict = self.get_validation_result("101")

                    self.set_datafile_id(local_target["recordID"])
                    result_dict["extra_information"] = dict(
                        summary=htags.resolve_description_data(self.get_datafile_description(),
                                                               dict()),
                        target=local_target)

        # set data for candidates
        self.set_description_targets(original_targets)
        self.refresh_targets_data()
        result_dict["extra_information"]["candidates_data"] = self.description_targets

        return result_dict

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
                result_dict["extra_information"] = dict(
                    summary=htags.resolve_description_data(self.get_datafile_description(),
                                                           dict()),
                    target=benchmark_target)

        return result_dict

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

    def get_dynamic_elements_ena(self, args):
        """
        function generates dynamic stages for ENA based on the study type
        :param args:
        :return:
        """

        args = args.split(",")
        # args: stub_ref

        stub_ref = args[0]

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
                                  content=str("get_stage_html"),
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
                dynamic_stages.append(stage_dict)

        return dynamic_stages

    def validate_figshare_token(self):
        t = Figshare().get_token_for_user(user_id=ThreadLocal.get_current_user().id)
        if t:
            return False
        else:
            return True

    def get_stage_html(self, stage):
        stage_items = stage['items']

        html_tag = list()

        if stage_items:
            for st in stage_items:

                # if required, resolve data source for select-type controls,
                # i.e., if a callback is defined on the 'option_values' field

                if "option_values" in st:
                    st["option_values"] = htags.get_control_options(st)

                html_tag.append(st)

        return html_tag

    def set_items_type(self, stage):
        for item in stage.get("items", list()):
            if not item.get("type"):
                item["type"] = "string"

        return stage

    def handle_save_triggers(self, old_data, new_data, stage):
        for sti in stage.get("items", list()):
            item_id = sti['id']  # placeholder parameter

            trigger_elem = sti.get("trigger", dict())
            if trigger_elem:
                new_value = new_data[sti['id']]  # placeholder parameters
                old_value = str()
                if old_data.get(sti['id'], str()):
                    old_value = old_data[sti['id']]

                call_back_function = trigger_elem.get("callback", dict()).get("function", str())
                call_back_parameter = trigger_elem.get("callback", dict()).get("parameter", str())

                if call_back_function:
                    if call_back_parameter:
                        new_stages = getattr(WizardHelper, call_back_function)(self,
                                                                               call_back_parameter.format(**locals()))
                    else:
                        new_stages = getattr(WizardHelper, call_back_function)(self)

        return
