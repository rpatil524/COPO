# settings for services e.g. postgres, mongo, redis, irods...

import os

# settings for postgres
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ['POSTGRES_DB'],
        'USER': os.environ['POSTGRES_USER'],
        'PASSWORD': os.environ['POSTGRES_PASSWORD'],
        'HOST': os.environ['POSTGRES_SERVICE'],
        'PORT': os.environ['POSTGRES_PORT']
    }
}

# settings for mongodb
MONGO_DB = os.environ['MONGO_DB']
MONGO_HOST = os.environ['MONGO_HOST']
MONGO_USER = os.environ['MONGO_USER']
MONGO_USER_PASSWORD = os.environ['MONGO_USER_PASSWORD']
MONGO_PORT = int(os.environ['MONGO_PORT'])

# settings for redis
SESSION_ENGINE = 'redis_sessions.session'
SESSION_REDIS_HOST = os.environ['REDIS_HOST']
SESSION_REDIS_PORT = int(os.environ['REDIS_PORT'])

# settings for figshare
FIGSHARE_CREDENTIALS = {
    'client_id': os.environ['FIGSHARE_CLIENT_ID'],
    'consumer_secret': os.environ['FIGSHARE_CONSUMER_SECRET'],
    'client_secret': os.environ['FIGSHARE_CLIENT_SECRET']
}
