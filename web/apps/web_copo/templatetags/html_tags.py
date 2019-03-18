__author__ = 'tonietuk'

import time
import json
import copy
import pandas as pd
from uuid import uuid4
from bson import ObjectId
from django import template
from django.urls import reverse
from web.apps.web_copo.schemas.utils import data_utils
from web.apps.web_copo.lookup.lookup import HTML_TAGS
import web.apps.web_copo.lookup.lookup as lkup
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.lookup.copo_lookup_service import COPOLookup
from dal.copo_base_da import DataSchemas
from dal.copo_da import ProfileInfo, Repository, Profile, Publication, Source, Person, Sample, Submission, DataFile, \
    DAComponent, Annotation, CGCore
from allauth.socialaccount import providers
from django_tools.middlewares import ThreadLocal
import hurry

register = template.Library()

# dictionary of components table id, gotten from the UI
table_id_dict = dict(publication="publication_table",
                     person="person_table",
                     sample="sample_table",
                     datafile="datafile_table",
                     annotation="annotation_table",
                     profile="profile_table"
                     )
da_dict = dict(
    publication=Publication,
    person=Person,
    sample=Sample,
    source=Source,
    profile=Profile,
    datafile=DataFile,
    submission=Submission,
    annotation=Annotation,
    cgcore=CGCore
)


@register.simple_tag
def get_providers_orcid_first():
    """
    Returns a list of social authentication providers with Orcid as the first entry

    Usage: `{% get_providers_orcid_first as socialaccount_providers %}`.

    Then within the template context, `socialaccount_providers` will hold
    a list of social providers configured for the current site.
    """
    p_list = providers.registry.get_list()
    for idx, p in enumerate(p_list):
        if p.id == 'orcid':
            o = p_list.pop(idx)
    return [o] + p_list


def get_element_by_id(field_id):
    elem = {}
    out_list = get_fields_list(field_id)
    for f in out_list:
        if f["id"] == field_id:
            f["label"] = trim_parameter_value_label(f["label"])
            elem = f
            break
    return elem


def trim_parameter_value_label(label):
    if "Parameter Value" in label:
        return str.capitalize(label[label.index('[') + 1:label.index(']')])
    else:
        return label


@register.filter("generate_ui_labels")
def generate_ui_labels(field_id):
    out_list = get_fields_list(field_id)
    label = ""
    for f in out_list:
        if f["id"] == field_id:
            label = f["label"]
            break
    return label


def get_control_options(f):
    # option values are typically defined as a list,
    # or in some cases (e.g., 'copo-multi-search'),
    # as a dictionary. However, option values could also be resolved or generated dynamically
    # using callbacks. Callbacks, essentially, define functions that resolve options data

    option_values = list()

    if f.get("control", "text") in ["copo-lookup", "copo-lookup2"]:
        return COPOLookup(accession=f.get('data', str()),
                          data_source=f.get('data_source', str())).broker_component_search()['result']

    if "option_values" not in f:  # you shouldn't be here
        return option_values

    # return existing option values
    if isinstance(f["option_values"], list) and f["option_values"]:
        return f["option_values"]

    # resolve option values from a data source
    if f.get("data_source", str()):
        return COPOLookup(data_source=f.get('data_source', str())).broker_data_source()

    if isinstance(f["option_values"], dict):
        if f.get("option_values", dict()).get("callback", dict()).get("function", str()):
            call_back_function = f.get("option_values", dict()).get("callback", dict()).get("function", str())
            option_values = getattr(d_utils, call_back_function)()
        else:
            # e.g., multi-search has this format
            option_values = f["option_values"]

    return option_values


@register.filter("generate_copo_form")
def generate_copo_form(component=str(), target_id=str(), component_dict=dict(), message_dict=dict(), profile_id=str(),
                       **kwargs):
    # message_dict templates are defined in the lookup dictionary: "MESSAGES_LKUPS"

    label_dict = get_labels()

    da_object = DAComponent(component=component, profile_id=profile_id)

    if component in da_dict:
        da_object = da_dict[component](profile_id)

    form_value = component_dict

    # get record, if in edit mode
    if target_id:
        form_value = da_object.get_record(target_id)

    form_value["_id"] = str(target_id)

    form_schema = list()

    # get schema fields
    for f in da_object.get_component_schema(**kwargs):
        if f.get("show_in_form", True):

            # if required, resolve data source for select-type controls,
            # i.e., if a callback is defined on the 'option_values' field
            if "option_values" in f or f.get("control", "text") in ["copo-lookup", "copo-lookup2"]:
                f['data'] = form_value.get(f["id"].split(".")[-1], str())
                f["option_values"] = get_control_options(f)

            # resolve values for unique items...
            # if a list of unique items is provided with the schema, use it, else dynamically
            # generate unique items based on the component records
            if "unique" in f and not f.get("unique_items", list()):
                f["unique_items"] = generate_unique_items(component=component, profile_id=profile_id,
                                                          elem_id=f["id"].split(".")[-1], record_id=target_id)

            # filter based on sample type
            if component == "sample" and not filter_sample_type(form_value, f):
                continue

            form_schema.append(f)

    return dict(component_name=component,
                form_label=label_dict.get(component, dict()).get("label", str()),
                form_value=form_value,
                target_id=target_id,
                form_schema=form_schema,
                form_message=message_dict,
                )


