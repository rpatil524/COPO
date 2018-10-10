import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings.all")

application = get_wsgi_application()

import glob
import pandas as pd
from dal.copo_base_da import DataSchemas
from dal.mongo_util import get_collection_ref
from web.apps.web_copo.lookup.resolver import RESOLVER
import web.apps.web_copo.schemas.utils.data_utils as d_utils

Schemas = get_collection_ref("Schemas")
Dropdowns = get_collection_ref("Dropdowns")

drop_downs_pth = RESOLVER['copo_drop_downs']


def main():
    # generate ui schemas
    ui_schemas()

    # todo: automatically create index: db.getCollection('Dropdowns').createIndex( { accession: 1, type:1, label:1} )

    # generate agrovoc data source
    agrovoc_datasource("agrovoclabels")

    # generate countries list data source
    countrieslist_datasource("countrieslist")

    # generate media types
    mediatype_datasource("mediatypelabels")


def ui_schemas():
    """
    function generates ui schemas
    :return:
    """
    # instantiate data schema
    data_schema = DataSchemas("COPO")

    # delete existing schemas
    data_schema.delete_ui_template()

    # generate new schemas
    data_schema.get_ui_template()

    return True


def agrovoc_datasource(type):
    """
    function generates data source for Agrovoc terms lookup
    :return:
    """

    # drop existing records of type
    Dropdowns.remove({"type": type})

    data = d_utils.json_to_pytype(os.path.join(drop_downs_pth, 'agrovocLabels.json'))["bindings"]
    data_df = pd.DataFrame(data)

    data_df['accession'] = data_df['uri'].apply(lambda x: x.get('value', str()))
    data_df['label'] = data_df['label'].apply(lambda x: x.get('value', str()))
    data_df['description'] = ' '
    data_df['type'] = type

    data_df = data_df[['accession', 'label', 'description', 'type']]
    result = data_df.to_dict('records')

    Dropdowns.insert_many(result)

    return True


def countrieslist_datasource(type):
    """
    function generates data source for lookup of countries
    :return:
    """

    # drop existing records of type
    Dropdowns.remove({"type": type})

    data = d_utils.json_to_pytype(os.path.join(drop_downs_pth, 'countries.json'))["bindings"]
    data_df = pd.DataFrame(data)

    data_df['accession'] = data_df['iso_3166-2']
    data_df['label'] = data_df['name']
    data_df['type'] = type

    data_df['description'] = '<table style="width:100%"><tr><td>Code</td><td>' + data_df[
        'country-code'] + '</td></tr><tr><td>Region</td><td>' + data_df[
                                 'region'] + '</td></tr><tr><td>Sub-region</td><td>' + data_df[
                                 'sub-region'] + '</td></tr></table>'

    data_df = data_df[['accession', 'label', 'description', 'type']]
    result = data_df.to_dict('records')

    Dropdowns.insert_many(result)

    return True


def mediatype_datasource(type):
    """
    :param type: is the 'datasource' used in the ui control element
    :return:
    """

    # drop existing records of type
    Dropdowns.remove({"type": type})

    # get all mediatype files
    pth = os.path.join(drop_downs_pth, 'media_types')
    all_files = glob.glob(os.path.join(pth, "*.csv"))

    all_list = list()
    for f in all_files:
        df = pd.read_csv(f)
        df['type'] = df['Template'].str.split("/").str.get(0)
        stem_part = set(df['type'][~df['type'].isna()]).pop()
        df['type'] = stem_part
        vv = df['Template'][df['Template'].isna()].index
        tt = df['Name'][vv]
        df.loc[list(vv), 'Template'] = stem_part + '/' + tt
        df = df[['Name', 'Template', 'type']]
        all_list = all_list + df.to_dict('records')

    data_df = pd.DataFrame(all_list)
    data_df['accession'] = data_df['Template']
    data_df['label'] = data_df['Template']
    data_df['description'] = '<table style="width:100%"><tr><td>Category</td><td>' + data_df[
        'type'] + '</td></tr></table>'
    data_df['type'] = type

    data_df = data_df[['accession', 'label', 'description', 'type']]
    result = data_df.to_dict('records')

    Dropdowns.insert_many(result)

    return True


if __name__ == "__main__":
    main()
