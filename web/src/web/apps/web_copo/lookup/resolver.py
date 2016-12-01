# resolves from imports to absolute paths

import os
from django.conf import settings

web_copo = os.path.join(settings.BASE_DIR, 'web', 'apps', 'web_copo')

RESOLVER = dict()
RESOLVER['schemas_copo'] = os.path.join(web_copo, 'schemas', 'copo', 'dbmodels')
RESOLVER['schemas_ena'] = os.path.join(web_copo, 'schemas', 'ena', 'dbmodels')
RESOLVER['uimodels_copo'] = os.path.join(web_copo, 'schemas', 'copo', 'uimodels')
RESOLVER['schemas_generic'] = os.path.join(web_copo, 'schemas', 'generic')
RESOLVER['uimodels_ena'] = os.path.join(web_copo, 'schemas', 'ena', 'uimodels')
RESOLVER['api_return_templates'] = os.path.join(settings.BASE_DIR, 'api', 'return_templates')
RESOLVER['wizards_datafile'] = os.path.join(web_copo, 'wizards', 'datafile')
RESOLVER['wizards_sample'] = os.path.join(web_copo, 'wizards', 'sample')
RESOLVER['lookup'] = os.path.join(web_copo, 'lookup')
RESOLVER['copo_exceptions'] = os.path.join(settings.BASE_DIR, 'copo_exceptions')
RESOLVER['schemas_utils'] = os.path.join(web_copo, 'schemas', 'utils')
RESOLVER['schemas_xml_copo'] = os.path.join(web_copo, 'schemas', 'copo', 'dbmodels', 'xmls')