@register.filter("get_labels")
def get_labels():
    label_dict = dict(publication=dict(label="Publication"),
                      person=dict(label="Person"),
                      sample=dict(label="Sample"),
                      source=dict(label="Source"),
                      profile=dict(label="Profile"),
                      annotation=dict(label="Annotation"),
                      datafile=dict(label="Datafile"),
                      )

    return label_dict


@register.filter("filter_sample_type")
def filter_sample_type(form_value, elem):
    # filters UI elements based on sample type

    allowable = True
    default_type = "biosample"
    sample_types = list()

    for s_t in d_utils.get_sample_type_options():
        sample_types.append(s_t["value"])

    if "sample_type" in form_value:
        default_type = form_value["sample_type"]

    if default_type not in elem.get("specifications", sample_types):
        allowable = False

    return allowable


@register.filter("generate_component_record")
def generate_component_records(component=str(), profile_id=str(), label_key=str(), **kwargs):
    da_object = DAComponent(component=component, profile_id=profile_id)

    if component in da_dict:
        da_object = da_dict[component](profile_id)

    component_records = list()
    schema = da_object.get_component_schema(**kwargs)

    # if label_key is not provided, we will assume the first element in the schema to be the label_key

    if not label_key:
        label_key = schema[0]["id"].split(".")[-1]

    for record in da_object.get_all_records(**kwargs):
        option = dict(value=str(record["_id"]), label=record[label_key])
        component_records.append(option)

    return component_records


@register.filter("generate_unique_items")
def generate_unique_items(component=str(), profile_id=str(), elem_id=str(), record_id=str()):
    da_object = DAComponent(component=component, profile_id=profile_id)
    component_records = list()

    for record in da_object.get_all_records():
        if elem_id in record and not str(record["_id"]) == record_id:
            component_records.append(record[elem_id])

    return component_records


@register.filter("generate_table_columns")
def generate_table_columns(component=str()):
    da_object = DAComponent(component=component)

    # get and filter schema elements based on displayable columns
    schema = [x for x in da_object.get_schema().get("schema_dict") if x.get("show_in_table", True)]

    columns = list()
    columns.append(dict(data="record_id", visible=False))
    detail_dict = dict(className='summary-details-control detail-hover-message', orderable=False, data=None,
                       title='', defaultContent='', width="5%")

    if component == "datafile":
        special_dict = dict(className='describe-status', orderable=False, data=None,
                            title='', width="1%",
                            defaultContent='<span title="Click for description info" data-desc="" style="cursor: '
                                           'pointer;" class="metadata-rating uncertain">'
                                           '<i class="fa fa-square" aria-hidden="true"></i></span>')
        columns.insert(0, special_dict)

    columns.insert(0, detail_dict)

    # get indexed fields - only fields that are indexed can be ordered when using server-side processing
    indexed_fields = list()

    for k, v in da_object.get_collection_handle().index_information().items():
        indexed_fields.append(v['key'][0][0])

    for x in schema:
        x["id"] = x["id"].split(".")[-1]
        orderable = False
        if x["id"] in indexed_fields:
            orderable = True
        columns.append(dict(data=x["id"], title=x["label"], orderable=orderable))

    return columns


@register.filter("generate_server_side_table_records")
def generate_server_side_table_records(profile_id=str(), component=str(), request=dict()):
    # function generates component records for building an UI table using server-side processing
    # - please note that for effective data display,
    # all array and object-type fields (e.g., characteristics) are deferred to sub-table display.
    # please define such in the schema as "show_in_table": false and "show_as_attribute": true

    data_set = list()

    n_size = int(request.get("length", 10))  # assumes 10 records per page if length not set
    draw = int(request.get("draw", 1))
    start = int(request.get("start", 0))

    # instantiate data access object
    da_object = DAComponent(profile_id, component)

    return_dict = dict()

    records_total = da_object.get_collection_handle().count(
        {'profile_id': profile_id, 'deleted': data_utils.get_not_deleted_flag()})

    # get and filter schema elements based on displayable columns
    schema = [x for x in da_object.get_schema().get("schema_dict") if x.get("show_in_table", True)]

    # build db column projection
    projection = [(x["id"].split(".")[-1], 1) for x in schema]

    # order by
    sort_by = request.get('order[0][column]', '0')
    sort_by = request.get('columns[' + sort_by + '][data]', '')
    sort_direction = request.get('order[0][dir]', 'asc')

    sort_by = '_id' if not sort_by else sort_by
    sort_direction = 1 if sort_direction == 'asc' else -1

    # search
    search_term = request.get('search[value]', '').strip()

    # retrieve and process records
    records = da_object.get_all_records_columns_server(sort_by=sort_by, sort_direction=sort_direction,
                                                       search_term=search_term, projection=dict(projection),
                                                       limit=n_size, skip=start)

    records_filtered = records_total

    if search_term:
        records_filtered = da_object.get_collection_handle().count(
            {'profile_id': profile_id, 'deleted': data_utils.get_not_deleted_flag(),
             'name': {'$regex': search_term, "$options": 'i'}})

    if records:
        df = pd.DataFrame(records)

        df['record_id'] = df._id.astype(str)
        df["DT_RowId"] = df.record_id
        df.DT_RowId = 'row_' + df.DT_RowId
        df = df.drop('_id', axis='columns')

        for x in schema:
            x["id"] = x["id"].split(".")[-1]
            df[x["id"]] = df[x["id"]].apply(resolve_control_output_apply, args=(x,)).astype(str)

        data_set = df.to_dict('records')

    return_dict["records_total"] = records_total
    return_dict["records_filtered"] = records_filtered
    return_dict["data_set"] = data_set
    return_dict["draw"] = draw

    return return_dict


