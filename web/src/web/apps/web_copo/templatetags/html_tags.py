__author__ = 'tonietuk'

import json
import copy
from uuid import uuid4
from django import template
from django.core.urlresolvers import reverse
from django_tools.middlewares import ThreadLocal
from web.apps.web_copo.lookup.lookup import HTML_TAGS
import web.apps.web_copo.lookup.lookup as lkup
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from dal.copo_base_da import DataSchemas
from dal.copo_da import ProfileInfo, Profile, DAComponent
from allauth.socialaccount import providers

register = template.Library()

# dictionary of components table id, gotten from the UI
table_id_dict = dict(publication="publication_table",
                     person="person_table",
                     sample="sample_table",
                     datafile="datafile_table",
                     annotation="annotation_table",
                     profile="profile_table"
                     )


@register.assignment_tag
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

    if "option_values" in f:
        if isinstance(f["option_values"], list):
            option_values = f["option_values"]
        elif isinstance(f["option_values"], dict):
            if not f.get("option_values").get("callback"):
                option_values = f["option_values"]
            else:
                call_back_function = f.get("option_values", dict()).get("callback", dict()).get("function", str())
                call_back_parameter = f.get("option_values", dict()).get("callback", dict()).get("parameter", str())

                if call_back_function:
                    if call_back_parameter:
                        option_values = getattr(d_utils, call_back_function)(call_back_parameter.format(**locals()))
                    else:
                        option_values = getattr(d_utils, call_back_function)()

    return option_values


@register.filter("generate_copo_form")
def generate_copo_form(component=str(), target_id=str(), component_dict=dict(), message_dict=dict(), profile_id=str()):
    # message_dict templates are defined in the lookup dictionary: "MESSAGES_LKUPS"

    label_dict = get_labels()

    da_object = DAComponent(component=component, profile_id=profile_id)

    form_value = component_dict

    # get record, if in edit mode
    if target_id:
        form_value = da_object.get_record(target_id)

    form_schema = list()

    # get schema fields
    for f in da_object.get_schema().get("schema_dict"):
        if f.get("show_in_form", True):

            # if required, resolve data source for select-type controls,
            # i.e., if a callback is defined on the 'option_values' field
            if "option_values" in f:
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
def generate_component_records(component=str(), profile_id=str(), label_key=str()):
    da_object = DAComponent(component=component, profile_id=profile_id)
    component_records = list()
    schema = da_object.get_schema().get("schema_dict")

    # if label_key is not provided, we will assume the first element in the schema to be the label_key

    if not label_key:
        label_key = schema[0]["id"].split(".")[-1]

    for record in da_object.get_all_records():
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


