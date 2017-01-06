__author__ = 'etuka'
__date__ = '13 May 2016'

import ast
from bson import ObjectId
from django.contrib.auth.models import User

import web.apps.web_copo.lookup.lookup as lkup
from api.doi_metadata import DOI2Metadata
import web.apps.web_copo.templatetags.html_tags as htags
from dal.copo_da import Profile, Publication, Source, Person, Sample, Submission, DataFile, DAComponent, Annotation
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.schemas.utils.metadata_rater import MetadataRater


class BrokerDA:
    def __init__(self, **kwargs):
        self.param_dict = kwargs
        self.context = self.param_dict.get("context", dict())
        self.component = self.param_dict.get("component", str())
        self.visualize = self.param_dict.get("visualize", str())
        self.profile_id = self.param_dict.get("profile_id", str())
        self.auto_fields = self.param_dict.get("auto_fields", dict())

        if self.auto_fields and isinstance(self.auto_fields, str):
            self.auto_fields = ast.literal_eval(self.auto_fields)

        self.broker_visuals = BrokerVisuals(**kwargs)
        self.da_object = DAComponent(self.profile_id, self.component)

        da_dict = dict(
            publication=Publication,
            person=Person,
            sample=Sample,
            source=Source,
            profile=Profile,
            datafile=DataFile,
            submission=Submission,
            annotation=Annotation
        )

        if da_dict.get(self.component):
            self.da_object = da_dict[self.component](self.profile_id)

    def set_extra_params(self, extra_param):
        for k, v in extra_param.items():
            self.param_dict[k] = v

    def do_copo_schemas(self):
        copo_schemas = dict(
            ontology_schema=d_utils.get_copo_schema("ontology_annotation"),
            comment_schema=d_utils.get_copo_schema("comment"),
            characteristics_schema=d_utils.get_copo_schema("material_attribute_value"),
            source_schema=d_utils.get_copo_schema("source")
        )

        self.context["copo_schemas"] = copo_schemas
        return self.context

    def do_save_edit(self):
        kwargs = dict()
        kwargs["target_id"] = self.param_dict.get("target_id", str())

        record_object = self.da_object.save_record(self.auto_fields, **kwargs)

        # process visualisation context
        self.broker_visuals.set_extra_params(dict(record_object=record_object))

        visualize_dict = dict(profiles_counts=self.broker_visuals.do_profiles_counts,
                              sources_json=self.broker_visuals.get_sources_json,
                              sources_json_and_last_record_id=self.broker_visuals.get_sources_json_last_record_id,
                              last_record=self.broker_visuals.get_last_record,
                              get_profile_count=self.broker_visuals.get_profile_count
                              )

        if self.visualize in visualize_dict:
            self.context = visualize_dict[self.visualize]()
        elif self.param_dict.get("target_id", str()):
            self.context = self.broker_visuals.do_table_data()
        else:
            self.context = self.broker_visuals.do_row_data()

        return self.context

    def do_delete(self):
        target_ids = [ObjectId(i) for i in self.param_dict.get("target_ids")]

        self.da_object.get_collection_handle().update_many(
            {"_id": {"$in": target_ids}}, {"$set": {"deleted": d_utils.get_deleted_flag()}}
        )

        self.context = self.broker_visuals.do_table_data()
        return self.context

    def do_form(self):
        target_id = self.param_dict.get("target_id")
        component_dict = self.param_dict.get("component_dict", dict())
        message_dict = self.param_dict.get("message_dict", dict())

        self.context["form"] = htags.generate_copo_form(self.component, target_id, component_dict, message_dict,
                                                        self.profile_id)
        self.context["form"]["visualize"] = self.param_dict.get("visualize")
        return self.context

    def do_doi(self):
        id_handle = self.param_dict.get("id_handle")
        id_type = self.param_dict.get("id_type")

        doi_resolve = DOI2Metadata(id_handle, id_type).get_resolve(self.component)

        self.set_extra_params(dict(target_id=str(),
                                   component_dict=doi_resolve.get("component_dict", dict()),
                                   message_dict=doi_resolve.get("message_dict", dict()))
                              )

        return self.do_form()

    def do_initiate_submission(self):
        kwarg = dict(datafile_ids=self.param_dict.get("datafile_ids", list()))
        self.context["submission_token"] = str(self.da_object.save_record(dict(), **kwarg).get("_id", str()))
        return self.context

    def do_user_email(self):
        user_id = self.param_dict.get("user_id", str())
        user_email = self.param_dict.get("user_email", str())
        user = User.objects.get(pk=int(user_id))
        user.email = user_email
        user.save()

        return self.context


