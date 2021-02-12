from django.http import FileResponse
from django.views.generic.detail import DetailView


class BaseFileDownloadView(DetailView):
    def get(self, request, *args, **kwargs):
        filename = self.kwargs.get('filename', None)
        if filename is None:
            raise ValueError("Found empty filename")
        i = open(filename, 'rb')
        response = FileResponse(i)
        # https://docs.djangoproject.com/en/1.11/howto/outputting-csv/#streaming-large-csv-files
        # response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


class SomeFileDownloadView(BaseFileDownloadView):
    pass