@register.filter("generate_table_records")
def generate_table_records(profile_id=str(), component=str()):
    # function generates component records for building an UI table - please note that for effective tabular display,
    # all array and object-type fields (e.g., characteristics) are deferred to sub-table display.
    # please define such in the schema as "show_in_table": false and "show_as_attribute": true

    columns = list()
    data_set = list()

    # instantiate data access object
    da_object = DAComponent(profile_id, component)

    # get and filter schema elements based on displayable columns
    schema = [x for x in da_object.get_schema().get("schema_dict") if x.get("show_in_table", True)]

    # build db column projection
    projection = [(x["id"].split(".")[-1], 1) for x in schema]

    # retrieve and process records
    if component == "submission":
        records = da_object.get_all_records_columns(sort_by="date_created", sort_direction=1,
                                                    projection=dict(projection))
    else:
        records = da_object.get_all_records_columns(projection=dict(projection))

    if len(records):
        df = pd.DataFrame(records)

        df['record_id'] = df._id.astype(str)
        df["DT_RowId"] = df.record_id
        df.DT_RowId = 'row_' + df.DT_RowId
        df = df.drop('_id', axis='columns')

        if component == "submission":
            df["special_repositories"] = df["repository"]

            columns.append(dict(data="special_repositories", visible=False))

        columns.append(dict(data="record_id", visible=False))
        detail_dict = dict(className='summary-details-control detail-hover-message', orderable=False, data=None,
                           title='', defaultContent='', width="5%")

        if component == "datafile":
            special_dict = dict(className='describe-status', orderable=False, data=None,
                                title='', width="1%",
                                defaultContent='<span title="Click for description info" data-desc="" style="cursor: '
                                               'pointer;" class="metadata-rating uncertain">'
                                               '<i class="fa fa-square" aria-hidden="true"></i></span>')
            columns.insert(0, special_dict)

        columns.insert(0, detail_dict)

        df_columns = list(df.columns)

        for x in schema:
            x["id"] = x["id"].split(".")[-1]
            columns.append(dict(data=x["id"], title=x["label"]))
            if x["id"] not in df_columns:
                df[x["id"]] = str()
            df[x["id"]] = df[x["id"]].fillna('')
            df[x["id"]] = df[x["id"]].apply(resolve_control_output_apply, args=(x,))

        data_set = df.to_dict('records')

    correct_repos = list()
    # do check for custom repos here
    if component == "submission":

        user = ThreadLocal.get_current_user()
        repo_ids = user.userdetails.repo_submitter
        all_repos = Repository().get_by_ids(repo_ids)

        for repo in all_repos:
            for r_id in repo_ids:
                if r_id == str(repo["_id"]):
                    correct_repos.append(repo)

        for repo in correct_repos:
            repo["_id"] = str(repo["_id"])

    return_dict = dict(dataSet=data_set,
                       columns=columns,
                       repos=correct_repos
                       )

    return return_dict


@register.filter("generate_copo_table_data")
def generate_copo_table_data(profile_id=str(), component=str()):
    # This method generates the 'json' for building an UI table

    # instantiate data access object
    da_object = DAComponent(profile_id, component)

    # get records
    records = da_object.get_all_records()

    columns = list()
    dataSet = list()

    displayable_fields = list()

    # headers
    for f in da_object.get_schema().get("schema_dict"):
        if f.get("show_in_table", True):
            displayable_fields.append(f)
            columns.append(dict(title=f["label"]))

    columns.append(dict(title=str()))  # extra 'blank' header for record actions column

    # data
    for rec in records:
        row = list()
        for df in displayable_fields:
            row.append(resolve_control_output(rec, df))

        row.append(str(rec["_id"]))  # last element in a row exposes the id of the record
        dataSet.append(row)

    # define action buttons
    button_templates = d_utils.get_button_templates()

    common_btn_dict = dict(row_btns=[button_templates['edit_row'], button_templates['delete_row']],
                           global_btns=[button_templates['delete_global']])

    sample_info = copy.deepcopy(button_templates['info_row'])
    sample_info["text"] = "Sample Attributes"

    buttons_dict = dict(publication=common_btn_dict,
                        person=common_btn_dict,
                        sample=dict(row_btns=[sample_info, button_templates['edit_row'],
                                              button_templates['delete_row']],
                                    global_btns=[button_templates['add_new_samples_global'],
                                                 button_templates['delete_global']]),
                        source=common_btn_dict,
                        profile=common_btn_dict,
                        annotation=common_btn_dict,
                        datafile=dict(
                            row_btns=[button_templates['info_row'], button_templates['describe_row'],
                                      button_templates['delete_row']],
                            global_btns=[button_templates['describe_global'],
                                         button_templates['undescribe_global']])
                        )

    action_buttons = dict(row_btns=buttons_dict.get(component).get("row_btns"),
                          global_btns=buttons_dict.get(component).get("global_btns")
                          )

    return_dict = dict(columns=columns,
                       dataSet=dataSet,
                       table_id=table_id_dict.get(component, str()),
                       action_buttons=action_buttons
                       )

    return return_dict


