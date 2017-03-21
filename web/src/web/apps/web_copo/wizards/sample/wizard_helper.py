__author__ = 'etuka'

import copy
import pandas as pd
from bson import ObjectId
from dal.copo_da import Sample
from dal import cursor_to_list
import web.apps.web_copo.lookup.lookup as lkup
from django_tools.middlewares import ThreadLocal
import web.apps.web_copo.templatetags.html_tags as htags
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.schemas.utils.data_utils import DecoupleFormSubmission


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

    def save_initial_samples(self, generated_samples, sample_type, initial_sample_attributes):
        bulk = Sample().get_collection_handle().initialize_unordered_bulk_op()

        # form record template, for first item in generated_sample
        auto_fields = dict()
        auto_fields[Sample().get_qualified_field("name")] = generated_samples[0]
        auto_fields[Sample().get_qualified_field("sample_type")] = sample_type
        for k, v in initial_sample_attributes.items():
            if k:
                auto_fields[Sample().get_qualified_field(k)] = v

        kwargs = dict()
        kwargs["target_id"] = str()
        kwargs["validate_only"] = True  # preventing save of record

        record = Sample(profile_id=self.profile_id).save_record(auto_fields, **kwargs)

        # use template record to generate other records, modifying only the name attribute
        for name in generated_samples:
            new_record = copy.deepcopy(record)
            new_record["name"] = name

            bulk.find({"name": new_record["name"]}).upsert().replace_one(new_record)

        feedback = bulk.execute()

        # validate result and retrieve inserted samples
        if 'upserted' in feedback:
            feedback = feedback['upserted']

        generated_sample_records = list()

        if isinstance(feedback, list) and len(feedback) == len(generated_samples):
            generated_samples_id = [p.get("_id") for p in feedback if "_id" in p]
            generated_sample_records = cursor_to_list(
                Sample().get_collection_handle().find({"_id": {"$in": generated_samples_id}}))

        return self.resolve_samples_display(generated_sample_records, sample_type)

    def sample_name_schema(self):
        """
        function return sample name schema with unique items
        :return: name schema
        """

        # get sample name element from the sample schema
        name_schema_template_list = [x for x in self.schema if x["id"].split(".")[-1] == "name"]

        sample_name_schema = dict()
        if name_schema_template_list:
            sample_name_schema = name_schema_template_list[0]
            sample_name_schema["help_tip"] = "Modify as required to reflect your specific sample name."
            sample_name_schema["label"] = str()
            sample_name_schema["control_meta"]["input_group_addon"] = "left"
            sample_name_schema["batch"] = "true"  # allows unique test to extend to siblings
            sample_name_schema["batchuniquename"] = "assigned_sample"
            sample_name_schema["batchuniquename"] = "assigned_sample"

            # get all sample names for unique test
            unique_names = htags.generate_unique_items(component="sample", profile_id=self.profile_id, elem_id="name",
                                                       record_id=str())
            sample_name_schema["unique_items"] = unique_names

        return sample_name_schema

    def resolve_object_arrays_column(sefl, columns):
        """
        function deconstructs object type controls into discrete items for tabular rendering and editing
        :param columns:
        :return:
        """
        object_array_controls = ["copo-characteristics", "copo-comment"]

        gap_elements = list()

        for col in [cl for cl in columns if cl["control"] in object_array_controls]:
            gap_dict = dict(parent_element=col, derived_elements=list())

            derived_id_count = 0

            for indx, cd in enumerate(col["data"]):
                derived_id_count += 1
                new_column = dict(
                    actual_id=col["actual_id"],
                    derived_id=col["actual_id"] + "_" + str(derived_id_count),
                    control=col["control"],
                    indx=indx,
                    title=col["title"] + " [" + list(cd[0].values())[0] + "]",
                    data=list(cd[1].values())[0],
                    meta=list(cd[1].keys())[0]
                )

                gap_dict.get("derived_elements").append(new_column)

                # get other elements
                for cd_ext in list(cd[2:]):
                    derived_id_count += 1
                    cd_ext_val = list(cd_ext.values())[0]
                    cd_ext_title = list(cd_ext.keys())[0]
                    new_column = dict(
                        actual_id=col["actual_id"],
                        derived_id=col["actual_id"] + "_" + str(derived_id_count),
                        control=col["control"],
                        indx=indx,
                        title=cd_ext_title,
                        data=cd_ext_val,
                        meta=cd_ext_title
                    )

                    gap_dict.get("derived_elements").append(new_column)

            gap_elements.append(gap_dict)

        for gp in gap_elements:
            slot_indx = columns.index(gp["parent_element"])
            columns[slot_indx:slot_indx + 1] = gp["derived_elements"][:]
            # get all derived elements

    def resolve_samples_display(self, generated_samples, sample_type):
        # resolve display metadata for samples
        combined_meta = list()
        form_elements = dict()  # form element specifications
        df = list()

        if len(generated_samples) > 0:
            rec = generated_samples[0]
            # get columns, and corresponding data using the representative candidate record, rec
            for f in self.schema:
                if self.truth_test_1(f, sample_type):

                    # get short-form id
                    f["id"] = f["id"].split(".")[-1]

                    col = dict(title=f["label"], actual_id=f["id"], derived_id=f["id"], control=f["control"])

                    # resolve element control for form generation
                    if "option_values" in f:
                        f["option_values"] = htags.get_control_options(f)

                    form_elements[f["id"]] = f

                    col["data"] = htags.resolve_control_output(rec, f)

                    combined_meta.append(col)

            # resolve object arrays for display in separate columns: e.g. of these are characteristics, comments'
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

    def sample_cell_update(self, target_rows, auto_fields, update_metadata):
        """
        function saves an update made to a sample cell
        :param target_rows:
        :param auto_fields:
        :param update_metadata:
        :return:
        """

        column_reference = update_metadata.get("column_reference", str())  # element key; the update target
        sample_type = update_metadata.get("sample_type", str())  # the sample type
        update_element_indx = update_metadata.get("update_element_indx", str())  # if a list element type, the index
        update_meta = update_metadata.get("update_meta", str())  # present if a composite element is being updated

        # get schema spec for the target element
        elem_spec = [f for f in self.schema if f["id"].split(".")[-1] == column_reference]

        if elem_spec:
            elem_spec = elem_spec[0]
            elem_spec["id"] = column_reference

            partial_schema = dict(fields=[elem_spec])

            # resolve the new entry given  'partial_schema'
            resolved_data = DecoupleFormSubmission(auto_fields, d_utils.json_to_object(
                partial_schema).fields).get_schema_fields_updated()

            # kick in some validation here before proceeding to save!
            validate_status = self.do_validation(elem_spec, resolved_data, target_rows)

            if validate_status.get("status") == "error":
                return validate_status

            # set bulk object
            bulk = Sample().get_collection_handle().initialize_unordered_bulk_op()

            if update_element_indx != "":
                update_element_indx = int(update_element_indx)
                # do positional element update
                object_list = list()
                for t_r in target_rows:
                    object_list.append(ObjectId(t_r["recordID"]))

                update_candidates = cursor_to_list(Sample().get_collection_handle().find({"_id": {"$in": object_list}}))
                for u_c in update_candidates:  # set element based on index
                    amendable_entity = u_c[column_reference]
                    if isinstance(amendable_entity, list):
                        amendable_entity[update_element_indx:update_element_indx + 1] = resolved_data[column_reference][
                                                                                        :]
                        bulk.find({'_id': u_c["_id"]}).update({'$set': {column_reference: amendable_entity}})
            else:
                for t_r in target_rows:
                    bulk.find({'_id': ObjectId(t_r["recordID"])}).update(
                        {'$set': {column_reference: resolved_data[column_reference]}})

            # execute bulk object
            bulk.execute()

        update_list = list()
        for t_r in target_rows:
            update_list.append(ObjectId(t_r["recordID"]))

        updated_samples = cursor_to_list(Sample().get_collection_handle().find({"_id": {"$in": update_list}}))

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

    def do_validation(self, elem_spec, resolved_data, target_rows):
        """
        validates data given element's specification or schema
        :param elem_spec:
        :param resolved_data:
        :param target_rows:
        :return:
        """
        validation_result = dict(status="success", message="")
        resolved_data = resolved_data[elem_spec["id"].split(".")[-1]]

        # validate required attributes
        if "required" in elem_spec and str(elem_spec["required"]).lower() == "true":
            if isinstance(resolved_data, str) and resolved_data.strip() == str():
                validation_result["status"] = "error"
                validation_result["message"] = "The " + elem_spec["label"] + " value is required!"

                return validation_result

                # should probably add validation for object types here, that might need some thinking though

        # validate unique attributes
        if "unique" in elem_spec and str(elem_spec["unique"]).lower() == "true":
            if isinstance(resolved_data, str) and Sample().get_collection_handle().find(
                    {'name': {'$regex': "^" + resolved_data + "$", "$options": 'i'}}).count() >= 1:
                validation_result["status"] = "error"
                validation_result["message"] = "Nothing to update or the " + elem_spec[
                    "label"] + " value already exists!"

                return validation_result

                # should probably add validation for object types here, that might need some thinking though

        # validate characteristics attributes
        if "control" in elem_spec and elem_spec["control"] == "copo-characteristics":
            objects_of_interest = dict(unit=str(), value=str())

            if resolved_data:
                extracted_objects = resolved_data[0]
                for k, v in extracted_objects.items():
                    if k in objects_of_interest:
                        objects_of_interest[k] = v['annotationValue']

            is_numeric = False
            if objects_of_interest['value']:
                try:
                    objects_of_interest['value'] = float(objects_of_interest['value'])
                    is_numeric = True
                except ValueError:
                    pass

            if is_numeric and not objects_of_interest['unit']:
                validation_result["status"] = "error"
                validation_result["message"] = "Numeric value requires a unit!"

                return validation_result
            # commenting out the 'elif' condition below prevents an update lock up;
            # a case where you can't update the value because of the unit, and vice versa
            # elif not is_numeric and objects_of_interest['unit']:
            #     validation_result["status"] = "error"
            #     validation_result["message"] = "Non-numeric value does not require a unit!"
            #
            #     return validation_result

        return validation_result
