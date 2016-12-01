__author__ = 'etuka'
__date__ = '21 Nov 2016'

import web.apps.web_copo.lookup.lookup as lkup
import web.apps.web_copo.schemas.utils.data_utils as d_utils
import web.apps.web_copo.wizards.sample.wizard_helper as wizh


class BrokerRequests:
    def __init__(self, **kwargs):
        self.param_dict = kwargs

        self.context = self.param_dict.get("context", dict())

        # instance of wizard helper ready to handle request actions
        self.wizard_helper = wizh.WizardHelper()

    def get_request_dict(self):
        # request-to-action mapping
        request_dict = dict(sample_wizard_components=self.do_sample_wizard_components
                            )

        return request_dict

    def post_context(self, request_action):
        request_dict = self.get_request_dict()

        request_action = request_action.split(",")

        for rqa in request_action:
            if rqa in request_dict:
                request_dict[rqa]()

        return self.context

    def do_sample_wizard_components(self):
        self.context['wiz_message'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["sample_wizard_messages"])[
            "properties"]
        self.context['wiz_howtos'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["sample_wizard_howto"])
        self.context['wizard_stages'] = dict()

        start = d_utils.json_to_pytype(lkup.WIZARD_FILES["sample_start"])['properties']
        biosample = d_utils.json_to_pytype(lkup.WIZARD_FILES["biosample"])['properties']
        isasample = d_utils.json_to_pytype(lkup.WIZARD_FILES["isasample"])['properties']

        self.context['wizard_stages']['start'] = self.wizard_helper.treat_wizard_stages(start)
        self.context['wizard_stages']['biosample'] = self.wizard_helper.treat_wizard_stages(biosample)
        self.context['wizard_stages']['isasample'] = self.wizard_helper.treat_wizard_stages(isasample)

        return self.context
