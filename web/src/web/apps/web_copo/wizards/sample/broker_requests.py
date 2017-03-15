__author__ = 'etuka'
__date__ = '21 Nov 2016'

import ast
import web.apps.web_copo.lookup.lookup as lkup
import web.apps.web_copo.schemas.utils.data_utils as d_utils
import web.apps.web_copo.wizards.sample.wizard_helper as wizh


class BrokerRequests:
    def __init__(self, **kwargs):
        self.param_dict = kwargs

        self.context = self.param_dict.get("context", dict())
        self.generated_samples = self.param_dict.get("generated_samples", list())
        self.target_rows = self.param_dict.get("target_rows", list())
        self.sample_type = self.param_dict.get("sample_type", str())
        self.number_to_generate = self.param_dict.get("number_to_generate", str())
        self.target_id = self.param_dict.get("target_id", str())

        self.auto_fields = self.param_dict.get("auto_fields", dict())

        if self.auto_fields and isinstance(self.auto_fields, str):
            self.auto_fields = ast.literal_eval(self.auto_fields)

        self.update_metadata = self.param_dict.get("update_metadata", dict())

        if self.update_metadata and isinstance(self.update_metadata, str):
            self.update_metadata = ast.literal_eval(self.update_metadata)

        self.initial_sample_attributes = self.param_dict.get("initial_sample_attributes", dict())

        if self.initial_sample_attributes and isinstance(self.initial_sample_attributes, str):
            self.initial_sample_attributes = ast.literal_eval(self.initial_sample_attributes)

        # instance of wizard helper for handling request actions
        self.wizard_helper = wizh.WizardHelper()

    def get_request_dict(self):
        # request-to-action mapping
        request_dict = dict(sample_wizard_components=self.do_sample_wizard_components,
                            save_generated_samples=self.do_save_generated_samples,
                            sample_cell_update=self.do_sample_cell_update,
                            sample_name_schema=self.do_sample_name_schema,
                            )

        return request_dict

    def post_context(self, request_action):
        request_dict = self.get_request_dict()

        request_action = request_action.split(",")

        for rqa in request_action:
            if rqa in request_dict:
                request_dict[rqa]()

        return self.context

    def do_save_generated_samples(self):
        self.context['generated_samples'] = self.wizard_helper.save_initial_samples(self.generated_samples,
                                                                                    self.sample_type,
                                                                                    self.initial_sample_attributes)
        return self.context

    def do_sample_name_schema(self):
        self.context['sample_name_schema'] = self.wizard_helper.sample_name_schema()

        return self.context

    def do_sample_cell_update(self):
        self.context['updated_samples'] = self.wizard_helper.sample_cell_update(self.target_rows, self.auto_fields,
                                                                                self.update_metadata)
        return self.context

    def do_sample_wizard_components(self):
        self.context['wiz_message'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["sample_wizard_messages"])[
            "properties"]
        self.context['wizard_stages'] = self.wizard_helper.generate_stage_items()

        return self.context
