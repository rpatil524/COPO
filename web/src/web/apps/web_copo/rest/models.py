import os.path
from chunked_upload.models import ChunkedUpload
from django.conf import settings
from django_tools.middlewares import ThreadLocal
import datetime

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def generate_filename2(instance, filename):
    partition = datetime.datetime.now().strftime("%H_%M_%S_%f")
    filename = os.path.join(settings.UPLOAD_PATH, str(ThreadLocal.get_current_user().id), partition, instance.filename)
    return filename


class CopoChunkedUpload(ChunkedUpload):
    pass


# Override the default filename
CopoChunkedUpload._meta.get_field('file').upload_to = generate_filename2