def get_record_data(record_object=dict(), component=str()):
    # This function is targeted for tabular record display for a single row data

    schema = DAComponent(component=component).get_schema().get("schema_dict")

    row = list()

    for f in schema:
        if f.get("show_in_table", True):
            row.append(resolve_control_output(record_object, f))

    row.append(str(record_object["_id"]))  # last element in a row exposes the id of the record

    return_dict = dict(row_data=row,
                       table_id=table_id_dict.get(component, str())
                       )

    return return_dict


@register.filter("generate_copo_profiles_data")
def generate_copo_profiles_data(profiles=list()):
    data_set = list()

    for pr in profiles:
        temp_set = list()
        temp_set.append({"header": "ID", "data": str(pr["_id"]), "key": "_id"})
        for f in Profile().get_schema().get("schema_dict"):
            if f.get("show_in_table", True):
                temp_set.append({"header": f.get("label", str()), "data": resolve_control_output(pr, f),
                                 "key": f["id"].split(".")[-1]})
        # add whether this is a shared profile
        shared = dict()
        shared['header'] = None
        shared['data'] = pr.get('shared', False)
        shared['key'] = 'shared_profile'
        temp_set.append(shared)

        data_set.append(temp_set)

    return_dict = dict(dataSet=data_set)

    return return_dict


@register.filter("generate_copo_shared_profiles_data")
def generate_copo_shared_profiles_data(profiles=list()):
    data_set = list()

    for pr in profiles:
        temp_set = list()
        temp_set.append({"header": "ID", "data": str(pr["_id"]), "key": "_id"})
        for f in Profile().get_schema().get("schema_dict"):
            if f.get("show_in_table", True):
                temp_set.append({"header": f.get("label", str()), "data": resolve_control_output(pr, f),
                                 "key": f["id"].split(".")[-1]})

        data_set.append(temp_set)

    return_dict = dict(dataSet=data_set)

    return return_dict


@register.filter("generate_submission_accessions_data")
def generate_submission_accessions_data(submission_record):
    """
    method presents accession data in a tabular display friendly way
    great care should be taken here to manipulate accessions from different repositories,
    as they might be stored differently
    :param submission_record:
    :return:
    """
    columns = list()
    data_set = list()
    accessions = submission_record.get("accessions", dict())
    repository = submission_record.get("repository", str())

    if accessions:
        # -----------COLLATE ACCESSIONS FOR ENA SEQUENCE READS----------
        if repository == "ena":
            columns = [{"title": "Accession"}, {"title": "Alias"}, {"title": "Comment"}, {"title": "Type"}]

            for key, value in accessions.items():
                if isinstance(value, dict):  # single accession instance expected
                    data_set.append([value["accession"], value["alias"], str(), key])
                elif isinstance(value, list):  # multiple accession instances expected
                    for v in value:
                        if key == "sample":
                            data_set.append([v["sample_accession"], v["sample_alias"], v["biosample_accession"], key])
                        else:
                            data_set.append([v["accession"], v["alias"], str(), key])


        elif repository == "ena-ant":
            # -----------COLLATE ACCESSIONS FOR ENA ANNOTATIONS----------
            columns = [{"title": "Accession"}, {"title": "Alias"}, {"title": "Comment"}, {"title": "Type"}]

            for key, value in accessions.items():
                if isinstance(value, dict):  # single accession instance expected
                    data_set.append([value["accession"], value["alias"], str(), key])
                elif isinstance(value, list):  # multiple accession instances expected
                    for v in value:
                        if key == "sample":
                            try:
                                data_set.append(
                                    [v["sample_accession"], v["sample_alias"], v["biosample_accession"], key])
                            except:
                                pass
                        else:
                            try:
                                data_set.append([v["accession"], v["alias"], str(), key])
                            except:
                                pass

        elif repository == "figshare":
            # -----------COLLATE ACCESSIONS FOR FIGSHARE REPO----------
            columns = [{"title": "Accession"}, {"title": "Alias"}, {"title": "Comment"}, {"title": "Type"}]

            for idx, value in enumerate(accessions):
                data_set.append([value, "Figshare File: " + str(idx + 1), str(), str()])

        elif repository == "dataverse":
            # -----------COLLATE ACCESSIONS FOR DATAVERSE REPO----------
            columns = [{"title": "DOI"}, {"title": "Dataverse"}, {"title": "Dataverse Alias"},
                       {"title": "Dataset Title"}]

            data_set.append(
                [accessions["dataset_doi"], accessions["dataverse_title"], accessions["dataverse_alias"],
                 accessions["dataset_title"]]
            )

        elif repository == "dspace":
            columns = [{"title": "Description"}, {"title": "Format"}, {"title": "Filesize"}, {"title": "Retrieve Link"},
                       {"title": "Metadata Link"}]
            for a in accessions:
                link_ref = a["dspace_instance"] + a["link"]
                meta_link = '<a target="_blank" href="' + a["meta_url"] + '">' + a["meta_url"] + '</a>'
                retrieve_link = '<a href="' + link_ref + '/retrieve">' + link_ref + '</a>'
                data_set.append(
                    [a["description"], a["format"], (hurry.filesize.size(a["sizeBytes"])),
                     retrieve_link,
                     meta_link]
                )

        elif repository == "ckan":
            columns = [{"title": "Name"}, {"title": "Metadata Link"}, {"title": "Resource Link"}, {"title": "Format"}]
            for a in accessions:
                retrieve_link = '<a href="' + a["result"]["url"] + '">' + a["result"]["url"] + '</a>'
                meta_link = '<a target="_blank" href="' + a["result"]["repo_url"] + 'package_show?id=' + a['result'][
                    'package_id'] + '">' + 'Show Metadata' + '</a>'
                data_set.append(
                    [a["result"]["name"], meta_link, retrieve_link, a["result"]["format"]]
                )

    return_dict = dict(dataSet=data_set,
                       columns=columns,
                       repository=repository
                       )

    return return_dict


