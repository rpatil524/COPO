__author__ = 'felix.shaw@tgac.ac.uk - 22/10/15'

from datetime import datetime
from django_tools.middlewares import ThreadLocal
from bson import ObjectId
from web.apps.chunked_upload.models import ChunkedUpload
from web.apps.web_copo.lookup.lookup import DB_TEMPLATES
import web.apps.web_copo.utils.EnaUtils as u
from dal import cursor_to_list
from dal.copo_base_da import DataSchemas
from dal.mongo_util import get_collection_ref
from web.apps.web_copo.schemas.utils import data_utils
from web.apps.web_copo.schemas.utils.data_utils import DecoupleFormSubmission

PubCollection = 'PublicationCollection'
PersonCollection = 'PersonCollection'
DataCollection = 'DataCollection'
SampleCollection = 'SampleCollection'
SubmissionCollection = 'SubmissionCollection'
SourceCollection = 'SourceCollection'
DataFileCollection = 'DataFileCollection'
RemoteFileCollection = 'RemoteFileCollection'
DescriptionCollection = 'DescriptionCollection'
ProfileCollection = 'Profiles'

handle_dict = dict(publication=get_collection_ref(PubCollection),
                   person=get_collection_ref(PersonCollection),
                   sample=get_collection_ref(SampleCollection),
                   source=get_collection_ref(SourceCollection),
                   profile=get_collection_ref(ProfileCollection),
                   submission=get_collection_ref(SubmissionCollection),
                   datafile=get_collection_ref(DataFileCollection)
                   )


class ProfileInfo:
    def __init__(self, profile_id=None):
        self.profile_id = profile_id

    def get_counts(self):
        """
        Method to return current numbers of Publication, Person, Data,
        Sample and Submission objects in the given profile
        :return: Dictionary containing the data
        """

        num_dict = dict(num_pub="publication",
                        num_person="person",
                        num_data="datafile",
                        num_sample="sample",
                        num_submission="submission",
                        )

        status = dict()

        for k, v in num_dict.items():
            if handle_dict.get(v, None):
                status[k] = handle_dict.get(v).count(
                    {'profile_id': self.profile_id, 'deleted': data_utils.get_not_deleted_flag()})

        return status

    def source_count(self):
        return handle_dict.get("source").count(
            {'profile_id': self.profile_id, 'deleted': data_utils.get_not_deleted_flag()})


class DAComponent:
    def __init__(self, profile_id=None, component=str()):
        self.profile_id = profile_id
        self.component = component

    def get_record(self, oid):
        doc = None
        if self.get_collection_handle():
            doc = self.get_collection_handle().find_one({"_id": ObjectId(oid)})
        if not doc:
            pass
        return doc

    def get_collection_handle(self):
        return handle_dict.get(self.component, None)

    def get_id_base(self):
        base_dict = dict(
            publication="copo.publication",
            person="copo.person",
            datafile="copo.datafile",
            sample="copo.sample",
            source="copo.source",
            profile="copo.profile",
            submission="copo.submission",
            investigation="i_",
            study="s_",
            assay="a_",
        )

        return base_dict.get(self.component, str())

    def get_qualified_field(self, elem=str()):
        return self.get_id_base() + "." + elem

    def get_schema(self):
        schema_base = DataSchemas("COPO").get_ui_template().get("copo")
        x = data_utils.json_to_object(schema_base.get(self.component, dict()))

        return dict(schema_dict=schema_base.get(self.component, dict()).get("fields", list()),
                    schema=x.fields
                    )

    def save_record(self, auto_fields=dict(), **kwargs):
        fields = dict()

        # set auto fields
        if auto_fields:
            fields = DecoupleFormSubmission(auto_fields, self.get_schema().get("schema")).get_schema_fields_updated()

        target_id = kwargs.pop("target_id", str())

        # set system fields
        system_fields = dict(
            date_modified=data_utils.get_datetime(),
            deleted=data_utils.get_not_deleted_flag()
        )

        if not target_id:
            system_fields["date_created"] = data_utils.get_datetime()
            system_fields["profile_id"] = self.profile_id

        # extend system fields
        for k, v in kwargs.items():
            system_fields[k] = v

        # add system fields to 'fields' and set default values - insert mode only
        for f in self.get_schema().get("schema"):
            f_id = f.id.split(".")[-1]

            if f_id in system_fields:
                fields[f_id] = system_fields.get(f_id)

            if not target_id and f_id not in fields:
                fields[f_id] = data_utils.default_jsontype(f.type)

        if target_id:
            self.get_collection_handle().update(
                {"_id": ObjectId(target_id)},
                {'$set': fields})
        else:
            doc = self.get_collection_handle().insert(fields)
            target_id = str(doc)

        # return saved record
        rec = self.get_record(target_id)

        return rec

    def get_all_records(self, sort_by='_id', sort_direction=-1):
        doc = dict(deleted=data_utils.get_not_deleted_flag())
        if self.profile_id:
            doc["profile_id"] = self.profile_id

        return cursor_to_list(self.get_collection_handle().find(doc).sort([[sort_by, sort_direction]]))


