__author__ = 'etuka'
__date__ = '17 June 2016'

import json
import web.apps.web_copo.wizards.datafile.wizard_helper as wizh


class BrokerRequests:
    def __init__(self, **kwargs):
        self.param_dict = kwargs

        self.context = self.param_dict.get("context", dict())

        self.auto_fields = self.param_dict.get("auto_fields", dict())
        if self.auto_fields and isinstance(self.auto_fields, str):
            self.auto_fields = json.loads(self.auto_fields)

        self.profile_id = self.param_dict.get("profile_id", str())
        self.description_token = self.param_dict.get("description_token", str())
        self.description_targets = self.param_dict.get("description_targets", list())  # subset of items in bundle

        # an wizard helper instance to handle request actions
        self.wizard_helper = wizh.WizardHelper(description_token=self.description_token, profile_id=self.profile_id)

    def get_request_dict(self):
        # request-to-action mapping
        request_dict = dict(initiate_description=self.do_initiate_description,
                            next_stage=self.do_next_stage,
                            get_description_bundle=self.do_get_description_bundle,
                            get_discrete_attributes=self.do_get_discrete_attributes,
                            un_describe=self.do_un_describe,
                            datafile_pairing=self.do_datafile_pairing,
                            datafile_unpairing=self.do_datafile_unpairing
                            )

        return request_dict

    def post_context(self, request_action):
        request_dict = self.get_request_dict()

        request_action = request_action.split(",")

        for rqa in request_action:
            if rqa in request_dict:
                request_dict[rqa]()

        return self.context

    def do_initiate_description(self):
        self.context['result'] = self.wizard_helper.initiate_description(self.description_targets)

    def do_next_stage(self):
        self.context['next_stage'] = self.wizard_helper.resolve_next_stage(self.auto_fields)

    def do_get_description_bundle(self):
        self.context['result'] = self.wizard_helper.get_description_bundle()

    def do_get_discrete_attributes(self):
        self.context['table_data'] = self.wizard_helper.generate_discrete_attributes()

    def do_un_describe(self):
        self.context['result'] = self.wizard_helper.discard_description(self.description_targets)

    def do_datafile_pairing(self):
        # call to pair datafiles - having library layout set to 'PAIRED'
        self.context['result'] = self.wizard_helper.datafile_pairing()

    def do_datafile_unpairing(self):
        # call to unpair datafiles
        self.context['result'] = self.wizard_helper.datafile_unpairing()
