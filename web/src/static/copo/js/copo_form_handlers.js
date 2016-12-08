/**Created by etuka on 06/05/2016.
 * contains functions for generating form html from JSON-based tags
 */

var olsURL = ""; // url of ols lookup for ontology fields
var copoSchemas = {};
var copoFormsURL = "/copo/copo_forms/";
var copoVisualsURL = "/copo/copo_visualize/"; //visualise it
var globalDataBuffer = {};
var htmlForm = $('<div/>'); //global form div
var htmlFormSource = $('<div/>'); // form div for source
var componentRecords = Object(); //components records...used for validation
var formMode = "add";
var componentData = null;

$(document).ready(function () {
    var csrftoken = $.cookie('csrftoken');

    //get urls
    olsURL = $("#elastic_search_ajax").val();

    //retrieve and set form resources
    $.ajax({
        url: copoFormsURL,
        type: "POST",
        headers: {'X-CSRFToken': csrftoken},
        data: {
            'task': 'resources'
        },
        success: function (data) {
            copoSchemas = data.copo_schemas;
        },
        error: function () {
            alert("Couldn't retrieve form resources!");
        }
    });

    //handle event for form calls
    $(document).on("click", ".new-form-call", function (e) {//call to generate form
        e.preventDefault();

        var component = "";
        try {
            var component = $(this).attr("data-component");
        } catch (err) {
            console.log(err);
        }

        var errorMsg = "Couldn't build " + component + " form!";

        if (component == 'annotation') {
            $('#processing_div').hide()
            $('#file_picker_modal').modal('show')
            $("#form_submit_btn").on('click', function () {
                var formData = new FormData();
                formData.append('file', $('#InputFile')[0].files[0]);
                var csrftoken = $.cookie('csrftoken');
                var url = "/api/upload_annotation_file/"
                $.ajax({
                    url: url,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    data: formData,
                    processData: false,
                    contentType: false,
                    dataType: 'json'
                }).done(function (e) {
                    $('#annotation_table_wrapper').hide()
                    $('#annotation_content').show()
                    $('#annotation_content').html(e.html)

                    $.cookie('document_id', e._id.$oid, {expires: 1, path: '/',});
                    setup_annotator()
                    $('#file_picker_modal').modal('hide')
                });
            })
        }
        else {

            $.ajax({
                url: copoFormsURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': 'form',
                    'component': component
                },
                success: function (data) {
                    json2HtmlForm(data);
                    componentData = data;
                },
                error: function () {
                    alert(errorMsg);
                }
            });
        }
    });


    $(document).on("click", ".popover .copo-close", function () {
        $(this).parents(".popover").popover('destroy');
    });


}); //end of document ready

//map controls to rendering functions
var controlsMapping = {
    "text": "do_text_ctrl",
    "textarea": "do_textarea_ctrl",
    "hidden": "do_hidden_ctrl",
    "copo-select": "do_copo_select_ctrl",
    "ontology term": "do_ontology_term_ctrl",
    "select": "do_select_ctrl",
    "copo-multi-search": "do_copo_multi_search_ctrl",
    "copo-multi-select": "do_copo_multi_select_ctrl",
    "copo-comment": "do_copo_comment_ctrl",
    "copo-characteristics": "do_copo_characteristics_ctrl",
    "copo-sample-source": "do_copo_sample_source_ctrl",
    "copo-sample-source-2": "do_copo_sample_source_ctrl_2",
    "oauth_required": "do_oauth_required",
    "copo-button-list": "do_copo_button_list_ctrl",
    "copo-item-count": "do_copo_item_count_ctrl"
};

function json2HtmlForm(data) {
    var dataCopy = $.extend(true, Object(), data.form.component_records);

    //remove record with target_id from this list...to enable unique validation in edit mode
    var delKey = null;
    $.each(dataCopy, function (key, val) {
        if (val._id == data.form.target_id) {
            delKey = key;
            return false;
        }

    });

    delete dataCopy[delKey];
    componentRecords[data.form.component_name] = dataCopy;


    //tidy up before closing the modal
    var doTidyClose = {
        closeIt: function (dialogRef) {
            $('.popover').popover('destroy'); //hide any shown popovers
            htmlForm.empty(); //clear form
            htmlFormSource.empty(); //clear form
            dialogRef.close();
        }
    };

    var dialog = new BootstrapDialog({
        type: BootstrapDialog.TYPE_PRIMARY,
        size: BootstrapDialog.SIZE_NORMAL,
        title: function () {
            return $('<span>' + get_form_title(data) + '</span>');
        },
        closable: false,
        animate: true,
        onhide: function (dialogRef) {
            //remove all dangling popovers
            $('.popover').popover('destroy');
        },
        onshown: function (dialogRef) {

            //prevent enter keypress from submitting form automatically
            $("form").keypress(function (e) {
                //Enter key
                if (e.which == 13) {
                    return false;
                }
            });

            //custom validators
            custom_validate(htmlForm.find("form"));

            //validate on submit event
            htmlForm.find("form").validator().on('submit', function (e) {
                if (e.isDefaultPrevented()) {
                    reset_custom_fields_validate();
                    return false;
                } else {
                    e.preventDefault();

                    if (!global_form_validate(data.form.form_schema, htmlForm.find("form"))) {
                        return false;
                    }

                    save_form(data.form);
                    dialogRef.close();
                }
            });

            refresh_form_aux_controls();

            setup_formelement_hint($('input[name="helptips-chk"]'), htmlForm.find("form").find(":input"));

        },
        buttons: [
            {
                label: 'Cancel',
                action: function (dialogRef) {
                    doTidyClose["closeIt"](dialogRef);
                }
            },
            {
                icon: 'glyphicon glyphicon-save',
                label: 'Save',
                id: 'global_form_save_btn',
                cssClass: 'btn-primary',
                action: function (dialogRef) {
                    validate_forms(htmlForm.find("form"));
                }
            }
        ]
    });

    var $dialogContent = $('<div/>');

    var form_help_div = set_up_form_help_div(data);
    var form_message_div = get_form_message(data);

    var form_body_div = set_up_form_body_div(data);

    $dialogContent.append(form_help_div).append(form_message_div).append(form_body_div);
    dialog.realize();
    dialog.setMessage($dialogContent);
    dialog.open();


} //end of json2HTMLForm

function reset_custom_fields_validate() {
    $('.copo-select').each(function () {
        if (this.id) {
            $(this).css("display", "none");
        }
    });
}

function make_custom_fields_validate() {
    $('.copo-select').each(function () {
        if (this.id && $(this).val().trim() == "") {
            $(this).removeAttr("style");
            $(this).focus();
        }
    });
}

