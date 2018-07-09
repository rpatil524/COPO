var wizardMessages;
var sampleDescriptionToken = '';
var sampleTableInstance = null;

$(document).ready(function () {
    //****************************** Event Handlers Block *************************//

    // test begins

    // test ends


    //page global variables
    var csrftoken = $('[name="csrfmiddlewaretoken"]').val();
    var component = "sample";
    var wizardURL = "/rest/sample_wiz/";
    var copoFormsURL = "/copo/copo_forms/";

    //get component metadata
    var componentMeta = get_component_meta(component);

    //load records
    load_records(componentMeta);

    //load pending description
    pending_sample_description();

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
        toggle_display_help_tips(state, $("#sampleWizard"));
    });


    // handle/attach events to table buttons
    $('body').on('addbuttonevents', function (event) {
        do_record_task(event);
    });

    //trigger refresh of table
    $('body').on('refreshtable', function (event) {
        do_render_component_table(globalDataBuffer, componentMeta);
    });

    //add new component button
    $(document).on("click", ".new-samples-template", function (event) {
        trigger_description_pane();
    });

    //details button hover
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view ' + component + ' details');
    });


    //avoid enter key to submit wizard forms
    $(document).on("keyup keypress", ".wizard-dynamic-form", function (event) {
        var keyCode = event.keyCode || event.which;
        if (keyCode === 13) {
            event.preventDefault();
            return false;
        }
    });

    //delete an incomplete description
    $(document).on("click", ".delete-description-i", function (event) {
        event.preventDefault();
        delete_incomplete_description($(this), $(this).attr("data-target"));
    });

    //reload an incomplete description
    $(document).on("click", ".reload-description-i", function (event) {
        event.preventDefault();
        reload_incomplete_description($(this), $(this).attr("data-target"));
    });

    //custom stage renderers
    var dispatchStageRenderer = {
        perform_sample_generation: function (stage) {
            generate_sample_edit_table(stage);
        }
    }; //end of dispatchStageCallback

    //Enter-key event for table cell update...
    $(document).on('keypress', '.cell-edit-panel', function (event) {
        var keyCode = event.keyCode || event.which;
        if (keyCode === 13) {
            event.preventDefault();

            var cells = sampleTableInstance.cells('.focus');

            if (cells && cells[0].length > 0) {
                $(document).find(".copo-form-group").webuiPopover('destroy');

                var cell = cells[0];
                var targetCell = sampleTableInstance.cell(cell[0].row, cell[0].column);

                manage_cell_edit(sampleTableInstance, targetCell);
            }

            return false;
        }
    });


    //******************************* wizard events *******************************//

    //handle event for saving description for later...
    $('#reload_act').on('click', function (event) {
        window.location.reload();
    });

    //handle event for discarding current description...
    $('#remove_act').on('click', function (event) {
        //confirm user decision
        BootstrapDialog.show({
            title: "Discard Description",
            message: "Are you sure you want to discard the current description?",
            cssClass: 'copo-modal3',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            buttons: [
                {
                    label: 'Cancel',
                    cssClass: 'tiny ui basic button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                },
                {
                    label: '<i class="copo-components-icons fa fa-times"></i> Discard',
                    cssClass: 'tiny ui basic red button',
                    action: function (dialogRef) {
                        if (sampleDescriptionToken == '') {
                            dialogRef.close();
                            window.location.reload();
                        } else {
                            $.ajax({
                                url: wizardURL,
                                type: "POST",
                                headers: {
                                    'X-CSRFToken': csrftoken
                                },
                                data: {
                                    'request_action': "discard_description",
                                    'description_token': sampleDescriptionToken

                                },
                                success: function (data) {
                                    dialogRef.close();
                                    window.location.reload();

                                },
                                error: function () {
                                    alert("An error occurred!");
                                }
                            });
                        }
                    }
                }
            ]
        });

    });

    $('.wiz-showme').on('click', function (e) {
        e.preventDefault();

        var target = $(this).attr("data-target");
        var label = $(this).attr("data-label");
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


    });


    //handle events for step change
    $('#sampleWizard').on('actionclicked.fu.wizard', function (evt, data) {
        $(self).data('step', data.step);

        stage_navigate(evt, data);
    });

    //handle events for step change
    $('#sampleWizard').on('changed.fu.wizard', function (evt, data) {
        toggle_display_help_tips($('input[name="' + wizhlptipchk + '"]').bootstrapSwitch('state'), $("#sampleWizard"));
    });

    //sample accession resolution
    $(document).on("click", ".resolver-submit", function (event) {
        event.preventDefault();

        var parentElem = $(this).closest(".copo-form-group");
        var dataElem = parentElem.find(".resolver-data");
        var resolverValue = dataElem.val().replace(/^\s+|\s+$/g, '');


        if (resolverValue.length == 0) {
            return false;
        }

        var spinnerElem = $('<button/>',
            {
                type: "button",
                class: "btn btn-default",
                html: '<i class="fa fa-spinner fa-pulse fa-1x"></i>'
            });

        spinnerElem.insertBefore($(this));

        //get resolver uri
        var resolverURL = dataElem.attr("data-resolve-uri") + resolverValue;

        //get resolver component
        var resolverComponent = dataElem.attr("data-resolve-component");

        if (resolverComponent.toLowerCase() == "biosample") {
            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'request_action': "resolve_uri",
                    'resolver_uri': resolverURL

                },
                success: function (data) {
                    spinnerElem.remove();
                    if (data.resolved_output.status == 'success') {
                        //set hidden value, and display result to user
                        parentElem.removeClass("has-error has-danger");
                        parentElem.find(".help-block").html("Successfully resolved accession. Resolved sample has been registered, and also displayed below. Click 'Next' to proceed.");
                        $('#' + dataElem.attr('id') + "_hidden").val(JSON.stringify(data.resolved_output.value));
                        parentElem.find(".feedback-element").html(JSON.stringify(data.resolved_output.value));
                    } else {
                        $('#' + dataElem.attr('id') + "_hidden").val('');
                        parentElem.find(".feedback-element").html('');
                        parentElem.addClass("has-error has-danger");
                        parentElem.find(".help-block").html("Couldn't resolve " + resolverValue + "!");
                    }
                },
                error: function () {
                    alert("Error while attempting to resolve accession!");
                }
            });
        }
    });

    $(document).on("change", ".copo-input-data", function () {
        if (["provided_names", "bundle_name"].indexOf(this.id) > -1) {
            var shownValue = $(this).val().trim();
            var hiddenValue = $('#' + this.id + "_hidden").val().trim();

            if (shownValue != hiddenValue) {
                $(this).closest(".copo-form-group").find(".help-block").html('');
                $('#' + this.id + "_hidden").val('');
                return false;
            }
        }
    });

    //copo-trigger-submit control handling
    $(document).on("click", ".copo-trigger-submit", function (event) {
        event.preventDefault();

        var parentElem = $(this).closest(".copo-form-group");
        var triggerTarget = $(this).attr("data-target");
        var dataElem = parentElem.find(".copo-input-data");
        var inputValue = dataElem.val().replace(/^\s+|\s+$/g, '');


        if (inputValue.length == 0) {
            parentElem.find(".feedback-element").html('');
            parentElem.addClass("has-error has-danger");
            parentElem.find(".help-block").html('');
            parentElem.find(".help-block").eq(0).html("Please enter a value for " + parentElem.find("label").html() + "!");
            return false;
        }

        parentElem.find(".spinner-element").remove();

        var spinnerElem = $('<button/>',
            {
                type: "button",
                class: "btn btn-default spinner-element",
                html: '<i class="fa fa-spinner fa-pulse fa-1x"></i>'
            });

        spinnerElem.insertBefore($(this));


        if (triggerTarget == "provided_names") {
            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'request_action': "validate_sample_names",
                    'sample_names': inputValue,
                    'description_token': sampleDescriptionToken

                },
                success: function (data) {
                    spinnerElem.remove();
                    if (data.validation_result.status == "success") {
                        //set hidden value, and give all clear signal
                        parentElem.find(".help-block").html('');
                        parentElem.removeClass("has-error has-danger");
                        parentElem.find(".help-block").eq(0).html("Supplied names are valid and have been registered! Click 'Next' to proceed.");
                        $('#' + dataElem.attr('id') + "_hidden").val(inputValue);
                        parentElem.find(".feedback-element").html('');
                        dataElem.trigger('change'); //this was needed to properly propagate error reporting
                    } else {
                        parentElem.find(".help-block").html('');
                        $('#' + dataElem.attr('id') + "_hidden").val('');
                        parentElem.find(".feedback-element").html('');
                        parentElem.addClass("has-error has-danger");
                        parentElem.find(".help-block").eq(0).html("Validation error! Please see below for details.");

                        var tbl = $('<table/>',
                            {
                                id: "feedback_provided_names",
                                "class": "ui celled table hover copo-noborders-table",
                                cellspacing: "0",
                                width: "100%"
                            });

                        var dataSet = data.validation_result.errors;

                        parentElem.find(".feedback-element").append(tbl);


                        $('#feedback_provided_names').DataTable({
                            data: dataSet,
                            "paging": false,
                            "lengthChange": false,
                            "searching": false,
                            columns: data.validation_result.error_columns
                        });
                    }
                },
                error: function () {
                    alert("Error while attempting to validate sample names!");
                }
            });
        } else if (triggerTarget == "bundle_name") {
            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'request_action': "validate_bundle_name",
                    'bundle_name': inputValue,
                    'description_token': sampleDescriptionToken

                },
                success: function (data) {
                    spinnerElem.remove();
                    if (data.validation_status == "success") {
                        //set hidden value, and give all clear signal
                        parentElem.find(".help-block").html('');
                        parentElem.removeClass("has-error has-danger");
                        parentElem.find(".help-block").eq(0).html("Bundle name is valid and will be used to generate sample names of the form: " + inputValue + "_1, " + inputValue + "_2,...! " + " Click 'Next' to proceed.");
                        $('#' + dataElem.attr('id') + "_hidden").val(inputValue);
                        dataElem.trigger('change'); //this was needed to properly propagate error reporting
                    } else {
                        parentElem.find(".help-block").html('');
                        $('#' + dataElem.attr('id') + "_hidden").val('');
                        parentElem.addClass("has-error has-danger");
                        parentElem.find(".help-block").eq(0).html("Generating sample names from bundle name will violate unique constraint! Please enter another bundle name and click 'Validate!'");
                    }
                },
                error: function () {
                    alert("Error while attempting to validate bundle name!");
                }
            });
        }
    });


    //instantiate/refresh tooltips
    refresh_tool_tips();


    //****************************** Functions Block ******************************//
    function add_step(auto_fields) {

        // retrieve and/or re-validate next stage
        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'request_action': 'next_stage',
                'description_token': sampleDescriptionToken,
                'auto_fields': auto_fields,
                'profile_id': $('#profile_id').val()
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

                //check for and set the description token
                if (wizard_components.hasOwnProperty('wiz_token')) {
                    sampleDescriptionToken = wizard_components.wiz_token;
                }

                //check for and set wizard messages
                if (wizard_components.hasOwnProperty('wiz_message')) {
                    wizardMessages = wizard_components.wiz_message;
                }

                //check call to refresh wizard
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
    }

    function stage_navigate(evt, data) {
        if (data.direction == 'next') {

            evt.preventDefault();


            //end of wizard intercept
            if ($('#sampleWizard').find('.steps li.active:first').attr('data-name') == 'review') {
                finalise_description();
                return false;
            }

            //get referenced stage
            var activeStageIndx = $('#sampleWizard').wizard('selectedItem').step;


            //trigger form validation
            var stageForm = $("#wizard_form_" + activeStageIndx);
            if (stageForm.length) {
                stageForm.trigger('submit');

                if (stageForm.find("#bcopovalidator").val() == "false") {
                    stageForm.find("#bcopovalidator").val("true");
                    return false;
                }
            }

            // get form inputs
            var form_values = {};

            if (Number(activeStageIndx) > 1) {
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

    }

    function set_wizard_stage(proposedState) {
        $('#sampleWizard').wizard('selectedItem', {
            step: proposedState
        });
    }

    function refresh_wizard() {
        //get referenced stage
        var activeStageIndx = $('#sampleWizard').wizard('selectedItem').step;

        //remove steps from wizard to start from current step
        var numSteps = $('#sampleWizard').find('.steps li').length;
        var stepIndex = activeStageIndx + 1;
        var howMany = numSteps - stepIndex;

        $('#sampleWizard').wizard('removeSteps', stepIndex, howMany);
    }


    function process_wizard_stage(stage) {
        // get next step index
        var numSteps = $('#sampleWizard').find('.steps li').length;


        if (!stage.hasOwnProperty("ref")) {
            //reveal the last stage
            $('#sampleWizard').find('.steps li:last-child').show();
            set_wizard_stage(numSteps);

            return false;
        }

        //check stage has not been rendered already
        var foundStage = false;

        $('#sampleWizard').find('.steps li').each(function () {
            if ($(this).find(".wiz-title").attr("data-stage") == stage.ref) {
                foundStage = true;
                return false;
            }
        });

        if (foundStage) {
            set_wizard_stage($('#sampleWizard').wizard('selectedItem').step + 1);
            return false;
        }


        //generate stage content
        var stage_pane = '<div id="custom-renderer_' + stage.ref + '"></div>';

        if (!stage.hasOwnProperty("renderer")) {
            stage_pane = get_pane_content(wizardStagesForms(stage), numSteps, stage.message);
        }

        $('#sampleWizard').wizard('addSteps', numSteps, [
            {
                label: '<span data-stage="' + stage.ref + '" class=wiz-title>' + stage.title + '</span>',
                pane: stage_pane
            }
        ]);


        //set focus to the currently added stage
        set_wizard_stage(numSteps);

        //get custom renderer
        if (stage.hasOwnProperty("renderer")) {
            dispatchStageRenderer[stage.renderer](stage);
        }

        //set up validator
        set_up_validator();

        //form controls help tip
        refresh_tool_tips()

        //autocomplete
        auto_complete();

    } //end of func


    function set_up_validator() {
        //get all forms and add validator
        $('#sampleWizard').find(".wizard-dynamic-form").each(function () {
            var theForm = $(this);

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

        });
    }

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
    }


    function trigger_description_pane() {
        //function responds to user click of the description button

        $('[data-toggle="tooltip"]').tooltip('destroy');

        if (!$("#wizard_toggle").is(":visible")) {
            $("#wizard_toggle").collapse("toggle");

            //hide the review stage -- to be redisplayed when all the dynamic stages are displayed
            $('#sampleWizard').find('.steps li:last-child').hide();
        }

        $("[data-toggle='tooltip']").tooltip();
    }


    //handles button events on a record or group of records
    function do_record_task(event) {
        var task = event.task.toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var tableID = event.tableID; //get target table

        //describe task
        if (task == "describe") {
            trigger_description_pane();
            return false;
        }

        //retrieve target records and execute task
        var table = $('#' + tableID).DataTable();
        var records = []; //
        $.map(table.rows('.selected').data(), function (item) {
            records.push(item);
        });


        //edit task
        if (task == "edit") {
            $.ajax({
                url: copoFormsURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': 'form',
                    'component': component,
                    'target_id': records[0].record_id //only allowing row action for edit, hence first record taken as target
                },
                success: function (data) {
                    json2HtmlForm(data);
                },
                error: function () {
                    alert("Couldn't build sample form!");
                }
            });
        }

        //table.rows().deselect(); //deselect all rows


    } //end of func

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
    }

    function manage_cell_edit(table, cell) {
        // function handles editing of cell

        var node = cell.node();

        //does cell have 'focus'?
        var nodeClass = node.className.split(" ");

        if (nodeClass.indexOf("focus") == -1) {
            return false;
        }

        //get record id of target cell
        var recordID = table.row(cell.index().row).id().split("row_")[1];


        //is it a call to edit or save?
        if ($(node).find(".cell-edit-panel").length) { // call to save
            //get cell form data
            var form_values = {};
            $(node).find(".cell-edit-panel").find(":input").each(function () {
                try {
                    form_values[this.id] = $(this).val().trim();
                }
                catch (err) {
                    form_values[this.id] = $(this).val();
                }
            });

            $(node).find("#cell-loader").show();
            $(node).find(".cell-edit-panel").hide();

            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'request_action': "save_cell_data",
                    'cell_reference': dtColumns[cell.index().column].data,
                    'record_id': recordID,
                    'auto_fields': JSON.stringify(form_values),
                    'description_token': sampleDescriptionToken

                },
                success: function (data) {
                    if (data.cell_update.status == 'success') {

                        //set data and redraw table
                        table
                            .cell(cell.index().row, cell.index().column)
                            .data(data.cell_update.value)
                            .invalidate()
                            .draw();

                        //refresh search box
                        table
                            .search('')
                            .draw();


                        //re-enable table navigation keys
                        table.keys.enable();

                        //deselect previously selected rows
                        table.rows('.selected').deselect();

                        //set focus on next row
                        table.cell(cell.index().row + 1, cell.index().column).focus();
                    } else {
                        $(node).find("#cell-loader").hide();
                        $(node).find(".cell-edit-panel").show();
                        alert("Error: " + data.cell_update.message);
                    }
                },
                error: function () {
                    alert("Error while attempting to update sample cell!");
                }
            });

        } else { // call to edit
            //disable table navigation keys
            table.keys.disable();

            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'request_action': "get_cell_control",
                    'cell_reference': dtColumns[cell.index().column].data,
                    'record_id': recordID,
                    'description_token': sampleDescriptionToken

                },
                success: function (data) {
                    var formElem = data.cell_control.control_schema;
                    var elemValue = data.cell_control.schema_data;
                    var htmlCtrl = dispatchFormControl[controlsMapping[formElem.control.toLowerCase()]](formElem, elemValue);
                    htmlCtrl.find("label").remove();

                    var cellEditPanel = get_cell_edit_panel();
                    cellEditPanel.find("#cell-loader").hide();
                    cellEditPanel.find(".cell-edit-panel").append(htmlCtrl);
                    $(node)
                        .html('')
                        .append(cellEditPanel);

                    //set focus to control
                    if (cellEditPanel.find(".form-control")) {
                        cellEditPanel.find(".form-control").focus();
                    } else if (cellEditPanel.find(".input-copo")) {
                        cellEditPanel.find(".input-copo").focus();
                    }

                    refresh_tool_tips();
                    toggle_display_help_tips($('input[name="' + wizhlptipchk + '"]').bootstrapSwitch('state'), $("#sampleWizard"));

                    //set focus to selectize control
                    if (selectizeObjects.hasOwnProperty(formElem.id)) {
                        var selectizeControl = selectizeObjects[formElem.id];
                        selectizeControl.focus();
                    }
                },
                error: function () {
                    alert("Error while attempting to build cell form!");
                    table.keys.enable();
                    return false;
                }
            });
        }
    }

    function get_cell_edit_panel() {
        var attributesPanel = $('<div/>', {
            class: "cell-edit-panel",
            style: "min-width:450px; border:none; margin-bottom:0px; padding:5px;"
        });

        var loaderObject = $('<div>', {
            style: 'text-align: center; margin-top: 3px;',
            id: "cell-loader",
            html: "<span class='fa fa-spinner fa-pulse fa-2x'></span>"
        });

        return $('<div>').append(attributesPanel).append(loaderObject);
    }

    function generate_sample_edit_table(stage) {
        //function provides stage information sample attribute editing
        var tableID = stage.ref + "_table";
        var stageHTML = $('<div/>', {"class": "alert alert-default"});
        var messageDiv = $('<div/>',
            {
                "class": wizardMessages.review_message.text_class,
                style: "line-height: 150%",
                html: wizardMessages.review_message.text
            });

        $('#custom-renderer_' + stage.ref).html('').append(stageHTML);

        stageHTML.append(messageDiv);

        //table element
        var tableDiv = $('<div/>', {style: "margin-top: 10px;"});
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
        var loaderHTML = $('<div/>', {style: "margin-top:20px;"});
        var loaderMessage = $('<div/>', {
            class: "text-primary",
            style: "margin-top: 20px; font-weight:bold;",
            html: "Generating samples..."
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
                'description_token': sampleDescriptionToken

            },
            success: function (data) {
                loaderHTML.remove();

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
                            filename: "copo_samples_" + String(sampleDescriptionToken)
                        }
                    ],
                    language: {
                        "info": " _START_ to _END_ of _TOTAL_ samples",
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
                        columns: ':not(:first-child)',
                        focus: ':eq(1)', // cell that will receive focus when the table is initialised, set to the first editable cell defined
                        keys: [9, 13, 37, 39, 38, 40],
                        blurable: false
                    },
                    scrollX: true,
                    // scroller: true,
                    // scrollY: 300,
                    columns: dtColumns
                });

                sampleTableInstance = table;

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
                            batch_update_records(table);
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
                alert("Couldn't generate stage information!");
            }
        });

    }

    function batch_update_records(table) {
        //function uses value from focused cell to update selected records
        var cells = table.cells('.focus');
        var cell = null;

        //get referenced cell
        if (cells && cells[0].length > 0) {
            cell = cells[0];
            cell = table.cell(cell[0].row, cell[0].column);
        } else {
            return false;
        }

        //var node = cell.node();

        //get record id of target cell
        var recordID = table.row(cell.index().row).id().split("row_")[1];

        //get selected rows ids for batch update
        var target_rows = table.rows('.selected').ids().toArray();


        if (target_rows.length == 0) {
            BootstrapDialog.show({
                title: "Batch update action",
                message: "Select one or more records to update corresponding cells",
                cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [{
                    label: 'OK',
                    cssClass: 'tiny ui basic orange button',
                    action: function (dialogRef) {
                        dialogRef.close();
                        return false;
                    }
                }]
            });

            return false;
        }

        //disable table navigation keys
        table.keys.disable();

        var loaderObject = $('<div>', {
            style: 'text-align: center; margin-top: 3px;',
            html: "<span class='fa fa-spinner fa-pulse fa-2x'></span>"
        });

        $("#updating_cell_button").html("");
        $("#updating_cell_button").append("<span>Updating records, please wait</span>");
        $("#updating_cell_button").append(loaderObject);


        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': "batch_update",
                'cell_reference': dtColumns[cell.index().column].data,
                'record_id': recordID,
                'target_rows': JSON.stringify(target_rows),
                'description_token': sampleDescriptionToken

            },
            success: function (data) {
                if (data.batch_update) {
                    if (data.batch_update.status == "success") {
                        if (data.batch_update.data_set) {
                            dtRows = data.batch_update.data_set;

                            table.rows().deselect();

                            table
                                .clear()
                                .draw();
                            table
                                .rows
                                .add(dtRows);
                            table
                                .columns
                                .adjust()
                                .draw();
                            table
                                .search('')
                                .columns()
                                .search('')
                                .draw();
                        } else {
                            //get selected rows indexes for batch update

                            var rowIndexes = table.rows('.selected').indexes().toArray(); //get selected rows index

                            var cellNodes = table.cells(rowIndexes, cell.index().column).nodes(); //get target cells node
                            $(cellNodes).html(data.batch_update.value); //batch update cells display with new value

                            var col = dtColumns[cell.index().column].data; //get target column

                            for (var i = 0; i < rowIndexes.length; ++i) { //update data-source
                                dtRows[rowIndexes[i]][col] = data.batch_update.value;
                            }

                            table.rows().deselect();

                            table
                                .rows()
                                .invalidate()
                                .draw();

                            //refresh search box
                            table
                                .search('')
                                .draw();
                        }

                        table.cell(cell.index().row, cell.index().column).focus();

                    } else {
                        alert(data.batch_update.message);
                    }

                    table.keys.enable();

                    $("#updating_cell_button").html("");
                    $("#updating_cell_button").append("<span>Update selected records</span>");

                }
            },
            error: function () {
                alert("Batch update error!");
                table.keys.enable();

                $("#updating_cell_button").html("");
                $("#updating_cell_button").append("<span>Update selected records</span>");
            }
        });

    }

    function finalise_description() {
        var $dialogContent = $('<div/>');
        var notice_div = $('<div/>').html("Finalising description...");
        var spinner_div = $('<div/>', {style: "margin-left: 40%; padding-top: 15px; padding-bottom: 15px;"}).append($('<div class="copo-i-loader"></div>'));

        var dialog = new BootstrapDialog({
            type: BootstrapDialog.TYPE_PRIMARY,
            size: BootstrapDialog.SIZE_NORMAL,
            title: function () {
                return $('<span>Sample Description</span>');
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
                        'request_action': "finalise_description",
                        'description_token': sampleDescriptionToken

                    },
                    success: function (data) {
                        if (data.finalise_result.status == 'success') {
                            window.location.reload();
                        } else {
                            var $feeback = $('<div/>', {
                                "class": "webpop-content-div",
                                style: "padding-bottom: 15px;"
                            }).html("The following error was encountered while finalising description! Please click the review button to effect changes.");
                            var $button = $('<div class="tiny ui red button">Review description</div>');
                            $button.on('click', {dialogRef: dialogRef}, function (event) {
                                event.data.dialogRef.close();
                            });

                            dialog.setType(BootstrapDialog.TYPE_DANGER);
                            dialog.getModalBody().html('').append($feeback).append($button);
                        }

                    },
                    error: function () {
                        alert("Error finalising description!");
                    }
                });
            },
            buttons: []
        });


        $dialogContent.append(notice_div).append(spinner_div);
        dialog.realize();
        dialog.setMessage($dialogContent);
        dialog.open();
    }

    function pending_sample_description() {
        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': "pending_description",
                'profile_id': $('#profile_id').val()
            },
            success: function (data) {
                if (data.pending.length) {
                    var infoPanelElement = trigger_global_notification();

                    for (var i = 0; i < data.pending.length; ++i) {
                        var rec = data.pending[i];
                        var message = $('<div/>');
                        message.append("<h4>Incomplete description</h4>");
                        message.append("<span>Modified on: </span>");
                        message.append(rec.created_on);
                        message.append("<div></div>");
                        message.append("<span>Number of samples: </span>");
                        message.append(rec.number_of_samples);
                        message.append("<div></div>");
                        message.append("<span style='color: #c93c00'>" + rec.grace_period + " before automatic deletion</span>");
                        message.append("<div style='margin-top: 10px;'></div>");

                        var dismissTour = '<a class="delete-description-i pull-right" href="#" role="button" ' +
                            'style="text-decoration: none; color:  #c93c00;" data-target="' + rec._id + '" title="delete description" aria-haspopup="true" aria-expanded="false">' +
                            '<i class="fa fa-times-circle" aria-hidden="true">' +
                            '</i>&nbsp; Delete</a>';

                        var takeTour = '<a class="reload-description-i" href="#" role="button" ' +
                            'style="text-decoration: none; color: #35637e;" data-target="' + rec._id + '" title="reload description" aria-haspopup="true" aria-expanded="false">' +
                            '<i class="fa fa-refresh" aria-hidden="true">' +
                            '</i>&nbsp; Reload</a>';

                        message.append("<hr/>");
                        message.append(dismissTour);
                        message.append(takeTour);

                        var alertElement = $(".alert-templates").find(".alert-info").clone();
                        alertElement.addClass("inc-desc-badge");
                        alertElement.find(".alert-message").append(message);
                        infoPanelElement.prepend(alertElement);
                    }
                }
            },
            error: function () {
                console.log("Couldn't complete request for pending description");
            }
        });
    }

    function delete_incomplete_description(elem, description_token) {
        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': "delete_pending_description",
                'description_token': description_token
            },
            success: function (data) {
                elem.closest(".inc-desc-badge").remove();
            },
            error: function () {
                console.log("Couldn't complete request for deleting description");
            }
        });
    }


    function reload_incomplete_description(elem, description_token) {
        if ($("#wizard_toggle").is(":visible")) {
            BootstrapDialog.show({
                title: 'Description reload warning',
                message: "<div class='webpop-content-div'>There's a running description session. Terminate the current session before attempting a reload.</div>",
                cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [
                    {
                        label: 'OK',
                        cssClass: 'tiny ui basic orange button',
                        action: function (dialogRef) {
                            dialogRef.close();
                        }
                    }
                ]
            });

            return false;
        } else {
            $("#wizard_toggle").collapse("toggle");

            //hide the review stage -- to be redisplayed when all the dynamic stages are displayed
            $('#sampleWizard').find('.steps li:last-child').hide();

            elem.closest(".inc-desc-badge").remove();

            sampleDescriptionToken = description_token;
        }
    }

}); //end document ready