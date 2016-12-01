__author__ = 'etuka'

import web.apps.web_copo.templatetags.html_tags as htags


class WizardHelper:
    def treat_stage(self, stage):
        html_tag = list()

        if "items" in stage:
            for st in stage['items']:

                # if required, resolve data source for select-type controls,
                # i.e., if a callback is defined on the 'option_values' field

                if "option_values" in st:
                    st["option_values"] = htags.get_control_options(st)

                html_tag.append(st)

            stage['items'] = html_tag

        return stage

    def treat_wizard_stages(self, stages):
        stage_list = list()

        for st in stages:
            stage_list.append(self.treat_stage(st))

        return stage_list
