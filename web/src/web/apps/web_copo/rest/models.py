import time
import os.path
from chunked_upload.models import ChunkedUpload
from django.conf import settings
from web.apps.web_copo.schemas.utils import data_utils
import datetime


def generate_filename2(instance, filename):
    partition = datetime.datetime.now().strftime("%H_%M_%S_%f")
    filename = os.path.join(settings.UPLOAD_PATH, str(data_utils.get_current_user().id), partition, instance.filename)
    return filename



class CopoChunkedUpload(ChunkedUpload):
    pass

# Override the default filename
CopoChunkedUpload._meta.get_field('file').upload_to = generate_filename2