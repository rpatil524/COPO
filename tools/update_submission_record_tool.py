#!/usr/bin/python

import threading
import pymongo
import numpy as np
import pdb
import time
from bson.objectid import ObjectId

MONGO_DB = 'copo_mongo'
MONGO_HOST = '127.0.0.1'
MONGO_PORT = 27017
collection_name = 'test_submisson_progress_collection'
collection = pymongo.MongoClient(MONGO_HOST, MONGO_PORT)[MONGO_DB][collection_name]
mu = 40
sigma = 4


the_ids = list()
the_ids.append(ObjectId("5739f36a68236b8ca9e54011"))
the_ids.append(ObjectId("573c96df68236bd7a2ba132b"))
the_ids.append(ObjectId("573dd99568236b09876bb411"))
the_ids.append(ObjectId("573ef76968236b2e3909779b"))
the_ids.append(ObjectId("5745851468236ba373c72914"))



loops = 50000



def update_submission_record():
    print('starting thread')

    x = 0


    for idx, i in enumerate(the_ids):
        collection.remove({'sub_id': i})
        collection.insert(
            {
                'sub_id': i,
                'complete': idx * 25,
                'speeds': []
            }
        )


    while x < loops:
        for idx, i in enumerate(the_ids):
            collection.update(
                {'sub_id': i},
                {
                    '$push': {'speeds': np.cos(x) * idx + 1}, # make sine wave for each collection, increasing in both amplitude and frequency
                    '$set': {'complete': float(x * idx + 1)/2 % 100}
                }
                )


        time.sleep(1.0/2.0)
        print('loop: ' + str(x))
        x = x + 1


update_submission_record()

#t = threading.Thread(target=update_submission_record)
#t.daemon = True
#t.start()
#print('threads submitted')
