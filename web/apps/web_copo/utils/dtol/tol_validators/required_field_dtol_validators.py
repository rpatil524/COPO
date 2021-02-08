from dal.copo_da import Sample, Profile
from submission.helpers.generic_helper import notify_dtol_status
from .tol_validator import TolValidtor
from .validation_messages import MESSAGES as msg

blank_vals = ["NOT_COLLECTED", "NOT_PROVIDED", "NOT_APPLICABLE", "NA"]


class ColumnValdator(TolValidtor):
    def validate(self):
        columns = list(self.data.columns)
        # check required fields are present in spreadsheet
        for item in self.fields:
            notify_dtol_status(data={"profile_id": self.profile_id}, msg="Checking - " + item,
                               action="info",
                               html_id="sample_info")
            if item not in columns:
                # invalid or missing field, inform user and return false
                self.errors.append("Field not found - " + item)
                self.flag = False
                # if we have a required fields, check that there are no missing values
        return self.errors, self.flag


class CellMissingDataValidator(TolValidtor):
    def validate(self):
        for header, cells in self.data.iteritems():
            # here we need to check if there are not missing values in its cells
            if header in self.fields:
                if header == "SYMBIONT" and self.kwargs.get(type) == "DTOL":
                    # dtol manifests are allowed to have blank field in SYMBIONT
                    pass
                else:
                    cellcount = 0
                    for c in cells:
                        cellcount += 1
                        if not c.strip():
                            # we have missing data in required cells
                            if header == "SYMBIONT":
                                self.errors.append(msg["validation_msg_missing_symbiont"] % (
                                    header, str(cellcount + 1), "TARGET and SYMBIONT"))
                            else:
                                self.errors.append(msg["validation_msg_missing_data"] % (
                                    header, str(cellcount + 1), blank_vals))
                            self.flag = False
        return self.errors, self.flag


class RackTubeNotNullValidator(TolValidtor):
    def validate(self):
        for index, row in self.data.iterrows():
            if row["RACK_OR_PLATE_ID"] in blank_vals and row["TUBE_OR_WELL_ID"] in blank_vals:
                self.errors.append(msg["validation_msg_rack_tube_both_na"] % (str(index + 1)))
                self.flag = False
        return self.errors, self.flag


class RackPlateUniquenessValidator(TolValidtor):
    def validate(self):
        # check for uniqueness of RACK_OR_PLATE_ID and TUBE_OR_WELL_ID in this manifest
        rack_tube = self.data["RACK_OR_PLATE_ID"] + "/" + self.data["TUBE_OR_WELL_ID"]

        # duplicated returns a boolean array, false for not duplicate, true for duplicate
        u = list(rack_tube[rack_tube.duplicated()])
        if len(u) > 0:
            self.errors.append(msg["validation_msg_duplicate_tube_or_well_id"] % (u))
            self.flag = False
        # now check for uniqueness across all Samples
        type = Profile().get_type(profile_id=self.profile_id)
        if "ASG" not in type:
            dup = Sample().check_dtol_unique(rack_tube)
            if len(dup) > 0:
                # errors = list(map(lambda x: "<li>" + x + "</li>", errors))
                err = list(map(lambda x: x["RACK_OR_PLATE_ID"] + "/" + x["TUBE_OR_WELL_ID"], dup))
                self.errors.append(msg["validation_msg_duplicate_tube_or_well_id_in_copo"] % (err))
                self.flag = False
        else:
            # duplicates are allowed for asg but one element of duplicate set must have target in sybiont fields
            for i in u:
                rack, tube = i.split('/')
                rows = self.data.loc[
                    (self.data["RACK_OR_PLATE_ID"] == rack) & (self.data["TUBE_OR_WELL_ID"] == tube)]
                if "TARGET" not in rows["SYMBIONT"].values:
                    self.errors.append(msg["validation_msg_duplicate_without_target"] % (
                            rows["RACK_OR_PLATE_ID"][0] + "/" + rows["TUBE_OR_WELL_ID"][0]))
                    self.flag = False
        return self.errors, self.flag