@register.filter("generate_attributes")
def generate_attributes(component, target_id):
    da_object = DAComponent(component=component)

    if component in da_dict:
        da_object = da_dict[component]()

    # get and filter schema elements based on displayable columns
    schema = [x for x in da_object.get_schema().get("schema_dict") if x.get("show_as_attribute", False)]

    # build db column projection
    projection = [(x["id"].split(".")[-1], 1) for x in schema]

    # account for description metadata in datafiles
    if component == "datafile":
        projection.append(('description', 1))

    filter_by = dict(_id=ObjectId(target_id))
    record = da_object.get_all_records_columns(projection=dict(projection), filter_by=filter_by)

    result = dict()

    if len(record):
        record = record[0]

        if component == "sample":  # filter based on sample type
            sample_types = [s_t['value'] for s_t in d_utils.get_sample_type_options()]
            sample_type = record.get("sample_type", str())
            schema = [x for x in schema if sample_type in x.get("specifications", sample_types)]

        for x in schema:
            x['id'] = x["id"].split(".")[-1]

        if component == "datafile":
            key_split = "___0___"
            attributes = record.get("description", dict()).get("attributes", dict())
            stages = record.get("description", dict()).get("stages", list())

            datafile_attributes = dict()
            datafile_items = list()

            for st in stages:
                for item in st.get("items", list()):
                    if str(item.get("hidden", False)).lower() == "false":
                        atrib_val = attributes.get(st["ref"], dict()).get(item["id"], str())
                        item["id"] = st["ref"] + key_split + item["id"]
                        datafile_attributes[item["id"]] = atrib_val
                        datafile_items.append(item)

            record.update(datafile_attributes)
            schema = schema + datafile_items

        result = resolve_display_data(schema, record)

    return result


def resolve_control_output_apply(data, args):
    if args.get("type", str()) == "array":  # resolve array data types
        resolved_value = list()
        for d in data:
            resolved_value.append(get_resolver(d, args))
    else:  # non-array types
        resolved_value = get_resolver(data, args)

    return resolved_value


def resolve_control_output_description(data, args):
    key_split = "___0___"
    st_key_split = args.id.split(key_split)

    data = data['attributes'][st_key_split[0]][st_key_split[1]]

    if args.get("type", str()) == "array":  # resolve array data types
        resolved_value = list()
        for d in data:
            resolved_value.append(get_resolver(d, args))
    else:  # non-array types
        resolved_value = get_resolver(data, args)

    return resolved_value


def resolve_control_output(data_dict, elem):
    resolved_value = str()

    key_split = elem["id"].split(".")[-1]
    if key_split in data_dict:
        # resolve array data types
        if elem.get("type", str()) == "array":
            resolved_value = list()
            data = data_dict[key_split]
            for d in data:
                resolved_value.append(get_resolver(d, elem))
        else:
            # non-array types
            resolved_value = get_resolver(data_dict[key_split], elem)

    return resolved_value


