__author__ = 'etuka'

import web.apps.web_copo.schemas.utils.data_utils as d_utils
import web.apps.web_copo.templatetags.html_tags as htags
from django_tools.middlewares import ThreadLocal
import web.apps.web_copo.lookup.lookup as lkup
from dal.copo_da import Sample


class WizardHelper:
    def __init__(self):
        self.profile_id = ThreadLocal.get_current_request().session['profile_id']
        self.schema = Sample().get_schema().get("schema_dict")

    def generate_attributes(self, target_id):

        sample_attributes = dict()
        record = Sample().get_record(target_id)
        sample_attributes["record"] = record
        table_schema = list()

        sample_types = list()

        for s_t in d_utils.get_sample_type_options():
            sample_types.append(s_t["value"])

        sample_type = str()

        if "sample_type" in record:
            sample_type = record["sample_type"]

        for f in self.schema:
            # get relevant attributes based on sample type
            if f.get("show_in_sub_table", False) and sample_type in f.get("specifications", sample_types):
                # if required, resolve data source for select-type controls,
                # i.e., if a callback is defined on the 'option_values' field
                if "option_values" in f:
                    f["option_values"] = htags.get_control_options(f)

                # change sample-source control to wizard-compliant version
                if f.get("control", str()) == "copo-sample-source":
                    f["control"] = "copo-sample-source-2"

                # get short-form id
                f["id"] = f["id"].split(".")[-1]

                # might not need to include name
                if f["id"] == "name":
                    continue

                table_schema.append(f)

        sample_attributes["schema"] = table_schema

        return sample_attributes

    def generate_stage_items(self):

        sample_types = list()

        for s_t in d_utils.get_sample_type_options():
            sample_types.append(s_t["value"])

        wizard_stages = dict()

        # get start stages
        start = d_utils.json_to_pytype(lkup.WIZARD_FILES["sample_start"])['properties']
        wizard_stages['start'] = start

        # if required, resolve data source for select-type controls,
        # i.e., if a callback is defined on the 'option_values' field
        for stage in wizard_stages['start']:
            if "items" in stage:
                for st in stage['items']:
                    if "option_values" in st:
                        st["option_values"] = htags.get_control_options(st)

        # get sample types
        for s_t in sample_types:
            s_stages = d_utils.json_to_pytype(lkup.WIZARD_FILES["sample_attributes"])['properties']

            form_schema = list()

            for f in self.schema:
                # get relevant attributes based on sample type
                if f.get("show_in_form", True) and s_t in f.get("specifications", sample_types):
                    # if required, resolve data source for select-type controls,
                    # i.e., if a callback is defined on the 'option_values' field
                    if "option_values" in f:
                        f["option_values"] = htags.get_control_options(f)

                    # change sample-source control to wizard-compliant version
                    if f.get("control", str()) == "copo-sample-source":
                        f["control"] = "copo-sample-source-2"

                    # get short-form id
                    f["id"] = f["id"].split(".")[-1]

                    # might not need to include name
                    if f["id"] == "name":
                        continue

                    form_schema.append(f)

                for p in s_stages:
                    if p["ref"] == "sample_attributes":
                        p["items"] = form_schema

            wizard_stages[s_t] = s_stages

        return wizard_stages

    def save_samples(self, generated_samples, sample_type):
        bulk = Sample().get_collection_handle().initialize_unordered_bulk_op()
        for sample in generated_samples:
            auto_fields = dict()
            auto_fields[Sample().get_qualified_field("name")] = sample["name"]
            auto_fields[Sample().get_qualified_field("sample_type")] = sample_type

            # set qualified path for attributes
            for k, v in sample["attributes"].items():
                if k:
                    auto_fields[Sample().get_qualified_field(k)] = v

            kwargs = dict()
            kwargs["target_id"] = str()
            kwargs["validate_only"] = True # preventing save per record in order to do bulk save

            record = Sample(profile_id=self.profile_id).save_record(auto_fields, **kwargs)
            bulk.insert(record)
        bulk.execute()

        return True