function build_form_body(data) {
    var formJSON = data.form;
    var formValue = formJSON.form_value;

    //clean slate for form
    var formCtrl = htmlForm.find("form");
    if (formCtrl.length) {
        formCtrl.empty();
    } else {
        formCtrl = $('<form/>',
            {
                "data-toggle": "validator"
            });
    }

    //generate controls given component schema
    for (var i = 0; i < formJSON.form_schema.length; ++i) {

        var formElem = formJSON.form_schema[i];

        var control = formElem.control;
        var elemValue = null;

        if (formValue) {
            var elem = formElem.id.split(".").slice(-1)[0];
            if (formValue[elem]) {
                elemValue = formValue[elem];
            }
        }

        if (formElem.hidden == "true") {
            control = "hidden";
        }

        try {
            formCtrl.append(dispatchFormControl[controlsMapping[control.toLowerCase()]](formElem, elemValue));
        }
        catch (err) {
            console.log(err);
            formCtrl.append('<div class="form-group copo-form-group"><span class="text-danger">Form Control Error</span> (' + formElem.label + '): Cannot resolve form control!</div>');
        }
    }

    return htmlForm.append(formCtrl);

}


function get_form_message(data) {
    var messageDiv = $('<div/>',
        {
            style: "display:none;"
        });

    var message_text = null;
    var message_type = null;


    try {
        message_text = data.form.form_message.text;
        message_type = data.form.form_message.type;

    } catch (err) {
    }

    if (message_text && message_type) {
        messageDiv = $('<div/>',
            {
                html: '<a href="#" class="close" data-dismiss="alert" aria-label="close">&times;</a><i class="' + data.form.form_message.icon_class + '" style="margin-right: 5px;"></i>' + data.form.form_message.text,
                class: "alert alert-" + data.form.form_message.type
            });
    }

    return $('<div/>',
        {
            class: "row"
        }).append($('<div/>',
        {
            class: "col-sm-12 col-md-12 col-lg-12"
        }).append(messageDiv));
}

function get_form_title(data) {
    var formTitle = "";

    if (data.form.target_id) {
        formTitle = "Edit " + data.form.form_label;
        formMode = "edit";
    } else {
        formTitle = "Add " + data.form.form_label;
        formMode = "add";
    }

    return formTitle;
}

function get_help_ctrl() {
    var helpCtrl = $('<div/>',
        {
            html: '<span style="padding:6px;">Help tips</span><input type="checkbox" name="helptips-chk">',
            class: "tips-switch-form-div form-group pull-right"
        });

    return helpCtrl;
}

function set_up_help_ctrl() {

    // now set up switch button to support the tool tips
    $("[name='helptips-chk']").bootstrapSwitch(
        {
            size: "mini",
            onColor: "primary",
            state: true
        });

    $('input[name="helptips-chk"]').on('switchChange.bootstrapSwitch', function (event, state) {
        if (!state) {
            //remove all dangling popovers
            $('.popover').popover('destroy');
        }
    });
}

function set_up_form_help_div(data) {
    var ctrlDiv = $('<div/>',
        {
            class: "row",
            style: "margin-bottom:20px;"
        });

    var cloneCol = $('<div/>',
        {
            class: "col-sm-7 col-md-7 col-lg-7"
        }).append(set_up_clone_ctrl(data));

    var helpCtrl = $('<div/>',
        {
            class: "col-sm-5 col-md-5 col-lg-5"
        }).append(get_help_ctrl());

    return ctrlDiv.append(cloneCol).append(helpCtrl);
}

function set_up_form_body_div(data) {
    var formBodyDiv = $('<div/>',
        {
            class: "row"
        }).append($('<div/>',
        {
            id: "copo_component_forms",
            class: "col-sm-12 col-md-12 col-lg-12"
        }).append(htmlForm).append(htmlFormSource));

    //build main form
    build_form_body(data);

    return formBodyDiv;
}

function set_up_clone_ctrl(data) {
    var ctrlsDiv = $('<div/>',
        {
            style: "padding:1px; margin-bottom:-15px;"
        });

    var form_values = Object();


    //build hidden fields to hold selected options, and supply control data
    var hiddenValuesCtrl = $('<input/>',
        {
            type: "hidden",
            class: "copo-multi-values",
            "data-maxItems": 1, //makes this a single select box, instead of the default multiple
            change: function (event) {
                event.preventDefault();

                data.form.form_value = form_values[$(this).val()];

                build_form_body(data);

                refresh_form_aux_controls();

                setup_formelement_hint($('input[name="helptips-chk"]'), htmlForm.find("form").find(":input"));

            }
        });

    //build select
    var selectCtrl = $('<select/>',
        {
            class: "input-copo copo-multi-select",
            placeholder: "Clone a " + data.form.form_label + " record...",
        });

    var showCloneCtrl = false;

    var min = 10000;
    var max = 99999;

    if (data.form.component_records.length > 0 && data.form.clonable) {
        showCloneCtrl = true;

        //construct options
        var labelElem = data.form.form_schema[0].id.split(".").slice(-1)[0];

        $('<option value=""></option>').appendTo(selectCtrl);

        for (var i = 0; i < data.form.component_records.length; ++i) {
            var option = data.form.component_records[i];
            var lbl = option[labelElem];
            var vl = option["_id"];

            //generate unique characters to append to label elem
            var rand_postfix = (Math.floor(Math.random() * (max - min + 1)) + min).toString();
            option[labelElem] = option[labelElem] + "_CLONED_" + rand_postfix;

            form_values[vl] = option;

            $('<option value="' + vl + '">' + lbl + '</option>').appendTo(selectCtrl);
        }
    }

    ctrlsDiv.append(selectCtrl).append(hiddenValuesCtrl);

    var cloneCtrl = form_div_ctrl().append(ctrlsDiv);

    if (!showCloneCtrl) {
        cloneCtrl = '';
    }

    return cloneCtrl;
}

function refresh_form_aux_controls() {
    //refresh controls
    refresh_tool_tips();

    //set up help tips
    set_up_help_ctrl();

    //refresh form validator
    refresh_validator(htmlForm.find("form"));
    refresh_validator(htmlFormSource.find("form"));
}

function set_validation_markers(formElem, ctrl) {
    //validation markers

    var validationMarkers = Object();
    var errorHelpDiv = "";

    //required marker
    if (formElem.hasOwnProperty("required") && (formElem.required.toString() == "true")) {
        ctrl.attr("required", true);
        ctrl.attr("data-error", "The " + formElem.label + " is required!");

        errorHelpDiv = $('<div></div>').attr({class: "help-block with-errors"});
    }

    //unique marker...
    if (formElem.hasOwnProperty("unique") && (formElem.unique.toString() == "true")) {
        ctrl.attr("data-unique", "unique");
        ctrl.attr('data-unique-error', "The " + formElem.label + " value already exists!");

        errorHelpDiv = $('<div></div>').attr({class: "help-block with-errors"});
    }

    //email marker...
    if (formElem.hasOwnProperty("email") && (formElem.email.toString() == "true")) {
        ctrl.attr("data-email", "email");
        ctrl.attr('data-email-error', "Please enter a valid value for the " + formElem.label);

        errorHelpDiv = $('<div></div>').attr({class: "help-block with-errors"});
    }

    validationMarkers['errorHelpDiv'] = errorHelpDiv;
    validationMarkers['ctrl'] = ctrl;

    return validationMarkers;
}