def get_resolver(data, elem):
    """
    function resolves data for UI display, by mapping control to a resolver function
    :param data:
    :param elem:
    :return:
    """
    func_map = dict()
    func_map["copo-characteristics"] = resolve_copo_characteristics_data
    func_map["copo-environmental-characteristics"] = resolve_environmental_characteristics_data
    func_map["copo-phenotypic-characteristics"] = resolve_phenotypic_characteristics_data
    func_map["copo-comment"] = resolve_copo_comment_data
    func_map["copo-multi-select"] = resolve_copo_multi_select_data
    func_map["copo-multi-select2"] = resolve_copo_multi_select_data
    func_map["copo-single-select"] = resolve_copo_multi_select_data
    func_map["copo-multi-search"] = resolve_copo_multi_search_data
    func_map["copo-lookup"] = resolve_copo_lookup_data
    func_map["copo-lookup2"] = resolve_copo_lookup2_data
    func_map["select"] = resolve_select_data
    func_map["copo-button-list"] = resolve_select_data
    func_map["ontology term"] = resolve_ontology_term_data
    func_map["copo-select"] = resolve_copo_select_data
    func_map["datetime"] = resolve_datetime_data
    func_map["datafile-description"] = resolve_description_data
    func_map["date-picker"] = resolve_datepicker_data
    func_map["copo-duration"] = resolve_copo_duration_data
    func_map["copo-datafile-id"] = resolve_copo_datafile_id_data

    control = elem.get("control", "text").lower()
    if control in func_map:
        resolved_data = func_map[control](data, elem)
    else:
        resolved_data = resolve_default_data(data)

    return resolved_data


def resolve_display_data(datafile_items, datafile_attributes):
    data = list()
    columns = list()
    key_split = "___0___"
    object_controls = d_utils.get_object_array_schema()

    schema_df = pd.DataFrame(datafile_items)

    for index, row in schema_df.iterrows():
        resolved_data = resolve_control_output(datafile_attributes, dict(row.dropna()))
        label = row["label"]

        if row['control'] in object_controls.keys():
            # get object-type-control schema
            control_df = pd.DataFrame(object_controls[row['control']])
            control_df['id2'] = control_df['id'].apply(lambda x: x.split(".")[-1])

            if resolved_data:
                object_array_keys = [list(x.keys())[0] for x in resolved_data[0]]
                object_array_df = pd.DataFrame([dict(pair for d in k for pair in d.items()) for k in resolved_data])

                for o_indx, o_row in object_array_df.iterrows():
                    # add primary header/value - first element in object_array_keys taken as header, second value
                    # e.g., category, value in material_attribute_value schema
                    # a slightly different implementation will be needed for an object-type-control
                    # that require a different display structure

                    class_name = key_split.join((row.id, str(o_indx), object_array_keys[1]))
                    columns.append(dict(title=label + " [{0}]".format(o_row[object_array_keys[0]]), data=class_name))
                    data.append({class_name: o_row[object_array_keys[1]]})

                    # add other headers/values e.g., unit in material_attribute_value schema
                    for subitem in object_array_keys[2:]:
                        class_name = key_split.join((row.id, str(o_indx), subitem))
                        columns.append(dict(
                            title=control_df[control_df.id2.str.lower() == subitem.lower()].iloc[0].label,
                            data=class_name))
                        data.append({class_name: o_row[subitem]})
        else:
            # account for array types
            if row["type"] == "array":
                for tt_indx, tt_val in enumerate(resolved_data):
                    shown_keys = (row["id"], str(tt_indx))
                    class_name = key_split.join(shown_keys)
                    columns.append(
                        dict(title=label + " [{0}]".format(str(tt_indx + 1)), data=class_name))

                    if isinstance(tt_val, list):
                        tt_val = ', '.join(tt_val)

                    data_attribute = dict()
                    data_attribute[class_name] = tt_val
                    data.append(data_attribute)
            else:
                shown_keys = row["id"]
                class_name = shown_keys
                columns.append(dict(title=label, data=class_name))
                val = resolved_data

                if isinstance(val, list):
                    val = ', '.join(val)

                data_attribute = dict()
                data_attribute[class_name] = val
                data.append(data_attribute)

    data_record = dict(pair for d in data for pair in d.items())

    # for k in columns:
    #     k["data"] = data_record[k["data"]]

    return dict(columns=columns, data_set=data_record)


def resolve_description_data(data, elem):
    attributes = data.get("attributes", dict())
    stages = data.get("stages", list())

    datafile_attributes = dict()
    datafile_items = list()
    key_split = "___0___"

    for st in stages:
        attributes[st["ref"]] = attributes.get(st["ref"], dict())
        for item in st.get("items", list()):
            if str(item.get("hidden", False)).lower() == "false":
                atrib_val = attributes.get(st["ref"], dict()).get(item["id"], str())
                item["id"] = st["ref"] + key_split + item["id"]
                datafile_attributes[item["id"]] = atrib_val
                datafile_items.append(item)

    return resolve_display_data(datafile_items, datafile_attributes)


def resolve_copo_characteristics_data(data, elem):
    schema = d_utils.get_copo_schema("material_attribute_value")

    resolved_data = list()

    for f in schema:
        if f.get("show_in_table", True):
            a = dict()
            if f["id"].split(".")[-1] in data:
                a[f["id"].split(".")[-1]] = resolve_ontology_term_data(data[f["id"].split(".")[-1]], elem)
                resolved_data.append(a)

    return resolved_data