@register.filter("generate_table_records")
def generate_table_records(profile_id=str(), component=str()):
    # generates component records for for building an UI table

    # instantiate data access object
    da_object = DAComponent(profile_id, component)

    # get records
    records = da_object.get_all_records()

    # get schema
    schema = da_object.get_schema().get("schema_dict")

    data_set = list()
    columns = list()

    # get columns
    for f in schema:
        if f.get("show_in_table", True):
            columns.append(dict(data=f["id"].split(".")[-1],
                                title=f.get("label", str())))

    # add record id column
    columns.append(dict(data="record_id"))

    # get records
    for pr in records:
        option = dict()

        for f in schema:
            if f.get("show_in_table", True):
                # add data
                option[f["id"].split(".")[-1]] = resolve_control_output(pr, f)

        # add record id
        option["record_id"] = str(pr["_id"])

        data_set.append(option)

    return_dict = dict(dataSet=data_set,
                       columns=columns,
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

        data_set.append(temp_set)

    return_dict = dict(dataSet=data_set)

    return return_dict


@register.filter("generate_attributes")
def generate_attributes(component, target_id):
    da_object = DAComponent(component=component)
    schema = da_object.get_schema().get("schema_dict")

    columns = list()
    record = da_object.get_record(target_id)

    filter_attributes = dict(component=component)  # holds parameters for filtering out display columns

    if component == "sample":  # sample decides what to show based on sample type
        sample_types = list()

        for s_t in d_utils.get_sample_type_options():
            sample_types.append(s_t["value"])

        sample_type = record.get("sample_type", str())
        filter_attributes["sample_types"] = sample_types
        filter_attributes["sample_type"] = sample_type

    for f in schema:
        # get relevant attributes based on filter
        filter_attributes["elem"] = f

        if attribute_filter(filter_attributes):

            # get short-form id
            f["id"] = f["id"].split(".")[-1]
            col = dict(title=f["label"], id=f["id"], control=f["control"])

            # if required, resolve data source for select-type controls,
            # i.e., if a callback is defined on the 'option_values' field
            if "option_values" in f:
                f["option_values"] = get_control_options(f)

            col["data"] = resolve_control_output(record, f)

            columns.append(col)

    return columns


def attribute_filter(filter_attributes):
    """
    filters attribute for display
    :param filter_attributes:
    :return:
    """
    clear_attribute = True

    elem = filter_attributes["elem"]
    component = filter_attributes["component"]

    if not elem.get("show_as_attribute", False):
        return False

    # do component-specific test here
    if component == "sample":
        if filter_attributes["sample_type"] not in elem.get("specifications", filter_attributes["sample_types"]):
            return False

    return clear_attribute


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
    func_map["copo-multi-search"] = resolve_copo_multi_search_data
    func_map["select"] = resolve_select_data
    func_map["copo-button-list"] = resolve_select_data
    func_map["ontology term"] = resolve_ontology_term_data
    func_map["copo-select"] = resolve_copo_select_data
    func_map["datetime"] = resolve_datetime_data
    func_map["datafile-description"] = resolve_description_data
    func_map["date-picker"] = resolve_datepicker_data
    func_map["copo-duration"] = resolve_copo_duration_data

    if elem["control"].lower() in func_map:
        resolved_data = func_map[elem["control"].lower()](data, elem)
    else:
        resolved_data = resolve_default_data(data)

    return resolved_data


def resolve_description_data(data, elem):
    resolved_value = list()

    # get attributes
    attributes = data.get("attributes", dict())

    # retrieve stages data
    for stage in data.get("stages", list()):
        ref = stage.get("ref", str())
        stage_data = attributes.get(ref, dict())

        if stage_data:
            stage_dict = dict(
                ref=ref,
                title=stage.get("title", str()),
                data=list()
            )

            # drill down to stage items
            for item in stage.get("items", list()):
                item_id = item.get("id", str())
                item_id = item_id.split(".")[-1]
                item_dict = dict(label=item.get("label", str()), data=str())

                resolved_value_sub = str()
                if item_id in stage_data:
                    # resolve array data types
                    if item.get("type", str()) == "array":
                        resolved_value_sub = list()
                        data = stage_data[item_id]
                        for d in data:
                            resolved_value_sub.append(get_resolver(d, item))
                    else:
                        # non-array types
                        resolved_value_sub = get_resolver(stage_data[item_id], item)

                    item_dict["data"] = resolved_value_sub

                stage_dict.get("data").append(item_dict)

            resolved_value.append(stage_dict)

    return resolved_value


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
                a[f["label"]] = resolve_ontology_term_data(data[f["id"].split(".")[-1]], elem)
                resolved_data.append(a)

    return str(resolved_data)  # turn this casting off after merge


def resolve_phenotypic_characteristics_data(data, elem):
    schema = d_utils.get_copo_schema("phenotypic_variables")

    resolved_data = list()

    for f in schema:
        if f.get("show_in_table", True):
            a = dict()
            if f["id"].split(".")[-1] in data:
                a[f["label"]] = resolve_ontology_term_data(data[f["id"].split(".")[-1]], elem)
                resolved_data.append(a)

    return str(resolved_data)  # turn this casting off after merge


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

    if option_values and data:
        for option in option_values:
            if isinstance(option, str):
                sv = option
                sl = option
            elif isinstance(option, dict):
                sv = option['value']
                sl = option['label']

            for d_v in data.split(","):
                if str(sv) == str(d_v):
                    resolved_value = resolved_value + [sl]

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
        resolved_value = data.strftime('%d %b, %Y, %H:%M:%S')
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
    req = ThreadLocal.get_current_request()
    protocol = req.META['wsgi.url_scheme']
    r = req.build_absolute_uri()
    ols_url = protocol + '://' + ThreadLocal.get_current_request().META['HTTP_HOST'] + reverse(
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
