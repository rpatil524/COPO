__author__ = 'felix.shaw@tgac.ac.uk - 28/07/2016'

#from web.apps.web_copo.schemas.utils.data_utils import json_to_pytype, get_datetime
#from web.apps.web_copo.lookup.lookup import MESSAGES_LKUPS
from datetime import datetime
import os
from enum import Enum
from exceptions_and_logging.CopoRuntimeError import CopoRuntimeError
from web.apps.web_copo.lookup.copo_enums import *


class Logger():



    def __init__(self, logfile_path, system_level=Loglvl.ERROR, log_type=Logtype.FILE):
        self.level = system_level
        self.log_type = log_type
        self.logfile_path = logfile_path



    def log(self, msg, level=Loglvl.ERROR, type=Logtype.CONSOLE):

        if level.value >= self.level.value:
            # pass to relevant logger handler
            if type.value == Logtype.CONSOLE.value:
                return self._log_to_console(msg, level)
            elif type.value == Logtype.FILE.value:
                return self._log_to_file(msg, level)



    def _log_to_console(self, msg, lvl=Loglvl.ERROR):
        # log to console in colour
        msg = str(msg)
        if lvl.value == Loglvl.ERROR.value:
            print(str(bcolors.FAIL.value + msg + bcolors.ENDC.value))
            raise CopoRuntimeError(message="Whoops! - Something went wrong.")
        elif lvl.value == Loglvl.WARNING.value:
            print(str(bcolors.WARNING.value + msg + bcolors.ENDC.value))
        elif lvl.value == Loglvl.INFO.value:
            print(str(bcolors.OKGREEN.value + msg + bcolors.ENDC.value))



    def _log_to_file(self, msg, lvl=Loglvl.ERROR):
        msg = str(msg)
        with open(os.path.join(self.logfile_path, str(datetime.now().date()) + '.log'), 'a+', encoding='utf-8') as file:
            time = datetime.now()
            time = str(time.hour) + "-" + str(time.minute) + "-" + str(time.second)
            if lvl.value == Loglvl.ERROR.value:
                file.write("ERROR - [" + time + "]: " + msg + "\n")
                raise CopoRuntimeError(message="Whoops! - Something went wrong.")
            elif lvl.value == Loglvl.WARNING.value:
                file.write("WARNING - [" + time + "]: " + msg + "\n")
            elif lvl.value == Loglvl.INFO.value:
                file.write("INFO - [" + time + "]: " + msg + "\n")


    '''
    def get_copo_exception(key):
        messages = json_to_pytype(MESSAGES_LKUPS["exception_messages"])["properties"]
        return messages.get(key, str())
    '''


