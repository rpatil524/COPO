__author__ = 'etuka'
__date__ = '21 Nov 2016'

import json
import web.apps.web_copo.wizards.sample.wizard_helper as wizh
import web.apps.web_copo.wizards.sample.ingest_data as tcsv
from dal.copo_da import Description


class BrokerRequests:
    def __init__(self, **kwargs):
        self.param_dict = kwargs

        self.context = self.param_dict.get("context", dict())
        self.target_id = self.param_dict.get("target_id", str())
        self.profile_id = self.param_dict.get("profile_id", str())
        self.description_token = self.param_dict.get("description_token", str())

        self.auto_fields = self.param_dict.get("auto_fields", dict())
        if self.auto_fields and isinstance(self.auto_fields, str):
            self.auto_fields = json.loads(self.auto_fields)

        # instance of wizard helper for handling request actions
        self.wizard_helper = wizh.WizardHelper(description_token=self.description_token, profile_id=self.profile_id)

    def get_request_dict(self):
        # request-to-action mapping
        request_dict = dict(
            initiate_description=self.do_initiate_description,
            resolved_object=self.do_resolved_object,
            next_stage=self.do_next_stage,
            resolve_uri=self.do_resolve_uri,
            validate_sample_names=self.do_validate_sample_names,
            validate_bundle_name=self.do_validate_bundle_name,
            get_discrete_attributes=self.do_get_discrete_attributes,
            get_cell_control=self.do_get_cell_control,
            save_cell_data=self.do_save_cell_data,
            finalise_description=self.do_finalise_description,
            discard_description=self.do_discard_description,
            batch_update=self.do_batch_update,
            pending_description=self.do_pending_description,
            delete_pending_description=self.do_delete_pending_description,
            description_csv=self.do_description_csv,
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
        self.context['result'] = self.wizard_helper.initiate_description()

        return self.context

    def do_resolved_object(self):
        resolved_object = self.param_dict.get("resolved_object", dict())

        if resolved_object and isinstance(resolved_object, str):
            resolved_object = json.loads(resolved_object)

        self.context['component_record'] = self.wizard_helper.resolve_sample_object(resolved_object)

        return self.context

    def do_next_stage(self):
        self.context['next_stage'] = self.wizard_helper.resolve_next_stage(self.auto_fields)

        return self.context

    def do_resolve_uri(self):
        self.context['resolved_output'] = self.wizard_helper.resolver_uri(self.param_dict.get("resolver_uri", str()))

    def do_validate_sample_names(self):
        self.context['validation_result'] = self.wizard_helper.validate_sample_names(
            self.param_dict.get("sample_names", str()))

    def do_validate_bundle_name(self):
        self.context['validation_status'] = self.wizard_helper.validate_bundle_name(
            self.param_dict.get("bundle_name", str()))["status"]

    def do_get_discrete_attributes(self):
        self.context['table_data'] = self.wizard_helper.generate_discrete_attributes()

    def do_get_cell_control(self):
        cell_reference = self.param_dict.get("cell_reference", str())
        self.context['cell_control'] = self.wizard_helper.get_cell_control(cell_reference, self.target_id)

    def do_save_cell_data(self):
        cell_reference = self.param_dict.get("cell_reference", str())
        self.context['cell_update'] = self.wizard_helper.save_cell_data(cell_reference, self.target_id,
                                                                        self.auto_fields)

    def do_batch_update(self):
        cell_reference = self.param_dict.get("cell_reference", str())
        target_rows = self.param_dict.get("target_rows", list())
        self.context['batch_update'] = self.wizard_helper.batch_update_cells(cell_reference, self.target_id,
                                                                             target_rows)

    def do_finalise_description(self):
        self.context['finalise_result'] = self.wizard_helper.finalise_description()

    def do_discard_description(self):
        self.context['discard_result'] = self.wizard_helper.discard_description()

    def do_pending_description(self):
        self.context['pending'] = self.wizard_helper.get_pending_description()

    def do_delete_pending_description(self):
        self.context['status'] = self.wizard_helper.discard_description()

    def do_description_csv(self):
        translate_csv = tcsv.IngestData(description_token=self.description_token, profile_id=self.profile_id)
        self.context['result'] = translate_csv.manage_process(csv_file=self.param_dict.get("description_file", str()))
