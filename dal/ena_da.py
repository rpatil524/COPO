from datetime import date
import difflib
import string
import uuid
import ast
import re
import random
from web.apps.web_copo.schemas.utils import data_utils as d_utils
from chunked_upload.models import ChunkedUpload
from dal.mongo_util import get_collection_ref
from dal.base_resource import Resource
from dal import ObjectId
from dal.copo_base_da import DataSchemas
__author__ = 'felix.shaw@tgac.ac.uk - 18/03/15'

EnaCollections = get_collection_ref("EnaCollections")


class EnaCollection(Resource):
    def GET(self, id):
        doc = EnaCollections.find_one({"_id": ObjectId(id)})
        if not doc:
            pass
        return doc

    def PUT(self, doc):
        return EnaCollections.insert(doc)

    def add_ena_study(self, ena_collection_id, study_type_list):
        # get study template from the ENA db template
        study_template = d_utils.get_db_template("ENA")['studies'][0]

        if study_template:
            for st in study_type_list:
                study_dict = study_template
                study_dict["studyCOPOMetadata"]["id"] = uuid.uuid4().hex
                study_dict["studyCOPOMetadata"]["studyType"] = st['study_type']

                # handles empty study reference assignment
                study_dict["studyCOPOMetadata"]["studyReference"] = ''.join(
                    random.choice(string.ascii_uppercase) for i in range(4))
                if st["study_type_reference"]:
                    study_dict["studyCOPOMetadata"]["studyReference"] = st["study_type_reference"]

                # ...since the model study is deleted by default
                study_dict["studyCOPOMetadata"]["deleted"] = "0"

                EnaCollections.update({"_id": ObjectId(ena_collection_id)},
                                      {"$push": {"studies": study_dict}})

    def clone_ena_study(self, ena_collection_id, cloned_elements):
        # get study template from the ENA db template
        study_template = d_utils.get_db_template("ENA")['studies'][0]

        if study_template:
            study_dict = study_template

            study_dict["studyCOPOMetadata"]["id"] = uuid.uuid4().hex
            study_dict["studyCOPOMetadata"]["deleted"] = "0"

            if cloned_elements["studyType"]:
                study_dict["studyCOPOMetadata"]["studyType"] = cloned_elements["studyType"]

            study_dict["studyCOPOMetadata"]["studyReference"] = ''.join(
                random.choice(string.ascii_uppercase) for i in range(4)) + "_CLONE"
            if cloned_elements["studyReference"]:
                study_dict["studyCOPOMetadata"]["studyReference"] = cloned_elements["studyReference"]

            # check for samples and other composite types
            new_samples = []
            for k, v in cloned_elements.items():
                if k[:-2] == "sample":
                    new_samples.append({'id': v, 'deleted': '0'})

            if new_samples:
                study_dict["studyCOPOMetadata"]['samples'] = new_samples

            # get study fields
            ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.fields

            for f in ena_d:
                key_split = f.id.split(".")
                target_key = key_split[len(key_split) - 1]
                if target_key in cloned_elements.keys():
                    study_dict["study"][target_key] = cloned_elements[target_key]

            EnaCollections.update({"_id": ObjectId(ena_collection_id)},
                                  {"$push": {"studies": study_dict}})

    def delete_study(self, ena_collection_id, study_id):
        EnaCollections.update(
            {"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
            {'$set': {"studies.$.studyCOPOMetadata.deleted": "1"}})

    def add_study_publication(self, study_id, ena_collection_id, auto_fields):
        ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.studyPublications.fields
        auto_fields = ast.literal_eval(auto_fields)

        # get target study
        study = self.get_ena_study(study_id, ena_collection_id)

        # each study should have an empty publication document for creating others
        publication_dict = study["study"]["studyPublications"][0]

        if publication_dict:
            publication_dict["id"] = uuid.uuid4().hex
            publication_dict["deleted"] = "0"

            for f in ena_d:
                key_split = f.id.split(".")
                if f.id in auto_fields.keys():
                    publication_dict[key_split[len(key_split) - 1]] = auto_fields[f.id]

            EnaCollections.update(
                {"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                {'$push': {"studies.$.study.studyPublications": publication_dict}})

    def add_study_contact(self, study_id, ena_collection_id, auto_fields):
        ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.studyContacts.fields
        auto_fields = ast.literal_eval(auto_fields)

        # get target study
        study = self.get_ena_study(study_id, ena_collection_id)

        # each study should have an empty contact document for creating others
        contact_dict = study["study"]["studyContacts"][0]

        if contact_dict:
            contact_dict["id"] = uuid.uuid4().hex
            contact_dict["deleted"] = "0"

            for f in ena_d:
                key_split = f.id.split(".")
                if f.id in auto_fields.keys():
                    contact_dict[key_split[len(key_split) - 1]] = auto_fields[f.id]

            EnaCollections.update(
                {"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                {'$push': {"studies.$.study.studyContacts": contact_dict}})

    def add_study_protocol(self, study_id, ena_collection_id, auto_fields):
        ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.studyProtocols.fields
        auto_fields = ast.literal_eval(auto_fields)

        # get target study
        study = self.get_ena_study(study_id, ena_collection_id)

        # each study should have an empty protocol document for creating others
        protocol_dict = study["study"]["studyProtocols"][0]

        if protocol_dict:
            protocol_dict["id"] = uuid.uuid4().hex
            protocol_dict["deleted"] = "0"

            for f in ena_d:
                key_split = f.id.split(".")
                if f.id in auto_fields.keys():
                    protocol_dict[key_split[len(key_split) - 1]] = auto_fields[f.id]

            EnaCollections.update(
                {"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                {'$push': {"studies.$.study.studyProtocols": protocol_dict}})

    def get_study_publications(self, study_id, ena_collection_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.study.studyPublications"},
                                        {"$match": {"studies.study.studyPublications.deleted": "0"}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyPublications"}}}])

        return verify_doc_type(doc)

    def get_study_publication(self, study_id, ena_collection_id, publication_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.study.studyPublications"},
                                        {"$match": {"studies.study.studyPublications.id": publication_id}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyPublications"}}}])

        data = verify_doc_type(doc)

        return data[0] if data else {}

    def get_study_publications_all(self, study_id, ena_collection_id):  # this will also include 'deleted' items
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyPublications"}}}])

        data = verify_doc_type(doc)

        return data[0] if data else []

    def get_study_contacts(self, study_id, ena_collection_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.study.studyContacts"},
                                        {"$match": {"studies.study.studyContacts.deleted": "0"}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyContacts"}}}])

        return verify_doc_type(doc)

    def get_study_contact(self, study_id, ena_collection_id, contact_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.study.studyContacts"},
                                        {"$match": {"studies.study.studyContacts.id": contact_id}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyContacts"}}}])

        data = verify_doc_type(doc)

        return data[0] if data else {}

    def get_study_contacts_all(self, study_id, ena_collection_id):  # this will also include 'deleted' items
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyContacts"}}}])

        data = verify_doc_type(doc)

        return data[0] if data else []

    def get_study_protocols(self, study_id, ena_collection_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.study.studyProtocols"},
                                        {"$match": {"studies.study.studyProtocols.deleted": "0"}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyProtocols"}}}])

        return verify_doc_type(doc)

    def get_study_protocol(self, study_id, ena_collection_id, protocol_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.study.studyProtocols"},
                                        {"$match": {"studies.study.studyProtocols.id": protocol_id}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyProtocols"}}}])

        data = verify_doc_type(doc)

        return data[0] if data else {}

    def get_study_protocols_all(self, study_id, ena_collection_id):  # this will also include 'deleted' items
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.study.studyProtocols"}}}])

        data = verify_doc_type(doc)

        return data[0] if data else []

    def add_file_to_ena_study(self, study_id, ena_collection_id, file_id):
        # get study dataFile template from the ENA db template
        datafile_template = d_utils.get_db_template("ENA")['studies'][0]['studyCOPOMetadata']['dataFiles'][0]
        data_file_id = uuid.uuid4().hex
        if datafile_template:
            datafile_dict = datafile_template
            datafile_dict["id"] = data_file_id
            datafile_dict["fileId"] = file_id
            datafile_dict["deleted"] = "0"

            EnaCollections.update({"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                                  {'$push': {"studies.$.studyCOPOMetadata.dataFiles": datafile_dict}})
        return data_file_id

    def update_ena_datafile(self, study_id, ena_collection_id, data_file_id, fields):
        data_file = self.get_study_datafile(study_id, ena_collection_id, data_file_id)
        all_data_files = self.get_study_datafiles_all(ena_collection_id, study_id)

        # get index of the target record in the list of datafiles
        indx = all_data_files.index(data_file)

        if indx:
            for k, v in fields.items():
                EnaCollections.update(
                    {"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                    {'$set': {"studies.$.studyCOPOMetadata.dataFiles." + str(indx) + "." + k: v}})

    def add_ena_sample(self, ena_collection_id, study_type_list, auto_fields):
        ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.studySamples.fields
        auto_fields = ast.literal_eval(auto_fields)

        sample_id = uuid.uuid4().hex
        a = {'id': sample_id}

        characteristics = []

        for f in ena_d:
            key_split = f.id.split(".")
            a[key_split[len(key_split) - 1]] = ""  # accommodates fields not displayed on form
            if f.id in auto_fields.keys():
                a[key_split[len(key_split) - 1]] = auto_fields[f.id]
                if key_split[len(key_split) - 1] == "organism":
                    characteristics.append({
                        "categoryTerm": "organism",
                        "characteristics": auto_fields[f.id],
                        "termSourceREF": auto_fields["termSourceREF_organism"],
                        "termAccessionNumber": auto_fields["termAccessionNumber_organism"]
                    })

        ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.studySamples.sampleCollection.fields

        for f in ena_d:
            key_split = f.id.split(".")
            a[key_split[len(key_split) - 1]] = ""
            if f.id in auto_fields.keys():
                a[key_split[len(key_split) - 1]] = auto_fields[f.id]

        # get characteristics, we have already begun with the organism,
        # retrieve and sort to maintain order as displayed form
        categories = [key for key, value in auto_fields.items() if key.startswith('categoryTerm_')]
        categories.sort()

        for category in categories:
            index_part = category.split("categoryTerm_")[1]
            if auto_fields['categoryTerm_' + index_part]:
                ch = {
                    "categoryTerm": auto_fields['categoryTerm_' + index_part],
                    "characteristics": auto_fields['characteristics_' + index_part],
                    "termSourceREF": auto_fields['termSourceREF_' + index_part],
                    "termAccessionNumber": auto_fields['termAccessionNumber_' + index_part],
                    "unit": auto_fields['unit_' + index_part]
                }

                characteristics.append(ch)

        a["characteristics"] = characteristics

        EnaCollections.update({"_id": ObjectId(ena_collection_id)},
                              {"$push": {"collectionCOPOMetadata.samples": a}})

        # assign sample to studies
        for study_id in study_type_list:
            a = {'id': sample_id, 'deleted': '0'}
            self.add_sample_to_ena_study(study_id, ena_collection_id, a)

        return sample_id

    def edit_ena_sample(self, ena_collection_id, sample_id, study_type_list, auto_fields):
        ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.studySamples.fields
        auto_fields = ast.literal_eval(auto_fields)

        characteristics = []

        for f in ena_d:
            key_split = f.id.split(".")
            if f.id in auto_fields.keys():
                EnaCollections.update(
                    {"_id": ObjectId(ena_collection_id), "collectionCOPOMetadata.samples.id": sample_id},
                    {'$set': {"collectionCOPOMetadata.samples.$." + key_split[len(key_split) - 1]: auto_fields[f.id]}})

                if key_split[len(key_split) - 1] == "organism":
                    characteristics.append({
                        "categoryTerm": "organism",
                        "characteristics": auto_fields[f.id],
                        "termSourceREF": auto_fields["termSourceREF_organism"],
                        "termAccessionNumber": auto_fields["termAccessionNumber_organism"]
                    })

        ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.studySamples.sampleCollection.fields

        for f in ena_d:
            key_split = f.id.split(".")
            if f.id in auto_fields.keys():
                EnaCollections.update(
                    {"_id": ObjectId(ena_collection_id), "collectionCOPOMetadata.samples.id": sample_id},
                    {'$set': {"collectionCOPOMetadata.samples.$." + key_split[len(key_split) - 1]: auto_fields[f.id]}})

        # get characteristics
        #
        categories = [key for key, value in auto_fields.items() if key.startswith('categoryTerm_')]
        categories.sort()

        for category in categories:
            index_part = category.split("categoryTerm_")[1]
            if auto_fields['categoryTerm_' + index_part]:
                ch = {
                    "categoryTerm": auto_fields['categoryTerm_' + index_part],
                    "characteristics": auto_fields['characteristics_' + index_part],
                    "termSourceREF": auto_fields['termSourceREF_' + index_part],
                    "termAccessionNumber": auto_fields['termAccessionNumber_' + index_part],
                    "unit": auto_fields['unit_' + index_part]
                }

                characteristics.append(ch)

        EnaCollections.update(
            {"_id": ObjectId(ena_collection_id), "collectionCOPOMetadata.samples.id": sample_id},
            {'$set': {"collectionCOPOMetadata.samples.$.characteristics": characteristics}})

        # update studies: add sample to study if study in the selected list,
        # delete from study not selected
        studies = EnaCollection().get_ena_studies(ena_collection_id)
        for st in studies:
            study_id = st["studyCOPOMetadata"]["id"]

            a = {'id': sample_id, 'deleted': '1'}
            if study_id in study_type_list:
                a = {'id': sample_id, 'deleted': '0'}

            self.hard_delete_sample_from_study(sample_id, study_id, ena_collection_id)
            self.add_sample_to_ena_study(study_id, ena_collection_id, a)

    def get_ena_sample(self, ena_collection_id, sample_id):
        doc = EnaCollections.find_one({"_id": ObjectId(ena_collection_id),
                                       "collectionCOPOMetadata.samples.id": sample_id},
                                      {"collectionCOPOMetadata.samples.$": 1})

        return doc['collectionCOPOMetadata']['samples'][0] if doc else ''

    # this might have to scale to handle samples at the Profile level
    def get_all_samples(self, ena_collection_id):
        ena_collection = EnaCollection().GET(ena_collection_id)
        samples = ena_collection["collectionCOPOMetadata"]["samples"]

        # the first entry is always a placeholder, and we don't want to include this in the returned data
        del samples[0]

        return samples

    def get_study_samples(self, ena_collection_id, study_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.studyCOPOMetadata.samples"},
                                        {"$match": {"studies.studyCOPOMetadata.samples.deleted": "0"}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.studyCOPOMetadata.samples"}}}])

        return verify_doc_type(doc)

    def get_study_datafiles(self, ena_collection_id, study_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.studyCOPOMetadata.dataFiles"},
                                        {"$match": {"studies.studyCOPOMetadata.dataFiles.deleted": "0"}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.studyCOPOMetadata.dataFiles"}}}])

        return verify_doc_type(doc)

    def get_study_datafiles_all(self, ena_collection_id, study_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.studyCOPOMetadata.dataFiles"},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.studyCOPOMetadata.dataFiles"}}}])

        return verify_doc_type(doc)

    def get_study_datafile(self, study_id, ena_collection_id, data_file_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}},
                                        {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.id": study_id}},
                                        {"$unwind": "$studies.studyCOPOMetadata.dataFiles"},
                                        {"$match": {"studies.studyCOPOMetadata.dataFiles.id": data_file_id}},
                                        {"$group": {"_id": "$_id",
                                                    "data": {"$push": "$studies.studyCOPOMetadata.dataFiles"}}}])

        data = verify_doc_type(doc)
        return data[0] if data else {}

    def add_assay_data_to_datafile(self, study_id, ena_collection_id, data_file_id, assay_data):

        data_file = self.get_study_datafile(study_id, ena_collection_id, data_file_id)
        all_data_files = self.get_study_datafiles_all(ena_collection_id, study_id)

        # get index of the target record in the list of datafiles
        indx = all_data_files.index(data_file)
        if indx:
            EnaCollections.update(
                {"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                {'$push': {"studies.$.studyCOPOMetadata.dataFiles." + str(indx) + ".attributes": assay_data}},
                upsert=True
            )

    def check_data_file_status(self, collection_id, study_id, file_id):

        file = self.get_study_datafile(study_id, collection_id, file_id)
        return 'attributes' in file and len(file['attributes']) > 0

    def add_sample_to_ena_study(self, study_id, ena_collection_id, sample):
        EnaCollections.update({"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                              {'$push': {"studies.$.studyCOPOMetadata.samples": sample}})

    def assign_samples_in_study(self, study_id, ena_collection_id, add_list, remove_list):
        if remove_list:
            for sample_id in remove_list:
                self.hard_delete_sample_from_study(sample_id, study_id, ena_collection_id)

        if add_list:
            for sample_id in add_list:
                self.hard_delete_sample_from_study(sample_id, study_id, ena_collection_id)
                a = {'id': sample_id, 'deleted': '0'}
                self.add_sample_to_ena_study(study_id, ena_collection_id, a)

    # this function allows the total removal of the specified sample record from a study
    def hard_delete_sample_from_study(self, sample_id, study_id, ena_collection_id):
        EnaCollections.update({"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                              {'$pull': {"studies.$.studyCOPOMetadata.samples": {'id': sample_id}}})

    def update_study_publication(self, publication_id, study_id, ena_collection_id, field_list):
        publication = self.get_study_publication(study_id, ena_collection_id, publication_id)
        all_publications = self.get_study_publications_all(study_id, ena_collection_id)

        indx = all_publications.index(publication)

        if indx:
            for f_l in field_list:
                for k, v in f_l.items():
                    EnaCollections.update(
                        {"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                        {'$set': {"studies.$.study.studyPublications." + str(indx) + "." + k: v}})

    def update_study_contact(self, contact_id, study_id, ena_collection_id, field_list):
        contact = self.get_study_contact(study_id, ena_collection_id, contact_id)
        all_contacts = self.get_study_contacts_all(study_id, ena_collection_id)

        indx = all_contacts.index(contact)

        if indx:
            for f_l in field_list:
                for k, v in f_l.items():
                    EnaCollections.update(
                        {"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id},
                        {'$set': {"studies.$.study.studyContacts." + str(indx) + "." + k: v}})

    def get_ena_study(self, study_id, ena_collection_id):
        doc = EnaCollections.find_one({"_id": ObjectId(ena_collection_id),
                                       "studies.studyCOPOMetadata.id": study_id},
                                      {"studies.studyCOPOMetadata.id.$": 1})

        return doc['studies'][0] if doc else {}

    def get_ena_studies(self, ena_collection_id):
        doc = EnaCollections.aggregate([{"$match": {"_id": ObjectId(ena_collection_id)}}, {"$unwind": "$studies"},
                                        {"$match": {"studies.studyCOPOMetadata.deleted": "0"}},
                                        {"$group": {"_id": "$_id", "data": {"$push": "$studies"}}}])  # using 'data'
        # as a projection variable (in the $group part), allows for harmonising the returned type in verify_doc_type

        return verify_doc_type(doc)

    def update_study_type(self, ena_collection_id, study_id, elem_dict):
        doc = EnaCollections.update({"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id}, {
            '$set': {"studies.$.studyCOPOMetadata.studyType": elem_dict["study_type"],
                     "studies.$.studyCOPOMetadata.studyReference": elem_dict["study_type_reference"]}})
        return doc

    def update_study_details(self, ena_collection_id, study_id, auto_fields):
        ena_d = d_utils.get_ui_template_as_obj("ENA").studies.study.fields
        auto_fields = ast.literal_eval(auto_fields)

        auto_dict = {}

        for f in ena_d:
            key_split = f.id.split(".")
            if f.id in auto_fields.keys():
                auto_dict["studies.$.study." + key_split[len(key_split) - 1]] = auto_fields[f.id]

        EnaCollections.update({"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id}, {
            '$set': auto_dict})

    def refactor_ena_schema(self, ena_collection_id):
        # get list of all studies in the collection and start gathering the different bits of metadata
        studies = self.get_ena_studies(ena_collection_id)
        for st in studies:
            study_id = st["studyCOPOMetadata"]["id"]

            # refactor for studySamples
            # study_samples = self.refactor_ena_study_samples(ena_collection_id, study_id)
            # EnaCollections.update({"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id}, {
            #     '$set': {"studies.$.study.studySamples": study_samples}})

            # refactor for assays
            study_assay = self.refactor_ena_study_assays(ena_collection_id, study_id)
            EnaCollections.update({"_id": ObjectId(ena_collection_id), "studies.studyCOPOMetadata.id": study_id}, {
                '$set': {"studies.$.study.assays": study_assay}})

        status = "success"
        return status

    def refactor_ena_study_samples(self, ena_collection_id, study_id):
        normalised_ranked_list = self.get_normalised_ranked_list([],
                                                                 DataSchemas("ENA").get_ui_template()[
                                                                     "studies"]["study"][
                                                                     "studySamples"])

        study_samples = []
        samples = self.get_study_samples(ena_collection_id, study_id)

        if samples:
            for sd in samples:
                sample_id = sd["id"]
                sample_details = self.get_ena_sample(ena_collection_id, sample_id)
                if sample_details:
                    study_sample = []
                    modified_ranked_list = self.get_modified_ranked_list(normalised_ranked_list)
                    for elem_dict in modified_ranked_list:
                        entry_dict = elem_dict
                        # get target values from sample_details and delete irrelevant entries in "entry_dict"
                        # also sort out "items" if entries exist for them
                        if entry_dict["ref"] in sample_details:
                            entry_dict["value"] = sample_details[entry_dict["ref"]]
                        structure = ""
                        if entry_dict["items"]:
                            # it might well be an "all for one, one for all" arrangement here...
                            # i.e., structure for a single entry under "items" suffices for the rest
                            structure = entry_dict["items"][0]["structure"].replace(" ", "").lower()
                        # now safe to delete redundant keys from entry_dict
                        del entry_dict["ref"]
                        del entry_dict["items"]
                        study_sample.append(entry_dict)

                        # another entry, this time for "items", that is, if exist!
                        if structure and structure in sample_details:
                            entry_dict = d_utils.get_isajson_refactor_type(structure)
                            entry_dict["items"] = sample_details[structure]
                            study_sample.append(entry_dict)
                    study_samples.append(study_sample)

        return study_samples

    def refactor_ena_study_assays(self, ena_collection_id, study_id):
        study_assay = d_utils.get_db_template("ENA")['studies'][0]['study']['assays'][0]

        # get study type to determine the context to represent
        study_type = self.get_ena_study(study_id, ena_collection_id)["studyCOPOMetadata"]["studyType"]

        normalised_ranked_list = self.get_normalised_ranked_list([],
                                                                 DataSchemas("ENA").get_ui_template()[
                                                                     "studies"]["study"][
                                                                     "assays"]["assaysTable"][study_type])
        assays_table = []
        datafiles = self.get_study_datafiles(ena_collection_id, study_id)

        if datafiles:
            for df in datafiles:
                # get samples, every sample attached to a file will also have an entry in assaysTables
                if df["samples"]:
                    for sample_id in df["samples"]:
                        sample_details = self.get_ena_sample(ena_collection_id, sample_id)
                        if sample_details:
                            temp_dict = sample_details

                            # sort out data file
                            temp_dict["rawDataFile"] = ChunkedUpload.objects.get(id=int(df["fileId"])).file.name

                            # sort out elements captured under attributes
                            temp_dict["attributes"] = df["attributes"]

                            # now start making entries
                            assay = []
                            modified_ranked_list = self.get_modified_ranked_list(normalised_ranked_list)
                            for elem_dict in modified_ranked_list:
                                entry_dict = elem_dict
                                if entry_dict["ref"] in temp_dict:
                                    entry_dict["value"] = temp_dict[entry_dict["ref"]]

                                items = entry_dict["items"]
                                # remove redundant fields
                                del entry_dict["ref"]
                                del entry_dict["items"]
                                assay.append(entry_dict)

                                if items:
                                    # spin off another entry_dict to cater for these items

                                    # it might well be an "all for one, one for all" arrangement here...
                                    # i.e., structure for a single entry under "items" suffices for the rest
                                    structure = items[0]["structure"].replace(" ", "").lower()
                                    entry_dict = d_utils.get_isajson_refactor_type(structure)
                                    # delete the blank entry in items
                                    del entry_dict["items"][0]

                                    for item in items:
                                        for attribute in temp_dict["attributes"]:
                                            if attribute["question"] == item["id"]:
                                                # get the template, and sort out this entry
                                                items_entry = d_utils.get_isajson_refactor_type(structure)["items"][0]
                                                if "parameter" in structure:
                                                    items_entry["parameterTerm"] = item["term"]
                                                    items_entry["parameterValue"] = attribute["answer"]["value"]
                                                    items_entry["termAccessionNumber"] = attribute["answer"][
                                                        "termAccessionNumber"]
                                                    items_entry["termSourceREF"] = attribute["answer"]["termSourceREF"]
                                                elif "characteristics" in structure:
                                                    pass
                                                elif "factor" in structure:
                                                    pass
                                                entry_dict["items"].append(items_entry)
                                                break

                                    # del entry_dict["items"][0] # no need keeping this dummy entry
                                    assay.append(entry_dict)
                            assays_table.append(assay)
            study_assay["assaysTable"] = assays_table
        return study_assay

    def get_normalised_ranked_list(self, ranked_list, target_dict):
        # method normalises all elements in the "fields" list from all sub-documents in the target_dict,
        # and sorts them by their rank (ISA-based)
        for key, value in target_dict.items():
            if key == "fields":
                ranked_list = ranked_list + value
            else:
                ranked_list = self.get_normalised_ranked_list(ranked_list, value)
        ranked_list = sorted(ranked_list, key=lambda k: k['rank'])
        return ranked_list

    def get_modified_ranked_list(self, ranked_list):
        # this method produces a list of elements and their associated structured fields (items)

        # first, get document context by comparing bases of element's id
        d = difflib.Differ()
        context = ranked_list[0]["id"]
        for elem_dict in ranked_list[1:]:
            v = list(d.compare(context, elem_dict["id"]))
            h = ''.join(e.strip() for e in v)
            context = h.split("-")[0]
        context = context.strip(".").rsplit(".", 1)[1]

        structured_labels = ["characteristics", "factor value", "parameter value"]

        base_nodes_gap = []
        modified_ranked_list = []

        for indx, elem_dict in enumerate(ranked_list):
            # grab key elements: i.e., non-structured nodes
            element_base = elem_dict["id"].rsplit(".", 2)[1]

            if not element_base == context:  # possible target for a protocol node
                # add protocol node if not already added
                entry_dict = d_utils.get_isajson_refactor_type("protocol")
                entry_dict["value"] = re.sub("([a-z])([A-Z])", "\g<1> \g<2>", element_base).lower()
                entry_dict["ref"] = element_base
                entry_dict["items"] = []

                if entry_dict not in modified_ranked_list:
                    base_nodes_gap.append(indx)
                    modified_ranked_list.append(entry_dict)

            if elem_dict["ref"].split("[", 1)[0].lower() not in structured_labels:
                if elem_dict["ref"].split("[", 1)[0].lower() == "comment":  # handles for comment elements
                    entry_dict = d_utils.get_isajson_refactor_type("comment")
                    entry_dict["commentTerm"] = elem_dict["ref"].split("[", 1)[1].strip("]")
                elif elem_dict["control"].lower() == "file":  # handles for files
                    entry_dict = d_utils.get_isajson_refactor_type("file")
                    entry_dict["name"] = elem_dict["ref"]
                elif d_utils.get_isajson_refactor_type(
                        elem_dict["id"].rsplit(".", 1)[1].lower()):  # handles for very specific elements
                    entry_dict = d_utils.get_isajson_refactor_type(elem_dict["id"].rsplit(".", 1)[1].lower())
                    entry_dict["name"] = elem_dict["ref"]
                else:
                    entry_dict = d_utils.get_isajson_refactor_type("generic")
                    entry_dict["name"] = elem_dict["ref"]
                entry_dict["ref"] = elem_dict["id"].rsplit(".", 1)[1]
                entry_dict["items"] = []

                if entry_dict not in modified_ranked_list:
                    base_nodes_gap.append(indx)
                    modified_ranked_list.append(entry_dict)

        base_nodes_gap.append(len(ranked_list))  # will allow interval to include last element in list

        # now attach structured nodes as items to their respective "parents"
        # exploit "base_nodes_gap" to inform this process
        for indx, elem_dict in enumerate(modified_ranked_list):
            for gap in range(base_nodes_gap[indx], base_nodes_gap[indx + 1]):
                # search for and append structured items, if found, within the search "gap"
                if ranked_list[gap]["ref"].split("[", 1)[0].lower() in structured_labels:
                    elem_dict["items"].append(
                        {"id": ranked_list[gap]["id"], "structure": ranked_list[gap]["ref"].split("[", 1)[0],
                         "term": ranked_list[gap]["ref"].split("[", 1)[1].strip("]")}
                    )

        return modified_ranked_list

    # todo: need to tidy up redundant methods from this point forward (down)

    def add_study(self, values, attributes):
        spec_attr = []
        for att_group in attributes:
            tmp = {
                "tag": att_group[0],
                "value": att_group[1],
                "unit": att_group[2],
            }
            spec_attr.append(tmp)
        spec = {
            "Study_Title": values['study_title'],
            "Study_Abstract": values['study_abstract'],
            "Center_Name": values['center_name'],
            "Study_Description": values['study_description'],
            "Center_Project_Name": values['center_project_name'],
            "Study_Attributes": spec_attr,
        }
        return EnaCollections.insert(spec)

    def update_study(self, ena_study_id, values, attributes):
        spec_attr = []
        for att_group in attributes:
            tmp = {
                "tag": att_group[0],
                "value": att_group[1],
                "unit": att_group[2],
            }
            spec_attr.append(tmp)
        spec = {
            "Study_Title": values['study_title'],
            "Study_Abstract": values['study_abstract'],
            "Center_Name": values['center_name'],
            "Study_Description": values['study_description'],
            "Center_Project_Name": values['center_project_name'],
            "Study_Attributes": spec_attr,
        }
        return EnaCollections.update(
            {
                "_id": ObjectId(ena_study_id)
            },
            spec
        )

    def add_sample_to_study(self, sample, attributes, study_id):
        # create new sample and add to study

        spec_attr = []
        for att_group in attributes:
            tmp = {
                "id": ObjectId(),
                "tag": att_group[0],
                "value": att_group[1],
                "unit": att_group[2],
            }
            spec_attr.append(tmp)
        spec = {
            "_id": ObjectId(),
            "Source_Name": sample['Source_Name'],
            "Characteristics": spec_attr,
            "Term_Source_REF": "TODO:ONTOTLOGY_ID",
            "Term_Accession_Number": sample['Taxon_ID'],
            "Protocol_REF": "TODO:PROTOCOL_STRING",
            "Sample_Name": sample['Anonymized_Name'],
            "Individual_Name": sample['Individual_Name'],
            "Description": sample['Description'],
            "Taxon_ID": sample['Taxon_ID'],
            "Scientific_Name": sample['Scientific_Name'],
            "Common_Name": sample['Common_Name'],
            "Anonymized_Name": sample["Anonymized_Name"],

        }

        EnaCollections.update(
            {"_id": ObjectId(study_id)},
            {'$push':
                 {"samples": spec}
             }
        )

    def update_sample_in_study(self, sample, attributes, study_id, sample_id):
        spec_attr = []
        for att_group in attributes:
            tmp = {
                "tag": att_group[0],
                "value": att_group[1],
                "unit": att_group[2],
            }
            spec_attr.append(tmp)
        x = sample['Source_Name']
        EnaCollections.update(
            {"_id": ObjectId(study_id), "samples._id": ObjectId(sample_id)},
            {'$set': {"samples.$.Source_Name": sample['Source_Name'], "samples.$.Characteristics": spec_attr,
                      "samples.$.Term_Source_REF": "TODO:ONTOLOGY", "samples.$.Protocol_REF": "TODO:PROTOCOL_STRING",
                      "samples.$.Sample_Name": sample['Anonymized_Name'],
                      "samples.$.Individual_Name": sample['Individual_Name'],
                      "samples.$.Description": sample['Description'], "samples.$.Taxon_ID": sample['Taxon_ID'],
                      "samples.$.Scientific_Name": sample['Scientific_Name'],
                      "samples.$.Common_Name": sample['Common_Name'],
                      "samples.$.Anonymized_Name": sample["Anonymized_Name"]}}
        )

    def get_sample(self, sample_id):
        doc = EnaCollections.find_one({"samples._id": ObjectId(sample_id)}, {"samples.$": 1})
        return doc['samples'][0]

    def get_samples_in_study(self, study_id):
        doc = EnaCollections.find({"_id": ObjectId(study_id)}, {"samples": 1})
        return doc

    def add_experiment_to_study(self, per_panel, common, study_id):
        exp_id = ObjectId()
        try:
            insert_size = int(common['insert_size'])
        except:
            insert_size = 0
        spec = {
            "_id": exp_id,
            "Parameter_Value[sequencing instrument]": common['platform'] + " " + common['model'],
            "Parameter_Value[library_source]": common['lib_source'],
            "Parameter_Value[library_selection]": common['lib_selection'],
            "Parameter_Value[lib_strategy]": common['lib_strategy'],
            "Library_Name": per_panel['lib_name'],
            "panel_ordering": int(per_panel['panel_ordering']),
            "panel_id": per_panel['panel_id'],
            "data_modal_id": per_panel['data_modal_id'],
            "copo_exp_name": common['copo_exp_name'],
            "insert_size": insert_size,
            "study_id": ObjectId(common['study']),
            "sample_id": ObjectId(per_panel['sample_id']),
            "Sample_Name": per_panel['sample_name'],
            "file_type": per_panel['file_type'],
            "last_updated": str(date.today()),
        }
        EnaCollections.update(
            {"_id": ObjectId(study_id)},
            {'$push':
                 {"experiments": spec}
             }
        )
        return str(exp_id)

    def update_experiment_in_study(self, per_panel, common, study_id):
        experiment_id = per_panel['experiment_id']
        try:
            insert_size = int(common['insert_size'])
        except:
            insert_size = 0
        spec = {
            "platform": common['platform'],
            "instrument": common['model'],
            "lib_source": common['lib_source'],
            "lib_selection": common['lib_selection'],
            "lib_strategy": common['lib_strategy'],
            "panel_ordering": int(per_panel['panel_ordering']),
            "panel_id": per_panel['panel_id'],
            "data_modal_id": per_panel['data_modal_id'],
            "copo_exp_name": common['copo_exp_name'],
            "insert_size": insert_size,
            "study_id": ObjectId(common['study']),
            "sample_id": ObjectId(per_panel['sample_id']),
            "lib_name": per_panel['lib_name'],
            "file_type": per_panel['file_type'],
            "last_updated": str(date.today()),
        }
        EnaCollections.update(
            {"_id": ObjectId(study_id), "experiments._id": ObjectId(experiment_id)},
            {
                '$set': {
                    "experiments.$.Parameter_Value[sequencing instrument]": common['platform'] + " " + common['model'],
                    "experiments.$.Parameter_Value[library_source]": common['lib_source'],
                    "experiments.$.Parameter_Value[library_selection]": common['lib_selection'],
                    "experiments.$.Parameter_Value[lib_strategy]": common['lib_strategy'],
                    "experiments.$.Library_Name": per_panel['lib_name'],
                    "experiments.$.panel_ordering": int(per_panel['panel_ordering']),
                    "experiments.$.panel_id": per_panel['panel_id'],
                    "experiments.$.data_modal_id": per_panel['data_modal_id'],
                    "experiments.$.copo_exp_name": common['copo_exp_name'], "experiments.$.insert_size": insert_size,
                    "experiments.$.study_id": ObjectId(common['study']),
                    "experiments.$.study_id": ObjectId(common['study']),
                    "experiments.$.sample_id": ObjectId(per_panel['sample_id']),
                    "experiments.$.Sample_Name": per_panel['sample_name'],
                    "experiments.$.file_type": per_panel['file_type']}}
        )
        return experiment_id

    def add_file_to_study(self, study_id, experiment_id, chunked_upload_id, hash):
        _id = ObjectId()
        spec = {
            "_id": str(_id),
            "experiment_id": str(experiment_id),
            "chunked_upload_id": chunked_upload_id,
            "hash": hash,
        }
        EnaCollections.update(
            {"_id": ObjectId(study_id)},
            {"$push": {"files": spec}}
        )

    def get_experiment_by_id(self, study_id):
        return EnaCollections.find_one({"_id": ObjectId(study_id)}, {"experiments": 1, "_id": 0})

    def get_experiments_by_modal_id(self, modal_id):
        return EnaCollections.find({"experiments.data_modal_id": modal_id}, {"experiments.$": 1})

    def get_distict_experiment_ids_in_study_(self, study_id):
        return EnaCollections.find({"_id": ObjectId(study_id)}).distinct("experiments.data_modal_id")

    def get_chunked_upload_id_from_file_id(self, file_id):
        return EnaCollections.find({"experiments.files": ObjectId(file_id)}, {"experiments.files.$": 1})

    def get_files_by_experiment_id(self, experiment_id):
        return EnaCollections.aggregate([
            {"$match": {"files.experiment_id": str(experiment_id)}},
            {"$unwind": "$files"},
            {"$match": {"files.experiment_id": str(experiment_id)}},
            {"$project": {"files": 1}}
        ])

    def remove_file_from_experiment(self, file_id):
        return EnaCollections.update({"files.chunked_upload_id": int(file_id)},
                                     {"$pull": {"files": {"chunked_upload_id": int(file_id)
                                                          }}})
