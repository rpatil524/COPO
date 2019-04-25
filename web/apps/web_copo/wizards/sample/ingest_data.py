__author__ = 'etuka'
__date__ = '22 March 2019'

import os
import csv
import ntpath
import pandas as pd
from django.conf import settings
from dal.copo_da import Sample, Description
from django.core.files.storage import FileSystemStorage
from web.apps.web_copo.lookup.copo_enums import Loglvl, Logtype

lg = settings.LOGGER

"""
class handles the ingestion of csv data to supply metadata for description
"""


class IngestData:
    def __init__(self, description_token=str(), profile_id=str()):
        self.description_token = description_token
        self.profile_id = self.set_profile_id(profile_id)
        self.schema = Sample().get_schema().get("schema_dict")

    def set_profile_id(self, profile_id):
        p_id = profile_id
        if not p_id and self.description_token:
            description = Description().GET(self.description_token)
            p_id = description.get("profile_id", str())

        return p_id

    def get_object_path(self):
        """
        function returns directory to description data
        :return:
        """
        object_path = os.path.join(settings.MEDIA_ROOT, 'description_data', self.description_token)
        return object_path

    def get_object_file_path(self):
        """
        function returns file path to description data
        :return:
        """
        file_path = os.path.join(self.get_object_path(), 'uploaded.csv')
        return file_path

    def save_uploaded_csv(self, csv_file):
        """
        function saves the passed file to the file system
        :param csv_file:
        :return: boolean - indicating success or otherwise of file save
        """

        result = dict(status='success', message='')

        if csv_file:
            csv_file.name = ntpath.basename(self.get_object_file_path())

            # removed previous file
            if os.path.exists(self.get_object_file_path()):
                os.remove(self.get_object_file_path())

            fs = FileSystemStorage(location=self.get_object_path())
            try:
                fs.save(csv_file.name, csv_file)
            except Exception as e:
                message = 'Error Ingesting data: ' + str(e)
                print(message)
                lg.log(message, level=Loglvl.ERROR, type=Logtype.FILE)
                raise

        return result

    def align_columns(self):
        """
        function compares ingested columns to generated columns - they should align
        :return:
        """

        result = dict(status='success', message='')

        if not os.path.exists(self.get_object_file_path()):
            result["status"] = "error"
            result["message"] = "Couldn't locate uploaded CSV. Try re-uploading."

            return result

        with open(self.get_object_file_path(), 'r') as fobject:
            ingested_columns = (next(csv.reader(fobject)))

        description = Description().GET(self.description_token)
        stored_columns = description.get("meta", dict()).get("generated_columns", list())

        ingested_columns = [x.strip().lower() for x in ingested_columns if x.strip()]
        stored_columns = [x['title'].strip().lower() for x in stored_columns if x['title'].strip()]

        if not ingested_columns == stored_columns:
            result["status"] = "error"
            result["message"] = "Headers from uploaded CSV do not match displayed columns."

            return result

        return result

    def align_rows(self):
        """
        function compares ingested sample names to generated names - they should align
        :return:
        """

        result = dict(status='success', message='')

        ingested_df = pd.read_csv(self.get_object_file_path())
        ingested_df.columns = [x.lower() for x in list(ingested_df.columns)]

        ingested_names = list(ingested_df.name)

        description = Description().GET(self.description_token)
        stored_names = description.get("meta", dict()).get("generated_names", str()).split(",")

        ingested_names.sort()
        stored_names.sort()

        if not ingested_names == stored_names:
            result["status"] = "error"
            result["message"] = "Sample names from uploaded CSV do not match displayed names."

            return result

        return result

    def manage_process(self, csv_file):
        """
        function orchestrates the ingestion of metadata to description metadata
        :param csv_file: metadata file to be ingested
        :return: returns updated dataset
        """

        # save uploaded csv
        result = self.save_uploaded_csv(csv_file=csv_file)
        if result["status"] == "error":
            return result

        # match ingested columns to rendered columns
        result = self.align_columns()
        if result["status"] == "error":
            return result

        # match ingested sample names to rendered names
        result = self.align_rows()
        if result["status"] == "error":
            return result

        # process data
        result = self.align_rows()
        if result["status"] == "error":
            return result

        return result

    def process_data(self):
        """
        having passed preliminary tests, function processes ingested data
        :return:
        """