//form controls
var dispatchFormControl = {
    do_text_ctrl: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        var txt = $('<input/>',
            {
                type: "text",
                class: "input-copo form-control",
                id: formElem.id,
                name: formElem.id
            });

        //set validation markers
        var vM = set_validation_markers(formElem, txt);

        ctrlsDiv.append(txt);
        ctrlsDiv.append(vM.errorHelpDiv);

        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_textarea_ctrl: function (formElem, elemValue) {

        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        var txt = $('<textarea/>',
            {
                class: "form-control",
                rows: 4,
                cols: 40,
                id: formElem.id,
                name: formElem.id
            });

        //set validation markers
        var vM = set_validation_markers(formElem, txt);

        ctrlsDiv.append(txt);
        ctrlsDiv.append(vM.errorHelpDiv);

        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_select_ctrl: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        //build select
        var selectCtrl = $('<select/>',
            {
                class: "form-control input-copo",
                id: formElem.id,
                name: formElem.id
            });

        if (formElem.option_values) {
            for (var i = 0; i < formElem.option_values.length; ++i) {
                var option = formElem.option_values[i];
                var lbl = "";
                var vl = "";
                if (typeof option === "string") {
                    lbl = option;
                    vl = option;
                } else if (typeof option === "object") {
                    lbl = option.label;
                    vl = option.value;
                }

                $('<option value="' + vl + '">' + lbl + '</option>').appendTo(selectCtrl);
            }
        }

        ctrlsDiv.append(selectCtrl);

        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_copo_characteristics_ctrl: function (formElem, elemValue) {
        var characteristicsSchema = copoSchemas.characteristics_schema;

        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        for (var i = 0; i < characteristicsSchema.length; ++i) {
            var mg = "margin-left:5px;";
            if (i == 0) {
                mg = '';
            }
            var fv = formElem.id + "." + characteristicsSchema[i].id.split(".").slice(-1)[0];

            if (characteristicsSchema[i].hidden == "false") {
                var sp = $('<span/>',
                    {
                        style: "display: inline-block; " + mg
                    });

                //get ontology ctrl
                var ontologyCtrlObject = get_ontology_span(sp, characteristicsSchema[i]);

                ontologyCtrlObject.find(":input").each(function () {
                    if (this.id) {
                        this.id = fv + "." + this.id;
                    }

                    //set placeholder text
                    if ($(this).hasClass("ontology-field")) {
                        $(this).attr("placeholder", characteristicsSchema[i].label.toLowerCase());
                    }
                });

                ctrlsDiv.append(ontologyCtrlObject);

            } else {
                ctrlsDiv.append($('<input/>',
                    {
                        type: "hidden",
                        id: fv,
                        name: fv
                    }));
            }
        }

        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_copo_comment_ctrl: function (formElem, elemValue) {
        var commentSchema = copoSchemas.comment_schema;

        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        for (var i = 0; i < commentSchema.length; ++i) {
            var mg = "margin-left:5px;";
            if (i == 0) {
                mg = '';
            }

            var fv = commentSchema[i].id.split(".").slice(-1)[0];

            if (commentSchema[i].hidden == "false") {
                var txt = $('<textarea/>',
                    {
                        class: "form-control",
                        rows: 2,
                        cols: 35,
                        placeholder: commentSchema[i].label.toLowerCase(),
                        id: formElem.id + '.' + fv,
                        name: formElem.id + '.' + fv
                    });

                var sp = $('<span/>',
                    {
                        style: "display: inline-block; " + mg
                    });

                sp.append(txt);
                ctrlsDiv.append(sp);

            } else {
                ctrlsDiv.append($('<input/>',
                    {
                        type: "hidden",
                        id: formElem.id + "." + fv,
                        name: formElem.id + "." + fv,
                    }));
            }
        }

        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_ontology_term_ctrl: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        //get ontology ctrl
        var ontologyCtrlObject = get_ontology_span($('<span/>'), formElem);

        ontologyCtrlObject.find(":input").each(function () {
            if (this.id) {
                var tempID = this.id;
                this.id = formElem.id + "." + tempID;
                this.name = formElem.id + "." + tempID;

                if ($(this).hasClass("ontology-field")) {
                    //set validation markers
                    var vM = set_validation_markers(formElem, $(this));
                    $(vM.errorHelpDiv).insertAfter($(this));

                }
            }

        });

        ctrlsDiv.append(ontologyCtrlObject);

        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_copo_multi_select_ctrl: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        //build hidden fields to hold selected options, and supply control data
        var hiddenValuesCtrl = $('<input/>',
            {
                type: "hidden",
                id: formElem.id,
                name: formElem.id,
                class: "copo-multi-values"
            });

        //build select
        var selectCtrl = $('<select/>',
            {
                class: "input-copo copo-multi-select",
                placeholder: "Select " + formElem.label + "...",
                multiple: "multiple"
            });

        if (formElem.option_values) {
            for (var i = 0; i < formElem.option_values.length; ++i) {
                var option = formElem.option_values[i];
                var lbl = "";
                var vl = "";
                if (typeof option === "string") {
                    lbl = option;
                    vl = option;
                } else if (typeof option === "object") {
                    lbl = option.label;
                    vl = option.value;
                }

                $('<option value="' + vl + '">' + lbl + '</option>').appendTo(selectCtrl);
            }
        }

        ctrlsDiv.append(selectCtrl).append(hiddenValuesCtrl);

        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_copo_multi_search_ctrl: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        ctrlsDiv = get_multi_search_span(formElem, ctrlsDiv);

        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_copo_select_ctrl: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        //generate element controls
        var txt = $('<input/>',
            {
                type: "text",
                class: "copo-select input-copo",
                id: formElem.id,
                name: formElem.id,
            });

        //set validation markers
        var vM = set_validation_markers(formElem, txt);

        ctrlsDiv.append(txt);
        ctrlsDiv.append(vM.errorHelpDiv);


        return get_form_ctrl(ctrlsDiv.clone(), formElem, elemValue);
    },
    do_copo_sample_source_ctrl: function (formElem, elemValue) {

        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        formElem["data_maxItems"] = 1; //enforces single item selection rather than the default multiple

        ctrlsDiv = get_multi_search_span(formElem, ctrlsDiv);

        if (Object.prototype.toString.call(elemValue) === '[object Array]' && elemValue.length > 1) {
            elemValue = elemValue.toString();
        }


        //resolve control values
        var ctrlObjects = resolve_ctrl_values(ctrlsDiv.clone(), 0, formElem, elemValue);
        var ctrlsWithValuesDiv = ctrlObjects.ctrlsWithValuesDiv;

        $("#global_form_save_btn").prop('disabled', false); //make sure outer save button is enabled by default

        var addBtn = $('<button/>',
            {
                style: "border-radius:0;",
                class: "btn btn-xs btn-primary create-sample-source-btn",
                html: '<i class="fa fa-plus-circle"></i> Create & Assign New Source',
                click: function (event) {
                    event.preventDefault();

                    var funcParams = Object();
                    funcParams['formElem'] = formElem;
                    funcParams['formValue'] = null;
                    funcParams['buttonObject'] = $(this);
                    funcParams['ctrlsDiv'] = ctrlsDiv;
                    funcParams['ctrlsWithValuesDiv'] = ctrlsWithValuesDiv;

                    if (htmlFormSource.find("form").length) {
                        hide_source_form(funcParams);
                    } else {
                        show_source_form(funcParams);
                    }
                }
            });

        var addbtnDiv = $('<div/>',
            {
                class: "col-sm-12 col-md-12 col-lg-12"
            }).append(addBtn);

        var addbtnDivRow = $('<div/>',
            {
                class: "row",
            }).append(addbtnDiv);

        return form_div_ctrl()
            .append(form_label_ctrl(formElem.label, formElem.id))
            .append(ctrlsWithValuesDiv)
            .append(form_help_ctrl(formElem.help_tip))
            .append(addbtnDivRow)
    },
    do_copo_sample_source_ctrl_2: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        formElem["data_maxItems"] = 1; //enforces single item selection rather than the default multiple

        ctrlsDiv = get_multi_search_span(formElem, ctrlsDiv);

        if (Object.prototype.toString.call(elemValue) === '[object Array]' && elemValue.length > 1) {
            elemValue = elemValue.toString();
        }


        //resolve control values
        var ctrlObjects = resolve_ctrl_values(ctrlsDiv.clone(), 0, formElem, elemValue);
        var ctrlsWithValuesDiv = ctrlObjects.ctrlsWithValuesDiv;


        //build source creation controls

        var sourceBtnDiv = $('<div/>',
            {
                id: "sourceFormCollapsible",
                class: "collapse"
            });

        var sourceButton = $('<button/>',
            {
                type: "button",
                style: "border-radius:0;",
                class: "btn btn-xs btn-primary create-sample-source-btn",
                html: '<i class="fa fa-plus-circle"></i> Create & Assign New Source',
                click: function (event) {
                    event.preventDefault();

                    var divState = sourceBtnDiv.is(":visible");

                    if (!htmlFormSource.find("form").length && divState) {
                        divState = false;
                    }

                    if (divState) {//already open, will be closing in a bit
                        $(this).find("i").attr({class: "fa fa-plus-circle"});
                        sourceBtnDiv.collapse('hide');
                    } else {//already close, will be opening in a bit
                        $(this).find("i").attr({class: "fa fa-minus-circle"});
                        sourceBtnDiv.empty();
                        htmlFormSource = $('<div/>');

                        var funcParams = Object();
                        funcParams['formElem'] = formElem;
                        funcParams['formValue'] = null;
                        funcParams['buttonObject'] = $(this);
                        funcParams['ctrlsDiv'] = ctrlsDiv;
                        funcParams['ctrlsWithValuesDiv'] = ctrlsWithValuesDiv;

                        build_source_form(funcParams);
                        sourceBtnDiv.append(htmlFormSource);
                        sourceBtnDiv.collapse('show');

                        refresh_tool_tips();
                    }
                }
            });

        var sourceCtrlDiv = $('<div/>').append(sourceButton).append(sourceBtnDiv);


        return form_div_ctrl()
            .append(form_label_ctrl(formElem.label, formElem.id))
            .append(ctrlsWithValuesDiv)
            .append(form_help_ctrl(formElem.help_tip))
            .append(sourceCtrlDiv)

    },
    do_hidden_ctrl: function (formElem, elemValue) {

        var hiddenCtrl = $('<input/>',
            {
                type: "hidden",
                id: formElem.id,
                name: formElem.id,
                value: elemValue
            });

        return hiddenCtrl;

    },
    do_oauth_required: function () {
        return $('<a/>', {
            href: "/rest/forward_to_figshare/",
            html: "Grant COPO access to your Figshare account"
        });
    },
    do_copo_button_list_ctrl: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });


        var btnGroup = $('<div/>',
            {
                class: "btn-group",
                "data-toggle": "buttons"

            });

        var hiddenCtrl = $('<input/>',
            {
                type: "hidden",
                name: formElem.id,
                id: formElem.id,
                value: formElem.option_values[0].value
            });


        for (var i = 0; i < formElem.option_values.length; ++i) {
            var option = formElem.option_values[i];

            var lactive = "";
            if (i == 0) {
                lactive = " active";
            }


            var lbl = $('<label/>',
                {
                    class: "btn copo-active btn-lg btn-default " + lactive,
                    "data-lbl": option.label,
                    "data-desc": option.description,
                    "data-value": option.value,
                    mouseenter: function (evt) {
                        $(this).popover({
                            title: $(this).attr("data-lbl"),
                            content: $(this).attr("data-desc"),
                            container: 'body',
                            trigger: 'hover',
                            html: true,
                            placement: 'right',
                            template: '<div class="popover copo-popover-popover1"><div class="arrow">' +
                            '</div><div class="popover-inner"><h3 class="popover-title copo-popover-title1">' +
                            '</h3><div class="popover-content"><p></p></div></div></div>'
                        });

                        $(this).popover("show");
                    },
                    click: function (evt) {
                        hiddenCtrl.val($(this).attr("data-value"));
                    }
                });


            var rdo = $('<input/>',
                {
                    type: "radio",
                    name: ""
                });

            var spn = $('<span/>',
                {
                    html: option.label
                });

            lbl.append(rdo).append(spn);
            btnGroup.append(lbl);
        }

        ctrlsDiv.append(form_label_ctrl(formElem.label, formElem.id)).append($('<div/>')).append(btnGroup).append(hiddenCtrl);

        return form_div_ctrl()
            .append(form_help_ctrl(formElem.help_tip))
            .append(ctrlsDiv);
    },
    do_copo_button_list_ctrl_old: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>');

        var hiddenCtrl = $('<input/>',
            {
                type: "hidden",
                id: formElem.id,
                name: formElem.id,
                value: elemValue
            });

        ctrlsDiv.append(hiddenCtrl);

        var listGroup = $('<div/>',
            {
                class: "list-group"
            });

        ctrlsDiv.append(form_label_ctrl(formElem.label, formElem.id)).append(listGroup);

        for (var i = 0; i < formElem.option_values.length; ++i) {
            var option = formElem.option_values[i];

            var listGroupTitleHTML = '<h4 class="list-group-item-heading">' + option.label + '</h4>';
            listGroupTitleHTML += '<p class="list-group-item-text" style="line-height: 1.7; font-size: 14px;">' + option.description + '</p>';

            var listDiv = $('<div/>',
                {
                    class: "copo-button-listDiv"
                });

            listGroup.append(listDiv);

            var optionValueElem = $('<input/>',
                {
                    type: "hidden",
                    class: "button-value-elem",
                    name: option.label + "_value",
                    value: option.value
                })

            var btnSample = $('<a/>',
                {
                    class: "list-group-item",
                    title: formElem.help_tip + " " + option.label,
                    style: "border: 1px solid #cccccc;",
                    href: "#",
                    click: function (event) {
                        event.preventDefault();
                        hiddenCtrl.val($(this).parent().find(".button-value-elem").val());

                        $(this).closest(".copo-button-listDiv").siblings('.copo-button-listDiv').removeClass("copo-list-type-selected well well-sm");
                        $(this).closest(".copo-button-listDiv").addClass("copo-list-type-selected well well-sm").css("margin-bottom", "0px");
                    }
                });

            btnSample.append(listGroupTitleHTML);
            listDiv.append(btnSample).append(optionValueElem);

            if (i == 0) {//remember to set this back to 0, for the first element to be selected by default
                hiddenCtrl.val(option.value);
                btnSample.closest(".copo-button-listDiv").addClass("copo-list-type-selected well well-sm").css("margin-bottom", "0px");
            }

        }

        return form_div_ctrl()
            .append(form_help_ctrl(formElem.help_tip))
            .append(ctrlsDiv)

    }
    ,
    do_copo_item_slider_ctrl: function (formElem, elemValue) {

        var ctrlsDiv = $('<div/>',
            {
                class: "range-slider-parent"
            });

        var countCtrl = $('<input/>',
            {
                min: "1",
                max: "100",
                step: "1",
                class: "form-control range-slider",
                "data-orientation": "horizontal",
                value: "1"
            });

        var hiddenCtrl = $('<input/>',
            {
                type: "hidden",
                class: "elem-value",
                id: formElem.id,
                name: formElem.id,
                value: "1"
            });

        var countCtrlDiv = $('<div/>',
            {
                style: "margin-top:15px;",
                title: "Slide to select " + formElem.label
            });

        countCtrlDiv.append(countCtrl);

        var countCtrlOutputDiv = $('<div/>',
            {
                style: "margin-top:20px; text-align:center;"
            });


        var countCtrlBtn = $('<button/>',
            {
                type: "button",
                style: "border-radius:0; background-image:none;",
                class: "btn btn-primary",
                html: formElem.label + ": "
            });

        countCtrlOutputDiv.append(countCtrlBtn);

        var countCtrlOutput = $('<span/>',
            {
                class: "range-slider-output",
                style: "font-size:20px;",
                html: "1"
            });

        countCtrlBtn.append(countCtrlOutput);


        ctrlsDiv.append(form_label_ctrl(formElem.label, formElem.id)).append(countCtrlDiv);
        ctrlsDiv.append(countCtrlOutputDiv);
        ctrlsDiv.append(hiddenCtrl);

        return form_div_ctrl()
            .append(form_help_ctrl(formElem.help_tip))
            .append(ctrlsDiv);
    },
    do_copo_item_count_ctrl: function (formElem, elemValue) {
        var ctrlsDiv = $('<div/>',
            {
                class: "ctrlDIV"
            });

        var errorHelpDiv = $('<div/>',
            {
                class: "help-block with-errors"
            });


        var counter_ctrl = $('<input/>',
            {
                type: "number",
                min: 1,
                class: "input-copo form-control",
                id: formElem.id,
                name: formElem.id,
                value: 1,
                keypress: function (evt) {
                    var charCode = (evt.which) ? evt.which : event.keyCode

                    if (charCode > 31 && (charCode < 48 || charCode > 57)) {
                        $(this).closest(ctrlsDiv).find(".help-block").html('<span style="color: #a94442;">Please enter a number!</span>');
                        $(this).val(1);
                        return false;
                    } else {
                        $(this).closest(ctrlsDiv).find(".help-block").html("");
                        return true;
                    }
                }
            });

        ctrlsDiv.append(form_label_ctrl(formElem.label, formElem.id)).append(counter_ctrl).append(errorHelpDiv);

        return form_div_ctrl()
            .append(form_help_ctrl(formElem.help_tip))
            .append(ctrlsDiv);
    }
};


