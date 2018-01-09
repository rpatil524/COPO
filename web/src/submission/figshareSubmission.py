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
from dal.figshare_da import Figshare


class FigshareSubmit(object):


    def __init__(self, sub_id):
        self.BASE_URL = FIGSHARE_API_URLS['base_url']
        request = ThreadLocal.get_current_request()
        self.TOKEN = Figshare().get_token_for_user(request.user.id)['token']
        self.HEADERS = {'Authorization': 'token ' + self.TOKEN}
        self.MEDIA_ROOT = settings.MEDIA_ROOT
        self.transfer_token = RemoteDataFile().create_transfer(sub_id)['_id']

    def submit(self, sub_id, dataFile_ids):
        t = threading.Thread(target=self._submit(sub_id=sub_id, dataFile_ids=dataFile_ids))
        t.daemon = True
        t.start()

    def _submit(self, sub_id, dataFile_ids):

        for f_id in dataFile_ids:

            mongo_file = DataFile().get_record(f_id)

            c = ChunkedUpload.objects.get(pk=int(mongo_file["file_id"]))

            file_path = os.path.join(self.MEDIA_ROOT, str(c.file))
            orig_name = c.filename

            sub = mongo_file['description']['attributes']
            data = dict()
            data['defined_type'] = sub.get('type_category', dict()).get('type')
            data['title'] = sub.get('title_author_description', dict()).get('title')
            authors = sub.get('title_author_description', dict()).get('author').split(',')
            lst = list()
            for x in authors:
                lst.append({'name': x})
            data['authors'] = lst
            data['description'] = sub.get('title_author_description', dict()).get('description')
            cat = sub.get('type_category', dict()).get('categories')
            if cat:
                cat = cat.split(',')
                cat = list(map(int, cat))
                data['categories'] = cat
            else:
                data['categories'] = list()
            data['tags'] = sub.get('tags', dict()).get('keywords').split(',')
            for idx, t in enumerate(data['tags']):
                if len(t) < 3:
                    if len(t) == 1:
                        t = t + (2 * t)
                    elif len(t) == 2:
                        t = t + t
                    data['tags'][idx] = t

            data['references'] = sub.get('tags', dict()).get('references').split(',')
            for idx, x in enumerate(data['references']):
                if x != '':
                    if (not x.startswith('http')) or (not x.startswith('https')):
                        if (not x.startswith('www')):
                            data['references'][idx] = 'http://www.' + x
                        else:
                            data['references'][idx] = 'http://' + x
            if len(data['references']) == 1 and data['references'][0] == '':
                # if blank ref, pop
                data.pop('references')
            data['funding'] = sub.get('tags', dict()).get('funding')
            data['licenses'] = sub.get('tags', dict()).get('licenses')
            data['publish'] = sub.get('figshare_publish', dict()).get('should_publish')


            # Create article
            #data = json.dumps({'title': orig_name, 'defined_type': 'figure'})
            endpoint = 'account/articles'
            resp = requests.post(self.BASE_URL.format(endpoint=endpoint), headers=self.HEADERS, data=json.dumps(data))

            article_id = json.loads(resp.content.decode('utf8'))['location'].rsplit('/', 1)[1]

            # Get file info
            #with open(file_path, 'rb') as fin:
            #    fin.seek(0, 2)  # Go to end of file
            #    size = fin.tell()
            size = c.offset
            info = json.dumps({'name': orig_name, 'size': size })

            # Initiate upload
            endpoint = 'account/articles/{}/files'.format(article_id)
            resp = requests.post(self.BASE_URL.format(endpoint=endpoint), headers=self.HEADERS, data=info)

            file_id = json.loads(resp.content.decode('utf-8'))['location'].rsplit('/', 1)[1]

            # Get upload/parts info
            endpoint = 'account/articles/{}/files/{}'.format(article_id, file_id)
            resp = requests.get(self.BASE_URL.format(endpoint=endpoint), headers=self.HEADERS)

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
                    RemoteDataFile().update_transfer(self.transfer_token, fields)

            # Mark file upload as completed
            upload_time = datetime.datetime.now() - t
            requests.post(self.BASE_URL.format(endpoint=endpoint), headers=self.HEADERS)

            fields = {'pct_completed': 100, 'transfer_status': 'success', 'completed_on':str(datetime.datetime.now()), 'article_id': article_id}
            RemoteDataFile().update_transfer(self.transfer_token, fields)

            if data['publish'] == 'True':
                # publish api
                endpoint = 'account/articles/{}/publish'.format(article_id)
                resp = requests.post(self.BASE_URL.format(endpoint=endpoint), headers=self.HEADERS)
                location = json.loads(resp.content.decode('utf8'))['location']
                # get accession data
                endpoint = 'articles/{}'.format(article_id)
                resp = requests.get(self.BASE_URL.format(endpoint=endpoint), headers=self.HEADERS)
                # save accessions to mongo profile record
                s = Submission().get_record(sub_id)
                s['article_id'] = json.loads(resp.content.decode('utf8'))['figshare_url']
                s['complete'] = True
                s['status'] = 'published'
                s['target_id'] = str(s.pop('_id'))
                Submission().save_record(dict(), **s)
            else:
                # save accessions to mongo profile record
                s = Submission().get_record(sub_id)
                s['article_id'] = article_id
                s['complete'] = True
                s['status'] = 'not published'
                s['target_id'] = str(s.pop('_id'))
                Submission().save_record(dict(), **s)


        # mark submission as complete
        Submission().mark_submission_complete(sub_id, article_id=article_id)
        Submission().mark_submission_complete(sub_id)
        Submission().mark_figshare_article_id(sub_id=sub_id, article_id=article_id)


    def publish_article(self, article_id):
        endpoint = 'account/articles/{}/publish'.format(article_id)
        post = self.BASE_URL.format(endpoint=endpoint)
        resp = requests.post(post, headers=self.HEADERS)
        if resp.status_code == 200 or resp.status_code == 201:
            Submission().mark_figshare_article_published(article_id)
        return resp


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