class Publication(DAComponent):
    def __init__(self, profile_id=None):
        super(Publication, self).__init__(profile_id, "publication")


class Person(DAComponent):
    def __init__(self, profile_id=None):
        super(Person, self).__init__(profile_id, "person")


class Source(DAComponent):
    def __init__(self, profile_id=None):
        super(Source, self).__init__(profile_id, "source")


class Sample(DAComponent):
    def __init__(self, profile_id=None):
        super(Sample, self).__init__(profile_id, "sample")


class Submission(DAComponent):
    def __init__(self, profile_id=None):
        super(Submission, self).__init__(profile_id, "submission")

    def get_incomplete_submissions_for_user(self, user_id, repo):
        doc = self.get_collection_handle().find(
            {"user_id": user_id,
             "repository": repo,
             "complete": False}
        )
        return doc

    def save_record(self, auto_fields=dict(), **kwargs):
        if kwargs.get("datafile_ids", list()):
            datafile_ids = kwargs.get("datafile_ids")
            kwargs["bundle"] = datafile_ids

            # get the target repository from one of the files
            repo = DataFile().get_record_property(datafile_ids[0], "target_repository")
            for k, v in dict(
                    repository=repo,
                    status=False,
                    complete=False,
                    user_id=ThreadLocal.get_current_user().id,
            ).items():
                auto_fields[self.get_qualified_field(k)] = v

        return super(Submission, self).save_record(auto_fields, **kwargs)

    def mark_all_token_obtained(self, user_id):

        # mark all submissions for profile with type figshare as token obtained
        return self.get_collection_handle().update_many(
            {
                'user_id': user_id,
                'repository': 'figshare'
            },
            {
                "$set": {
                    "token_obtained": True
                }
            }
        )

    def isComplete(self, sub_id):
        doc = self.get_collection_handle().find_one \
                (
                {
                    '_id': ObjectId(sub_id)
                }
            )
        return doc['complete']


class DataFile(DAComponent):
    def __init__(self, profile_id=None):
        super(DataFile, self).__init__(profile_id, "datafile")

    def get_by_file_id(self, file_id=None):
        docs = None
        if file_id:
            docs = self.get_collection_handle().find_one(
                {"file_id": file_id, "deleted": data_utils.get_not_deleted_flag()})

        return docs

    def get_relational_record_for_id(self, datafile_id):
        chunked_upload = ChunkedUpload.objects.get(id=int(datafile_id))
        return chunked_upload

    def get_record_property(self, datafile_id=str(), elem=str()):
        """
        eases the access to deeply nested properties
        :param datafile_id: record id
        :param elem: schema property(key)
        :return: requested property or some default value
        """

        datafile = self.get_record(datafile_id)
        description = datafile.get("description", dict())
        description_attributes = description.get("attributes", dict())
        description_stages = description.get("stages", list())

        property_dict = dict(
            target_repository=description_attributes.get("target_repository", dict()).get("deposition_context", str()),
            sequencing_instrument=description_attributes.get("nucleic_acid_sequencing", dict()).get(
                "sequencing_instrument", str()),
            study_type=description_attributes.get("study_type", dict()).get("study_type", str()),
            description_attributes=description_attributes,
            description_stages=description_stages
        )

        return property_dict.get(elem, str())