function form_help_ctrl(tip) {
    return $('<span/>',
        {
            html: tip,
            class: "form-input-help",
            style: "display:none;"
        });
}

function form_div_ctrl() {
    return $('<div/>',
        {
            class: "form-group copo-form-group"
        });
}

function form_label_ctrl(lbl, target) {
    return $('<label/>',
        {
            text: lbl,
            for: target
        });
}

function do_array_ctrls(ctrlsDiv, counter, formElem) {
    var addbtnDiv = $('<div/>',
        {
            style: 'margin-top:2px;'
        });

    var addBtn = $('<button/>',
        {
            style: "border-radius:0;",
            class: "btn btn-xs btn-success",
            type: "button",
            html: '<i class="fa fa-plus-circle"></i> Add ' + formElem.label,
            click: function (event) {
                ++counter;

                get_element_clone(ctrlsDiv, counter).insertBefore(addbtnDiv);

                //refresh controls
                refresh_tool_tips();
            }
        });

    addbtnDiv.append(addBtn);

    return addbtnDiv;
}

function get_element_clone(ctrlsDiv, counter) {
    var ctrlClone = ctrlsDiv.clone();

    ctrlClone.find(':input').each(function () {
        if (this.id) {
            var elemID = this.id;
            $(this).attr("id", elemID + "_" + counter);
            $(this).attr("name", elemID + "_" + counter);
        }
    });

    var cloneDiv = $('<div/>',
        {
            style: 'margin-top:20px;'
        });


    var delDiv = $('<div/>',
        {
            style: 'padding:5px;'
        });

    var delBtn = $('<button/>',
        {
            style: "border-radius:0;",
            class: "btn btn-xs btn-danger pull-right",
            html: '<i class="fa fa-trash-o"></i> Delete',
            click: function (event) {
                event.preventDefault();
                cloneDiv.remove();
            }
        });

    delDiv.append(delBtn);

    cloneDiv.append(ctrlClone).append(delDiv);

    return cloneDiv
}