def resolve_environmental_characteristics_data(data, elem):
    schema = d_utils.get_copo_schema("environment_variables")

    resolved_data = list()

    for f in schema:
        if f.get("show_in_table", True):
            a = dict()
            if f["id"].split(".")[-1] in data:
                a[f["id"].split(".")[-1]] = resolve_ontology_term_data(data[f["id"].split(".")[-1]], elem)
                resolved_data.append(a)

    return resolved_data  # turn this casting off after merge


def resolve_phenotypic_characteristics_data(data, elem):
    schema = d_utils.get_copo_schema("phenotypic_variables")

    resolved_data = list()

    for f in schema:
        if f.get("show_in_table", True):
            a = dict()
            if f["id"].split(".")[-1] in data:
                a[f["id"].split(".")[-1]] = resolve_ontology_term_data(data[f["id"].split(".")[-1]], elem)
                resolved_data.append(a)

    return resolved_data  # turn this casting off after merge


def resolve_copo_comment_data(data, elem):
    schema = d_utils.get_copo_schema("comment")

    resolved_data = list()

    for f in schema:
        if f.get("show_in_table", True):
            a = dict()
            if f["id"].split(".")[-1] in data:
                a[f["id"].split(".")[-1]] = data[f["id"].split(".")[-1]]
                resolved_data.append(a)

    if not resolved_data:
        resolved_data = str()
    elif len(resolved_data) == 1:
        resolved_data = resolved_data[0]
    return resolved_data


def resolve_copo_multi_select_data(data, elem):
    resolved_value = list()

    option_values = None

    if "option_values" in elem:
        option_values = get_control_options(elem)

    if data:
        if isinstance(data, str):
            data = data.split(",")

        data = [str(x) for x in data]

        if option_values:
            if isinstance(option_values[0], str):
                option_values = [dict(value=x, label=x) for x in option_values]

            o_df = pd.DataFrame(option_values)
            o_df.value = o_df.value.astype(str)
            resolved_value = list(o_df[o_df.value.isin(data)].label)

    return resolved_value


def resolve_copo_multi_search_data(data, elem):
    resolved_value = list()

    option_values = None

    if isinstance(data, list):
        data = ','.join(map(str, data))

    if "option_values" in elem:
        option_values = get_control_options(elem)

    if option_values and data:
        for d_v in data.split(","):
            resolved_value = resolved_value + [x[option_values["label_field"]] for x in option_values["options"] if
                                               d_v == x[option_values["value_field"]]]

    return resolved_value


def resolve_copo_lookup_data(data, elem):
    resolved_value = str()

    elem['data'] = data
    option_values = get_control_options(elem)

    if option_values:
        resolved_value = option_values[0]['label']

    return resolved_value


def resolve_copo_lookup2_data(data, elem):
    resolved_value = str()

    elem['data'] = data
    option_values = get_control_options(elem)

    if option_values:
        resolved_value = [x[
                              'label'] + "<span class='copo-embedded' style='margin-left: 5px;' data-source='{data_source}' data-accession='{data_accession}' >" \
                                         "<i title='click for related information' style='cursor: pointer;' class='fa fa-info-circle'></i></span>".format(
            data_source=elem['data_source'], data_accession=x['accession']) for x in option_values]

    return resolved_value


def resolve_select_data(data, elem):
    option_values = None
    resolved_value = str()

    if "option_values" in elem:
        option_values = get_control_options(elem)

    if option_values and data:
        for option in option_values:
            if isinstance(option, str):
                sv = option
                sl = option
            elif isinstance(option, dict):
                sv = option['value']
                sl = option['label']
            if str(sv) == str(data):
                resolved_value = sl

    return resolved_value


def resolve_ontology_term_data(data, elem):
    schema = DataSchemas("COPO").get_ui_template().get("copo").get("ontology_annotation").get("fields")

    resolved_data = list()

    for f in schema:
        if f.get("show_in_table", True):
            if f["id"].split(".")[-1] in data:
                resolved_data.append(data[f["id"].split(".")[-1]])

    if not resolved_data:
        resolved_data = str()
    elif len(resolved_data) == 1:
        resolved_data = resolved_data[0]
    return resolved_data


def resolve_copo_select_data(data, elem):
    return data


def resolve_datetime_data(data, elem):
    resolved_value = str()

    if data:
        if data.date:
            try:
                resolved_value = time.strftime('%a, %d %b %Y %H:%M', data.timetuple())
            except ValueError:
                pass
    return resolved_value


def resolve_datepicker_data(data, elem):
    resolved_value = str()
    if data:
        resolved_value = data
    return resolved_value


def resolve_copo_duration_data(data, elem):
    schema = d_utils.get_copo_schema("duration")

    resolved_data = list()

    for f in schema:
        if f.get("show_in_table", True):
            # a = dict()
            if f["id"].split(".")[-1] in data:
                # a[f["label"]] = data[f["id"].split(".")[-1]]
                resolved_data.append(f["label"] + ": " + data[f["id"].split(".")[-1]])

    return resolved_data


