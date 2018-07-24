var wizardMessages;
var datafileDescriptionToken = '';
var datafileTableInstance = null;

$(document).ready(function () {
    //****************************** Event Handlers Block *************************//
    // test begins

    // test ends


    //page global variables
    var csrftoken = $('[name="csrfmiddlewaretoken"]').val();
    var component = "datafile";
    var wizardURL = "/rest/data_wiz/";
    var copoFormsURL = "/copo/copo_forms/";
    var samples_from_study_url = "/rest/samples_from_study/";

    var wizardElement = $('#dataFileWizard');


    var cyverse_files = $('#cyverse_file_data').val()
    if (cyverse_files != "") {
        cyverse_files = JSON.parse(cyverse_files)
        $('#cyverse_files_link').on('click', function (e) {
            if (cyverse_files) {
                $('#file_tree').treeview({data: cyverse_files, showCheckbox: true});
                $('#file_tree').css('visibility', 'visible')
                e.preventDefault();
            }
        });
    }

    // firstly, if the url contains Figshare oauth return params and the selected_datafile is set, we are dealing with a
    // return from a Figshare oauth login, so attempt to load the datafile into the wizard

    // get url
    var url = window.location.search
    if (url.includes('state') && url.includes('code')) {
        // now check for selected_datafile
        if ($('#selected_datafile').val() != '' || $('#selected_datafile').val() != undefined) {
            //alert('ask toni how we can load file ' + $('#selected_datafile').val() + ' into his wizard')
        }
    }


    //get component metadata
    var componentMeta = get_component_meta(component);

    //load records
    load_records(componentMeta);


    // handle/attach events to table buttons
    $('body').on('addbuttonevents', function (event) {
        do_record_task(event);
    });

    //trigger refresh of table
    $('body').on('refreshtable', function (event) {
        do_render_component_table(globalDataBuffer, componentMeta);
    });


    //details button hover
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view ' + component + ' details');
    });


    //description table data
    var dtRows = [];
    var dtColumns = [];

    //wizard help tip switch
    var wizhlptipchk = 'wizard-help-checkbox';
    $("[name='" + wizhlptipchk + "']").bootstrapSwitch(
        {
            size: "mini",
            onColor: "primary",
            state: true
        });

    $('input[name="' + wizhlptipchk + '"]').on('switchChange.bootstrapSwitch', function (event, state) {
        toggle_display_help_tips(state, wizardElement);
    });


    // wizard quick intro
    $('.wiz-showme').on('click', function (e) {
        e.preventDefault();
        do_wizard_show_me($(this));
    });

    //handle event for displaying description bundle
    $('#bundle_act').on('click', function (event) {
        event.preventDefault();

        var tableID = 'bundle_view_tbl';
        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        var $dialogContent = $('<div/>');
        var table_div = $('<div/>').append(tbl);
        var spinner_div = $('<div/>', {style: "margin-left: 40%; padding-top: 15px; padding-bottom: 15px;"}).append($('<div class="copo-i-loader"></div>'));

        var dialog = new BootstrapDialog({
            type: BootstrapDialog.TYPE_PRIMARY,
            size: BootstrapDialog.SIZE_WIDE,
            title: function () {
                return $('<span>Description bundle</span>');
            },
            closable: false,
            animate: true,
            draggable: false,
            onhide: function (dialogRef) {
                //nothing to do for now
            },
            onshown: function (dialogRef) {
                $.ajax({
                    url: wizardURL,
                    type: "POST",
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
                    data: {
                        'request_action': 'get_description_bundle',
                        'description_token': datafileDescriptionToken
                    },
                    success: function (data) {
                        spinner_div.remove();

                        var dtd = data.result;
                        var cols = [
                            {title: "", className: 'select-checkbox', data: "chk_box", orderable: false},
                            {title: "Datafiles", data: "name"}
                        ];
                        var table = null;

                        table = $('#' + tableID).DataTable({
                            data: dtd,
                            searchHighlight: true,
                            "lengthChange": false,
                            order: [
                                [1, "asc"]
                            ],
                            scrollY: "300px",
                            scrollX: true,
                            scrollCollapse: true,
                            paging: false,
                            language: {
                                "info": " _START_ to _END_ of _TOTAL_ datafiles",
                                "search": " "
                            },
                            select: {
                                style: 'os',
                                selector: 'td:first-child'
                            },
                            columns: cols,
                            dom: 'lft<"row">rip'
                        });

                        $('#' + tableID + '_wrapper')
                            .find(".dataTables_filter")
                            .find("input")
                            .removeClass("input-sm")
                            .attr("placeholder", "Search bundle");

                    },
                    error: function () {
                        alert("Couldn't display description bundle!");
                        dialogRef.close();
                    }
                });
            },
            buttons: [{
                label: 'OK',
                cssClass: 'tiny ui basic primary button',
                action: function (dialogRef) {
                    dialogRef.close();
                }
            }]
        });


        $dialogContent.append(table_div).append(spinner_div);
        dialog.realize();
        dialog.setMessage($dialogContent);
        dialog.open();
    });

    //discard description
    $('#remove_act').on('click', function (event) {
        event.preventDefault();
        do_discard_description(descriptionToken);
    });

    //custom stage renderers
    var dispatchStageRenderer = {
        perform_datafile_generation: function (stage) {
            generate_datafile_edit_table(stage);
        }
    }; //end of dispatchStageCallback


    //avoid enter key to submit wizard forms
    $(document).on("keyup keypress", ".wizard-dynamic-form", function (event) {
        var keyCode = event.keyCode || event.which;
        if (keyCode === 13) {
            event.preventDefault();
            return false;
        }
    });

    // inform session of currently selected datafile id
    //check this with Felix...
    $(document).on('click', '.copo-dt', function (e) {
        var datafile_id = $(e.currentTarget).attr("data-record-id")
        $.ajax({
            url: '/rest/set_session_variable/',
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                "key": "datafile_id",
                "value": datafile_id
            },
            success: function (data) {
                console.log("sent data to session " + data)
            }
        });
    });

    //instantiate/refresh tooltips
    refresh_tool_tips();

    //handle annotation wizard study dropdown onchange
    $(document).on('change', '#study_copo', handle_wizard_study_dropdown_onchange);


    //******************************* wizard events *******************************//

    //handle events for step change
    wizardElement.on('actionclicked.fu.wizard', function (evt, data) {
        $(self).data('step', data.step);

        stage_navigate(evt, data);
    });

    //handle events for step change
    wizardElement.on('changed.fu.wizard', function (evt, data) {
        toggle_display_help_tips($('input[name="' + wizhlptipchk + '"]').bootstrapSwitch('state'), wizardElement);

        //form controls help tip
        refresh_tool_tips();
        var activeStageIndx = wizardElement.wizard('selectedItem').step;

        //set up validator
        set_up_validator($("#wizard_form_" + activeStageIndx));
    });


    //****************************** Functions Block ******************************//

    function stage_navigate(evt, data) {
        if (data.direction == 'next') {

            evt.preventDefault();


            //end of wizard intercept
            if (wizardElement.find('.steps li.active:first').attr('data-name') == 'review') {
                finalise_description();
                return false;
            }

            //get referenced stage
            var activeStageIndx = wizardElement.wizard('selectedItem').step;

            // get form inputs
            var form_values = {};

            //trigger form validation
            var stageForm = $("#wizard_form_" + activeStageIndx);
            if (stageForm.length) {
                stageForm.trigger('submit');

                if (stageForm.find("#bcopovalidator").val() == "false") {
                    stageForm.find("#bcopovalidator").val("true");
                    return false;
                }

                $('#wizard_form_' + activeStageIndx).find(":input").each(function () {
                    form_values[this.id] = $(this).val();
                });
            }

            //call to load next stage

            add_step(JSON.stringify(form_values));

        } else if (data.direction == 'previous') {
            // get the proposed or intended state, for which action is intercepted
            evt.preventDefault();

            set_wizard_stage(data.step - 1);
        }

    } //end stage_navigate()

    function add_step(auto_fields) {

        // retrieve and/or re-validate next stage
        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'request_action': 'next_stage',
                'description_token': datafileDescriptionToken,
                'auto_fields': auto_fields
            },
            success: function (data) {
                var wizard_components = data.next_stage;
                if (wizard_components.hasOwnProperty('abort') && wizard_components.abort) {
                    //abort the description

                    BootstrapDialog.show({
                        title: 'Wizard Error!',
                        message: "Can't continue with description due to incomplete control information. Please restart the description process.",
                        cssClass: 'copo-modal3',
                        closable: false,
                        animate: true,
                        type: BootstrapDialog.TYPE_DANGER,
                        buttons: [
                            {
                                label: '<i class="copo-components-icons fa fa-times"></i> OK',
                                cssClass: 'tiny ui basic red button',
                                action: function (dialogRef) {
                                    dialogRef.close();
                                    window.location.reload();
                                }
                            }
                        ]
                    });

                    return false;
                }

                //call to refresh wizard
                if (wizard_components.hasOwnProperty('refresh_wizard') && wizard_components.refresh_wizard) {
                    refresh_wizard();
                }

                //check for and set stage
                if (wizard_components.hasOwnProperty('stage')) {
                    process_wizard_stage(wizard_components.stage);
                }
            },
            error: function () {
                alert("Couldn't retrieve next stage!");
            }
        });
    } //end add_step()

    function finalise_description() {
        alert('finalise...');
    } //end finalise_description()

    function set_wizard_stage(proposedState) {
        wizardElement.wizard('selectedItem', {
            step: proposedState
        });
    }

    function refresh_wizard() {
        //get referenced stage
        var activeStageIndx = wizardElement.wizard('selectedItem').step;

        //remove steps from wizard to start from current step
        var numSteps = wizardElement.find('.steps li').length;
        var stepIndex = activeStageIndx + 1;
        var howMany = numSteps - stepIndex;

        wizardElement.wizard('removeSteps', stepIndex, howMany);
        wizardElement.find('.steps li:last-child').hide();
    }

    function process_wizard_stage(stage) {
        // get next step index
        var numSteps = wizardElement.find('.steps li').length;


        if (!stage.hasOwnProperty("ref")) {
            //no stage returned, signalling last stage
            wizardElement.find('.steps li:last-child').show();
            set_wizard_stage(numSteps);

            return false;
        }

        //check stage has not been rendered already
        var foundStage = false;

        wizardElement.find('.steps li').each(function () {
            if ($(this).find(".wiz-title").attr("data-stage") == stage.ref) {
                foundStage = true;
                return false;
            }
        });

        if (foundStage) {
            set_wizard_stage(wizardElement.wizard('selectedItem').step + 1);
            return false;
        }


        //generate stage content
        var stage_pane = '<div id="custom-renderer_' + stage.ref + '"></div>';

        if (!stage.hasOwnProperty("renderer")) {
            stage_pane = get_pane_content(wizardStagesForms(stage), numSteps, stage.message);
        }

        wizardElement.wizard('addSteps', numSteps, [
            {
                label: '<span data-stage="' + stage.ref + '" class=wiz-title>' + stage.title + '</span>',
                pane: stage_pane
            }
        ]);


        //set focus to the currently added stage
        set_wizard_stage(numSteps);

        //get custom renderer
        if (stage.hasOwnProperty("renderer")) {
            //custom content will sit here...

            $('#custom-renderer_' + stage.ref).append('<div class="stage-content"></div>');

            //add form to stage to capture current_stage and other required properties
            var formDiv = $('<div/>');
            var hiddenCtrl = $('<input/>',
                {
                    type: "hidden",
                    id: "current_stage",
                    name: "current_stage",
                    value: stage.ref
                });

            //append to this form, if need be, within a renderer
            var formCtrl = $('<form/>',
                {
                    id: "wizard_form_" + numSteps,
                    class: "wizard-dynamic-form"
                });

            formCtrl.append(hiddenCtrl);

            formDiv.append(formCtrl);
            $('#custom-renderer_' + stage.ref).append(formDiv);

            dispatchStageRenderer[stage.renderer](stage);

            set_up_validator($("#wizard_form_" + numSteps)); //needed here to account for delay in content display
        }

    } //end of func


    function set_up_validator(theForm) {
        //validate on submit event

        if (!theForm.length) {
            return false;
        }

        if (!theForm.find("#bcopovalidator").length) {
            custom_validate(theForm);
            refresh_validator(theForm);

            var bvalidator = $('<input/>',
                {
                    type: "hidden",
                    id: "bcopovalidator",
                    name: "bcopovalidator",
                    value: "true"
                });

            //add validator flag
            theForm.append(bvalidator);

            theForm.validator().on('submit', function (e) {
                if (e.isDefaultPrevented()) {
                    $(this).find("#bcopovalidator").val("false");
                    return false;
                } else {
                    e.preventDefault();
                    $(this).find("#bcopovalidator").val("true");
                }
            });
        }

    } //end set_up_validator()


    function get_pane_content(stage_content, step, stage_message) {
        var row = $('<div/>', {
            class: "row"
        });

        var left = $('<div/>', {
            class: "col-sm-8"
        });

        var right = $('<div/>', {
            class: "col-sm-4",
            html: ' <div class="webpop-content-div alert alert-default" style="background-color:#eee;">' + stage_message + '</div>'
        });

        row
            .append(left)
            .append(right);


        var stageHTML = $('<div/>');

        left.append(stageHTML);

        //form controls
        var formPanel = $('<div/>', {
            style: "margin-top: 5px; font-size: 14px;"
        });


        stageHTML.append(formPanel);

        var formPanelBody = $('<div/>');

        formPanel.append(formPanelBody);

        var formDiv = $('<div/>', {
            style: "margin-top: 20px;"
        });

        formPanelBody.append(formDiv);

        var formCtrl = $('<form/>',
            {
                id: "wizard_form_" + step,
                class: "wizard-dynamic-form"
            });

        formCtrl.append(stage_content);

        formDiv.append(formCtrl);

        return row;
    } //end get_pane_content

    function wizardStagesForms(stage) {
        var formValue = stage.data;

        var formDiv = $('<div/>');

        //build form elements
        for (var i = 0; i < stage.items.length; ++i) {
            var formElem = stage.items[i];
            var control = formElem.control;

            var elemValue = null;

            //set default values
            if (formElem.default_value) {
                elemValue = formElem.default_value;
            } else {
                elemValue = "";
            }

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
                formDiv.append(dispatchFormControl[controlsMapping[control.toLowerCase()]](formElem, elemValue));
            }
            catch (err) {
                formDiv.append('<div class="form-group copo-form-group"><span class="text-danger">Form Control Error</span> (' + formElem.label + '): Cannot resolve form control!</div>');
            }

        }

        //add current stage to form
        var hiddenCtrl = $('<input/>',
            {
                type: "hidden",
                id: "current_stage",
                name: "current_stage",
                value: stage.ref
            });

        formDiv.append(hiddenCtrl);

        return formDiv;
    } //end wizardStagesForms()


    function handle_wizard_study_dropdown_onchange(event) {
        var val = $(event.currentTarget).val();
        if (val == "none") {
            $('#sample_copo').find('option').remove().end().append('<option value="none"></option>');
            $('#sample_copo').attr('disabled', 'disabled');
            $('#study_ena').removeAttr('disabled');
            $('#sample_ena').removeAttr('disabled');
        }
        else {

            $('#study_ena').attr('disabled', 'disabled');
            $('#sample_ena').attr('disabled', 'disabled');
            $('#sample_copo').removeAttr('disabled');
            // now get samples in study
            $.ajax(
                {
                    headers: {'X-CSRFToken': csrftoken},
                    url: samples_from_study_url,
                    data: {'profile_id': val},
                    dataType: 'json',
                    method: 'POST'
                }
            ).done(function (data) {
                $('#sample_copo').find('option').remove()
                $(data).each(function (idx, element) {
                    var option = $('<option/>', {
                        html: element['name'] + ' (' + element['organism']['annotationValue'] + ')',
                        value: element['_id']['$oid']
                    });

                    $('#sample_copo').append(option)
                });

            }).fail(function (data) {
                console.log('error');
            });
        }
    }

    function do_wizard_show_me(elem) {
        var target = elem.attr("data-target");
        var label = elem.attr("data-label");
        var item = null;

        if ($("#" + target).length) {
            item = $("#" + target);
        } else if ($("." + target).length) {
            item = $("." + target)[0];
        }

        if (item) {
            item.webuiPopover('destroy');
            item.webuiPopover({
                title: label,
                content: '<div class="webpop-content-div">Click x to dismiss</div>',
                trigger: 'sticky',
                width: 200,
                arrow: true,
                closeable: true,
                backdrop: true
            });
        }
    } //end of function

    //handles button events on a record or group of records
    function do_record_task(event) {
        var task = event.task.toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var tableID = event.tableID; //get target table


        //retrieve target records and execute task
        var table = $('#' + tableID).DataTable();

        var records = table.rows('.selected').ids().toArray();

        if (records.length == 0) {
            return false;
        }

        if (task == "edit") {
            $.ajax({
                url: copoFormsURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'task': 'form',
                    'component': component,
                    'target_id': records[0].split("row_").slice(-1)[0] //only allowing row action for edit, hence first record taken as target
                },
                success: function (data) {
                    json2HtmlForm(data);
                },
                error: function () {
                    alert("Couldn't build datafile form!");
                }
            });
        } else if (task == "delete") {
            //...
        } else if (task == "describe") {
            var parameters = {'​description_targets': records};
            initiate_datafile_description(parameters);
            table.rows().deselect(); //deselect all rows
        } else if (task == "discard") {
            do_undescribe_confirmation(records, table);
        }

    } //end of func

    function initiate_datafile_description(parameters) {
        $('[data-toggle="tooltip"]').tooltip('destroy');

        if (!$("#wizard_toggle").is(":visible")) {
            var $dialogContent = $('<div/>');
            var notice_div = $('<div/>').html("Initiating description...");
            var spinner_div = $('<div/>', {style: "margin-left: 40%; padding-top: 15px; padding-bottom: 15px;"}).append($('<div class="copo-i-loader"></div>'));

            var description_token = '';
            if (parameters.hasOwnProperty('description_token')) {
                description_token = parameters.description_token;
            }

            var description_targets = [];
            if (parameters.hasOwnProperty('​description_targets')) {
                description_targets = JSON.stringify(parameters['​description_targets']);
            }

            var dialog = new BootstrapDialog({
                type: BootstrapDialog.TYPE_PRIMARY,
                size: BootstrapDialog.SIZE_NORMAL,
                title: function () {
                    return $('<span>Datafiles description</span>');
                },
                closable: false,
                animate: true,
                draggable: false,
                onhide: function (dialogRef) {
                    //nothing to do for now
                },
                onshown: function (dialogRef) {
                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: {
                            'request_action': "initiate_description",
                            'description_targets': description_targets,
                            'description_token': description_token,
                            'profile_id': $('#profile_id').val()

                        },
                        success: function (data) {
                            if (data.result.status == 'success') {
                                //set description token
                                datafileDescriptionToken = data.result.description_token;

                                //set wizard messages
                                wizardMessages = data.result.wiz_message;

                                //display wizard
                                $("#wizard_toggle").collapse("toggle");

                                //hide the review stage -- to be redisplayed when all the dynamic stages are displayed
                                wizardElement.find('.steps li:last-child').hide();

                                //remove incomplete description object from info pane
                                if (parameters.hasOwnProperty('info_object')) {
                                    parameters.info_object.closest(".inc-desc-badge").remove();
                                }

                                set_up_validator($("#wizard_form_1"));

                                dialogRef.close();

                            } else {
                                var $feeback = $('<div/>', {
                                    "class": "webpop-content-div",
                                    style: "padding-bottom: 15px;"
                                }).html("Please resolve the following issue to proceed with your description.<div style='margin-top: 10px; margin-bottom: 15px;'>" + data.result.message + "</div>");
                                var $button = $('<div class="tiny ui basic red button">Resolve issue</div>');
                                $button.on('click', {dialogRef: dialogRef}, function (event) {
                                    event.data.dialogRef.close();
                                });

                                dialog.setType(BootstrapDialog.TYPE_DANGER);
                                dialog.getModalBody().html('').append($feeback).append($button);
                            }

                        },
                        error: function () {
                            alert("Error instantiating description!");
                        }
                    });
                },
                buttons: []
            });

            $dialogContent.append(notice_div).append(spinner_div);
            dialog.realize();
            dialog.setMessage($dialogContent);
            dialog.open();

        } else {//wizard is already visible
            var message = "There's an ongoing description. What would you like to do? <div style='margin-top: 10px;'><ul><li><strong>Add to bundle </strong>: Click this button to add the selected datafiles to the current description bundle</li><li><strong>New description</strong>: Select this option to terminate the current description session and start a new one using the selected datafiles</li><li><strong>Cancel</strong>: Select this option to cancel the intended action</li></ul></div>";

            BootstrapDialog.show({
                title: "Description instantiation",
                message: message,
                // cssClass: 'copo-modal2',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                size: BootstrapDialog.SIZE_NORMAL,
                buttons: [
                    {
                        label: 'Add to bundle',
                        cssClass: 'tiny ui basic primary button',
                        action: function (dialogRef) {
                            dialogRef.close();
                        }
                    },
                    {
                        label: 'New description',
                        cssClass: 'tiny ui basic orange button',
                        action: function (dialogRef) {
                            dialogRef.close();
                        }
                    },
                    {
                        label: 'Cancel',
                        cssClass: 'tiny ui basic danger button',
                        action: function (dialogRef) {
                            dialogRef.close();
                        }
                    }
                ]
            });
        }

        $("[data-toggle='tooltip']").tooltip();

    } //end initiate_datafile_description()

    function do_undescribe_confirmation(records, tableInstance) {
        //function deletes description metadata from datafiles

        BootstrapDialog.show({
            title: "Discard description metadata",
            message: "Are you sure you want to remove description metadata for the selected files?",
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            buttons: [{
                label: 'Cancel',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    tableInstance.rows().deselect(); //deselect all rows
                    dialogRef.close();
                }
            }, {
                label: '<i class="copo-components-icons fa fa-times"></i> Discard',
                cssClass: 'tiny ui basic red button',
                action: function (dialogRef) {
                    dialogRef.close();

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: {
                            'request_action': 'un_describe',
                            'description_targets': JSON.stringify(records)
                        },
                        success: function (data) {
                            tableInstance.rows().deselect(); //deselect all rows
                        },
                        error: function () {
                            alert("Couldn't discard description for selected records!");
                        }
                    });
                }
            }]
        });
    }

    function generate_datafile_edit_table(stage) {
        //function provides stage information for datafile attributes editing
        var tableID = stage.ref + "_table";
        var stageHTML = $('<div/>', {"class": "alert alert-default"});

        var messageDiv = $('<a/>',
            {
                html: '<i class="fa fa-2x fa-info-circle text-info"></i><span class="action-label" style="padding-left: 8px;">Attributes editing tips...</span>',
                class: "text-info",
                style: "line-height: 150%; display:none;",
                href: "#attributes-edit",
                "data-toggle": "collapse"
            });

        //add info for user
        var message = $('<div/>', {class: "webpop-content-div"});
        message.append(stage.message);

        var panel = get_panel('info');
        panel.addClass('edit-datafile-badge');
        panel.find('.panel-body').append(message);
        panel.find('.panel-heading').remove();
        panel.find(".panel-footer").remove();

        var messageDivContent = $('<div/>',
            {
                class: "collapse",
                id: "attributes-edit"
            }
        );

        messageDivContent.append(panel);


        // refresh dynamic content
        $('#custom-renderer_' + stage.ref).find(".stage-content").html('');
        $('#custom-renderer_' + stage.ref).find(".stage-content").append(stageHTML);

        stageHTML.append($('<div/>', {style: "margin-bottom: 10px;"}).append(messageDiv));
        stageHTML.append(messageDivContent);

        //table element
        var tableDiv = $('<div/>');
        stageHTML.append(tableDiv);

        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        tableDiv.append(tbl);

        //loader element
        var loaderHTML = $('<div/>');
        var loaderMessage = $('<div/>', {
            class: "text-primary",
            style: "margin-top: 5px; font-weight:bold;",
            html: "Generating datafiles..."
        });

        loaderHTML.append(loaderMessage);
        loaderHTML.append(get_spinner_image());
        stageHTML.append(loaderHTML);

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': "get_discrete_attributes",
                'description_token': datafileDescriptionToken

            },
            success: function (data) {
                loaderHTML.remove();
                messageDiv.show();

                dtColumns = data.table_data.columns;
                dtRows = data.table_data.rows;

                var table = $('#' + tableID).DataTable({
                    data: dtRows,
                    dom: 'Bfr<"row"><"row info-rw" i>tlp',
                    searchHighlight: true,
                    lengthChange: true,
                    select: {
                        style: 'os',
                        selector: 'td:first-child'
                    },
                    order: [[0, 'asc']],
                    buttons: [
                        'selectAll',
                        {
                            text: 'Select filtered',
                            action: function (e, dt, node, config) {
                                var filteredRows = dt.rows({order: 'index', search: 'applied'});
                                if (filteredRows.count() > 0) {
                                    dt.rows().deselect();
                                    filteredRows.select();
                                }
                            }
                        },
                        'selectNone',
                        {
                            extend: 'excel',
                            text: 'Spreadsheet',
                            title: null,
                            filename: "copo_datafiles_" + String(datafileDescriptionToken)
                        }
                    ],
                    language: {
                        "info": " _START_ to _END_ of _TOTAL_ datafiles",
                        buttons: {
                            selectAll: "Select all",
                            selectNone: "Select none",
                        },
                        select: {
                            rows: {
                                _: "%d selected records can be <strong>batch-updated using focused cell value</strong><span class='focused-table-info'></span>",
                                0: "<span>Select one or more records to batch-update</span><span class='focused-table-info'></span>",
                                1: "%d selected record can be updated using focused cell value<span class='focused-table-info'></span>"
                            }
                        }
                    },
                    keys: {
                        columns: ':not(:first-child, :nth-child(2))',
                        focus: ':eq(2)', // cell that will receive focus when the table is initialised, set to the first editable cell defined
                        keys: [9, 13, 37, 39, 38, 40],
                        blurable: false
                    },
                    scrollX: true,
                    // scroller: true,
                    // scrollY: 300,
                    columns: dtColumns
                });

                datafileTableInstance = table;

                table
                    .buttons()
                    .nodes()
                    .each(function (value) {
                        $(this)
                            .removeClass("btn btn-default")
                            .addClass('tiny ui basic button');
                    });

                //add custom buttons

                var customButtons = $('<span/>', {
                    style: "padding-left: 15px;",
                    class: "copo-table-cbuttons"
                });


                $(table.buttons().container()).append(customButtons);

                //apply to selected rows button
                var applyButton = $('<button/>',
                    {
                        class: "tiny ui basic primary button",
                        id: "updating_cell_button",
                        type: "button",
                        html: '<span>Update selected records</span>',
                        click: function (event) {
                            event.preventDefault();

                            if (!$(this).hasClass('updating')) {
                                $(this).addClass('updating');
                                batch_update_records(table);
                            }
                        }
                    });

                customButtons.append(applyButton);

                refresh_tool_tips();

                //add event for enter key press and cell double-click
                table
                    .on('dblclick', 'td', function () {
                        var cell = table.cell($(this));
                        manage_cell_edit(table, cell);
                    });

                table
                    .on('key', function (e, datatable, key, cell, originalEvent) {
                        if (key == 13) {//trap enter key for editing a cell
                            manage_cell_edit(table, cell);
                        }
                    });

                //add event for cell focus
                table
                    .on('key-focus', function (e, datatable, cell, originalEvent) {
                        var rowIndx = cell.index().row + 1;
                        $('.focused-table-info').html($('<span style="margin-left: 5px; padding: 5px; font-size: 14px;"> Focused cell in row ' + rowIndx + '</span>'));
                    })
                    .on('key-blur', function (e, datatable, cell) {
                        //;
                    });

            },
            error: function () {
                alert("Couldn't generate datafiles!");
            }
        });
    } //end of function

}); //end document ready