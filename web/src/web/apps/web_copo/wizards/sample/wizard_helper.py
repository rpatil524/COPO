__author__ = 'etuka'
import re
import json
import numpy as np
import pandas as pd
from bson import ObjectId
from django.conf import settings
import urllib.request as urllib2
from dal.mongo_util import get_collection_ref

from dal.copo_da import Sample, Description
import web.apps.web_copo.lookup.lookup as lkup
from converters.ena.copo_isa_ena import ISAHelpers
import web.apps.web_copo.templatetags.html_tags as htags
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.schemas.utils.data_utils import DecoupleFormSubmission
from web.apps.web_copo.lookup.copo_enums import Loglvl, Logtype

lg = settings.LOGGER


class WizardHelper:
    def __init__(self, description_token, profile_id):
        self.schema = Sample().get_schema().get("schema_dict")
        self.description_token = description_token
        self.profile_id = self.set_profile_id(profile_id)
        self.key_split = "___0___"
        self.object_key = settings.SAMPLE_OBJECT_PREFIX + self.description_token
        self.store_name = settings.SAMPLE_OBJECT_STORE

    def set_profile_id(self, profile_id):
        """
        function sets profile id either from passed value or from description metadata
        :param profile_id:
        :return:
        """

        if not self.description_token:
            return profile_id

        description = Description().GET(self.description_token)

        if not description:
            return profile_id

        profile_id = description.get('profile_id', str())

        return profile_id

    def generate_stage_items(self):
        """
        function generates the stages of the wizard and creates a description token that will guide the description
        :return:
        """

        # get start stages
        wizard_stages = d_utils.json_to_pytype(lkup.WIZARD_FILES["sample_start"])['properties']

        # if required, resolve data source for select-type controls,
        # i.e., if a callback is defined on the 'option_values' field
        for stage in wizard_stages:
            if "items" in stage:
                for st in stage['items']:
                    if "option_values" in st:
                        st["option_values"] = htags.get_control_options(st)

        # create a description record for storing temporary values as the user moves through the wizard
        self.description_token = str(
            Description().create_description(stages=wizard_stages, attributes=dict(), profile_id=self.profile_id,
                                             component='sample', meta=dict())['_id'])

        return True

    def resolve_next_stage(self, auto_fields):
        """
        given data from a stage, function tries to resolve the next stage to be displayed to the user by the wizard
        :param auto_fields:
        :return:
        """

        next_stage_dict = dict(abort=False)
        current_stage = auto_fields.get("current_stage", str())

        if not current_stage:
            next_stage_dict['wiz_message'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["sample_wizard_messages"])[
                "properties"]

            if not self.description_token:  # likely the first (dynamic) stage to be requested
                self.generate_stage_items()
                next_stage_dict['wiz_token'] = self.description_token
            else:  # likely a call to reload an incomplete description
                # update timestamp
                Description().edit_description(self.description_token, dict(created_on=d_utils.get_datetime()))

        # start by getting the description record
        description = Description().GET(self.description_token)

        if not description:
            # invalid description; send signal to abort the wizard
            next_stage_dict["abort"] = True
            return next_stage_dict

        stages = description["stages"]
        attributes = description["attributes"]
        meta = description.get("meta", dict())

        # save in-coming stage data, check for changes, re-validate wizard, serve next stage
        next_stage_index = [indx for indx, stage in enumerate(stages) if stage['ref'] == current_stage]
        next_stage_index = next_stage_index[0] + 1 if len(next_stage_index) else 0

        # save current stage data, but hold on to previous data for comparison purposes
        previous_data = dict()
        if current_stage:
            previous_data = attributes.get(current_stage, dict())
            current_data = DecoupleFormSubmission(auto_fields,
                                                  d_utils.json_to_object(
                                                      stages[next_stage_index - 1]).items).get_schema_fields_updated()
            # save current stage data
            attributes[current_stage] = current_data

            # save attributes
            Description().edit_description(self.description_token, dict(attributes=attributes))

        # get next stage
        next_stage_dict['stage'] = self.serve_stage(stages, next_stage_index)

        if not next_stage_dict['stage']:
            # no stage to retrieve, this should signal end
            return next_stage_dict

        if next_stage_index > 0:
            if previous_data and not (previous_data == current_data):  # stage data has changed, refresh wizard
                next_stage_dict['refresh_wizard'] = True

                # remove store object, if any, associated with this description
                Description().remove_store_object(store_name=self.store_name, object_key=self.object_key)

                # update meta
                meta["generated_columns"] = list()

        # build data dictionary for stage
        if next_stage_dict['stage']['ref'] in attributes and "data" not in next_stage_dict['stage']:
            next_stage_dict['stage']['data'] = DecoupleFormSubmission(attributes[next_stage_dict['stage']['ref']],
                                                                      d_utils.json_to_object(
                                                                          next_stage_dict[
                                                                              'stage']).items).get_schema_fields_updated()

        # save last rendered stage
        if next_stage_dict['stage']['ref']:
            meta["last_rendered_stage"] = next_stage_dict['stage']['ref']

        Description().edit_description(self.description_token, dict(meta=meta))

        return next_stage_dict

    def serve_stage(self, stages, next_stage_index):
        """
        function determines how a given stage should be served
        :param stage:
        :return:
        """

        stage = dict()

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        if "callback" in stage:
            # execute callback to derive stage
            try:
                stage = getattr(WizardHelper, stage["callback"])(self, next_stage_index)
            except:
                pass

        return stage

    def display_sample_clone(self, next_stage_index):
        """
        stage callback function: determines if sample clone stage should be displayed
        :param stage:
        :return:
        """

        stage = dict()

        description = Description().GET(self.description_token)
        stages = description["stages"]
        attributes = description["attributes"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        user_choice = attributes.get("sample_clone", dict()).get("sample_clone", str())

        if not stage["ref"] == user_choice:
            stage = self.serve_stage(stages, next_stage_index + 1)

        return stage

    def sample_clone_options(self, next_stage_index):
        """
        stage callback function: determines if local sample clone option should be displayed given presence of samples
        :param next_stage_index:
        :return:
        """

        description = Description().GET(self.description_token)
        stages = description["stages"]

        stage = dict()

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

            if len(d_utils.get_samples_json()["options"]) == 0:
                # remove option for local sample clone

                for item in stage["items"]:
                    if item["id"] == "sample_clone":
                        indx = [indx for indx, x in enumerate(item["option_values"]) if x["value"] == "clone_existing"]
                        if indx:
                            del item["option_values"][indx[0]]

        return stage

    def display_sample_naming(self, next_stage_index):
        """
        stage callback function: determines sample naming method to display based on user choice
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.description_token)
        stages = description["stages"]
        attributes = description["attributes"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        user_choice = attributes.get("sample_naming_method", dict()).get("sample_naming_method", str())

        if not stage["ref"] == user_choice:
            stage = self.serve_stage(stages, next_stage_index + 1)

        # check for number of samples dependency, re-validate if necessary

        number_of_samples = attributes.get("number_of_samples", dict()).get("number_of_samples", 1)

        meta = description.get("meta", dict())
        number_of_samples_old = meta.get(stage["ref"] + "_number_of_samples", None)

        if number_of_samples_old and not number_of_samples == number_of_samples_old:
            status = self.revalidate_sample_name(user_choice)  # revalidate
            if stage["ref"] in attributes and status == 'error':
                data = attributes[stage["ref"]]

                data[user_choice + "_hidden"] = str()
                stage["data"] = DecoupleFormSubmission(data,
                                                       d_utils.json_to_object(stage).items).get_schema_fields_updated()

        return stage

    def get_sample_attributes(self, next_stage_index):
        """
        stage callback function: identifies sample attribute to present to user, mostly based on sample type choice
        :param next_stage_index:
        :return:
        """
        stage = dict()

        sample_types = list()

        for s_t in d_utils.get_sample_type_options():
            sample_types.append(s_t["value"])

        description = Description().GET(self.description_token)
        stages = description["stages"]
        attributes = description["attributes"]
        meta = description["meta"]

        # get sample type - user choice
        user_choice = attributes.get("sample_type", dict()).get("sample_type", str())

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

            # compose stage items if first time here
            stage_items = list()

            for f in self.schema:
                # get relevant attributes based on sample type
                if f.get("show_in_form", True) and user_choice in f.get("specifications", sample_types):
                    # if required, resolve data source for select-type controls,
                    # i.e., if a callback is defined on the 'option_values' field
                    if "option_values" in f:
                        f["option_values"] = htags.get_control_options(f)

                    # get short-form id
                    f["id"] = f["id"].split(".")[-1]

                    # don't need to include sample name
                    if f["id"] == "name":
                        continue

                    stage_items.append(f)

            stage["items"] = stage_items

            # update description
            stages[next_stage_index] = stage

            Description().edit_description(self.description_token, dict(stages=stages))

            # build data dictionary depending on clone option
            clone_option = attributes.get("sample_clone", dict()).get("sample_clone", str())

            # this stage is dependent on sample clone; if this has changed, re-validate data...
            clone_option_old = meta.get(stage["ref"] + "_sample_clone", None)

            stage['data'] = attributes.get(stage["ref"], dict())

            if not clone_option == "no":
                if clone_option_old and not clone_option_old == clone_option:
                    # clone option changed, re-validate attributes:
                    clone_value = attributes.get(clone_option, dict())
                    stage['data'] = self.resolve_clone_data(clone_value, clone_option)
                else:
                    # clone option not changed, but has value changed
                    clone_value = attributes.get(clone_option, dict())
                    clone_value_old = attributes.get(clone_option + "_old", None)
                    if (clone_value_old and not clone_value_old == clone_value) or not attributes.get(stage["ref"],
                                                                                                      dict()):
                        # clone value changed or first time
                        clone_value = attributes.get(clone_option, dict())
                        stage['data'] = self.resolve_clone_data(clone_value, clone_option)

        # store dependency
        meta[stage["ref"] + "_sample_clone"] = clone_option
        Description().edit_description(self.description_token, dict(meta=meta))

        return stage

    def perform_sample_generation(self, next_stage_index):
        """
        stage callback function: to initiate display of requested number of samples and attributes
        :param next_stage_index:
        :return:
        """

        stage = dict()

        description = Description().GET(self.description_token)
        stages = description["stages"]

        if next_stage_index < len(stages):
            stage = stages[next_stage_index]

        return stage

    def generate_discrete_attributes(self):
        """
        function generate discrete attributes for individual sample editing
        :return:
        """

        # if there's stored object, use that rather than generating dataset from scratch
        stored_data_set = list()
        try:
            with pd.HDFStore(self.store_name) as store:
                if self.object_key in store:
                    stored_data_set = store[self.object_key].to_dict('records')
        except Exception as e:
            print('HDF5 Access Error: ' + str(e))

        description = Description().GET(self.description_token)
        stored_columns = description["meta"].get("generated_columns", list())

        if stored_columns and stored_data_set:
            return dict(columns=stored_columns, rows=stored_data_set)

        # object type controls and their corresponding schemas
        object_array_controls = ["copo-characteristics", "copo-comment"]
        object_array_schemas = [d_utils.get_copo_schema("material_attribute_value"),
                                d_utils.get_copo_schema("comment")]

        # data and columns lists
        dataSet = list()
        data = list()

        columns = [dict(title=' ', name='s_n', data="s_n", className='select-checkbox'),
                   dict(title='Name', name='name', data="name")]

        attributes = description["attributes"]

        # get stored sample attributes
        sample_attributes = attributes.get("sample_attributes", dict())

        # get sample schema
        schema_df = pd.DataFrame(self.schema)
        schema_df['id2'] = schema_df['id'].apply(lambda x: x.split(".")[-1])

        schema_df = schema_df[schema_df['id2'].isin(list(sample_attributes.keys()))]

        for index, row in schema_df.iterrows():
            resolved_data = htags.resolve_control_output(sample_attributes, row)
            label = row["label"]

            if row['control'] in object_array_controls:
                # get object-type-control schema
                control_index = object_array_controls.index(row['control'])
                control_df = pd.DataFrame(object_array_schemas[control_index])
                control_df['id2'] = control_df['id'].apply(lambda x: x.split(".")[-1])

                for indx_1, item in enumerate(resolved_data):
                    # item must contain at least 2 elements; also, discount objects with no header
                    # (e.g., category value for characteristics; name value for comments)
                    if len(item) > 1 and list(item[0].values())[0].strip():

                        # add primary header/value
                        shown_keys = (row["id"].split(".")[-1], str(indx_1), list(item[1].keys())[0].strip())
                        class_name = self.key_split.join(shown_keys)

                        columns.append(
                            dict(title=label + "[{0}]".format(list(item[0].values())[0].strip()), data=class_name))
                        dataSet.append(list(item[1].values())[0].strip())
                        data_attribute = dict()
                        data_attribute[class_name] = dataSet[-1]
                        data.append(data_attribute)

                        # add other headers/values e.g., Unit
                        for subitem in item[2:]:
                            if list(subitem.values())[0].strip():
                                # use object schema to resolve label
                                shown_keys = (row["id"].split(".")[-1], str(indx_1), list(subitem.keys())[0].strip())
                                class_name = self.key_split.join(shown_keys)
                                columns.append(dict(
                                    title=control_df[control_df.id2 == list(subitem.keys())[0].strip()].iloc[0].label,
                                    data=class_name))
                                dataSet.append(list(subitem.values())[0].strip())

                                data_attribute = dict()
                                data_attribute[class_name] = dataSet[-1]
                                data.append(data_attribute)



            else:
                shown_keys = row["id"].split(".")[-1]
                class_name = shown_keys
                columns.append(dict(title=label, data=class_name))
                val = resolved_data[0] if row['type'] == "array" else resolved_data
                if isinstance(val, list):
                    val = ', '.join(val)
                dataSet.append(val)

                data_attribute = dict()
                data_attribute[class_name] = dataSet[-1]
                data.append(data_attribute)

        # generate sample names
        user_choice = attributes.get("sample_naming_method", dict()).get("sample_naming_method", str())
        sample_names = attributes.get(user_choice, dict()).get(user_choice + "_hidden", str())
        sample_names = self.resolve_sample_names(user_choice, sample_names)

        name_series = pd.Series(sample_names.split(",") if "," in sample_names else sample_names.split())
        name_series = name_series[name_series.str.strip() != '']

        number_of_samples = attributes.get("number_of_samples", dict()).get("number_of_samples", 1)
        name_series = name_series.head(int(number_of_samples))

        # save control information
        auto_fields = dict()
        auto_fields[Sample().get_qualified_field("name")] = str()
        auto_fields[Sample().get_qualified_field("sample_type")] = attributes.get("sample_type", dict()).get(
            "sample_type", str())

        fields = DecoupleFormSubmission(auto_fields, Sample().get_schema().get("schema")).get_schema_fields_updated()

        for k, v in sample_attributes.items():
            fields[k] = v

        fields["target_id"] = str()
        fields["validate_only"] = True  # prevents saving of record

        record = Sample(profile_id=self.profile_id).save_record(dict(), **fields)

        # save initial attributes to db
        SampleCollection = get_collection_ref('SampleCollection')

        # remove previous entries associated with this token
        SampleCollection.delete_many(
            {"description_token": self.description_token, "deleted": d_utils.get_deleted_flag()})

        record['deleted'] = d_utils.get_deleted_flag()
        record['description_token'] = self.description_token

        # build db dataset
        samples_df = pd.DataFrame(name_series)
        samples_df.columns = ['name']

        new_samples_list = samples_df.to_dict('records')
        result = SampleCollection.insert_many(new_samples_list)
        object_ids = result.inserted_ids
        record.pop('name', None)

        SampleCollection.update_many(
            {"_id": {"$in": object_ids}},
            {'$set': record})

        # build display dataset
        samples_df["DT_RowId"] = object_ids
        samples_df.DT_RowId = 'row_' + samples_df.DT_RowId.astype(str)

        data_record = dict(pair for d in data for pair in d.items())
        for k, v in data_record.items():
            samples_df[k] = v

        samples_df.insert(loc=0, column='s_n', value=np.arange(1, int(number_of_samples) + 1))  # - for sorting

        data_set = samples_df.to_dict('records')

        # save generated dataset
        try:
            with pd.HDFStore(self.store_name) as store:
                store[self.object_key] = pd.DataFrame(data_set)
        except Exception as e:
            lg.log('HDF5 Access Error: ' + str(e), level=Loglvl.ERROR, type=Logtype.FILE)

        # save generated columns
        meta = description.get("meta", dict())
        meta["generated_columns"] = columns

        # save meta
        Description().edit_description(self.description_token, dict(meta=meta))

        return dict(columns=columns, rows=data_set)

    def resolve_sample_names(self, naming_method, proposed_name):
        """
        based on user choice (naming_method) sample names may have been supplied or left to be generated as bundle name
        :param naming_method:
        :param proposed_name:
        :return:
        """
        samples_names = proposed_name

        if naming_method == "bundle_name":
            description = Description().GET(self.description_token)
            samples_names = description["meta"].get("generated_names", str())

        return samples_names

    def revalidate_sample_name(self, naming_method):
        """
        function checks that supplied names are still valid - needed when a any stage change is encountered
        :param naming_method:
        :return:
        """

        description = Description().GET(self.description_token)
        attributes = description["attributes"]

        name_value = attributes.get(naming_method, dict()).get(naming_method, str())

        if naming_method == "bundle_name":
            return self.validate_bundle_name(name_value)
        elif naming_method == "provided_names":
            return self.validate_sample_names(name_value)["status"]

        return

    def resolve_clone_data(self, clone_value, clone_option):
        """
        function resolves stage data based on clone option
        :param clone_value:
        :param clone_option:
        :return:
        """

        data = dict()

        if clone_option == "clone_existing":
            data = Sample().get_record(clone_value["clone_existing"])
            del data["_id"]
        elif clone_option == "clone_biosample":
            data = json.loads(clone_value["clone_resolved_hidden"])

        return data

    def resolve_sample_object(self, resolved_object):
        """
        function normalises a resolved sample object to extract relevant sample attributes
        :param resolved_object: sample object to be normalised
        :return: the normalised object, which should conform to the sample schema
        """

        sample_object = dict(organism=dict(), characteristics=list(), comments=list())

        ch = resolved_object.get("characteristics", dict())

        for key in list(ch.keys()):
            key_refined = re.findall('[a-zA-Z][^A-Z]*', key)
            key_refined = [i.lower() for i in key_refined]
            key_refined = ' '.join([str(i.lower()) for i in key_refined])
            key_refined = key_refined.strip()

            # each attribute can be divided into either of two buckets:
            # characteristics; if it is ontologised, comment; if free text.

            if isinstance(ch[key], list):  # attribute values are observed to be wrapped up as lists
                for value in ch[key]:
                    if isinstance(value, dict):
                        if all(x in list(value.keys()) for x in ['ontologyTerms', 'text']):
                            if isinstance(value['text'], str):
                                material_value_dict = dict()

                                # category
                                category_dict = dict(annotationValue=key_refined)

                                # purify category schema
                                ontology_schema = d_utils.get_db_json_schema("ontology_annotation")
                                for onto in ontology_schema:
                                    ontology_schema = ISAHelpers().resolve_schema_key(ontology_schema, onto,
                                                                                      "ontology_annotation",
                                                                                      category_dict)

                                material_value_dict['category'] = ontology_schema

                                # value
                                value_dict = dict(annotationValue=value['text'])

                                ontology_term = value['ontologyTerms'][0]  # interested only in the first entry,
                                # ...we do recognise that there might be more than one entries here,
                                # but selecting one should suffice

                                value_dict['termAccession'] = ontology_term
                                term_source = ''
                                c_split = (ontology_term.split("/"))[-1]
                                if c_split != ontology_term and c_split.split("_")[0] != c_split:
                                    term_source = c_split.split("_")[0]
                                value_dict['termSource'] = term_source

                                # purify value schema
                                ontology_schema = d_utils.get_db_json_schema("ontology_annotation")
                                for onto in ontology_schema:
                                    ontology_schema = ISAHelpers().resolve_schema_key(ontology_schema, onto,
                                                                                      "ontology_annotation",
                                                                                      value_dict)

                                material_value_dict['value'] = ontology_schema

                                # unit - not really expecting any values or not yet determined how to extract if any
                                unit_dict = dict(annotationValue=str(), termAccession=str(), termSource=str())

                                # purify unit schema
                                ontology_schema = d_utils.get_db_json_schema("ontology_annotation")
                                for onto in ontology_schema:
                                    ontology_schema = ISAHelpers().resolve_schema_key(ontology_schema, onto,
                                                                                      "ontology_annotation",
                                                                                      unit_dict)

                                material_value_dict['unit'] = ontology_schema

                                material_attribute_schema = d_utils.get_db_json_schema("material_attribute_value")
                                for onto in material_attribute_schema:
                                    material_attribute_schema = ISAHelpers().resolve_schema_key(
                                        material_attribute_schema, onto,
                                        "material_attribute_value",
                                        material_value_dict)

                                if key_refined == 'organism':  # organism entered differently
                                    sample_object[key_refined] = material_value_dict['value']
                                else:
                                    sample_object['characteristics'].append(material_attribute_schema)
                        elif all(x in list(value.keys()) for x in ['text']):
                            if isinstance(value['text'], str):
                                comment_schema = d_utils.get_db_json_schema("comment")
                                for k in comment_schema:
                                    comment_schema = ISAHelpers().resolve_schema_key(comment_schema, k,
                                                                                     "comment",
                                                                                     dict(name=key_refined,
                                                                                          value=value['text']))

                                sample_object['comments'].append(comment_schema)

        return sample_object

    def do_validation(self, validation_parameters):
        """
        validates supplied entry
        :param validation_parameters: dict(schema=dict(), data=str())
        :return:
        """
        validation_result = dict(status="success", message="")

        schema = validation_parameters.get("schema", dict())
        data = validation_parameters.get("data", str())

        # validate required attributes
        if "required" in schema and str(schema["required"]).lower() == "true":
            if isinstance(data, str) and data.strip() == str():
                validation_result["status"] = "error"
                validation_result["message"] = "This is a required field!"

                return validation_result

                # should probably add validation for object types here, that might need some thinking with nested dicts

        # validate unique attributes
        if "unique" in schema and str(schema["unique"]).lower() == "true":
            if isinstance(data, str) and Sample().get_collection_handle().find(
                    {schema["id"].split(".")[-1]: {'$regex': "^" + data + "$",
                                                   "$options": 'i'}}).count() >= 1:
                validation_result["status"] = "error"
                validation_result["message"] = "Nothing to update or value already exists!"

                return validation_result

                # should probably add validation for object types here, that might need some thinking though

        # validate characteristics attributes
        if schema.get("control", str()) == "copo-characteristics":
            if set(['value', 'unit']) < set(data.keys()):
                value = data['value']['annotationValue'].strip()
                unit = data['unit']['annotationValue'].strip()

                is_numeric = False
                try:
                    float(value)
                    is_numeric = True
                except ValueError:
                    pass

                if is_numeric and not unit:
                    validation_result["status"] = "error"
                    validation_result["message"] = "Numeric value requires a unit!"

                    # commenting out the 'elif' condition below prevents an update lock up;
                    # a case where you can't update the value because of the unit, and vice versa

                    return validation_result

        return validation_result

    def resolver_uri(self, uri):
        """
        function resolves given uri to some remote service to retrieve data
        :param resolver_uri:
        :return:
        """
        result = dict(status="error")

        try:
            response = urllib2.urlopen(uri).read()
            my_json = response.decode('utf8').replace("\n", '')

            result["status"] = "success"
            result["value"] = self.resolve_sample_object(json.loads(my_json))
        except:
            pass

        return result

    def validate_sample_names(self, sample_names):
        """
        function validates sample names - sample names are expected as comma or tab separated string
        :param sample_names:
        :return:
        """
        result = dict(status="success")
        errors = list()

        description = Description().GET(self.description_token)

        name_series = pd.Series(sample_names.split(",") if "," in sample_names else sample_names.split())
        name_series = name_series[name_series.str.strip() != '']

        # check for uniqueness of supplied names with existing sample names
        records_df = pd.DataFrame(
            Sample(profile_id=self.profile_id).get_all_records_columns(projection={'name': 1, '_id': 0}))

        if len(records_df):
            existing_name = list(name_series[name_series.isin(records_df.name)].unique())

            if len(existing_name):
                errors.append(["Existing names", "Supplied name(s) already exist", ', '.join(existing_name)])

        # check for duplicates in supplied names
        repeated_names = name_series.value_counts()[name_series.value_counts() > 1]
        if len(repeated_names):
            errors.append([
                "Repeating names",
                "Supplied name(s) are repeated",
                repeated_names.to_string().replace("\n", '<br/>')
            ])

        # do we have matching number of supplied names to number of samples to be described?

        number_of_samples = description["attributes"].get("number_of_samples", dict()).get("number_of_samples", 0)
        if len(name_series) < int(number_of_samples):
            errors.append([
                "Insufficient names",
                "Supplied names are less than the requested number of samples",
                "Supplied names: {0}<br/>Requested number of samples: {1}".format(str(len(name_series)),
                                                                                  number_of_samples)
            ])

        # set error status
        if len(errors):
            result['status'] = "error"
            result['errors'] = errors
            result["error_columns"] = [{"title": "Error code"}, {"title": "Error message"}, {"title": "Error details"}]

        else:
            # store dependency
            meta = description.get("meta", dict())
            meta["provided_names_number_of_samples"] = number_of_samples
            # save meta
            Description().edit_description(self.description_token, dict(meta=meta))

        return result

    def validate_bundle_name(self, bundle_name):
        """
        function validates the suitability of bundle_name for generating unique sample names
        :param bundle_name:
        :return:
        """

        # get number of samples to inform name generation
        description = Description().GET(self.description_token)
        number_of_samples = description["attributes"].get("number_of_samples", dict()).get("number_of_samples", 0)

        # initial attempt at generating names
        bn_df = pd.DataFrame(pd.Series([bundle_name] * int(number_of_samples)), columns=['bundle_name'])
        bn_df['generated_name'] = bn_df.apply(lambda row: row['bundle_name'] + "_" + str(row.name + 1), axis=1)

        generated_names = ','.join(list(bn_df['generated_name']))

        validate = self.validate_sample_names(generated_names)

        # get meta
        meta = description.get("meta", dict())

        meta["generated_names"] = str()

        if validate["status"] == "success":
            meta["generated_names"] = generated_names

            # store dependency
            meta["bundle_name_number_of_samples"] = number_of_samples

        # save meta
        Description().edit_description(self.description_token, dict(meta=meta))

        return dict(status=validate["status"])

    def get_cell_control(self, cell_reference, record_id):
        """
        function builds control for a UI data cell
        :param cell_reference:
        :param row_data:
        :return:
        """

        # object type controls and their corresponding schemas
        object_array_controls = ["copo-characteristics", "copo-comment"]
        object_array_schemas = [d_utils.get_copo_schema("material_attribute_value"),
                                d_utils.get_copo_schema("comment")]

        control_schema = dict()

        key = cell_reference.split(self.key_split)

        if len(key) > 1:  # object type key
            parent_schema = [f for f in self.schema if f["id"].split(".")[-1] == key[0]]
            if parent_schema:
                parent_schema = parent_schema[0]
                if parent_schema['control'] in object_array_controls:
                    control_index = object_array_controls.index(parent_schema['control'])
                    control_schema = [f for f in object_array_schemas[control_index] if
                                      f["id"].split(".")[-1] == key[2]]

        else:  # string type
            control_schema = [f for f in self.schema if f["id"].split(".")[-1] == key[0]]

        if control_schema:
            control_schema = control_schema[0]

        if "option_values" in control_schema:
            control_schema["option_values"] = htags.get_control_options(control_schema)

        # get target record
        record = Sample().get_record(record_id)

        if len(key) == 1:
            schema_data = record[key[0]]
        else:
            schema_data = record[key[0]]
            schema_data = schema_data[int(key[1])]
            schema_data = schema_data[key[2]]

        return dict(control_schema=control_schema, schema_data=schema_data)

    def save_cell_data(self, cell_reference, record_id, auto_fields):
        """
        function save updated cell data; for the target_cell and target_rows
        :param cell_reference:
        :param auto_fields:
        :param target_rows:
        :return:
        """
        result = dict(status='success', value='')

        # object type controls and their corresponding schemas
        object_array_controls = ["copo-characteristics", "copo-comment"]
        object_array_schemas = [d_utils.get_copo_schema("material_attribute_value"),
                                d_utils.get_copo_schema("comment")]

        # get cell schema
        control_schema = dict()

        key = cell_reference.split(self.key_split)

        # gather parameters for validation
        validation_parameters = dict(schema=dict(), data=str())

        if len(key) > 1:  # object type key
            parent_schema = [f for f in self.schema if f["id"].split(".")[-1] == key[0]]
            if parent_schema:
                parent_schema = parent_schema[0]
                validation_parameters["schema"] = parent_schema
                if parent_schema['control'] in object_array_controls:
                    control_index = object_array_controls.index(parent_schema['control'])
                    control_schema = [f for f in object_array_schemas[control_index] if
                                      f["id"].split(".")[-1] == key[2]]

        else:
            control_schema = [f for f in self.schema if f["id"].split(".")[-1] == key[0]]
            validation_parameters["schema"] = control_schema[0] if control_schema else {}

        control_schema = control_schema[0] if control_schema else {}
        partial_schema = dict(fields=[control_schema])

        # resolve the new entry given partial_schema
        resolved_data = DecoupleFormSubmission(auto_fields, d_utils.json_to_object(
            partial_schema).fields).get_schema_fields_updated()

        # get target record
        record = Sample().get_record(record_id)

        if len(key) == 1:
            record[key[0]] = resolved_data[key[0]]
            validation_parameters["data"] = record[key[0]]
            result["value"] = htags.get_resolver(resolved_data[key[0]], control_schema)
        else:
            record[key[0]][int(key[1])][key[2]] = resolved_data[key[2]]
            validation_parameters["data"] = record[key[0]][int(key[1])]
            result["value"] = htags.get_resolver(resolved_data[key[2]], control_schema)

        # kick in some validation here before proceeding to save!
        validate_status = self.do_validation(validation_parameters)

        result["status"] = validate_status["status"]
        result["message"] = validate_status["message"]

        # return if error
        if result["status"] == "error":
            return result

        SampleCollection = get_collection_ref('SampleCollection')

        _id = record.pop('_id', None)

        if _id:
            SampleCollection.update(
                {"_id": ObjectId(_id)},
                {'$set': record})

        # refresh stored dataset with new display value
        try:
            with pd.HDFStore(self.store_name) as store:
                gd_df = store[self.object_key]
                gd_df.loc[gd_df.loc[gd_df['DT_RowId'].isin(["row_" + record_id])].index, cell_reference] = result[
                    "value"]
                store[self.object_key] = gd_df
        except Exception as e:
            lg.log('HDF5 Access Error: ' + str(e), level=Loglvl.ERROR, type=Logtype.FILE)

        return result

    def batch_update_cells(self, cell_reference, record_id, target_rows):
        """
        function uses a reference cell to update a batch of records
        :param cell_reference:
        :param record_id:
        :param target_rows:
        :return:
        """

        # to improve performance UI-side, use the refresh_threshold to decide if to send back the entire dataset
        refresh_threshold = 1000

        result = dict(status='success', value='')

        SampleCollection = get_collection_ref('SampleCollection')

        # object type controls and their corresponding schemas
        object_array_controls = ["copo-characteristics", "copo-comment"]
        object_array_schemas = [d_utils.get_copo_schema("material_attribute_value"),
                                d_utils.get_copo_schema("comment")]

        # get cell schema
        control_schema = dict()

        key = cell_reference.split(self.key_split)

        # gather parameters for validation
        validation_parameters = dict(schema=dict(), data=str())

        if len(key) > 1:  # object type key
            parent_schema = [f for f in self.schema if f["id"].split(".")[-1] == key[0]]
            if parent_schema:
                parent_schema = parent_schema[0]
                validation_parameters["schema"] = parent_schema
                if parent_schema['control'] in object_array_controls:
                    control_index = object_array_controls.index(parent_schema['control'])
                    control_schema = [f for f in object_array_schemas[control_index] if
                                      f["id"].split(".")[-1] == key[2]]

        else:
            control_schema = [f for f in self.schema if f["id"].split(".")[-1] == key[0]]
            validation_parameters["schema"] = control_schema[0] if control_schema else {}

        control_schema = control_schema[0] if control_schema else {}

        # get target record
        record = Sample().get_record(record_id)

        if len(key) == 1:
            resolved_data = record[key[0]]
            validation_parameters["data"] = resolved_data
            result["value"] = htags.get_resolver(resolved_data, control_schema)
        else:
            resolved_data = record[key[0]][int(key[1])][key[2]]
            validation_parameters["data"] = record[key[0]][int(key[1])]
            result["value"] = htags.get_resolver(resolved_data, control_schema)

        if isinstance(result["value"], list):  # ...this to get lists to render properly
            result["value"] = " ".join(result["value"])

        # kick in some validation here before proceeding to save!
        validate_status = self.do_validation(validation_parameters)

        result["status"] = validate_status["status"]
        result["message"] = validate_status["message"]

        # terminate if error
        if result["status"] == "error":
            return result

        # update db records
        object_ids = [ObjectId(x.split("row_")[-1]) for x in target_rows]

        if len(key) == 1:
            SampleCollection.update_many(
                {"_id": {"$in": object_ids}},
                {'$set': {key[0]: resolved_data}})
        else:
            SampleCollection.update_many(
                {"_id": {"$in": object_ids}},
                {'$set': {key[0] + "." + key[1] + "." + key[2]: resolved_data}})

        # refresh stored dataset with new display value
        try:
            with pd.HDFStore(self.store_name) as store:
                gd_df = store[self.object_key]
                gd_df.loc[gd_df.loc[gd_df['DT_RowId'].isin(target_rows)].index, cell_reference] = result["value"]
                store[self.object_key] = gd_df

                if len(target_rows) > refresh_threshold:
                    result["data_set"] = gd_df.to_dict('records')
        except Exception as e:
            lg.log('HDF5 Access Error: ' + str(e), level=Loglvl.ERROR, type=Logtype.FILE)

        return result

    def finalise_description(self):
        """
        function makes described sample accessible in the main stream of sample records
        :return:
        """
        result = dict(status='success', value='')

        SampleCollection = get_collection_ref('SampleCollection')
        fields = dict()

        fields['deleted'] = d_utils.get_not_deleted_flag()

        SampleCollection.update_many(
            {"description_token": self.description_token},
            {'$set': fields})

        Description().delete_description([self.description_token])

        return result

    def discard_description(self):
        """
        function discards the current description
        :return:
        """

        result = dict(status='success')

        SampleCollection = get_collection_ref('SampleCollection')

        # delete store object
        Description().remove_store_object(store_name=self.store_name, object_key=self.object_key)

        # remove entries associated with this token
        SampleCollection.delete_many(
            {"description_token": self.description_token, "deleted": d_utils.get_deleted_flag()})

        Description().delete_description([self.description_token])

        return result

    def get_pending_description(self):
        """
        function returns any pending description record
        :param profile_id:
        :return:
        """

        # first, remove obsolete description records
        Description().purge_descriptions()

        projection = dict(created_on=1, attributes=1)
        filter_by = dict(profile_id=self.profile_id)
        records = Description().get_all_records_columns(sort_by='created_on', projection=projection,
                                                        filter_by=filter_by)

        # step toward computing grace period before automatic removal of description
        description_df = Description().get_elapsed_time_dataframe()
        no_of_days = settings.DESCRIPTION_GRACE_PERIOD

        refined_records = list()

        for r in records:
            ll = description_df[description_df._id == r['_id']]
            val = dict(
                created_on=htags.resolve_datetime_data(r['created_on'], dict()),
                _id=str(r['_id']),
                number_of_samples=r['attributes'].get("number_of_samples", dict()).get("number_of_samples", 'N/A'),
                grace_period=str(int(float(no_of_days) - float(ll.diff_days))) + ' days'
            )

            refined_records.append(val)

        return refined_records
