__author__ = 'etuka'

import copy
import pandas as pd
from bson import ObjectId
from dal.copo_da import Sample
from dal import cursor_to_list
from dal.mongo_util import get_collection_ref
import web.apps.web_copo.lookup.lookup as lkup
from django_tools.middlewares import ThreadLocal
import web.apps.web_copo.templatetags.html_tags as htags
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.schemas.utils.data_utils import DecoupleFormSubmission

temp_collection_handle = get_collection_ref('TemporaryCollection')


class WizardHelper:
    def __init__(self):
        self.profile_id = ThreadLocal.get_current_request().session['profile_id']
        self.schema = Sample().get_schema().get("schema_dict")
        self.sample_types = list()

        for s_t in d_utils.get_sample_type_options():
            self.sample_types.append(s_t["value"])

    def generate_stage_items(self):
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
        for s_t in self.sample_types:
            s_stages = d_utils.json_to_pytype(lkup.WIZARD_FILES["sample_attributes"])['properties']

            form_schema = list()

            for f in self.schema:
                # get relevant attributes based on sample type
                if f.get("show_in_form", True) and s_t in f.get("specifications", self.sample_types):
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

    def finalise_sample_description(self, generated_samples):
        object_ids = list()
        for g_s in generated_samples:
            object_ids.append(ObjectId(g_s))

        samples = cursor_to_list(temp_collection_handle.find({"_id": {"$in": object_ids}}))
        df = pd.DataFrame(samples)
        df.drop('_id', axis=1)
        df = df.to_dict('records')

        bulk = Sample().get_collection_handle().initialize_unordered_bulk_op()
        for rec in df:
            bulk.find({"name": rec["name"]}).upsert().replace_one(rec)

        feedback = bulk.execute()

        # now delete from temp or...maybe we work on the main sample table from the onset?

        return True

    def save_temp_samples(self, generated_samples, sample_type, number_to_generate):
        bulk = temp_collection_handle.initialize_unordered_bulk_op()

        sample = generated_samples[0]
        auto_fields = dict()
        auto_fields[Sample().get_qualified_field("name")] = sample["name"]
        auto_fields[Sample().get_qualified_field("sample_type")] = sample_type

        # set qualified path for attributes
        for k, v in sample["attributes"].items():
            if k:
                auto_fields[Sample().get_qualified_field(k)] = v

        kwargs = dict()
        kwargs["target_id"] = str()
        kwargs["validate_only"] = True  # preventing save of record

        record = Sample(profile_id=self.profile_id).save_record(auto_fields, **kwargs)

        number_to_generate = int(number_to_generate)
        generated_name_list = list()
        for indx in range(1, number_to_generate + 1):
            new_record = copy.deepcopy(record)
            new_name = new_record["name"] + "_" + str(indx)
            generated_name_list.append(new_name)
            new_record["name"] = new_name

            bulk.find({"name": new_record["name"]}).upsert().replace_one(new_record)

        feedback = bulk.execute()

        # validate result and retrieve inserted samples
        if 'upserted' in feedback:
            feedback = feedback['upserted']

        generated_samples = list()

        if isinstance(feedback, list) and len(feedback) == number_to_generate:
            generated_samples_id = [p.get("_id") for p in feedback if "_id" in p]
            generated_samples = cursor_to_list(temp_collection_handle.find({"_id": {"$in": generated_samples_id}}))

        return self.resolve_samples_display(generated_samples, sample_type)

    def resolve_object_arrays_column(sefl, columns):
        # object_array_controls = ["copo-characteristics", "copo-comment"]
        object_array_controls = ["copo-comment"]

        gap_elements = list()

        for col in columns:
            if col["control"] in object_array_controls:
                gap_dict = dict(parent_element=col, derived_elements=list())

                for indx, cd in enumerate(col["data"]):
                    if col["control"] == "copo-comment":
                        new_column = dict(
                            actual_id=col["actual_id"],
                            derived_id=col["actual_id"] + "_" + str(indx),
                            control=col["control"], indx=indx
                        )
                        new_column["title"] = col["title"] + " [" + cd[0] + "]"
                        new_column["data"] = cd[1]

                        gap_dict.get("derived_elements").append(new_column)

                gap_elements.append(gap_dict)

        for gp in gap_elements:
            slot_indx = columns.index(gp["parent_element"])
            columns[slot_indx:slot_indx + 1] = gp["derived_elements"][:]
            # get all derived elements

    def resolve_samples_display(self, generated_samples, sample_type):
        # resolve display metadata for samples
        columns = list()
        combined_meta = list()
        form_elements = dict()  # form element specifications
        df = list()

        if len(generated_samples) > 0:
            # get columns
            for f in self.schema:
                if self.truth_test_1(f, sample_type):

                    # get short-form id
                    f["id"] = f["id"].split(".")[-1]

                    columns.append(dict(title=f["label"], actual_id=f["id"], derived_id=f["id"], control=f["control"]))

                    # resolve element control for form generation
                    if "option_values" in f:
                        f["option_values"] = htags.get_control_options(f)

                    # change sample-source control to wizard-compliant version
                    if f.get("control", str()) == "copo-sample-source":
                        f["control"] = "copo-sample-source-2"

                    form_elements[f["id"]] = f

            # get corresponding data; use a representative candidate
            for rec in [generated_samples[0]]:
                for f in self.schema:
                    if self.truth_test_1(f, sample_type):
                        resolved_data = htags.resolve_control_output(rec, f)
                        for col in columns:
                            if col["actual_id"] == f["id"].split(".")[-1]:
                                col["data"] = resolved_data
                                combined_meta.append(col)

            # resolve object arrays: e.g. of these are characteristics, comment'
            self.resolve_object_arrays_column(combined_meta)

            # now apply metadata to all generated samples
            df = pd.DataFrame(generated_samples)
            df['_id'] = df['_id'].apply(self.stringify_it)
            df['_recordMeta'] = df['name'].apply(self.record_meta, args=(combined_meta,))

            df = df.to_dict('records')

        return dict(generated_samples=df, form_elements=form_elements)

    def stringify_it(self, x):
        return str(x)

    def record_meta(self, x, args):
        combined_data = copy.deepcopy(args)

        for col in combined_data:
            if col["actual_id"] == "name":
                col["data"] = x
                break

        return combined_data

    def sample_cell_update(self, target_rows, column_reference, auto_fields, sample_type):
        """
        function saves an update made to a sample cell
        :param target_rows:
        :param column_reference:
        :param auto_fields:
        :param sample_type:
        :return:
        """

        # get schema spec for the target element
        elem_spec = [f for f in self.schema if f["id"].split(".")[-1] == column_reference]

        if elem_spec:
            elem_spec = elem_spec[0]
            elem_spec["id"] = column_reference

            partial_schema = dict(fields=[elem_spec])

            # resolve the new entry given the schema specification
            resolved_data = DecoupleFormSubmission(auto_fields, d_utils.json_to_object(
                partial_schema).fields).get_schema_fields_updated()

            # update sample records
            bulk = temp_collection_handle.initialize_unordered_bulk_op()
            for t_r in target_rows:
                bulk.find({'_id': ObjectId(t_r["recordID"])}).update(
                    {'$set': {column_reference: resolved_data[column_reference]}})
            bulk.execute()

        update_list = list()
        for t_r in target_rows:
            update_list.append(ObjectId(t_r["recordID"]))

        updated_samples = cursor_to_list(temp_collection_handle.find({"_id": {"$in": update_list}}))

        for t_r in target_rows:
            for u_s in updated_samples:
                if t_r["recordID"] == str(u_s["_id"]):
                    u_s["_cell_id"] = t_r["rowID"]

        return self.resolve_samples_display(updated_samples, sample_type)

    def truth_test_1(self, elem, sample_type):
        """
        test for truth of expression
        :param elem: schema element
        :param sample_type: the associated sample type
        :return: boolean
        """
        claim_is = False

        hidden = elem.get("hidden", "false")
        if elem.get("show_in_form", True) and (hidden == "false" or hidden == False) and sample_type in elem.get(
                "specifications", self.sample_types):
            claim_is = True

        return claim_is
