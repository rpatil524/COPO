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
from web.apps.web_copo.schemas.utils import data_utils


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

    def do_form_control_schemas(self):
        """
        function returns object type control schemas used in building form controls
        :return:
        """

        copo_schemas = dict()
        for k, v in d_utils.object_type_control_map().items():
            copo_schemas[k] = d_utils.get_copo_schema(v)

        self.context["copo_schemas"] = copo_schemas
        return self.context

    def do_save_edit(self):
        kwargs = dict()
        kwargs["target_id"] = self.param_dict.get("target_id", str())

        # set report parameter
        status = "success"  # 'success', 'warning', 'info', 'danger' - modelled after bootstrap alert classes
        action_type = "add"

        report_metadata = dict()

        if self.param_dict.get("target_id", str()):
            action_type = "edit"

        record_object = self.da_object.save_record(self.auto_fields, **kwargs)

        if not record_object:
            status = "danger"

        if action_type == "add":
            report_metadata["message"] = "New " + self.component + " record created!"
            if status != "success":
                report_metadata["message"] = "There was a problem creating the " + self.component + " record!"
        elif action_type == "edit":
            report_metadata["message"] = "Record updated!"
            if status != "success":
                report_metadata["message"] = "There was a problem updating the " + self.component + " record!"

        report_metadata["status"] = status
        self.context["action_feedback"] = report_metadata

        # process visualisation context,

        # set extra parameters which will be passed along to the visualize object
        self.broker_visuals.set_extra_params(dict(record_object=record_object))

        # build dictionary of executable tasks/functions
        visualize_dict = dict(profiles_counts=self.broker_visuals.do_profiles_counts,
                              created_component_json=self.broker_visuals.get_created_component_json,
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

        # if ever it was needed to re-implement 'soft' delete uncomment the following lines and
        # comment out the 'hard' delete query

        self.da_object.get_collection_handle().update_many(
            {"_id": {"$in": target_ids}}, {"$set": {"deleted": d_utils.get_deleted_flag()}}
        )

        # hard delete
        # self.da_object.get_collection_handle().remove({'_id': {'$in': target_ids}})

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

    def do_form_and_component_records(self):
        # generates form, and in addition returns records of the form component, this could, for instance, be
        # used for cloning of a record

        self.context = self.do_form()
        self.context["component_records"] = htags.generate_component_records(self.component, self.profile_id)

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

    def do_component_record(self):
        self.context["component_record"] = self.da_object.get_record(self.param_dict.get("target_id"))

        return self.context

    def do_sanitise_submissions(self):
        records = self.da_object.get_all_records()

        for submission in records:
            if "bundle_meta" not in submission:
                bundle_meta = list()

                for file_id in submission.get("bundle", list()):
                    datafile = DataFile().get_record(file_id)
                    if datafile:
                        upload_status = False

                        if str(submission.get("complete", False)).lower() == 'true':
                            upload_status = True
                        bundle_meta.append(
                            dict(
                                file_id=file_id,
                                file_path=datafile.get("file_location", str()),
                                upload_status=upload_status
                            )
                        )
                submission["bundle_meta"] = bundle_meta
                submission['target_id'] = str(submission.pop('_id'))
                self.da_object.save_record(dict(), **submission)

        self.context["sanitise_status"] = True

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
            publication=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            person=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            datafile=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            sample=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            submission=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
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
            publication=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            person=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            sample=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
            profile=(htags.generate_copo_profiles_data, dict(profiles=Profile().get_for_user())),
            datafile=(htags.generate_table_records, dict(profile_id=self.profile_id, component=self.component)),
        )

        # NB: in table_data_dict, use an empty dictionary as a parameter to functions that define zero arguments

        if self.component in table_data_dict:
            kwargs = table_data_dict[self.component][1]
            self.context["table_data"] = table_data_dict[self.component][0](**kwargs)

        self.context["component"] = self.component
        return self.context

    def do_get_submission_accessions(self):
        target_id = self.param_dict.get("target_id", str())
        submission_record = Submission().get_record(target_id)

        self.context["submission_accessions"] = htags.generate_submission_accessions_data(submission_record)
        return self.context

    def do_profiles_counts(self):
        self.context["profiles_counts"] = htags.generate_copo_profiles_counts(Profile().get_for_user())
        return self.context

    def get_profile_count(self):
        self.context["profile_count"] = True
        return self.context

    def get_created_component_json(self):
        record_object = self.param_dict.get("record_object", dict())

        target_id = str(record_object.get("_id", str()))
        option_values = dict()

        if self.component == "source":
            option_values = d_utils.generate_sources_json(target_id)
        elif self.component == "sample":
            option_values = d_utils.get_samples_json(target_id)

        self.context["option_values"] = option_values
        self.context["created_record_id"] = str(record_object.get("_id", str()))
        return self.context

    def get_last_record(self):
        self.context["record_object"] = self.param_dict.get("record_object", dict())
        return self.context

    def do_wizard_messages(self):
        self.context['wiz_message'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS["datafile_wizard"])["properties"]
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
        if self.component == "datafile":  # datafile attributes are rendered differently
            return self.do_description_summary()

        target_id = self.param_dict.get("target_id", str())
        self.context['component_attributes'] = htags.generate_attributes(self.component, target_id)
        self.context['component_label'] = htags.get_labels().get(self.component, dict()).get("label", str())

        return self.context

    def get_component_help_messages(self):
        self.context['context_help'] = dict()
        self.context['help_messages'] = dict()

        paths_dict = lkup.MESSAGES_LKUPS['HELP_MESSAGES']

        if self.component in paths_dict:
            self.context['help_messages'] = d_utils.json_to_pytype(lkup.MESSAGES_LKUPS['HELP_MESSAGES'][self.component])

        # context help, relevant to the current component (e.g., datafile)
        if "context_help" in paths_dict:
            help_dict = d_utils.json_to_pytype(
                lkup.MESSAGES_LKUPS['HELP_MESSAGES']["context_help"])
            properties_temp = help_dict['properties']
            v = [x for x in properties_temp if len(x['context']) > 0 and x['context'][0] == self.component]
            if v:
                help_dict['properties'] = v
            self.context['context_help'] = help_dict

        # get user email
        self.context = self.do_user_has_email()

        return self.context

    def do_user_has_email(self):
        req = data_utils.get_current_request()
        user = User.objects.get(pk=int(req.user.id))

        self.context['user_has_email'] = bool(user.email.strip())

        return self.context

    def do_update_quick_tour_flag(self):
        req = data_utils.get_current_request()
        quick_tour_flag = self.param_dict.get("quick_tour_flag", "false")

        if quick_tour_flag == "false":
            quick_tour_flag = False
        else:
            quick_tour_flag = True

        req.session["quick_tour_flag"] = quick_tour_flag
        self.context["quick_tour_flag"] = req.session["quick_tour_flag"]

        return self.context

    def do_get_component_info(self):
        target_id = self.param_dict.get("target_id", str())
        da_object = DAComponent(target_id, self.component)
        print(target_id)

        print(self.component)
        self.context["component_info"] = "welcome to " + str(da_object.get_component_count())

        return self.context

    def do_get_profile_info(self):
        self.context["component_info"] = "welcome to " + self.component

        return self.context
