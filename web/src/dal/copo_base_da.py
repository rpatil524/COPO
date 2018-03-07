

__author__ = 'felixshaw'

import bson.objectid as o
from web.apps.web_copo.schemas.utils import data_utils
from django.urls import reverse

from web.apps.web_copo.vocab.status_vocab import STATUS_CODES
from web.apps.web_copo.schemas.utils.data_formats import DataFormats
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from dal.mongo_util import get_collection_ref
from dal.base_resource import Resource

Schemas = get_collection_ref("Schemas")
Collections = get_collection_ref("CollectionHeads")
Profiles = get_collection_ref("Profiles")


class Collection_Head(Resource):
    # method to create a skelton collection object
    def PUT(self):
        return Collections.insert({})

    def update(self, collection_head_id, doc):
        Collections.update(
            {
                '_id': collection_head_id
            },
            {
                '$set': doc
            }
        )

    def GET(self, id):
        return Collections.find_one({"_id": o.ObjectId(id)})

    def add_collection_details(self, collection_head_id, details_id):
        Collections.update(
            {
                "_id": o.ObjectId(collection_head_id)
            },
            {
                '$push': {"collection_details": details_id}
            }
        )

    def collection_details_id_from_head(self, head_id):
        collection = Collections.find_one({"_id": o.ObjectId(head_id)})
        return 0


class Profile_Status_Info(Resource):

    def get_profiles_status(self):
        from .copo_da import Profile
        # this method examines all the profiles owned by the current user and returns
        # the number of profiles which have been marked as dirty
        issues = {}
        issue_desc = []
        issue_id = []
        issues_count = 0
        try:
            user_id = data_utils.get_current_user().id
            prof = Profiles.find({"user_id": user_id})
        except AttributeError as e:
            prof = []

        # iterate profiles and find collections which are dirty
        for p in prof:
            try:
                collections_ids = p['collections']
            except:
                issues_count += 1
                context = {}
                context["profile_name"] = p['title']
                context["link"] = reverse('copo:view_copo_profile', args=[p["_id"]])
                issue_desc.append(STATUS_CODES['PROFILE_EMPTY'].format(**context))
                break
            # now get the corresponding collection_heads
            collections_heads = Collections.find({'_id': {'$in': collections_ids}},
                                                 {'is_clean': 1, 'collection_details': 1})
            # for c in collections_heads:
            #     try:
            #         if c['is_clean'] == 0:
            #             profile = Profile().get_profile_from_collection_id(c["_id"])
            #             issues_count += 1
            #             context = {}
            #             context["profile_name"] = p['title']
            #             context["link"] = reverse('copo:view_copo_profile', args=[profile["_id"]])
            #
            #             # now work out why the collection is dirty
            #             if False:
            #                 pass
            #             else:
            #                 issue_desc.append(STATUS_CODES['PROFILE_NOT_DEPOSITED'].format(**context))
            #     except:
            #         pass
        issues['issue_id_list'] = issue_id
        issues['num_issues'] = issues_count
        issues['issue_description_list'] = issue_desc
        return issues


class DataSchemas:
    def __init__(self, schema):
        self.schema = schema.upper()

    def add_ui_template(self, template):
        # remove any existing UI templates for the target schema
        self.delete_ui_template()

        doc = {"schemaName": self.schema, "schemaType": "UI", "data": template}
        Schemas.insert(doc)

    def delete_ui_template(self):
        Schemas.remove({"schemaName": self.schema, "schemaType": "UI"})

    def get_ui_template(self):
        doc = Schemas.find_one({"schemaName": self.schema, "schemaType": "UI"})

        if doc:
            doc = doc["data"]
        else:
            # try generating the template
            temp_dict = DataFormats(self.schema).generate_ui_template()

            # store a copy in the DB
            if temp_dict["status"] == "success" and temp_dict["data"]:
                self.add_ui_template(temp_dict["data"])
                doc = temp_dict["data"]
            else:
                # todo: we could do with some human intervention, report error!
                doc = None
        return doc

    def get_ui_template_as_obj(self):
        """obj_type specifies how the document should be returned: as 'dict' - python dictionary or
         'obj' - an object-typed notation"""
        doc = self.get_ui_template()
        if doc:
            return d_utils.json_to_object(doc)
        return doc