function resolve_ctrl_values(ctrlsDiv, counter, formElem, elemValue) {
    var ctrlsWithValuesDiv = ctrlsDiv.clone();
    var ctrlsWithValuesDivArray = '';

    //validate elemValue
    if (Object.prototype.toString.call(elemValue) === '[object Object]') {
        if ($.isEmptyObject(elemValue)) {
            elemValue = "";
        }
    }

    if (elemValue) {
        if (formElem.type == "array") {
            if (elemValue.length > 0) {

                //first element should not be open to deletion
                ctrlsWithValuesDiv.find(":input").each(function () {
                    if (this.id) {
                        var sendOfValue = elemValue;
                        if (Object.prototype.toString.call(elemValue) === '[object Array]') {
                            sendOfValue = elemValue[0];
                        }

                        var resolvedValue = resolve_ctrl_values_aux_1(this.id, formElem, sendOfValue);
                        $(this).val(resolvedValue);
                        this.setAttribute("value", resolvedValue);
                    }
                });

                //sort other elements of the elemValue array
                if (Object.prototype.toString.call(elemValue) === '[object Array]' && elemValue.length > 1) {
                    ctrlsWithValuesDivArray = $('<div/>');

                    for (var i = 1; i < elemValue.length; ++i) {
                        ++counter;

                        var ctrlsWithValuesDivSiblings = get_element_clone(ctrlsDiv.clone(), counter);
                        ctrlsWithValuesDivSiblings.find(":input").each(function () {
                            if (this.id) {
                                var tId = this.id.substring(0, this.id.lastIndexOf("_")); //strip off subscript

                                var resolvedValue = resolve_ctrl_values_aux_1(tId, formElem, elemValue[i]);
                                $(this).val(resolvedValue);
                                this.setAttribute("value", resolvedValue);
                            }
                        });

                        ctrlsWithValuesDivArray.append(ctrlsWithValuesDivSiblings);
                    }
                }
            }

        } else {//not array type elemValue
            ctrlsWithValuesDiv.find(":input").each(function () {
                if (this.id) {
                    var sendOfValue = elemValue;

                    if (Object.prototype.toString.call(elemValue) === '[object Array]') {
                        sendOfValue = elemValue.join();
                    }

                    var resolvedValue = resolve_ctrl_values_aux_1(this.id, formElem, sendOfValue);
                    $(this).val(resolvedValue);
                    this.setAttribute("value", resolvedValue);

                    if ($(this).prop("tagName") == "SELECT") {//this was what worked, as .val() failed to dance
                        for (var i = 0; i < this.length; ++i) {
                            if (this.options[i].value == resolvedValue) {
                                this.options[i].setAttribute("selected", "selected");
                                break;
                            }
                        }
                    }

                }
            });
        }
    }

    var ctrlObjects = {};
    ctrlObjects['counter'] = counter;
    ctrlObjects['ctrlsWithValuesDivArray'] = ctrlsWithValuesDivArray;
    ctrlObjects['ctrlsWithValuesDiv'] = ctrlsWithValuesDiv;

    return ctrlObjects;
}

