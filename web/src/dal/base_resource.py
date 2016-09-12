__author__ = 'felixshaw'

class Resource(object):
    def GET(self, id, **kwargs):
        return NotImplemented()

    def POST(self, **kwargs):
        return NotImplemented()

    def DELETE(self, id, **kwargs):
        return NotImplemented()

    def PUT(self, **kwargs):
        return NotImplemented()

    def __call__(self, request, **kwargs):
        handler = getattr(self, request.method)
        return handler(request, **kwargs)