class Profile(DAComponent):
    def __init__(self, profile=None):
        super(Profile, self).__init__(None, "profile")

    def get_for_user(self, user=None):
        if not user:
            user = ThreadLocal.get_current_user().id

        docs = self.get_collection_handle().find({"user_id": user, "deleted": data_utils.get_not_deleted_flag()}).sort(
            [['_id', -1]])

        if docs:
            return docs
        else:
            return None

    def save_record(self, auto_fields=dict(), **kwargs):
        if not kwargs.get("target_id", str()):
            for k, v in dict(
                    copo_id=data_utils.get_copo_id(),
                    user_id=data_utils.get_user_id()
            ).items():
                auto_fields[self.get_qualified_field(k)] = v

        return super(Profile, self).save_record(auto_fields, **kwargs)


class RemoteDataFile:
    def __init__(self, profile_id=None):
        self.RemoteFileCollection = get_collection_ref(RemoteFileCollection)
        self.profile_id = profile_id

    def GET(self, id):
        doc = self.RemoteFileCollection.find_one({"_id": ObjectId(id)})
        if not doc:
            pass
        return doc

    def get_by_sub_id(self, sub_id):
        doc = self.RemoteFileCollection.find_one({"submission_id": sub_id})
        if not doc:
            pass
        return doc

    def create_transfer(self, submission_id, file_path=None):
        fields = data_utils.json_to_pytype(DB_TEMPLATES['REMOTE_FILE_COLLECTION'])
        fields['submission_id'] = submission_id
        fields['profile_id'] = self.profile_id
        fields['file_path'] = file_path
        transfer_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        fields["commenced_on"] = transfer_time
        fields["current_time"] = transfer_time
        fields["transfer_rate"] = []

        if file_path:
            d = DataFile().GET(submission_id)
            chunked_upload = ChunkedUpload.objects.get(id=int(d['file_id']))
            fields["file_size_bytes"] = u.filesize_toString(chunked_upload.offset)

        doc = self.RemoteFileCollection.insert(fields)

        # return inserted record
        df = self.GET(str(doc))
        return df

    def update_transfer(self, transfer_id, fields, delete="0"):

        fields["deleted"] = delete
        if 'transfer_rate' in fields:
            speed = fields.pop("transfer_rate")
            self.RemoteFileCollection.update(
                {
                    "_id": ObjectId(transfer_id)
                },
                {
                    '$push': {"transfer_rate": float(speed)},
                    '$set': fields
                }
            )
        else:
            self.RemoteFileCollection.update(
                {
                    "_id": ObjectId(transfer_id)
                },
                {
                    '$set': fields
                }
            )

    def get_all_records(self):
        doc = {'profile_id': self.profile_id, 'deleted': data_utils.get_not_deleted_flag()}
        return cursor_to_list(self.RemoteFileCollection.find(doc))

    def get_by_datafile(self, datafile_id):
        doc = {'datafile_id': ObjectId(datafile_id), 'deleted': data_utils.get_not_deleted_flag()}
        return cursor_to_list(self.RemoteFileCollection.find(doc))

    def sanitise_remote_files(self):
        pass


class Description:
    def __init__(self, profile_id=None):
        self.DescriptionCollection = get_collection_ref(DescriptionCollection)
        self.profile_id = profile_id

    def GET(self, id):
        doc = self.DescriptionCollection.find_one({"_id": ObjectId(id)})
        if not doc:
            pass
        return doc

    def create_description(self, stages=list(), attributes=dict()):
        self.purge_descriptions()

        fields = dict(
                    stages=stages,
                    attributes=attributes,
                    created_on=data_utils.get_datetime(),
                    user_id=ThreadLocal.get_current_user().id
            )
        doc = self.DescriptionCollection.insert(fields)

        # return inserted record
        df = self.GET(str(doc))
        return df

    def edit_description(self, description_id, fields):
        self.DescriptionCollection.update(
            {"_id": ObjectId(description_id)},
            {'$set': fields})

    def get_all_descriptions(self):
        return cursor_to_list(self.DescriptionCollection.find())

    def is_valid_token(self, description_token):
        is_valid = False

        if description_token:
            if self.DescriptionCollection.find_one({"_id": ObjectId(description_token)}):
                is_valid = True

        return is_valid

    def purge_descriptions(self):
        """
        purges the Description collection of all 'obsolete' tokens
        :return:
        """

        user_id = ThreadLocal.get_current_user().id

        bulk = self.DescriptionCollection.initialize_unordered_bulk_op()
        bulk.find({'user_id': user_id}).remove()
        bulk.execute()