def resolve_copo_datafile_id_data(data, elem):
    resolved_data = dict()

    da_object = DAComponent(component="datafile")

    if data:
        datafile = da_object.get_record(data)
        resolved_data["recordLabel"] = datafile.get("name", str())
        resolved_data["recordID"] = data

    return resolved_data


def resolve_default_data(data):
    return data


@register.filter("generate_copo_profiles_counts")
def generate_copo_profiles_counts(profiles=list()):
    data_set = list()

    for pr in profiles:
        data_set.append(dict(profile_id=str(pr["_id"]), counts=ProfileInfo(str(pr["_id"])).get_counts()))
    return data_set


@register.filter("lookup_info")
def lookup_info(val):
    if val in lkup.UI_INFO.keys():
        return lkup.UI_INFO[val]
    return ""


def get_fields_list(field_id):
    key_split = field_id.split(".")

    new_dict = DataSchemas(field_id.split(".")[0].upper()).get_ui_template()

    for kp in key_split[:-1]:
        if kp in new_dict:
            new_dict = new_dict[kp]

    return new_dict["fields"]


@register.filter("id_to_class")
def id_to_class(val):
    return val.replace(".", "_")


def generate_figshare_oauth_html():
    elem = {'label': 'Figshare', 'control': 'oauth_required'}
    do_tag(elem)


def get_ols_url():
    req = data_utils.get_current_request()
    protocol = req.META['wsgi.url_scheme']
    r = req.build_absolute_uri()
    ols_url = protocol + '://' + data_utils.get_current_request().META['HTTP_HOST'] + reverse(
        'copo:ajax_search_ontology')

    return ols_url


def do_tag(the_elem, default_value=None):
    elem_id = the_elem["id"]
    try:
        copo_module = elem_id.split('.')[1]
        field_type = elem_id.rsplit('.', 1)[1]
    except:
        pass
    elem_label = the_elem["label"]
    elem_help_tip = the_elem["help_tip"]
    div_id = uuid4()

    # try and get elem_class - this can be used as a hook for the form item in javascript
    try:
        elem_class = the_elem["additional_class"]
    except:
        elem_class = ''

    # get url of ols lookup for ontology fields
    ols_url = get_ols_url()

    if default_value is None:
        elem_value = the_elem["default_value"]
    else:
        elem_value = default_value

    elem_control = the_elem["control"].lower()
    option_values = ""
    html_tag = ""

    html_all_tags = HTML_TAGS

    if (elem_control == "select" or elem_control == "copo-multi-select") and the_elem["option_values"]:
        for ov in the_elem["option_values"]:
            if isinstance(ov, str):
                sv = ov
                sl = ov
            elif isinstance(ov, dict):
                sv = ov['value']
                sl = ov['label']

            selected = ""
            if elem_value:
                if elem_control == "select" and elem_value == sv:
                    selected = "selected"
                elif elem_control == "copo-multi-select" and sv in elem_value.split(","):
                    selected = "selected"
            option_values += "<option value='{sv!s}' {selected!s}>{sl!s}</option>".format(**locals())

    if elem_control == "copo-multi-search" and the_elem["elem_json"]:
        elem_json = json.dumps(the_elem["elem_json"])

    if the_elem["hidden"] == "true":
        html_tag = html_all_tags["hidden"].format(**locals())
    else:
        if elem_control in [x.lower() for x in list(html_all_tags.keys())]:
            if elem_control == "ontology term" or elem_control == "characteristic/factor":
                v = ''
                termAccession = ''
                termSource = ''
                annotationValue = ''
                value = ''
                unit = ''
                if isinstance(elem_value, list):
                    elem_value = elem_value[0]

                if isinstance(elem_value, dict):
                    if "key" in elem_value:
                        annotationValue = elem_value["key"]
                    if "termSource" in elem_value:
                        termSource = elem_value["termSource"]
                    if "termAccession" in elem_value:
                        termAccession = elem_value["termAccession"]
                    if "value" in elem_value:
                        value = elem_value["value"]
                    if "unit" in elem_value:
                        unit = elem_value["unit"]
                    if "annotationValue" in elem_value:
                        annotationValue = elem_value["annotationValue"]
                elif isinstance(elem_value, str):
                    annotationValue = elem_value

            html_tag = html_all_tags[elem_control].format(**locals())

    return html_tag


'''
@register.filter("partial_submission_bannerpartial_submission_banner")
def do_partial_submission_banner(val):
    html = ''
    if val is None:
        pass
    else:
        html = '<div class="page-header warning-banner">' \
               '<div class="icon">' \
               '<i class="fa fa-cloud-upload fa-4x"></i>' \
               '</div>' \
               '<div class="resume-text">' \
               '<h3 class="h3">Resume Submission?</h3>' \
               'It looks like you were in the middle of a submission. <a href="' + val[0][
                   'url'] + '"> Click here to resume</a>' \
                            '</div>' \
                            '</div>'
    return format_html(html)
'''
