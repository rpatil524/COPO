from submission.helpers.generic_helper import notify_dtol_status
from .tol_validator import TolValidtor


class ColumnValdator(TolValidtor):
    def validate(self, profile_id, fields, data, errors, flag):
        columns = list(data.columns)
        # check required fields are present in spreadsheet
        for item in fields:
            notify_dtol_status(data={"profile_id": profile_id}, msg="Checking - " + item,
                               action="info",
                               html_id="sample_info")
            if item not in columns:
                # invalid or missing field, inform user and return false
                errors.append("Field not found - " + item)
                flag = False
                # if we have a required fields, check that there are no missing values
        return errors, flag
