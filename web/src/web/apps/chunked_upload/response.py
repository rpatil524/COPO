from django.http import HttpResponse

from .settings_old import ENCODER, MIMETYPE


class Response(HttpResponse):
    """
    """

    def __init__(self, content, status=None, *args, **kwargs):
        super(Response, self).__init__(
            content=ENCODER(content),
            content_type=MIMETYPE,
            status=status,
            *args, **kwargs
        )
