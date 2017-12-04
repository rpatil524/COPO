__author__ = 'etuka'
__date__ = '17 June 2016'

import ast

from dal.copo_da import Description
import web.apps.web_copo.wizards.datafile.wizard_helper as wizh


class BrokerRequests:
    def __init__(self, **kwargs):
        self.param_dict = kwargs

        self.context = self.param_dict.get("context", dict())

        self.auto_fields = self.param_dict.get("auto_fields", dict())
        if self.auto_fields and isinstance(self.auto_fields, str):
            self.auto_fields = ast.literal_eval(self.auto_fields)

        self.description_token = self.param_dict.get("description_token", str())
        self.description_targets = self.param_dict.get("description_targets", list())  # subset of items in bundle
        self.description_bundle = self.param_dict.get("description_bundle", list())  # all items in the description

        # an wizard helper instance to handle request actions
        self.wizard_helper = wizh.WizardHelper(self.description_token, self.description_targets)

    def get_request_dict(self):
        # request-to-action mapping
        request_dict = dict(initiate_wizard=self.do_initiate_wizard,
                            validate_bundle_candidates=self.do_validate_bundle_candidates,
                            inherit_metadata=self.do_inherit_metadata,
                            inherit_metadata_refresh=self.do_inherit_metadata_refresh,
                            get_next_stage=self.do_get_next_stage,
                            save_stage_data=self.do_save_stage_data,
                            refresh_targets_data=self.do_refresh_targets_data,
                            get_item_stage_display=self.do_get_item_stage_display,
                            is_same_metadata=self.do_is_same_metadata,
                            is_description_mismatch=self.do_is_description_mismatch,
                            discard_description=self.do_discard_description,
                            negotiate_datafile_pairing=self.do_negotiate_datafile_pairing,
                            datafile_pairing=self.do_datafile_pairing,
                            datafile_unpairing=self.do_datafile_unpairing,
                            )

        return request_dict

    def post_context(self, request_action):
        request_dict = self.get_request_dict()

        request_action = request_action.split(",")

        if not self.verify_token():  # a token is needed for every description. If not available (re)initiate wizard
            request_action = list(["initiate_wizard"] + request_action)

        seen_list = list()

        for rqa in request_action:
            if rqa in request_dict and rqa not in seen_list:
                request_dict[rqa]()
                seen_list.append(rqa)

        if self.description_bundle:
            # set|refresh data for items in the description bundle
            self.wizard_helper.set_description_targets(self.description_bundle)
            self.context['targets_data'] = self.wizard_helper.refresh_targets_data()

        return self.context

    def verify_token(self):
        return Description().is_valid_token(self.description_token)

    def do_initiate_wizard(self):
        process = self.wizard_helper.initiate_process()
        self.context[process['process_name']] = process['process_data']
        self.context['description_token'] = self.wizard_helper.get_description_token()

        return

    def do_validate_bundle_candidates(self):
        self.context['validatation_results'] = self.wizard_helper.validate_bundle_candidates(self.description_bundle)

        return

    def do_inherit_metadata(self):
        self.wizard_helper.inherit_metadata(self.param_dict.get("target_id", str()))

        return

    def do_inherit_metadata_refresh(self):
        self.do_inherit_metadata()
        self.do_initiate_wizard()

        return

    def do_get_next_stage(self):
        rendered_stages = self.param_dict.get("rendered_stages", list())  # stages currently rendered on UI
        self.wizard_helper.set_rendered_stages(rendered_stages)

        validation_dict = self.wizard_helper.revalidate_stage_display()

        self.context['validation_dict'] = validation_dict

        if validation_dict.get("is_valid_stage_sequence", True):
            self.context['stage'] = self.wizard_helper.stage_description(self.auto_fields.get("current_stage", str()))

        return

    def do_save_stage_data(self):
        self.wizard_helper.save_stage_data(self.auto_fields)
        current_stage = self.auto_fields.get("current_stage", str())

        # ...also, call to retrieve default stage form (i.e., without user-specified data)
        if self.param_dict.get("default_stage_form", False):
            self.context['stage'] = self.wizard_helper.get_item_stage_display(current_stage, str())

        return

    def do_refresh_targets_data(self):
        return

    def do_get_item_stage_display(self):
        # call to retrieve stage for a single item in description bundle
        target_id = str()
        stage_id = self.param_dict.get("stage_id", str())

        if self.description_targets:
            target_id = self.description_targets[0]["recordID"]

        self.context['stage'] = self.wizard_helper.get_item_stage_display(stage_id, target_id)

        return

    def do_is_same_metadata(self):
        # call to test equality of metadata across bundle items in a stage
        stage_ref = self.param_dict.get("stage_ref", str())
        self.context['state'] = self.wizard_helper.is_same_metadata(stage_ref)

        return

    def do_is_description_mismatch(self):
        # verify mismatch in stage description
        self.context['state'] = self.wizard_helper.is_description_mismatch(self.auto_fields)

        return

    def do_discard_description(self):
        # remove all description metadata from targets
        self.wizard_helper.discard_description()

        return

    def do_negotiate_datafile_pairing(self):
        # call to get datafile pairing information within the ENA deposition context
        self.context['pairing_info'] = self.wizard_helper.negotiate_datafile_pairing()

        return

    def do_datafile_pairing(self):
        # call to pair datafiles - having library layout set to 'PAIRED'
        self.context['result'] = self.wizard_helper.datafile_pairing()

        return

    def do_datafile_unpairing(self):
        # call to unpair datafiles
        self.context['result'] = self.wizard_helper.datafile_unpairing()

        return