function resolve_ctrl_values_aux_1(ctrlObjectID, formElem, elemValue) {
    var embedValue = null;

    if (ctrlObjectID.length == formElem.id.length) { //likely end-point element
        embedValue = elemValue;
    } else if (ctrlObjectID.length > formElem.id.length) { //likely a composite element
        var elemKeys = ctrlObjectID.split(formElem.id + ".").slice(-1)[0].split(".");

        embedValue = elemValue;
        for (var i = 0; i < elemKeys.length; ++i) {
            embedValue = embedValue[elemKeys[i]];
        }
    }

    return embedValue;
}

function build_source_form(funcParams) {
    var formValue = funcParams.formValue;

    //build panel to hold form
    var newSourcePanel = $('<div/>', {
        class: "panel panel-primary",
        style: 'margin-top:1px;'
    });

    var newSourcePanelHeading = $('<div/>', {
        class: "panel-heading",
        html: "New Source"
    });

    var newSourcePanelBody = $('<div/>', {
        class: "panel-body"
    });

    newSourcePanel.append(newSourcePanelHeading).append(newSourcePanelBody);

    //form control
    var sourceSchema = copoSchemas.source_schema;

    var formCtrl = $('<form/>',
        {
            "data-toggle": "validator"
        });

    newSourcePanelBody.append(formCtrl);


    //generate controls given component schema
    for (var i = 0; i < sourceSchema.length; ++i) {
        var sourceFormElem = sourceSchema[i];
        var control = sourceFormElem.control;
        var elemValue = null;

        if (formValue) {
            var elem = sourceFormElem.id.split(".").slice(-1)[0];
            if (formValue[elem]) {
                elemValue = formValue[elem];
            }
        }

        if (sourceFormElem.hidden == "true") {
            control = "hidden";
        }

        try {
            formCtrl.append(dispatchFormControl[controlsMapping[control.toLowerCase()]](sourceFormElem, elemValue));
        }
        catch (err) {
            formCtrl.append('<div class="form-group copo-form-group"><span class="text-danger">Form Control Error</span> (' + sourceFormElem.label + '): Cannot resolve form control!</div>');
        }
    }

    //add source panel to DOM! This will enable us to begin registering events on form objects
    htmlFormSource.append(newSourcePanel);

    //save and cancel buttons
    var saveSourceBtnDiv = $('<div/>',
        {
            style: 'margin-top:10px;',
            class: 'pull-right',
        });


    var saveSourcebtn = $('<button/>',
        {
            class: "btn btn-sm btn-primary",
            html: '<i class="glyphicon glyphicon-save"></i>Save Source',
            click: function (event) {
                event.preventDefault();
                validate_forms(htmlFormSource.find("form"));
            }
        });

    var cancelSourceBtn = $('<button/>',
        {
            style: 'margin-right:3px;',
            class: "btn btn-sm btn-default",
            html: 'Cancel',
            click: function (event) {
                event.preventDefault();
                hide_source_form(funcParams);
            }
        });

    //add buttons div
    saveSourceBtnDiv.append(cancelSourceBtn).append(saveSourcebtn);

    //add buttons to panel
    newSourcePanelBody.append('<hr/>').append(saveSourceBtnDiv);

    //add clone control
    source_clone_ctrl(funcParams);

    //add custom validators
    custom_validate(htmlFormSource.find("form"));

    //add validate on submit event
    htmlFormSource.find("form").validator().on('submit', function (e) {
        if (e.isDefaultPrevented()) {
            return false;
        } else {
            e.preventDefault();
            save_source_form(funcParams);
        }
    });

    refresh_form_aux_controls();

    //help tips
    setup_formelement_hint($('input[name="helptips-chk"]'), htmlFormSource.find("form").find(":input"));
}

