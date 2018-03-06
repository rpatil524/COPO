__author__ = 'felix.shaw@tgac.ac.uk - 31/03/2016'

import pdb
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
import web.apps.web_copo.views as v
from dal.copo_da import Profile
from dal.copo_da import Publication, Person, Source, Sample
from dal.mongo_util import get_mongo_client, to_django_context
import json
from converters.copo2json import Copo2Json
from web.apps.web_copo.schemas.utils.data_utils import pretty_print


class CopoViewsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='test_user', email='test_user@copo.com', password='password')
        self.client = Client()
        self.client.login(username='test_user', password='password')
        self.profile_id = None

    def test_index(self):
        response = self.client.get(reverse('copo:index'))
        self.assertEqual(response.status_code, 200, 'Index page didn\'t load properly.')

    def test_ena_workflow(self):
        self.profile_tests()
        self.samples_test()
        self.publications_tests()
        self.people_tests()
        self.file_tests()
        self.json_transform_tests()
        self.transfer_tests()

    def profile_tests(self):
        data = {'study_abstract': 'test abstract', 'study_title': 'test title'}
        response = self.client.post(reverse('copo:new_profile'), data, follow=True)
        plist = Profile().get_for_user(self.user.id)
        self.assertEqual(plist.count(), 1, 'Wrong number of Profiles detected, should be one.')
        p = plist[0]

        self.profile_id = p['_id']
        self.assertNotEqual(p['copo_id'], '0000000000000',
                            'COPO ID not produced, are you able to ping the ID issuing server?')
        self.assertEqual(response.status_code, 200, 'Page not rendered correctly.')
        self.assertTemplateUsed(response, 'copo/landing_page.html',
                                'Correct Template not used, should have returned to index page.')

    def publications_tests(self):
        auto_fields = {
            "copo.publication.title": "Test Title",
            "copo.publication.authorList": "Author1 T1,Author2 T2,Author3 T3", "": "",
            "copo.publication.doi": "12345", "copo.publication.pubMedID": "12345",
            "copo.publication.status.annotationValue": "PubMed - indexed for MEDLINE",
            "copo.publication.status.termSource": "xyz", "copo.publication.status.termAccession": "xyz",
            "copo.publication.created_on": "01:01:2000", "copo.publication.comments": "no comments"}
        auto_fields = json.dumps(auto_fields)
        task = 'save'
        # set session variable
        s = self.client.session
        s['profile_id'] = str(self.profile_id)
        s.save()
        # call view
        response = self.client.post(reverse('copo:edit_publication'),
                                    {'auto_fields': auto_fields, 'task': task})
        # check responses
        plist = Publication(self.profile_id).get_all_pubs_in_profile()
        self.assertEqual(plist.count(), 1, 'Wrong number of Publications found, should be one.')
        self.assertEqual(response.status_code, 200, 'Publications test failed to return status 200.')

    def people_tests(self):
        auto_fields = {"copo.person.lastName": "Copo", "copo.person.firstName": "Test", "copo.person.midInitials": "T",
                       "copo.person.email": "test.email@tgac.ac.uk", "copo.person.phone": "01603440000",
                       "copo.person.fax": "01603440001",
                       "copo.person.address": "The Genome Analysis Centre, Norwich, Norfolk, NR4 7UH",
                       "copo.person.affiliation": "TGAC", "copo.person.roles.annotationValue": "investigator",
                       "copo.person.roles.termSource": "http://www.ebi.ac.uk/efo/EFO_0001739",
                       "copo.person.roles.termAccession": "efo:http://www.ebi.ac.uk/efo/EFO_0001739",
                       "copo.person.comments": "no comment", "copo.person.created_on": ""}
        auto_fields = json.dumps(auto_fields)
        task = 'save'
        # set session variable
        s = self.client.session
        s['profile_id'] = str(self.profile_id)
        s.save()
        # call view
        response = self.client.post(reverse('copo:edit_person'), {'auto_fields': auto_fields, 'task': task})
        # check that object was created
        people = Person(str(self.profile_id)).get_all_people()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(people), 1)

    def samples_test(self):
        task = 'save'

        auto_fields = json.dumps({"copo.source.name": "dog001", "copo.source.organism.annotationValue": "dog",
                                  "copo.source.organism.termSource": "http://purl.obolibrary.org/obo/NCBITaxon_9615",
                                  "copo.source.organism.termAccession": "mro:http://purl.obolibrary.org/obo/NCBITaxon_9615",
                                  "category_annotationValue_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "age",
                                  "category_termAccession_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "",
                                  "category_termSource_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "",
                                  "value_annotationValue_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "4",
                                  "value_termAccession_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "",
                                  "value_termSource_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "",
                                  "unit_annotationValue_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "year",
                                  "unit_termAccession_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "",
                                  "unit_termSource_copo.source.characteristics_4f8b886d-0570-470e-bd94-1f782b6781af": "",
                                  "": "", "copo.sample.name": "blood1", "copo.sample.source_id": "",
                                  "category_annotationValue_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "bloodtype",
                                  "category_termAccession_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "",
                                  "category_termSource_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "",
                                  "value_annotationValue_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "O+",
                                  "value_termAccession_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "",
                                  "value_termSource_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "",
                                  "unit_annotationValue_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "blood",
                                  "unit_termAccession_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "",
                                  "unit_termSource_copo.sample.characteristic_0827e05d-96a8-4d96-a5b2-9a9606b6cff1": "",
                                  "category_annotationValue_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": "control",
                                  "category_termAccession_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": "",
                                  "category_termSource_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": "",
                                  "value_annotationValue_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": "true",
                                  "value_termAccession_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": "",
                                  "value_termSource_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": "",
                                  "unit_annotationValue_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": "true",
                                  "unit_termAccession_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": "",
                                  "unit_termSource_copo.sample.factor_a648d2f2-dcca-48e4-9e47-9d3763938c69": ""})

        # auto_fields = json.dumps({"copo.source.name": 'xyz'})
        s = self.client.session
        s['profile_id'] = str(self.profile_id)
        s.save()

        response = self.client.post(reverse('copo:edit_sample'), {'auto_fields': auto_fields, 'task': task})
        source_data = Source(profile_id=str(self.profile_id)).get_all_sources()
        sample_data = Sample(profile_id=str(self.profile_id)).get_all_samples()
        pretty_print(source_data)
        print('\/\/\/\/\/\/\/')
        pretty_print(sample_data)
        self.assertEqual(1, 1)

    def file_tests(self):
        # tests for file uploading and metadata labelling
        self.assertEqual(1, 1)

    def json_transform_tests(self):
        frag = Copo2Json(str(self.profile_id)).convert()
        f = open('/Users/fshaw/Desktop/test.json', 'w+')
        f.write(json.dumps(frag, sort_keys=True, indent=4, separators=(',', ': ')))
        f.close()

    def transfer_tests(self):
        # tests for aspera transfer to ENA
        self.assertEqual(1, 1)

    def tearDown(self):
        db = get_mongo_client()
        db.drop_database('copo_mongo_test')
