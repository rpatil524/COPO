__author__ = 'felix.shaw@tgac.ac.uk - 03/05/2016'
import json
import requests
import os
from web.apps.web_copo.lookup.lookup import FIGSHARE_API_URLS
from chunked_upload.models import ChunkedUpload
from django.conf import settings
from dal.copo_da import DataFile, Submission
import threading
import datetime
from dal.copo_da import RemoteDataFile
from dal.figshare_da import Figshare
from django_tools.middlewares import ThreadLocal


class FigshareSubmit(object):

    def submit(self, sub_id, dataFile_ids, token):
        t = threading.Thread(target=self._submit(sub_id=sub_id, dataFile_ids=dataFile_ids, token=token))
        t.daemon = True
        t.start()

    def _submit(self, sub_id, dataFile_ids, token):

        Submission().mark_submission_commencing(sub_id)

        BASE_URL = FIGSHARE_API_URLS['base_url']
        TOKEN = token
        HEADERS = {'Authorization': 'token ' + TOKEN}
        MEDIA_ROOT = settings.MEDIA_ROOT
        transfer_token = RemoteDataFile().create_transfer(sub_id)['_id']

        for f_id in dataFile_ids:

            mongo_file = DataFile().GET(f_id)

            c = ChunkedUpload.objects.get(pk=int(mongo_file["file_id"]))

            file_path = os.path.join(MEDIA_ROOT, str(c.file))
            orig_name = c.filename

            sub = mongo_file['description']['attributes']
            data = dict()
            data['defined_type'] = sub.get('figshare_type', dict()).get('article_type')
            data['title'] = sub.get('figshare_title', dict()).get('article_title')
            authors = sub.get('figshare_authors', dict()).get('article_author').split(',')
            lst = list()
            for x in authors:
                lst.append({'name': x})
            data['authors'] = lst
            data['description'] = sub.get('figshare_description', dict()).get('article_description')
            cat = sub.get('figshare_categories', dict()).get('article_categories')
            cat = cat.split(',')
            cat = list(map(int, cat))
            data['categories'] = cat
            data['tags'] = sub.get('figshare_tags', dict()).get('article_keywords').split(',')
            data['references'] = sub.get('figshare_references', dict()).get('article_references').split(',')
            for idx, x in enumerate(data['references']):
                if (not x.startswith('http')) or (not x.startswith('https')):
                    data['references'][idx] = 'http://' + x
            data['funding'] = sub.get('figshare_grant', dict()).get('article_funding')
            data['licenses'] = sub.get('figshare_licenses', dict()).get('article_licenses')
            data['publish'] = sub.get('figshare_publish', dict()).get('should_publish')


            # Create article
            #data = json.dumps({'title': orig_name, 'defined_type': 'figure'})
            endpoint = 'account/articles'
            resp = requests.post(BASE_URL.format(endpoint=endpoint), headers=HEADERS, data=json.dumps(data))

            article_id = json.loads(resp.content.decode('utf8'))['location'].rsplit('/', 1)[1]

            # Get file info
            #with open(file_path, 'rb') as fin:
            #    fin.seek(0, 2)  # Go to end of file
            #    size = fin.tell()
            size = c.offset
            data = json.dumps({'name': orig_name, 'size': size })

            # Initiate upload
            endpoint = 'account/articles/{}/files'.format(article_id)
            resp = requests.post(BASE_URL.format(endpoint=endpoint), headers=HEADERS, data=data)

            file_id = json.loads(resp.content.decode('utf-8'))['location'].rsplit('/', 1)[1]

            # Get upload/parts info
            endpoint = 'account/articles/{}/files/{}'.format(article_id, file_id)
            resp = requests.get(BASE_URL.format(endpoint=endpoint), headers=HEADERS)

            url = '{upload_url}'.format(**json.loads(resp.content.decode('utf-8')))
            parts = json.loads(requests.get(url).content.decode('utf-8'))['parts']


            # start upload timer
            t = datetime.datetime.now()

            # Upload parts
            with open(file_path, 'rb') as fin:
                for idx, part in enumerate(parts):

                    percent_done = idx / len(parts) * 100
                    size = part['endOffset'] - part['startOffset'] + 1

                    address = '{}/{}'.format(url, part['partNo'])
                    x = datetime.datetime.now()
                    requests.put(address, data=fin.read(size))
                    delta = datetime.datetime.now() - x
                    # calculate current upload rate in MB per second
                    bw = (size / delta.total_seconds()) / 1000 / 1000
                    fields = {'transfer_rate': bw, 'pct_completed': percent_done}
                    RemoteDataFile().update_transfer(transfer_token, fields)

            # Mark file upload as completed
            upload_time = datetime.datetime.now() - t
            requests.post(BASE_URL.format(endpoint=endpoint), headers=HEADERS)

            fields = {'pct_completed': 100, 'transfer_status': 'success', 'completed_on':str(datetime.datetime.now()), 'article_id': article_id}
            RemoteDataFile().update_transfer(transfer_token, fields)

        # mark submission as complete
        Submission().mark_submission_complete(sub_id)


    def isValidCredentials(self, user_id):

        # check if token exists for user
        token = Figshare().get_token_for_user(user_id=ThreadLocal.get_current_user().id)
        if token:
            # now check if token works
            headers = {'Authorization': 'token ' + token['token']}
            r = requests.get('https://api.figshare.com/v2/account/articles', headers=headers)
            if r.status_code == 200:
                return True
            else:
                # we have an invalid token stored, so we should delete it and prompt the user for a new one
                Figshare().delete_tokens_for_user(user_id=user_id)
        return False