function save_source_form(funcParams) {
    //start save routine
    var ctrlsDiv = funcParams.ctrlsDiv;
    var formElem = funcParams.formElem;
    var ctrlsWithValuesDiv = funcParams.ctrlsWithValuesDiv;
    var csrftoken = $.cookie('csrftoken');

    var form_values = {};
    htmlFormSource.find("form").find(":input").each(function () {
        form_values[this.id] = $(this).val();
    });

    var auto_fields = JSON.stringify(form_values);

    $.ajax({
        url: copoFormsURL,
        type: "POST",
        headers: {'X-CSRFToken': csrftoken},
        data: {
            'task': "save",
            'auto_fields': auto_fields,
            'component': "source",
            'visualize': "sources_json_and_last_record_id"
        },
        success: function (data) {

            var sampleSourceValues = []; //basically, this means only the last created source is set (or only set one sample source)

            if (data.last_record_id) {
                sampleSourceValues.push(data.last_record_id);
            }

            if (sampleSourceValues.length > 0) {
                sampleSourceValues = sampleSourceValues.join();
            }

            var ctrlObjectsSourceContext = resolve_ctrl_values(ctrlsDiv.clone(), 0, formElem, sampleSourceValues);
            ctrlObjectsSourceContext.ctrlsWithValuesDiv.find(".elem-json").val(JSON.stringify(data.option_values));

            ctrlsWithValuesDiv.html(ctrlObjectsSourceContext.ctrlsWithValuesDiv.html());

            refresh_tool_tips();
        },
        error: function () {
            alert("Couldn't add source!");
        }
    });
    //end save routine


    //after save...remove form
    hide_source_form(funcParams);
}

function hide_source_form(funcParams) {
    $('.popover').popover('destroy'); //hide any shown popovers
    htmlFormSource.empty();
    funcParams.buttonObject.find("i").attr({class: "fa fa-plus-circle"});

    $("#global_form_save_btn").prop('disabled', false); //enable save button in parent form
}

function show_source_form(funcParams) {
    funcParams.buttonObject.find("i").attr({class: "fa fa-minus-circle"});
    $("#global_form_save_btn").prop('disabled', true); //disable save button in parent form

    build_source_form(funcParams);
}

function source_clone_ctrl(funcParams) {
    var component = "source";
    var formElem = funcParams.formElem;
    var sourceSchema = copoSchemas.source_schema;
    var csrftoken = $.cookie('csrftoken');

    //do clone only if there are 'clonables'
    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {'X-CSRFToken': csrftoken},
        data: {
            'task': 'sources_json_component',
            'component': component
        },
        success: function (data) {
            componentRecords[component] = $.extend(true, Object(), data.component_records);
            formElem.option_values = data.option_values;

            if (formElem.option_values.options.length > 0) {
                var cloneSourceCtrlsDiv = get_multi_search_span(formElem, $('<div/>')).clone();

                //we don't need the id's and name's attr
                cloneSourceCtrlsDiv.find(".copo-multi-values")
                    .removeAttr("id")
                    .removeAttr("name")
                    .attr("placeholder", "Clone a Source record...") //set placeholder
                    .attr('data-maxItems', '1') //make this a single select box; default is multiple


                if (funcParams.hasOwnProperty("selectedSource")) {
                    cloneSourceCtrlsDiv.find(".copo-multi-values").val(funcParams.selectedSource._id);
                }


                var cloneCtrl = $('<div/>',
                    {
                        class: "col-sm-7 col-md-7 col-lg-7",
                    }).append(form_div_ctrl().append(cloneSourceCtrlsDiv));

                var cloneSourceDivRow = $('<div/>',
                    {
                        class: "row",
                        style: "margin-bottom:15px;"
                    }).append(cloneCtrl);

                cloneSourceDivRow.insertBefore(htmlFormSource.find("form"));

                //handle change event for cloning source
                cloneSourceCtrlsDiv.find(".copo-multi-values").on('change', function (event) {
                    event.preventDefault();

                    if (funcParams.hasOwnProperty("selectedSource") &&
                        funcParams.selectedSource._id == $.extend(true, Object(), formElem.option_values.component_records[$(this).val()])["_id"]) {
                        return false;
                    }

                    var component_record = $.extend(true, Object(), formElem.option_values.component_records[$(this).val()]);
                    var labelElem = sourceSchema[0].id.split(".").slice(-1)[0];

                    //generate unique characters to append to label elem
                    var min = 10000;
                    var max = 99999;
                    var rand_postfix = (Math.floor(Math.random() * (max - min + 1)) + min).toString();
                    component_record[labelElem] = component_record[labelElem] + "_CLONED_" + rand_postfix;

                    hide_source_form(funcParams);
                    funcParams['formValue'] = component_record;
                    funcParams['selectedSource'] = $.extend(true, Object(), formElem.option_values.component_records[$(this).val()]);
                    show_source_form(funcParams);

                    return false;
                });

                refresh_tool_tips();

            }

        },
        error: function () {
            alert("Couldn't retrieve sources!");
        }
    });


}

function get_ontology_span(ontologySpan, formElem) {
    var ontologySchema = copoSchemas.ontology_schema;

    for (var i = 0; i < ontologySchema.length; ++i) {
        var fv = ontologySchema[i].id.split(".").slice(-1)[0];

        if (ontologySchema[i].hidden == "false") {

            //set restricted ontologies
            var localolsURL = olsURL;
            if (formElem.ontology_names && formElem.ontology_names.length) {
                localolsURL = olsURL.replace("999", formElem.ontology_names.join(","));
            }

            ontologySpan.append('<input autocomplete="off" data-autocomplete="' + localolsURL + '" class="input-copo form-control ontology-field" type="text" id="' + fv + '" name="' + fv + '" />');

        } else {
            ontologySpan.append($('<input/>',
                {
                    type: "hidden",
                    id: fv,
                    name: fv
                }));
        }
    }

    return ontologySpan;
}

function get_multi_search_span(formElem, ctrlsDiv) {
    //build hidden fields to hold selected options and supply control data respectively

    var data_maxItems = 'null';
    if (formElem.data_maxItems) {
        data_maxItems = formElem.data_maxItems;
    }

    var hiddenValuesCtrl = $('<input/>',
        {
            type: "hidden",
            id: formElem.id,
            name: formElem.id,
            class: "copo-multi-values",
            "data-maxItems": data_maxItems, //sets the maximum selectable elements, default is 'null'
        });

    var hiddenJsonCtrl = $('<input/>',
        {
            type: "hidden",
            class: "elem-json",
            value: JSON.stringify(formElem.option_values)
        });

    var selectCtrl = $('<select/>',
        {
            class: "input-copo copo-multi-search",
            placeholder: "Select " + formElem.label + "...",
            multiple: "multiple"
        });

    ctrlsDiv.append(selectCtrl).append(hiddenValuesCtrl).append(hiddenJsonCtrl);

    //set validation markers
    var vM = set_validation_markers(formElem, hiddenValuesCtrl);
    ctrlsDiv.append(vM.errorHelpDiv);

    return ctrlsDiv;
}

