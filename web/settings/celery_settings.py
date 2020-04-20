# settings for celery
from .data import SESSION_REDIS_HOST, SESSION_REDIS_PORT

# celery settings
CELERY_BROKER_URL = f'redis://{SESSION_REDIS_HOST}:{SESSION_REDIS_PORT}'
CELERY_RESULT_BACKEND = f'redis://{SESSION_REDIS_HOST}:{SESSION_REDIS_PORT}'
#CELERY_BROKER_URL = 'amqp://fshaw:Apple123@127.0.0.1:5672/copo'
#CELERY_RESULT_BACKEND = 'pyamqp://'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 50000

CELERY_BIN = '/home/fshaw/Documents/environments/copo_conda1/bin/python -m celery'