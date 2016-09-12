# resolves from imports to absolute paths

import os
import web.apps.web_copo.lookup
import copo_exceptions
import api.return_templates
import web.apps.web_copo.schemas.utils
import web.apps.web_copo.wizards.datafile
import web.apps.web_copo.schemas.ena.dbmodels
import web.apps.web_copo.schemas.copo.dbmodels
import web.apps.web_copo.schemas.copo.dbmodels.xmls

RESOLVER = dict()
RESOLVER['schemas_copo'] = os.path.dirname(web.apps.web_copo.schemas.copo.dbmodels.__file__)
RESOLVER['schemas_ena'] = os.path.dirname(web.apps.web_copo.schemas.ena.dbmodels.__file__)
RESOLVER['api_return_templates'] = os.path.dirname(api.return_templates.__file__)
RESOLVER['wizards_datafile'] = os.path.dirname(web.apps.web_copo.wizards.datafile.__file__)
RESOLVER['lookup'] = os.path.dirname(web.apps.web_copo.lookup.__file__)
RESOLVER['copo_exceptions'] = os.path.dirname(copo_exceptions.__file__)
RESOLVER['schemas_utils'] = os.path.dirname(web.apps.web_copo.schemas.utils.__file__)
RESOLVER['schemas_xml_copo'] = os.path.dirname(web.apps.web_copo.schemas.copo.dbmodels.xmls.__file__)
