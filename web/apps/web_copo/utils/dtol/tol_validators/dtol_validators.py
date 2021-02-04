from submission.helpers.generic_helper import notify_dtol_status
from .tol_validator import TolValidtor
from .validation_messages import MESSAGES as msg

blank_vals = ['NOT_COLLECTED', 'NOT_PROVIDED', 'NOT_APPLICABLE']


class ColumnValdator(TolValidtor):
    def validate(self, profile_id, fields, data, errors, flag, **kwargs):
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


class CellMissingDataValidator(TolValidtor):
    def validate(self, profile_id, fields, data, errors, flag, **kwargs):
        for header, cells in data.iteritems():
            # here we need to check if there are not missing values in its cells
            if header in fields:
                if header == "SYMBIONT" and kwargs.get(type) == "DTOL":
                    # dtol manifests are allowed to have blank field in SYMBIONT
                    pass
                else:
                    cellcount = 0
                    for c in cells:
                        cellcount += 1
                        if not c.strip():
                            # we have missing data in required cells
                            if header == "SYMBIONT":
                                errors.append(msg["validation_msg_missing_symbiont"] % (
                                    header, str(cellcount + 1), "TARGET and SYMBIONT"))
                            else:
                                errors.append(msg["validation_msg_missing_data"] % (
                                    header, str(cellcount + 1), blank_vals))
                            flag = False
        return errors, flag
