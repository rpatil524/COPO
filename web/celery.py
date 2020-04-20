from __future__ import absolute_import, unicode_literals

import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings.all')

app = Celery('web')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# define periodic tasks here

app.conf.beat_schedule = {
    'update_ena_status': {
        'task': 'web.apps.web_copo.tasks.process_ena_submission',
        'schedule': timedelta(seconds=5) #crontab(minute="*/1")  # execute every n minutes minute="*/n"
    }
}


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
