import re

from dal.copo_da import Profile
from submission.helpers.generic_helper import notify_dtol_status
from web.apps.web_copo.lookup import dtol_lookups as lookup
from web.apps.web_copo.utils.dtol.Dtol_Helpers import validate_date
from .tol_validator import TolValidtor
from .validation_messages import MESSAGES as msg



class DtolEnumerationValidator(TolValidtor):

    def validate(self):
        whole_used_specimens = set()
        regex_human_readable = ""
        p_type = Profile().get_type(profile_id=self.profile_id)
        for header, cells in self.data.iteritems():

            notify_dtol_status(data={"profile_id": self.profile_id}, msg="Checking - " + header,
                               action="info",
                               html_id="sample_info")
            if header in self.fields:
                if header == "SYMBIONT" and "DTOL" in p_type:
                    # dtol manifests are allowed to have blank field in SYMBIONT
                    pass
                else:
                    # check if there is an enum for this header
                    allowed_vals = lookup.DTOL_ENUMS.get(header, "")

                    # check if there's a regex rule for the header and exceptional handling
                    if lookup.DTOL_RULES.get(header, ""):
                        regex_rule = lookup.DTOL_RULES[header].get("ena_regex", "")
                        regex_human_readable = lookup.DTOL_RULES[header].get("human_readable", "")
                    else:
                        regex_rule = ""
                    cellcount = 0
                    for c in cells:
                        cellcount += 1

                        c_value = c
                        if allowed_vals:
                            if header == "COLLECTION_LOCATION":
                                # special check for COLLETION_LOCATION as this needs invalid list error for feedback
                                c_value = str(c).split('|')[0].strip()
                                location_2part = str(c).split('|')[1:]
                                if c_value.upper() not in allowed_vals or not location_2part:
                                    self.errors.append(msg["validation_msg_invalid_list"] % (
                                        c_value, header, str(cellcount + 1)))
                                    self.flag = False
                            elif header == "ORGANISM_PART":
                                # special check for piped values
                                for part in str(c).split('|'):
                                    if part.strip() not in allowed_vals:
                                        self.errors.append(msg["validation_msg_invalid_data"] % (
                                            part, header, str(cellcount + 1), allowed_vals
                                        ))
                                        self.flag = False
                            elif c_value.strip() not in allowed_vals:
                                # check value is in allowed enum
                                self.errors.append(msg["validation_msg_invalid_data"] % (
                                    c_value, header, str(cellcount + 1), allowed_vals))
                                self.flag = False
                            if header == "ORGANISM_PART" and c_value.strip() == "WHOLE_ORGANISM":
                                # send specimen in used whole specimens set
                                current_specimen = self.data.at[cellcount - 1, "SPECIMEN_ID"]
                                if current_specimen in whole_used_specimens:
                                    self.errors.append(msg["validation_msg_used_whole_organism"] % current_specimen)
                                    self.flag = False
                                else:
                                    whole_used_specimens.add(current_specimen)
                        if regex_rule:
                            # handle any regular expressions provided for valiation
                            if c and not re.match(regex_rule, c.replace("_", " "), re.IGNORECASE):
                                self.errors.append(msg["validation_msg_invalid_data"] % (
                                    c, header, str(cellcount + 1), regex_human_readable))
                                self.flag = False
                        # validation checks for SERIES
                        if header == "SERIES":
                            try:
                                int(c)
                            except ValueError:
                                self.errors.append(msg["validation_msg_invalid_data"] % (
                                    c, header, str(cellcount + 1), "integers"))
                                self.flag = False
                        elif header == "TIME_ELAPSED_FROM_COLLECTION_TO_PRESERVATION":
                            # check this is either a NOT_* or an integer
                            if c_value.strip() not in lookup.blank_vals:
                                try:
                                    float(c_value)
                                except ValueError:
                                    self.errors.append(msg["validation_msg_invalid_data"] % (
                                        c_value, header, str(cellcount + 1),
                                        "integer or " + ", ".join(lookup.blank_vals)
                                    ))
                                    self.flag = False
                        # validation checks for date types
                        if header in lookup.date_fields and c_value.strip() not in lookup.blank_vals:
                            try:
                                validate_date(c)
                            except ValueError as e:
                                self.errors.append(
                                    msg["validation_msg_invalid_date"] % (c, str(cellcount + 1), header))
                                self.flag = False
        return self.errors, self.flag