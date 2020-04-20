# settings for celery
from .data import SESSION_REDIS_HOST, SESSION_REDIS_PORT

# celery settings
CELERY_BROKER_URL = f'redis://{SESSION_REDIS_HOST}:{SESSION_REDIS_PORT}'
CELERY_RESULT_BACKEND = f'redis://{SESSION_REDIS_HOST}:{SESSION_REDIS_PORT}'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

#CELERY_LOGFILE='/usr/users/TSL_20/minottoa/suptest/supervisord.log'
#CELERY_PIDFILE='/usr/users/TSL_20/minottoa/suptest/supervisord.pid'

#CELERY_STDOUT_LOGFILE='/usr/users/TSL_20/minottoa/suptest/celery.log'
#stdout_logfile='/usr/users/TSL_20/minottoa/suptest/celerybeat.log'
