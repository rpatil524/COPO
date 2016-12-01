import time
import os.path
from chunked_upload.models import ChunkedUpload
from chunked_upload.settings import UPLOAD_PATH
from django_tools.middlewares import ThreadLocal


def generate_filename2(instance, filename):
    filename = os.path.join(UPLOAD_PATH, str(ThreadLocal.get_current_user().id), instance.filename)
    return time.strftime(filename)



class CopoChunkedUpload(ChunkedUpload):
    pass

# Override the default filename
CopoChunkedUpload._meta.get_field('file').upload_to = generate_filename2