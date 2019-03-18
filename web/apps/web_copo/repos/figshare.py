__author__ = 'felix.shaw@tgac.ac.uk - 29/04/15'

import json
from urllib.parse import parse_qs

import requests
from requests_oauthlib import OAuth1, OAuth1Session
from django.urls import reverse
from os import path
import shutil
from web.apps.web_copo.schemas.utils import data_utils
from django.http import HttpResponse
import jsonpickle
from django.conf import settings

client = requests.session()
json_header = {'content-type': 'application/json'}
client_key = 'id6JBVVeItadGDmjRUDljg'
client_secret = 'BC2tEMeCAT3veHhzfd2xIA'
resource_owner_key = ''
resource_owner_secret = ''
tokens = None


def retrieve_token():
    # get token
    tokens = Figshare_token().get_token_from_db()
    resource_owner_key = tokens['owner_key']
    resource_owner_secret = tokens['owner_secret']
    token_object = OAuth1(client_key,
                    client_secret=client_secret,
                    resource_owner_key=resource_owner_key,
                    resource_owner_secret=resource_owner_secret,
                    signature_type='auth_header')
    return token_object

# submit to figshare
def submit_to_figshare(article_id):
    try:
        token_object = retrieve_token()
        collection = FigshareCollection().get_collection_head_from_article(article_id)
        article = FigshareCollection().get_article(article_id)
        request = data_utils.get_current_request()
        # get file path
        p = path.join(article['path'], article['hashed_name'])
        new_name = path.join(settings['MEDIA_ROOT'], article['original_name'])
        shutil.copyfile(p, new_name)
        # make article on figshare
        figshare_article = make_article(name=collection['name'], description=article['description'], type=article['article_type'], oauth=token_object)
        figshare_article_id = figshare_article['article_id']
        FigshareCollection().add_figshare_accession_to_article(figshare_id=figshare_article_id, article_id=article_id)
        FigshareCollection().add_figshare_url_to_article(figshare_id=figshare_article_id, article_id=article_id)
        add_file_to_article(oauth=token_object, article_id=figshare_article_id, filename=new_name)
        for tag in article['tags']:
            add_tags_to_article(oauth=token_object, article_id=figshare_article_id, tag=tag)
    except RuntimeError as e:
        print(e)
        return None
    return figshare_article_id

def delete_from_figshare(article_id):
    try:
        figshare_id = FigshareCollection().get_figshare_id(article_id)
        token_object = retrieve_token()
        delete_article(oauth=token_object, article_id=figshare_id["figshare_accession"])
    except:
        return False
    return True

def submit_to_figshare_v2():
    pass

# figshare API methods
def make_article(name, description, type, oauth=None):
    url = 'http://api.figshare.com/v1/my_data/articles'
    body = {'title': name, 'description': description, 'defined_type': type}
    response = client.post(url, auth=oauth, data=json.dumps(body), headers=json_header)
    return json.loads(response.content.decode("utf-8"))


def delete_article(oauth=None, article_id=0):
    response = client.delete('http://api.figshare.com/v1/my_data/articles/' + str(article_id), auth=oauth)
    return json.loads(response.content.decode("utf-8"))

def get_my_articles(oauth=None):
    url = 'http://api.figshare.com/v1/my_data/articles'
    response = client.get(url, auth=oauth, headers=json_header)
    return json.loads(response.content.decode("utf-8"))


def add_file_to_article(oauth=None, article_id=0, filename=''):
    url = 'http://api.figshare.com/v1/my_data/articles/' + str(article_id) + '/files'
    files = {'filedata': (filename, open(filename, 'rb'))}
    response = client.put(url, auth=oauth, files=files)
    return json.loads(response.content.decode("utf-8"))


def add_tags_to_article(oauth=None, article_id=0, tag=''):
    tag = {'tag_name': tag}
    response = client.put('http://api.figshare.com/v1/my_data/articles/' + str(article_id) + '/tags', auth=oauth,
                          data=json.dumps(tag), headers=json_header)
    return json.loads(response.content.decode("utf-8"))

# Figshare OAUTH methods
def check_figshare_credentials(request):
    # this method called from JS frontend - if credentials exist, set a session variable containing
    # the oauth object and return true. If credentials don't exist, send redirect URL to frontend and return false
    if (Figshare_token().token_exists()):

        #else retrieve saved tokens and validate
        tokens = Figshare_token().get_token_from_db()
        if(not valid_tokens(tokens)):
            Figshare_token().delete_old_token()
            tokens = get_authorize_url()
        out = {'exists': True}
    else:
        #if no token exists in the database
        out = {}
        out['exists'] = False
        out['url'] = get_authorize_url()

    return HttpResponse(jsonpickle.encode(out))




def set_figshare_credentials(request):
    # call backend method to get and save access token to dal
    get_access_token(request)
    return HttpResponse('<script>window.top.close();</script>')


def get_authorize_url():

    request_token_url = 'http://api.figshare.com/v1/pbl/oauth/request_token'
    authorization_url = 'http://api.figshare.com/v1/pbl/oauth/authorize'

    #Obtain request token
    request = data_utils.get_current_request()
    domain = request.META['HTTP_HOST']
    callback_uri = 'http://' + domain + reverse('rest:set_figshare_credentials')
    oauth = OAuth1Session(client_key, client_secret=client_secret, callback_uri=callback_uri)
    fetch_response = oauth.fetch_request_token(request_token_url)
    request.session['resource_owner_key'] = fetch_response.get('oauth_token')
    request.session['resource_owner_secret'] = fetch_response.get('oauth_token_secret')

    #Obtain Authorize Token
    authorize_url = authorization_url + '?oauth_token='
    authorize_url = authorize_url + request.session['resource_owner_key']

    #redirect user to auth page
    return authorize_url


def get_access_token(request):

    access_token_url = 'http://api.figshare.com/v1/pbl/oauth/access_token'

    redirect_response = request.get_full_path()
    oauth = OAuth1Session(client_key, client_secret=client_secret)
    oauth_response = oauth.parse_authorization_response(redirect_response)
    verifier = oauth_response.get('oauth_verifier')

    #Obtain Access Token
    oauth = OAuth1(client_key,
                   client_secret=client_secret,
                   resource_owner_key=request.session['resource_owner_key'],
                   resource_owner_secret=request.session['resource_owner_secret'],
                   verifier=verifier)

    r = requests.post(url=access_token_url, auth=oauth)
    credentials = parse_qs(r.content)
    tokens = {}
    tokens['owner_key'] = credentials[b'oauth_token'][0].decode("utf-8")
    tokens['owner_secret'] = credentials[b'oauth_token_secret'][0].decode("utf-8")
    Figshare_token().add_token(owner_key=tokens['owner_key'], owner_secret=tokens['owner_secret'])
    return tokens


def valid_tokens(tokens):

    oauth = OAuth1(client_key,
                  client_secret=client_secret,
                  resource_owner_key=tokens['owner_key'],
                  resource_owner_secret=tokens['owner_secret'],
                  signature_type='auth_header')
    url = 'http://api.figshare.com/v1/my_data/articles'
    client = requests.session()
    json_header = {'content-type': 'application/json'}
    response = client.get(url, auth=oauth, headers=json_header)
    if(response.status_code == 401):
        # probably invalid token
        return False
    return True