function get_form_ctrl(ctrlsDiv, formElem, elemValue) {
    //control clone parameters...
    var addbtnDiv = '';
    var counter = 0;

    //resolve control values
    var ctrlObjects = resolve_ctrl_values(ctrlsDiv.clone(), counter, formElem, elemValue);

    if (formElem.type == "array") {
        addbtnDiv = do_array_ctrls(ctrlsDiv.clone(), ctrlObjects.counter, formElem);
    }

    return form_div_ctrl()
        .append(form_label_ctrl(formElem.label, formElem.id))
        .append(ctrlObjects.ctrlsWithValuesDiv)
        .append(ctrlObjects.ctrlsWithValuesDivArray)
        .append(addbtnDiv)
        .append(form_help_ctrl(formElem.help_tip));
}

function validate_forms(formObject) {
    make_custom_fields_validate(); //removes disruptions to validator
    formObject.trigger('submit');
}

function custom_validate(formObject) {
    formObject.validator({
        custom: {
            unique: function ($el) {//validates for unique fields
                var parts = $el.attr("id").split(".").slice(1);
                var component = parts[0];
                var ctrl = parts[1];

                var oKFlag = true;
                if (componentRecords.hasOwnProperty(component)) {
                    var matchValue = "";
                    var newValue = $el.val().trim().toLowerCase();
                    $.each(componentRecords[component], function (key, val) {
                        matchValue = val[ctrl];
                        if (Object.prototype.toString.call(matchValue) === '[object String]') {
                            if (newValue == matchValue.trim().toLowerCase()) {
                                oKFlag = false;
                                return false;
                            }
                        }
                    });
                }

                if (!oKFlag) {
                    return "Not valid!";
                }
            },
            email: function ($el) {//validates for email fields
                var re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
                var newValue = $el.val().trim();

                var oKFlag = re.test(newValue);

                if (!oKFlag) {
                    return "Not valid!";
                }
            }
        }
    });
}


function global_form_validate(form_schema, formObject) {
    //this will only deal with required fields (for some custom controls) that were not previously validated
    var custControls = ["copo-sample-source", "copo-sample-source-2", "copo-select", "copo-multi-search", "copo-multi-select"];
    var allowSubmit = true;

    var form_values = Object();
    formObject.find(":input").each(function () {
        form_values[this.id] = $(this).val();
    });

    var violationList = Array();

    for (var i = 0; i < form_schema.length; ++i) {
        var ctrlObject = form_schema[i];

        if (ctrlObject.hasOwnProperty("required") && (ctrlObject.required.toString() == "true")) {
            if (ctrlObject.hasOwnProperty("control") && $.inArray(ctrlObject.control, custControls) > -1) {
                if (!form_values[ctrlObject.id].trim()) {
                    violationList.push(ctrlObject.label);
                }
            }
        }
    }

    var formErrors = $('<div/>',
        {
            id: "show_form_errors",
            style: "margin-top: 10px;",
            class: "col-sm-12 col-md-12 col-lg-12 form-group"
        });

    if (violationList.length > 0) {
        allowSubmit = false;

        var message = "The following field is required!";

        if (violationList.length > 1) {
            message = "The following fields are required!";
        }

        //push error to UI
        formObject.find("#show_form_errors").remove();

        var alertDiv = $('<div/>',
            {
                class: "alert alert-danger"
            });

        alertDiv.append('<a href="#" class="close" data-dismiss="alert" aria-label="close">&times;</a>');

        var lDiv = $('<div/>').append($('<div/>',
            {
                class: "row",
                style: "margin-left: 10px;",
                html: '<span>' + message + '</span>'
            }));

        $.each(violationList, function (k, v) {
            k = (k + 1).toString();
            lDiv.append($('<div/>',
                {
                    class: "row",
                    style: "margin-left: 10px; margin-bottom:5px;",
                    html: '<span>' + k + '.</span>' + '<span style="margin-left:5px;">' + v + '</span>'
                }));
        });
        alertDiv.append(lDiv);

        formObject.append(formErrors);

        formErrors.append(alertDiv);

        //automatically close the alert
        alertDiv.fadeTo(2500, 500).slideUp(1000, function () {
            alertDiv.slideUp(1000);
        });
    }

    return allowSubmit
}

function save_form(formJSON) {
    var task = "save";
    var error_msg = "Couldn't add " + formJSON.form_label + "!";
    if (formJSON.target_id) {
        task = "edit";
        error_msg = "Couldn't edit " + formJSON.form_label + "!";
    }

    //manage auto-generated fields
    var form_values = Object();
    htmlForm.find("form").find(":input").each(function () {
        form_values[this.id] = $(this).val();
    });

    //handle some special controls
    for (var i = 0; i < formJSON.form_schema.length; ++i) {
        if (formJSON.form_schema[i].control == "copo-sample-source" && formJSON.form_schema[i].type == "array") {
            $.each(form_values[formJSON.form_schema[i].id].split(","), function (indx, value) {
                if (indx == 0) {
                    form_values[formJSON.form_schema[i].id] = value;
                } else {
                    form_values[formJSON.form_schema[i].id + "_" + indx] = value;
                }
            });
        }
    }

    var auto_fields = JSON.stringify(form_values);

    //get the visualisation context (i.e., what to be displayed after form save) and pass on
    var visualize = "";
    if (formJSON.visualize) {
        visualize = formJSON.visualize;
    }

    csrftoken = $.cookie('csrftoken');

    $.ajax({
        url: copoFormsURL,
        type: "POST",
        headers: {'X-CSRFToken': csrftoken},
        data: {
            'task': task,
            'auto_fields': auto_fields,
            'component': formJSON.component_name,
            'visualize': visualize,
            'target_id': formJSON.target_id
        },
        success: function (data) {
            globalDataBuffer = data;
            if (data.table_data) {
                if (data.component && data.component == "profile") {
                    var event = jQuery.Event("refreshprofiles");
                    $('body').trigger(event);
                } else {
                    do_render_table(data);
                }

            } else if (data.profiles_counts) {
                var event = jQuery.Event("refreshprofilescounts");
                $('body').trigger(event);
            } else if (data.profile_count) {
                var event = jQuery.Event("getprofilecount");
                $('body').trigger(event);
            }

        },
        error: function () {
            alert(error_msg);
        }
    });
} //end of function