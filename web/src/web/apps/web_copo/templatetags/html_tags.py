__author__ = 'tonietuk'
 
import json
from uuid import uuid4
from django import template
from django.core.urlresolvers import reverse
from django_tools.middlewares import ThreadLocal
from web.apps.web_copo.lookup.lookup import HTML_TAGS
import web.apps.web_copo.lookup.lookup as lkup
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from dal.copo_base_da import DataSchemas
from dal.copo_da import ProfileInfo, Profile, DAComponent
 
register = template.Library()
 
table_id_dict = dict(publication="publication_table",
                     person="person_table",
                     sample="sample_table",
                     datafile="datafile_table"
                     )
 
 
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
    # option values are typically defined as a list of option,
    # or in some special cases (e.g., 'copo-multi-search'),
    # as JSON (dictionary). However, the options could also be resolved or generated dynamically
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
def generate_copo_form(component=str(), target_id=str(), component_dict=dict(), message_dict=dict()):
    # message_dict templates are defined in the lookup dictionary, "MESSAGES_LKUPS"
 
    label_dict = dict(publication="Publication",
                      person="Person",
                      sample="Sample",
                      source="Source",
                      profile="Profile"
                      )
 
    form_value = component_dict
    form_schema = list()
 
    da_object = DAComponent(component=component)
 
    # get schema fields
    for f in da_object.get_schema().get("schema_dict"):
        if f.get("show_in_form", True):
 
            # if required, resolve data source for select-type controls,
            # i.e., if a callback is defined on the 'option_values' field
 
            if "option_values" in f:
                f["option_values"] = get_control_options(f)
 
            form_schema.append(f)
 
    # get record, if in edit context...and set form title
 
    if target_id:
        form_value = da_object.get_record(target_id)
 
    # get all records: used in the UI for 'cloning' purposes
    component_records = list()
    for record in da_object.get_all_records():
        rec_dict = dict(_id=str(record["_id"]))
        for f in da_object.get_schema().get("schema_dict"):
            if f.get("show_in_form", True):
                key_split = f["id"].split(".")[-1]
                rec_dict[key_split] = record.get(key_split, d_utils.default_jsontype(f.get("type", str())))
 
        component_records.append(rec_dict)
 
    return dict(component_name=component,
                form_label=label_dict.get(component, str()),
                form_value=form_value,
                target_id=target_id,
                form_schema=form_schema,
                form_message=message_dict,
                component_records=component_records
                )
 
 
@register.filter("generate_copo_table_data")
def generate_copo_table_data(profile_id=str(), component=str()):
    # This method generates the 'json' for building an UI table
 
    # define button
    button_templates = d_utils.get_button_templates()
 
    common_btn_dict = dict(row_btns=[button_templates['edit_row'], button_templates['delete_row']],
                           global_btns=[button_templates['delete_global']])
 
    buttons_dict = dict(publication=common_btn_dict,
                        person=common_btn_dict,
                        sample=common_btn_dict,
                        source=common_btn_dict,
                        profile=common_btn_dict,
                        datafile=dict(
                            row_btns=[button_templates['info_row'], button_templates['describe_row'],
                                      button_templates['delete_row']],
                            global_btns=[button_templates['describe_global'], button_templates['undescribe_global']])
                        )
 
    # instantiate data access object
    da_object = DAComponent(profile_id, component)
 
    # get records
    records = da_object.get_all_records()
 
    columns = list()
    dataSet = list()
 
    # headers
    for f in da_object.get_schema().get("schema_dict"):
        if f.get("show_in_table", True):
            columns.append(dict(title=f["label"]))
 
    columns.append(dict(title=str()))  # extra 'blank' header for record actions column
 
    # data
    for rec in records:
        row = list()
        for f in da_object.get_schema().get("schema_dict"):
            if f.get("show_in_table", True):
                row.append(resolve_control_output(rec, f))
 
        row.append(str(rec["_id"]))  # last element in a row exposes the id of the record
        dataSet.append(row)
 
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
 
    return data_set
 
 
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
    func_map = dict(
        resolve_copo_sample_source_data=resolve_copo_sample_source_data,
        resolve_copo_characteristics_data=resolve_copo_characteristics_data,
        resolve_copo_comment_data=resolve_copo_comment_data,
        resolve_copo_multi_select_data=resolve_copo_multi_select_data,
        resolve_copo_multi_search_data=resolve_copo_multi_search_data,
        resolve_select_data=resolve_select_data,
        resolve_ontology_term_data=resolve_ontology_term_data,
        resolve_copo_select_data=resolve_copo_select_data,
        resolve_datetime_data=resolve_datetime_data,
        resolve_description_data=resolve_description_data
    )
    resolver_list = [
        dict(control="copo-sample-source", resolver="resolve_copo_sample_source_data"),
        dict(control="copo-characteristics", resolver="resolve_copo_characteristics_data"),
        dict(control="copo-comment", resolver="resolve_copo_comment_data"),
        dict(control="copo-multi-select", resolver="resolve_copo_multi_select_data"),
        dict(control="copo-multi-search", resolver="resolve_copo_multi_search_data"),
        dict(control="select", resolver="resolve_select_data"),
        dict(control="ontology term", resolver="resolve_ontology_term_data"),
        dict(control="copo-select", resolver="resolve_copo_select_data"),
        dict(control="datetime", resolver="resolve_datetime_data"),
        dict(control="datafile-description", resolver="resolve_description_data")
    ]
 
    resolver = [x for x in resolver_list if x['control'] == elem["control"].lower()]
    if resolver:
        resolver = func_map[resolver[0]["resolver"]](data, elem)
    else:
        resolver = resolve_default_data(data)
 
    return resolver
 
 
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
                item_dict = dict(label=item.get("label", str()), data=str())
 
                if item_id in stage_data:
                    # use item control and determine how to retrieve item data
                    item_dict["data"] = get_resolver(stage_data[item_id], item)
 
                stage_dict.get("data").append(item_dict)
 
            resolved_value.append(stage_dict)
 
    return resolved_value
 
 
def resolve_copo_sample_source_data(data, elem):
    option_values = None
    resolved_value = str()
    if "option_values" in elem:
        option_values = get_control_options(elem)
 
    if option_values and data:
        value_field = option_values.get("value_field", str())
        label_field = option_values.get("label_field", str())
        for option in option_values["options"]:
            if option.get(value_field, str()) == data:
                resolved_value = option.get(label_field, str())
 
    return resolved_value
 
 
def resolve_copo_characteristics_data(data, elem):
    schema = DataSchemas("COPO").get_ui_template().get("copo").get("material_attribute_value").get("fields")
 
    resolved_data = list()
 
    for f in schema:
        if f.get("show_in_table", True):
            a = dict()
            if f["id"].split(".")[-1] in data:
                a[f["label"]] = resolve_ontology_term_data(data[f["id"].split(".")[-1]], elem)
                resolved_data.append(a)
 
    return resolved_data
 
 
def resolve_copo_comment_data(data, elem):
    schema = DataSchemas("COPO").get_ui_template().get("copo").get("comment").get("fields")
 
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