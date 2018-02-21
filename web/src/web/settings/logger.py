import os

from web.apps.web_copo.lookup.copo_enums import Loglvl, Logtype
from exceptions_and_logging.logger import Logger
import exceptions_and_logging.logs

from .base import BASE_DIR
log_path = os.path.join(BASE_DIR, 'exceptions_and_logging', 'logs')
print('COPO CWD is: ' + BASE_DIR)
# set the log level to the lowest level of logging you want to see
# i.e. for only errors, set to Loglvl.ERROR, for errors and warnings, Loglvl.WARNING, and for all, Loglvl.INFO
# logs sent through with Loglvl.ERROR will cause the execution of the current request to halt
LOGGER = Logger(logfile_path=log_path, system_level=Loglvl.INFO, log_type=Logtype.CONSOLE)