class BrokerVisuals:
    def __init__(self, **kwargs):
        self.param_dict = kwargs
        self.component = self.param_dict.get("component", str())
        self.profile_id = self.param_dict.get("profile_id", str())
        self.context = self.param_dict.get("context", dict())

    def set_extra_params(self, extra_param):
        for k, v in extra_param.items():
            self.param_dict[k] = v

    def do_table_data(self):
        table_data_dict = dict(
            annotation=(htags.generate_copo_table_data, dict(profile_id=self.profile_id, component=self.component)),
            publication=(htags.generate_copo_table_data, dict(profile_id=self.profile_id, component=self.component)),
            person=(htags.generate_copo_table_data, dict(profile_id=self.profile_id, component=self.component)),
            datafile=(htags.generate_copo_table_data, dict(profile_id=self.profile_id, component=self.component)),
            sample=(htags.generate_copo_table_data, dict(profile_id=self.profile_id, component=self.component)),
            profile=(htags.generate_copo_profiles_data, dict(profiles=Profile().get_for_user())),
        )

        # NB: in table_data_dict, use an empty dictionary as a parameter for listed functions that define zero arguments

        if self.component in table_data_dict:
            kwargs = table_data_dict[self.component][1]
            self.context["table_data"] = table_data_dict[self.component][0](**kwargs)

        self.context["component"] = self.component
        return self.context

    def do_row_data(self):
        record_object = self.param_dict.get("record_object", dict())

        table_data_dict = dict(
            publication=(htags.get_record_data, dict(record_object=record_object, component=self.component)),
            person=(htags.get_record_data, dict(record_object=record_object, component=self.component)),
            sample=(htags.get_record_data, dict(record_object=record_object, component=self.component)),
            profile=(htags.generate_copo_profiles_data, dict(profiles=Profile().get_for_user())),
            datafile=(htags.get_record_data, dict(record_object=record_object, component=self.component))
        )

        # NB: in table_data_dict, use an empty dictionary as a parameter to functions that define zero arguments

        if self.component in table_data_dict:
            kwargs = table_data_dict[self.component][1]
            self.context["table_data"] = table_data_dict[self.component][0](**kwargs)

        self.context["component"] = self.component
        return self.context

    def do_profiles_counts(self):
        self.context["profiles_counts"] = htags.generate_copo_profiles_counts(Profile().get_for_user())
        return self.context

    def get_profile_count(self):
        self.context["profile_count"] = True
        return self.context

    def get_sources_json(self):
        self.context["option_values"] = d_utils.generate_sources_json()
        return self.context

    def get_sources_json_last_record_id(self):
        record_object = self.param_dict.get("record_object", dict())

        self.context = self.get_sources_json()
        self.context["last_record_id"] = str(record_object.get("_id", str()))
        return self.context

    def get_sources_json_component(self):
        self.context["option_values"] = d_utils.generate_sources_json()
        self.context["component_records"] = htags.generate_component_records(self.component, self.profile_id)

        return self.context

    def get_last_record(self):
        self.context["record_object"] = self.param_dict.get("record_object", dict())
        return self.context

    def do_wizard_messages(self):
        self.context['wiz_message'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["datafile_wizard"])["properties"]
        self.context['wiz_howtos'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["datafile_wizard_howto"])
        return self.context

    def do_metadata_ratings(self):
        self.context['metadata_ratings'] = MetadataRater(self.param_dict.get("datafile_ids")).get_datafiles_rating()
        return self.context

    def do_description_summary(self):
        self.context['description'] = htags.resolve_description_data(
            DataFile().get_record(self.param_dict.get("target_id")).get("description", dict()), dict())
        return self.context

    def do_un_describe(self):
        datafile_ids = [ObjectId(i) for i in self.param_dict.get("datafile_ids")]

        DataFile().get_collection_handle().update_many(
            {"_id": {"$in": datafile_ids}}, {"$set": {"description": dict()}}
        )

        return self.context

    def do_attributes_display(self):
        target_id = self.param_dict.get("target_id", str())
        self.context['sample_attributes'] = htags.generate_attributes(self.component, target_id)

        return self.context
