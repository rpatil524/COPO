__author__ = 'felix.shaw@tgac.ac.uk - 22/10/15'

from datetime import datetime
from bson import ObjectId, json_util
from chunked_upload.models import ChunkedUpload
from web.apps.web_copo.lookup.lookup import DB_TEMPLATES
import web.apps.web_copo.utils.EnaUtils as u
from dal import cursor_to_list
from dal.copo_base_da import DataSchemas
from dal.mongo_util import get_collection_ref
from web.apps.web_copo.schemas.utils import data_utils
from web.apps.web_copo.schemas.utils.data_utils import DecoupleFormSubmission
from django.contrib.auth.models import User
from django.conf import settings

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
AnnotationReference = 'AnnotationCollection'
GroupCollection = 'GroupCollection'
RepositoryCollection = 'RepositoryCollection'

handle_dict = dict(publication=get_collection_ref(PubCollection),
                   person=get_collection_ref(PersonCollection),
                   sample=get_collection_ref(SampleCollection),
                   source=get_collection_ref(SourceCollection),
                   profile=get_collection_ref(ProfileCollection),
                   submission=get_collection_ref(SubmissionCollection),
                   datafile=get_collection_ref(DataFileCollection),
                   annotation=get_collection_ref(AnnotationReference),
                   group=get_collection_ref(GroupCollection),
                   repository=get_collection_ref(RepositoryCollection)
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
                        num_annotation="annotation"
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

    def get_component_count(self):
        count = 0
        if self.get_collection_handle():
            count = self.get_collection_handle().count(
                {'profile_id': self.profile_id, 'deleted': data_utils.get_not_deleted_flag()})

        return count

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
            annotation="copo.annotation",
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

        # should have target_id for updates and return empty string for inserts
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

        # if True, then the database action (to save/update) is never performed, but validated 'fields' are returned
        validate_only = kwargs.pop("validate_only", False)

        # use the equality (==) test to save-guard against all sorts of value the 'validate_only' can assume
        if validate_only == True:
            return fields
        else:
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

    def get_all_records_columns(self, sort_by='_id', sort_direction=-1, projection=dict()):
        doc = dict(deleted=data_utils.get_not_deleted_flag())
        if self.profile_id:
            doc["profile_id"] = self.profile_id

        return cursor_to_list(self.get_collection_handle().find(doc, projection).sort([[sort_by, sort_direction]]))

    def execute_query(self, query_dict=dict()):
        if self.profile_id:
            query_dict["profile_id"] = self.profile_id

        return cursor_to_list(self.get_collection_handle().find(query_dict))


class Publication(DAComponent):
    def __init__(self, profile_id=None):
        super(Publication, self).__init__(profile_id, "publication")


class Annotation(DAComponent):
    def __init__(self, profile_id=None):
        super(Annotation, self).__init__(profile_id, "annotation")

    def get_annotations_for_page(self, document_id):
        doc = self.get_collection_handle().find_one(
            {"_id": ObjectId(document_id)},
        )
        return doc

    def update_annotation(self, document_id, annotation_id, fields, delete=False):
        # first remove element
        self.get_collection_handle().update(
            {
                'annotation._id': ObjectId(annotation_id)
            },
            {
                '$pull':
                    {'annotation':
                         {'_id': ObjectId(annotation_id)}
                     }
            }
        )
        if delete == False:
            # now add new element
            fields['_id'] = annotation_id
            self.get_collection_handle().update(
                {
                    '_id': ObjectId(document_id)
                },
                {
                    '$push': {'annotation': fields}
                }
            )
            return fields
        return ''

    def add_to_annotation(self, id, fields):
        fields['_id'] = ObjectId()
        self.get_collection_handle().update(
            {'_id': ObjectId(id)},
            {'$push':
                 {'annotation': fields}
             }
        )
        return fields

    def annotation_exists(self, doc_name, uid):
        return self.get_collection_handle().find({'document_name': {'$regex': "^" + doc_name}}).count() > 0

    def get_annotation_by_name(self, doc_name, uid):
        return self.get_collection_handle().find_one({'document_name': {'$regex': "^" + doc_name}})


class Person(DAComponent):
    def __init__(self, profile_id=None):
        super(Person, self).__init__(profile_id, "person")

    def get_people_for_profile(self):
        docs = self.get_collection_handle().find({'profile_id': self.profile_id})
        if docs:
            return docs
        else:
            return False

    def create_sra_person(self):
        """
        creates an (SRA) person record and attach to profile
        Returns:
        """
        user = data_utils.get_current_user()

        auto_fields = {
            'copo.person.roles.annotationValue': 'SRA Inform On Status',
            'copo.person.lastName': user.last_name,
            'copo.person.firstName': user.first_name,
            'copo.person.roles.annotationValue_1': 'SRA Inform On Error',
            'copo.person.email': user.email
        }

        people = self.get_all_records()
        sra_roles = list()
        for record in people:
            for role in record.get("roles", list()):
                sra_roles.append(role.get("annotationValue", str()))

        # has sra roles?
        has_sra_roles = all(x in sra_roles for x in ['SRA Inform On Status', 'SRA Inform On Error'])

        if not has_sra_roles:
            kwargs = dict()
            self.save_record(auto_fields, **kwargs)

        return


class Source(DAComponent):
    def __init__(self, profile_id=None):
        super(Source, self).__init__(profile_id, "source")

    def get_from_profile_id(self, profile_id):
        return self.get_collection_handle().find({'profile_id': profile_id})


class Sample(DAComponent):
    def __init__(self, profile_id=None):
        super(Sample, self).__init__(profile_id, "sample")

    def get_from_profile_id(self, profile_id):
        return self.get_collection_handle().find({'profile_id': profile_id})


class Submission(DAComponent):
    def __init__(self, profile_id=None):
        super(Submission, self).__init__(profile_id, "submission")

    def get_incomplete_submissions_for_user(self, user_id, repo):
        doc = self.get_collection_handle().find(
            {"user_id": user_id,
             "repository": repo,
             "complete": "false"}
        )
        return doc

    def save_record(self, auto_fields=dict(), **kwargs):
        if kwargs.get("datafile_ids", list()):
            datafile_ids = kwargs.get("datafile_ids")
            kwargs["bundle"] = datafile_ids

            bundle_meta = list()

            # store bundle metadata also, this will be used to capture richer context e.g., upload status
            for file_id in datafile_ids:
                datafile = DataFile().get_record(file_id)
                if datafile:
                    bundle_meta.append(
                        dict(file_id=file_id, file_path=datafile.get("file_location", str()), upload_status=False))

            kwargs["bundle_meta"] = bundle_meta

            # get the target repository from one of the files
            repo = DataFile().get_record_property(datafile_ids[0], "target_repository")
            for k, v in dict(
                    repository=repo,
                    status=False,
                    complete='false',
                    user_id=data_utils.get_current_user().id,
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

    def mark_figshare_article_published(self, article_id):
        return self.get_collection_handle().update_many(
            {
                'accessions': article_id
            },
            {
                "$set": {
                    "status": 'published'
                }
            }
        )

    def clear_submission_metadata(self, sub_id):
        return self.get_collection_handle().update({"_id": ObjectId(sub_id)}, {"$set": {"meta": {}}})

    def isComplete(self, sub_id):
        doc = self.get_collection_handle().find_one({"_id": ObjectId(sub_id)})

        return doc.get("complete", False)

    def mark_submission_complete(self, sub_id, article_id=None):
        if article_id:
            if not type(article_id) is list:
                article_id = [article_id]
            f = {
                "$set": {
                    "complete": "true",
                    "completed_on": datetime.now(),
                    "accessions": article_id
                }
            }
        else:
            f = {
                "$set": {
                    "complete": "true",
                    "completed_on": datetime.now()
                }
            }
        doc = self.get_collection_handle().update_one(
            {
                '_id': ObjectId(sub_id)
            },
            f

        )

    def mark_figshare_article_id(self, sub_id, article_id):
        if not type(article_id) is list:
            article_id = [article_id]
        doc = self.get_collection_handle().update_one(
            {
                '_id': ObjectId(sub_id)
            },
            {
                "$set": {
                    "accessions": article_id,
                }
            }
        )

    def get_file_accession(self, sub_id):
        doc = self.get_collection_handle().find_one(
            {
                '_id': ObjectId(sub_id)
            },
            {
                'accessions': 1,
                'bundle': 1,
                'repository': 1
            }
        )
        if doc['repository'] == 'figshare':
            return {'accessions': doc['accessions'], 'repo': 'figshare'}
        else:
            filenames = list()
            for file_id in doc['bundle']:
                f = DataFile().get_by_file_name_id(file_id=file_id)
                filenames.append(f['name'])
            if isinstance(doc['accessions'], str):
                doc['accessions'] = None
            return {'accessions': doc['accessions'], 'filenames': filenames, 'repo': doc['repository']}

    def get_file_accession_for_dataverse_entry(self, mongo_file_id):
        return self.get_collection_handle().find_one({'accessions.mongo_file_id': mongo_file_id},
                                                     {'_id': 0, 'accessions.$': 1})

    def get_complete(self):
        complete_subs = self.get_collection_handle().find({'complete': True})
        return complete_subs

    def get_ena_type(self):
        subs = self.get_collection_handle().find({'repository': {'$in': ['ena-ant', 'ena', 'ena-asm']}})
        return subs

    def update_destination_repo(self, submission_id, repo_id):
        if repo_id == 'default':
            return self.get_collection_handle().update(
                {'_id': ObjectId(submission_id)}, {'$set': {'destination_repo': 'default'}}
            )
        r = Repository().get_record(ObjectId(repo_id))
        dest = {"url": r['url'], 'apikey': r['apikey'], "isCG": r['isCG'], "repo_id": repo_id, "name": r['name'],
                "type": r['type'], "username": r['username'], "password": r['password']}
        self.get_collection_handle().update(
            {'_id': ObjectId(submission_id)}, {'$set': {'destination_repo': dest, 'repository': r['type']}}
        )

        return r

    def update_meta(self, submission_id, meta):
        return self.get_collection_handle().update(
            {'_id': ObjectId(submission_id)}, {'$set': {'meta': json_util.loads(meta)}}
        )

    def get_dataverse_details(self, submission_id):
        doc = self.get_collection_handle().find_one(
            {'_id': ObjectId(submission_id)}, {'destination_repo': 1}
        )
        default_dataverse = {'url': settings.DATAVERSE["HARVARD_TEST_API"],
                             'apikey': settings.DATAVERSE["HARVARD_TEST_TOKEN"]}
        if 'destination_repo' in doc:
            if doc['destination_repo'] == 'default':
                return default_dataverse
            else:
                return doc['destination_repo']
        else:
            return default_dataverse

    def mark_as_published(self, submission_id):
        return self.get_collection_handle().update(
            {'_id': ObjectId(submission_id)}, {'$set': {'published': True}}
        )


class DataFile(DAComponent):
    def __init__(self, profile_id=None):
        super(DataFile, self).__init__(profile_id, "datafile")

    def get_for_profile(self, profile_id):
        docs = self.get_collection_handle().find({
            "profile_id": profile_id
        })
        return docs

    def get_by_file_id(self, file_id=None):
        docs = None
        if file_id:
            docs = self.get_collection_handle().find_one(
                {"file_id": file_id, "deleted": data_utils.get_not_deleted_flag()})

        return docs

    def get_by_file_name_id(self, file_id=None):
        docs = None
        if file_id:
            docs = self.get_collection_handle().find_one(
                {
                    "_id": ObjectId(file_id), "deleted": data_utils.get_not_deleted_flag()
                },
                {
                    "name": 1
                }
            )

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
            attach_samples=description_attributes.get("attach_samples", dict()).get("study_samples", str()),
            sequencing_instrument=description_attributes.get("nucleic_acid_sequencing", dict()).get(
                "sequencing_instrument", str()),
            study_type=description_attributes.get("study_type", dict()).get("study_type", str()),
            description_attributes=description_attributes,
            description_stages=description_stages
        )

        return property_dict.get(elem, str())

    def add_fields_to_datafile_stage(self, target_ids, fields, target_stage_ref):

        for target_id in target_ids:
            # for each file in target_ids retrieve the datafile object
            df = self.get_record(target_id)
            # get the stage using list comprehension and add new fields
            for idx, stage in enumerate(df['description']['stages']):
                if 'ref' in stage and stage['ref'] == target_stage_ref:
                    for field in fields:
                        df['description']['stages'][idx]['items'].append(field)

            # now update datafile record
            self.get_collection_handle().update({'_id': ObjectId(target_id)},
                                                {'$set': {'description.stages': df['description']['stages']}})


class Profile(DAComponent):
    def __init__(self, profile=None):
        super(Profile, self).__init__(None, "profile")

    def get_all_profiles(self, user=None):
        mine = list(self.get_for_user(user))
        shared = list(self.get_shared_for_user(user))
        return shared + mine

    def get_for_user(self, user=None):
        if not user:
            user = data_utils.get_current_user().id
        docs = self.get_collection_handle().find({"user_id": user, "deleted": data_utils.get_not_deleted_flag()}).sort(
            [['_id', -1]])

        if docs:
            return docs
        else:
            return None

    def get_shared_for_user(self, user=None):
        # get profiles shared with user
        if not user:
            user = data_utils.get_current_user().id
        groups = CopoGroup().Group.find({'member_ids': str(user)})

        p_list = list()
        for g in groups:
            gp = dict(g)
            p_list.extend(gp['shared_profile_ids'])
        # remove duplicates
        # p_list = list(set(p_list))
        docs = self.get_collection_handle().find(
            {
                "_id": {"$in": p_list},
                "deleted": data_utils.get_not_deleted_flag()
            }
        )
        out = list(docs)
        for d in out:
            d['shared'] = True

        return out

    def save_record(self, auto_fields=dict(), **kwargs):
        if not kwargs.get("target_id", str()):
            for k, v in dict(
                    copo_id=data_utils.get_copo_id(),
                    user_id=data_utils.get_user_id()
            ).items():
                auto_fields[self.get_qualified_field(k)] = v

        rec = super(Profile, self).save_record(auto_fields, **kwargs)

        # trigger after save actions
        if not kwargs.get("target_id", str()):
            Person(profile_id=str(rec["_id"])).create_sra_person()
        return rec

    def add_dataverse_details(self, profile_id, dataverse):
        handle_dict['profile'].update_one({'_id': ObjectId(profile_id)}, {'$set': {'dataverse': dataverse}})

    def check_for_dataverse_details(self, profile_id):
        p = self.get_record(ObjectId(profile_id))
        if 'dataverse' in p:
            return p['dataverse']

    def add_dataverse_dataset_details(self, profile_id, dataset):

        handle_dict['profile'].update_one({'_id': ObjectId(profile_id)}, {'$push': {'dataverse.datasets': dataset}})
        return [dataset]

    def check_for_dataset_details(self, profile_id):
        p = self.get_record(ObjectId(profile_id))
        if 'dataverse' in p:
            if 'datasets' in p['dataverse']:
                return p['dataverse']['datasets']


class CopoGroup(DAComponent):
    def __init__(self):
        super(CopoGroup, self).__init__(None, "group")
        self.Group = get_collection_ref(GroupCollection)

    def get_by_owner(self, owner_id):
        doc = self.Group.find({'owner_id': owner_id})
        if not doc:
            return list()
        return doc

    def create_shared_group(self, name, description, owner_id=None):
        group_fields = data_utils.json_to_pytype(DB_TEMPLATES['COPO_GROUP'])
        if not owner_id:
            owner_id = data_utils.get_user_id()
        group_fields['owner_id'] = owner_id
        group_fields['name'] = name
        group_fields['description'] = description
        group_fields['data_created'] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        uid = self.Group.insert(group_fields)
        if uid:
            return uid
        else:
            return False

    def delete_group(self, group_id):
        result = self.Group.delete_one({'_id': ObjectId(group_id)})
        return result.deleted_count > 0

    def add_profile(self, group_id, profile_id):
        return self.Group.update({'_id': ObjectId(group_id)}, {'$push': {'shared_profile_ids': ObjectId(profile_id)}})

    def remove_profile(self, group_id, profile_id):
        return self.Group.update(
            {'_id': ObjectId(group_id)},
            {'$pull': {'shared_profile_ids': ObjectId(profile_id)}}
        )

    def get_profiles_for_group_info(self, group_id):
        p_list = cursor_to_list(Profile().get_for_user(data_utils.get_user_id()))
        group = CopoGroup().get_record(ObjectId(group_id))
        for p in p_list:
            if p['_id'] in group['shared_profile_ids']:
                p['selected'] = True
            else:
                p['selected'] = False
        return p_list

    def get_repos_for_group_info(self, uid, group_id):
        g = CopoGroup().get_record(ObjectId(group_id))
        docs = cursor_to_list(Repository().Repository.find({'users.uid': uid}))
        for d in docs:
            if d['_id'] in g['repo_ids']:
                d['selected'] = True
            else:
                d['selected'] = False
        return list(docs)

    def get_users_for_group_info(self, group_id):
        group = CopoGroup().get_record(ObjectId(group_id))
        member_ids = group['member_ids']
        user_list = list()
        for u in member_ids:
            usr = User.objects.get(pk=u)
            x = {'id': usr.id, 'first_name': usr.first_name, 'last_name': usr.last_name, 'email': usr.email,
                 'username': usr.username}
            user_list.append(x)
        return user_list

    def add_user_to_group(self, group_id, user_id):
        return self.Group.update(
            {'_id': ObjectId(group_id)},
            {'$push': {'member_ids': user_id}})

    def remove_user_from_group(self, group_id, user_id):
        return self.Group.update(
            {'_id': ObjectId(group_id)},
            {'$pull': {'member_ids': user_id}}
        )

    def add_repo(self, group_id, repo_id):
        return self.Group.update({'_id': ObjectId(group_id)}, {'$push': {'repo_ids': ObjectId(repo_id)}})

    def remove_repo(self, group_id, repo_id):
        return self.Group.update(
            {'_id': ObjectId(group_id)},
            {'$pull': {'repo_ids': ObjectId(repo_id)}}
        )


class Repository(DAComponent):
    def __init__(self):
        super(Repository, self).__init__(None, "repository")
        self.Repository = get_collection_ref(RepositoryCollection)

    def get_by_uid(self, uid):
        doc = self.get_collection_handle().find({"uid": uid}, {"name": 1, "type": 1, "url": 1})
        return doc

    def get_by_ids(self, uids):
        oids = list(map(lambda x: ObjectId(x), uids))
        doc = self.get_collection_handle().find({"_id": {"$in": oids}})
        return cursor_to_list(doc)

    def get_by_username(self, username):
        doc = self.get_collection_handle().find({"username": username})
        return doc

    def get_users(self, repo_id):
        doc = self.get_collection_handle().find_one({"_id": ObjectId(repo_id)})
        return doc['users']

    def push_user(self, repo_id, uid, first_name, last_name, username, email):
        args = {'uid': uid, "first_name": first_name, "last_name": last_name, "username": username, "email": email}
        return self.Repository.update(
            {'_id': ObjectId(repo_id)},
            {'$push': {'users': args}}
        )

    def pull_user(self, repo_id, user_id):
        doc = self.Repository.update({'_id': ObjectId(repo_id)},
                                     {'$pull': {'users': {'uid': user_id}}})
        return doc


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
        # before creating a new transfer record for this submission, remove all others
        remote_record = self.get_by_sub_id(submission_id)
        if remote_record:
            self.delete_transfer(str(remote_record["_id"]))

        fields = data_utils.json_to_pytype(DB_TEMPLATES['REMOTE_FILE_COLLECTION'])
        fields['submission_id'] = submission_id
        fields['profile_id'] = self.profile_id
        fields['file_path'] = file_path
        transfer_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        fields["commenced_on"] = transfer_time
        fields["current_time"] = transfer_time
        fields["transfer_rate"] = ""

        if file_path:
            d = DataFile().GET(submission_id)
            chunked_upload = ChunkedUpload.objects.get(id=int(d['file_id']))
            fields["file_size_bytes"] = u.filesize_toString(chunked_upload.offset)

        doc = self.RemoteFileCollection.insert(fields)

        # return inserted record
        df = self.GET(str(doc))
        return df

    def delete_transfer(self, transfer_id):
        self.RemoteFileCollection.delete_one({'_id': ObjectId(transfer_id)})

    def update_transfer(self, transfer_id, fields, delete="0"):

        fields["deleted"] = delete
        if 'transfer_rate' in fields:
            # speed = fields.pop("transfer_rate")

            self.RemoteFileCollection.update(
                {
                    "_id": ObjectId(transfer_id)
                },
                {
                    # '$push': {"transfer_rate": float(speed)},
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
            user_id=data_utils.get_current_user().id
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

        user_id = data_utils.get_current_user().id

        bulk = self.DescriptionCollection.initialize_unordered_bulk_op()
        bulk.find({'user_id': user_id}).remove()
        bulk.execute()
