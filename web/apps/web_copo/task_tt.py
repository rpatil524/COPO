import datetime
from time import sleep
from django.conf import settings
from web.apps.web_copo.lookup.copo_enums import Loglvl, Logtype

lg = settings.LOGGER


def task1(group_name):
    sleep(5)

    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()

    message = 'Celery task you are soooo sweeto: ' + str(datetime.datetime.now().time())

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'chat_message',
            'message': message
        }
    )

    lg.log(message, level=Loglvl.INFO, type=Logtype.FILE)

    return True


def task2():
    lg.log("Updating ENA status", level=Loglvl.INFO, type=Logtype.FILE)

    return True
