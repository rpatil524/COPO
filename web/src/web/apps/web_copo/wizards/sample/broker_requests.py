__author__ = 'etuka'
__date__ = '21 Nov 2016'

import ast
import web.apps.web_copo.lookup.lookup as lkup
from django_tools.middlewares import ThreadLocal
import web.apps.web_copo.templatetags.html_tags as htags
import web.apps.web_copo.schemas.utils.data_utils as d_utils
import web.apps.web_copo.wizards.sample.wizard_helper as wizh


class BrokerRequests:
    def __init__(self, **kwargs):
        self.param_dict = kwargs

        self.context = self.param_dict.get("context", dict())
        self.generated_samples = self.param_dict.get("generated_samples", list())
        self.target_rows = self.param_dict.get("target_rows", list())
        self.sample_type = self.param_dict.get("sample_type", str())
        self.column_reference = self.param_dict.get("column_reference", str())
        self.number_to_generate = self.param_dict.get("number_to_generate", str())
        self.target_id = self.param_dict.get("target_id", str())

        self.auto_fields = self.param_dict.get("auto_fields", dict())

        if self.auto_fields and isinstance(self.auto_fields, str):
            self.auto_fields = ast.literal_eval(self.auto_fields)

        # instance of wizard helper for handling request actions
        self.wizard_helper = wizh.WizardHelper()

    def get_request_dict(self):
        # request-to-action mapping
        request_dict = dict(sample_wizard_components=self.do_sample_wizard_components,
                            finalise_description=self.do_finalise_description,
                            save_temp_samples=self.do_save_temp_samples,
                            sample_cell_update=self.do_sample_cell_update,
                            )

        return request_dict

    def post_context(self, request_action):
        request_dict = self.get_request_dict()

        request_action = request_action.split(",")

        for rqa in request_action:
            if rqa in request_dict:
                request_dict[rqa]()

        return self.context

    def do_finalise_description(self):
        status = self.wizard_helper.finalise_sample_description(self.generated_samples)
        return self.context

    def do_save_temp_samples(self):
        self.context['generated_samples'] = self.wizard_helper.save_temp_samples(self.generated_samples, self.sample_type, self.number_to_generate)
        return self.context

    def do_sample_cell_update(self):
        self.context['updated_samples'] = self.wizard_helper.sample_cell_update(self.target_rows, self.column_reference, self.auto_fields, self.sample_type)
        return self.context

    def do_sample_wizard_components(self):
        self.context['wiz_message'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["sample_wizard_messages"])[
            "properties"]
        self.context['wiz_howtos'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["sample_wizard_howto"])
        self.context['wizard_stages'] = self.wizard_helper.generate_stage_items()

        # get all records: used in the UI for 'cloning' and other purposes
        profile_id = ThreadLocal.get_current_request().session['profile_id']
        self.context["component_records"] = htags.generate_component_records("sample", profile_id)

        return self.context
