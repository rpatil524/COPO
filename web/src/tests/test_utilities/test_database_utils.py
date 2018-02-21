# Created by fshaw at 05/02/2018
from django.conf import settings
import json
import os

class Utils:

    def __init__(self):
        # GetDB - simple function to wrap getting a database
        # connection from the connection pool.
        self.db = settings.MONGO_CLIENT

    def get_pymongo_db(self):
        return self.db

    def get_ena_fixtures_json(self, file_location):
        with open(file_location) as json_data:
            d = json.load(json_data)
            return d

    def load_ena_fixtures(self, file_location):
        # load test data from json file

        # TODO - MongoIDs here are wrong. Either enter MongoIDs as static or return each new ID as the data is entered
        with open(file_location) as json_data:
            d = json.load(json_data)

            profile_id = self.db.Profiles.insert_one(d['profile']).inserted_id
            source = d['source']
            source['profile_id'] = str(profile_id)
            source_id = self.db.SourceCollection.insert_one(source).inserted_id
            samples = d['sample']
            for s in samples:
                s['derivesFrom'] = list()
                s['derivesFrom'].append(str(source_id))
                s['profile_id'] = str(profile_id)
            sample_ids = self.db.SampleCollection.insert_many(samples).inserted_ids
            self.db.DescriptionCollection.insert_one(d['description'])

            files = d['file']
            for idx, f in enumerate(files):
                f['profile_id'] = str(profile_id)
                f['description']['attributes']['attach_samples']['study_samples'] = str(sample_ids[idx])
                loc = os.path.join(settings.BASE_DIR, 'tests', 'test_data', 'small' + str(idx + 1) + '.fastq.gz')
                f['file_location'] = loc
            file_ids = self.db.DataFileCollection.insert_many(files).inserted_ids
            self.db.PersonCollection.insert_one(d['person'])

            submission = d['submission']
            submission['profile_id'] = str(profile_id)
            for idx, f in enumerate(files):
                submission['bundle'].append(str(file_ids[idx]))
                meta = dict()
                meta['file_id'] = str(file_ids[idx])
                meta['file_path'] = str(f['file_location'])
                meta['upload_status'] = False
                submission['bundle_meta'].append(meta)
            sub_id = self.db.SubmissionCollection.insert_one(submission).inserted_id

            return str(sub_id), str(profile_id)
