from io import BytesIO
from tempfile import NamedTemporaryFile

from django.http import FileResponse
from django.views.generic.detail import DetailView

from web.apps.web_copo.utils.dtol import Dtol_Helpers as dh


class BaseFileDownloadView(DetailView):
    def get(self, request, *args, **kwargs):
        with NamedTemporaryFile() as tmp:
            wb = dh.create_barcoding_spreadsheet()
            wb.save(tmp.name)
            output = BytesIO(tmp.read())
            response = FileResponse(output)
            # https://docs.djangoproject.com/en/1.11/howto/outputting-csv/#streaming-large-csv-files
            response['Content-Disposition'] = 'attachment; filename="%s"' % tmp.name
            response['Content-Type'] = 'application/vnd.ms-excel'
            return response


class SomeFileDownloadView(BaseFileDownloadView):
    pass
