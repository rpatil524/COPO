__author__ = 'etuka'
__date__ = '02 April 2019'

from datetime import datetime
from collections import defaultdict
from dal.copo_da import Submission, Person, Description
import web.apps.web_copo.schemas.utils.data_utils as data_utils


class SubmissionHelper:
    def __init__(self, submission_id=str()):
        self.submission_id = submission_id
        self.submission = Submission().get_record(self.submission_id)
        self.profile_id = str()
        self.description = dict()

        if self.submission:
            self.profile_id = self.submission.get("profile_id", str())

        if self.submission:
            self.description_token = self.submission.get("description_token", str())

        if self.description_token:
            self.description = Description().GET(self.description_token)

    def get_sra_contacts(self):
        """
        function returns users with any SRA roles
        :return:
        """

        sra_contacts = defaultdict(list)
        expected_roles = [x.lower() for x in ['SRA Inform On Status', 'SRA Inform On Error']]

        for rec in Person(profile_id=self.profile_id).get_all_records():
            roles = [role.get("annotationValue", str()).lower() for role in rec.get('roles', []) if
                     role.get("annotationValue", str()).lower() in expected_roles]
            if roles:
                sra_contacts[(rec['email'], rec['firstName'], rec['lastName'])].extend(roles)

        # if no sra contacts, add one from session user
        if not sra_contacts:
            user = data_utils.get_current_user()
            sra_contacts[(user.email, user.first_name, user.last_name)].append(expected_roles)

        return sra_contacts

    def get_study_release(self):
        """
        function returns the release date for a study
        :return:
        """

        release_date = dict()

        if not self.description:
            return release_date

        attributes = self.description.get("attributes", dict())
        release_date = attributes.get("project_details", dict()).get("project_release_date", str())

        if release_date:
            release_date = datetime.strptime(release_date, '%d/%m/%Y').strftime('%Y-%m-%d')
            present = datetime.now()
            past = datetime.strptime(release_date, "%Y-%m-%d")

            return dict(release_date=release_date, in_the_past=past.date() <= present.date())

        return release_date

    def get_study_descriptors(self):
        """
        function returns descriptors for a study e.g., name, title, description
        :return:
        """

        study_attributes = dict()

        if not self.description:
            return study_attributes

        attributes = self.description.get("attributes", dict())
        study_attributes["name"] = attributes.get("project_details", dict()).get("project_name", str())
        study_attributes["title"] = attributes.get("project_details", dict()).get("project_title", str())
        study_attributes["description"] = attributes.get("project_details", dict()).get("project_description", str())

        return study_attributes
