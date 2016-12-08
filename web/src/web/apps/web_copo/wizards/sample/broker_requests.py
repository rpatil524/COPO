__author__ = 'etuka'
__date__ = '21 Nov 2016'

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
        self.sample_type = self.param_dict.get("sample_type", str())
        self.target_id = self.param_dict.get("target_id", str())

        # instance of wizard helper ready to handle request actions
        self.wizard_helper = wizh.WizardHelper()

    def get_request_dict(self):
        # request-to-action mapping
        request_dict = dict(sample_wizard_components=self.do_sample_wizard_components,
                            save_samples=self.do_save_samples,
                            attributes_display=self.do_attributes_display
                            )

        return request_dict

    def post_context(self, request_action):
        request_dict = self.get_request_dict()

        request_action = request_action.split(",")

        for rqa in request_action:
            if rqa in request_dict:
                request_dict[rqa]()

        return self.context

    def do_save_samples(self):
        status = self.wizard_helper.save_samples(self.generated_samples, self.sample_type)
        return self.context

    def do_attributes_display(self):
        self.context['sample_attributes'] = self.wizard_helper.generate_attributes(self.target_id)

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
