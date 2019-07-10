var datafileDescriptionToken = '';
var datafileTableInstance = null;
var key_split = "___0___";

$(document).ready(function () {
    //****************************** Event Handlers Block *************************//


    //page global variables
    var csrftoken = $('[name="csrfmiddlewaretoken"]').val();
    var component = "datafile";
    var wizardURL = "/rest/data_wiz/";
    var copoFormsURL = "/copo/copo_forms/";
    var samples_from_study_url = "/rest/samples_from_study/";

    //wizard object
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
    componentMeta.table_columns = JSON.parse($("#table_columns").val());

    do_render_server_side_table(componentMeta);


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

    //trigger the description wizard
    $('body').on('addmetadata', function (event) {
        initiate_datafile_description({'description_token': event.bundleID});
    });

    //exit_description
    $('body').on('exitdescription', function (event) {
        terminate_description();
    });

    $("#upload_mirror").on('click', function (event) {
        $("#main_file_upload").trigger('click');
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

    //custom stage renderers
    var dispatchStageRenderer = {
        perform_datafile_generation: function (stage) {
            generate_datafile_edit_table(stage);
        },
        perform_datafile_pairing: function (stage) {
            display_pairing_info(stage);
        }
    }; //end of dispatchStageCallback

    //Enter-key event for table cell update...
    $(document).on('keypress', '.cell-edit-panel', function (event) {
        var keyCode = event.keyCode || event.which;
        if (keyCode === 13) {
            event.preventDefault();

            var cells = datafileTableInstance.cells('.focus');

            if (cells && cells[0].length > 0) {
                $(document).find(".copo-form-group").webuiPopover('destroy');

                var cell = cells[0];
                var targetCell = datafileTableInstance.cell(cell[0].row, cell[0].column);

                manage_cell_edit(datafileTableInstance, targetCell);
            }

            return false;
        }
    });


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
                console.log("sent data to session " + data);
            }
        });
    });

    //instantiate/refresh tooltips
    refresh_tool_tips();

    //handle annotation wizard study dropdown onchange
    $(document).on('change', '#study_copo', handle_wizard_study_dropdown_onchange);


    //******************************* wizard events *******************************//

    //handle event for saving description for later...
    $('#exit_wizard').on('click', function (event) {
        exit_wizard();
    });

    //handle events for step change
    wizardElement.on('actionclicked.fu.wizard', function (evt, data) {
        $(self).data('step', data.step);

        stage_navigate(evt, data);
    });

    //
    $(document).on('click', '.wiz-btn-next', function (event) {
        wizardElement.wizard('next');
    });

    $(document).on('click', '.wiz-btn-prev', function (event) {
        wizardElement.wizard('previous');
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

    function toggle_disable_next() {
        //disables/enables wizard's next button
        var elem = $(".btn-next");
        if (elem.hasClass("loading")) {
            elem.removeClass("loading");
            elem.prop('disabled', false);
        } else {
            elem.addClass("loading");
            elem.prop('disabled', true);
        }
    }

    function stage_navigate(evt, data) {
        if (data.direction == 'next') {

            evt.preventDefault();


            //end of wizard intercept
            if (wizardElement.find('.steps li.active:first').attr('data-name') == 'review') {
                finalise_description(datafileDescriptionToken, true);
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
            toggle_disable_next();


        } else if (data.direction == 'previous') {
            // get the proposed or intended state, for which action is intercepted
            evt.preventDefault();

            set_wizard_stage(data.step - 1);

            //re-enable stage navigation button
            var elem = $(".btn-next");
            if (elem.hasClass("loading")) {
                elem.removeClass("loading");
                elem.prop('disabled', false);
            }
        }

    } //end stage_navigate()

    function exit_wizard() {
        var message = $('<div/>', {class: "webpop-content-div"});
        message.append("Are you sure you want to stop describing this bundle? You can return to this description later.</div>");
        BootstrapDialog.show({
            title: "Exit wizard",
            message: message,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_WARNING,
            buttons: [
                {
                    label: 'Exit',
                    cssClass: 'tiny ui button',
                    action: function (dialogRef) {
                        terminate_description();

                        dialogRef.close();
                        return false;
                    }
                },
                {
                    label: 'Cancel',
                    cssClass: 'tiny ui button',
                    action: function (dialogRef) {
                        dialogRef.close();
                        return false;
                    }
                }
            ]
        });
    }

    function terminate_description() {
        datafileDescriptionToken = '';

        //clear wizard stages
        var numSteps = wizardElement.find('.steps li').length;
        var howMany = numSteps - 1;
        wizardElement.wizard('removeSteps', 1, howMany);
        wizardElement.find('.steps li:last-child').show();

        //reset wizard forms
        wizardElement.find('.wizard-dynamic-form').each(function () {
            $(this).trigger("reset");
        });

        var elem = $(".btn-next");
        if (elem.hasClass("loading")) {
            elem.removeClass("loading");
            elem.prop('disabled', false);
        }

        $("#wizard_toggle").hide();

        //set bundle status
        set_bundle_status();
    }

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

                //check for description name
                if (wizard_components.hasOwnProperty('description_label') && wizard_components.description_label.trim() != '') {
                    $("#datafile_description_panel_title").html(" " + wizard_components.description_label);
                }

                //set bundle status
                set_bundle_status();

            },
            error: function () {
                alert("Couldn't retrieve next stage!");
            }
        });
    } //end add_step()

    function finalise_description(description_token, show_exit_wizard) {
        var message = $('<div/>', {class: "webpop-content-div"});
        message.append("Do you want to proceed with the submission of this bundle?");
        var downloadTimer = null;

        var modal_buttons = [
            {
                id: 'btn-submission-go',
                label: 'Submit',
                cssClass: 'tiny ui basic teal button',
                action: function (dialogRef) {
                    var $button = this;
                    $button.disable();

                    $("#cover-spin").css("display", "block");
                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: {
                            'request_action': 'initiate_submission',
                            'description_token': description_token,
                            'profile_id': $('#profile_id').val()
                        },
                        success: function (data) {
                            if (data.result.existing || false) {
                                $("#cover-spin").css("display", "none");
                                message.html("<div class='text-info'>This bundle is already in the submission stream. You will now be redirected to the submission page. </div>");
                                message.append('<div style="margin-top: 5px;">Click the Cancel button below to remain on this page.</div>');
                                message.append('<div style="margin-top: 10px;"><progress value="0" max="10" id="progressBarSubmit"></progress></div>');
                                var timeleft = 10;
                                downloadTimer = setInterval(function () {
                                    document.getElementById("progressBarSubmit").value = 10 - timeleft;
                                    timeleft -= 1;
                                    if (timeleft <= 0) {
                                        clearInterval(downloadTimer);
                                        window.location.replace($("#submission_url").val());
                                    }
                                }, 1000);
                            } else {
                                dialogRef.close();
                                window.location.replace($("#submission_url").val());
                            }

                            return false;
                        },
                        error: function () {
                            $("#cover-spin").css("display", "none");
                            alert("Couldn't initiate submission!");
                        }
                    });
                }
            },
            {
                label: 'Cancel',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    dialogRef.close();
                    if (downloadTimer) {
                        clearInterval(downloadTimer);
                    }
                }
            }
        ];

        if (show_exit_wizard) {
            modal_buttons.splice(1, 0, {
                label: 'Exit wizard',
                cssClass: 'tiny ui basic secondary button',
                action: function (dialogRef) {
                    dialogRef.close();
                    if (downloadTimer) {
                        clearInterval(downloadTimer);
                    }

                    terminate_description();
                }
            });
        }

        var dialog = new BootstrapDialog.show({
            title: "Confirm bundle submission",
            message: message,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_INFO,
            // size: BootstrapDialog.SIZE_NORMAL,
            buttons: modal_buttons
        });

        return false;

    } //end finalise_description()

    function set_wizard_stage(proposedState) {
        wizardElement.wizard('selectedItem', {
            step: proposedState
        });

        toggle_disable_next();
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
            toggle_disable_next();
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

            set_up_validator($("#wizard_form_" + numSteps));
            toggle_disable_next();
        }

        //check for bundle violation
        if (stage.hasOwnProperty("bundle_violation")) {
            BootstrapDialog.show({
                title: "Incompatible metadata",
                message: stage.bundle_violation,
                // cssClass: 'copo-modal2',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_DANGER,
                size: BootstrapDialog.SIZE_NORMAL,
                buttons: [
                    {
                        label: 'OK',
                        cssClass: 'tiny ui basic red button',
                        action: function (dialogRef) {
                            dialogRef.close();
                        }
                    }
                ]
            });
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
        var stage_pane = $('<div/>', {
            class: "row"
        });

        var left = $('<div/>', {
            class: "col-sm-9"
        });

        var right = $('<div/>', {
            class: "col-sm-3"
        });

        var message = $('<div/>', {class: "webpop-content-div"});
        message.append(stage_message);


        var feedback = get_feedback_pane();
        feedback.find(".close").remove();
        feedback
            .removeClass("success");

        feedback.find(".header").html("");
        feedback.find("p").append(message);

        right.append(feedback);

        stage_pane
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

        var navrow = $('<div/>', {
            class: "row",
            style: "margin-top:20px;"
        });

        var navcol = $('<div/>', {
            class: "col-sm-12"
        });

        var navbuttons = '<div class="large ui buttons">\n' +
            '  <button class="ui button wiz-btn-prev btn-prev">Prev</button>\n' +
            '  <div class="or"></div>\n' +
            '  <button class="ui primary button wiz-btn-next btn-next">Next</button>\n' +
            '</div>';

        navcol.append(navbuttons);
        navrow.append(navcol);
        left.append('<hr/>');
        left.append(navrow);

        return stage_pane;
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
            } catch (err) {
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
        } else {

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
        //var tableID = event.tableID; //get target table

        var records = server_side_select[component];

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
        }

    } //end of func

    function initiate_datafile_description(parameters) {
        var description_token = '';

        if (parameters.hasOwnProperty('description_token')) {
            description_token = parameters.description_token;
        }

        if (!description_token) {
            var message = $('<div/>', {class: "webpop-content-div"});
            message.append("Couldn't retrieve bundle information. You may try refreshing your page to reload bundle information.</div>");

            BootstrapDialog.show({
                title: "Datafiles description error",
                message: message,
                cssClass: 'copo-modal2',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_DANGER,
                buttons: [
                    {
                        label: 'OK',
                        cssClass: 'tiny ui button',
                        action: function (dialogRef) {
                            dialogRef.close();
                            return false;
                        }
                    }
                ]
            });

            return false;
        }

        if (!$("#wizard_toggle").is(":visible")) {
            datafileDescriptionToken = description_token;
            bootstrap_wizard();
            return false;
        }

        if ($("#wizard_toggle").is(":visible") && (description_token !== datafileDescriptionToken)) {
            var message = $('<div/>', {class: "webpop-content-div"});

            message.append("There's an ongoing description. Do you want to suspend the current description and start a new one?</div>");

            BootstrapDialog.show({
                title: "Start new description",
                message: message,
                cssClass: 'copo-modal2',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [
                    {
                        label: 'Start new',
                        cssClass: 'tiny ui button',
                        action: function (dialogRef) {
                            datafileDescriptionToken = description_token;

                            //clear wizard stages
                            var numSteps = wizardElement.find('.steps li').length;
                            var howMany = numSteps - 1;
                            wizardElement.wizard('removeSteps', 1, howMany);
                            wizardElement.find('.steps li:last-child').show();

                            bootstrap_wizard();
                            dialogRef.close();
                            return false;
                        }
                    },
                    {
                        label: 'Cancel',
                        cssClass: 'tiny ui button',
                        action: function (dialogRef) {
                            dialogRef.close();
                            return false;
                        }
                    }
                ]
            });

            return false;
        } else {
            $('html, body').animate({
                scrollTop: $('#wizard_toggle').offset().top - 60
            }, 'slow');
        }

    } //end function

    function bootstrap_wizard() {
        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': "initiate_description",
                'description_token': datafileDescriptionToken,
                'profile_id': $('#profile_id').val()

            },
            success: function (data) {
                if (data.result.status == 'success') {
                    var wizard_components = data.result.next_stage;

                    //sometimes an abort signal might come through from the server...
                    if (wizard_components.hasOwnProperty('abort') && wizard_components.abort) {
                        //abort the description

                        BootstrapDialog.show({
                            title: 'Wizard Error!',
                            message: "Couldn't instantiate the description due to an unknown error. You may want to refresh your page to potential resolve the issue.",
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
                                        return false;
                                    }
                                }
                            ]
                        });

                        return false;
                    }

                    //set status for bundles
                    set_bundle_status();

                    //display wizard
                    $("#wizard_toggle").show();

                    $('html, body').animate({
                        scrollTop: $('#wizard_toggle').offset().top - 60
                    }, 'slow');

                    //hide the review stage -- to be redisplayed when all the dynamic stages have been displayed
                    wizardElement.find('.steps li:last-child').hide();

                    //display bundle name
                    if (wizard_components.hasOwnProperty('description_label') && wizard_components.description_label.trim() != '') {
                        $("#datafile_description_panel_title").html(" " + wizard_components.description_label);
                    }

                    //call to refresh wizard
                    if (wizard_components.hasOwnProperty('refresh_wizard') && wizard_components.refresh_wizard) {
                        refresh_wizard();
                    }

                    //check for and set stage
                    if (wizard_components.hasOwnProperty('stage')) {
                        process_wizard_stage(wizard_components.stage);
                    }

                    var elem = $(".btn-next");
                    if (elem.hasClass("loading")) {
                        elem.removeClass("loading");
                        elem.prop('disabled', false);
                    }

                } else {
                    alert("Error: " + data.result.message);
                }

            },
            error: function () {
                alert("Error instantiating description!");
            }
        });

        $("[data-toggle='tooltip']").tooltip();
    }

    function set_bundle_status() {
        $('.description-bundle-panel').find(".bundle-header, .bundle-status").removeClass("blue");

        if (datafileDescriptionToken) {
            var parentElem = $('.description-bundle-panel[data-id="' + datafileDescriptionToken + '"]');
            parentElem.prependTo(parentElem.parent());
            parentElem.find(".bundle-header, .bundle-status").addClass("blue");
        }
    }


    function display_pairing_info(stage) {
        //function handles display of pairing information

        if (stage.hasOwnProperty("error") && stage.error) {
            BootstrapDialog.show({
                title: "Pairing error",
                message: stage.error,
                cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_DANGER,
                buttons: [{
                    label: 'OK',
                    cssClass: 'tiny ui basic orange button',
                    action: function (dialogRef) {
                        set_wizard_stage(wizardElement.wizard('selectedItem').step - 1); //reset to first stage of the wizard
                        var elem = $(".btn-next");
                        if (elem.hasClass("loading")) {
                            elem.removeClass("loading");
                            elem.prop('disabled', false);
                        }
                        refresh_wizard(); //refresh wizard to account for the change

                        dialogRef.close();
                        return false;
                    }
                }]
            });

            return false;
        }

        var stageHTML = $('<div/>', {"class": "alert alert-default"});

        stageHTML.append($('<div/>', {style: "margin-bottom: 10px;"}));

        var messageDiv = $('<div/>',
            {
                html: '<i class="fa fa-info-circle text-info"></i><span class="action-label" style="padding-left: 8px;">' + stage.message + '</span>',
                class: "text-info",
                style: "line-height: 150%; display:none;",
                href: "#attributes-edit"
            });


        var tableID = 'datafile_pairing_tbl';
        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        $('#custom-renderer_' + stage.ref).find(".stage-content")
            .html('')
            .append(stageHTML);

        stageHTML.append($('<div/>', {style: "margin-bottom: 25px;"}).append(messageDiv));

        stageHTML.append(tbl);

        var dtd = stage.data;
        var cols = [
            {title: "File1", data: "file1"},
            {title: "File2", data: "file2"}
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
            buttons: [
                'selectAll',
                'selectNone',
                {
                    extend: 'csv',
                    text: 'Export & revise',
                    title: null,
                    filename: "copo_datafiles_pairs_" + String(datafileDescriptionToken)
                },
                {
                    text: 'Paste revised',
                    action: function (e, dt, node, config) {
                        BootstrapDialog.show({
                            title: "Revised pairing",
                            message: '<div id="pairing_info_message_div" style="margin-bottom: 10px; color: #ff0000;"></div><div>Copy and paste the revised pairing below: <textarea id="pairing_info_val" rows="10" cols="50" class="form-control"></textarea></div>',
                            buttons: [
                                {
                                    label: 'Cancel',
                                    cssClass: 'tiny ui basic button',
                                    action: function (dialogRef) {
                                        dialogRef.close();
                                    }
                                },
                                {
                                    icon: 'glyphicon glyphicon-refresh',
                                    label: 'Validate',
                                    cssClass: 'tiny ui basic primary button',
                                    action: function (dialogRef) {
                                        var pairing_info = $.trim(dialogRef.getModalBody().find("#pairing_info_val").val());
                                        var form_values = {};
                                        var activeStageIndx = wizardElement.wizard('selectedItem').step;
                                        $('#wizard_form_' + activeStageIndx).find(":input").each(function () {
                                            form_values[this.id] = $(this).val();
                                        });

                                        form_values.pairing_info = pairing_info;

                                        var $button = this;
                                        $button.spin();

                                        dialogRef.enableButtons(false);
                                        dialogRef.setClosable(false);

                                        //validate pairing and give feedback
                                        $.ajax({
                                            url: wizardURL,
                                            data: {
                                                "request_action": "validate_datafile_pairing",
                                                "auto_fields": JSON.stringify(form_values),
                                                "description_token": datafileDescriptionToken
                                            },
                                            type: "POST",
                                            beforeSend: function (xhr) {
                                                xhr.setRequestHeader('X-CSRFToken', csrftoken);
                                            },
                                            success: function (data) {
                                                if (data.result.status == "error") {
                                                    $button.stopSpin();
                                                    dialogRef.enableButtons(true);
                                                    dialogRef.setClosable(true);
                                                    dialogRef.getModalBody().find("#pairing_info_message_div").html(data.result.message);
                                                    return false;
                                                } else {
                                                    dialogRef.getModalBody().find("#pairing_info_message_div").html('');

                                                    table.rows().deselect();
                                                    table
                                                        .clear()
                                                        .draw();
                                                    table
                                                        .rows
                                                        .add(data.result.data);
                                                    table
                                                        .columns
                                                        .adjust()
                                                        .draw();
                                                    table
                                                        .search('')
                                                        .columns()
                                                        .search('')
                                                        .draw();

                                                    dialogRef.close();
                                                }
                                            }
                                        });
                                    }
                                }]
                        });

                    }
                }
            ],
            select: {
                style: 'multi'
            },
            language: {
                "info": " _START_ to _END_ of _TOTAL_ datafile pairs",
                "search": " ",
                buttons: {
                    selectAll: "Select all",
                    selectNone: "Clear selection"
                }
            },
            columns: cols,
            dom: 'Bfr<"row"><"row info-rw" i>tlp'
        });

        table
            .buttons()
            .nodes()
            .each(function (value) {
                $(this)
                    .removeClass("btn btn-default")
                    .addClass('tiny ui basic button');
            });

        $('#' + tableID + '_wrapper')
            .find(".dataTables_filter")
            .find("input")
            .removeClass("input-sm")
            .attr("placeholder", "Search pairs");

        //add custom buttons

        var customButtons = $('<span/>', {
            style: "padding-left: 15px;",
            class: "copo-table-cbuttons"
        });


        $(table.buttons().container()).append(customButtons);
        $('#' + tableID + '_wrapper').css({"margin-top": "10px"});
        $('#' + tableID + '_wrapper').find(".info-rw").css({"margin-top": "10px"});

        //apply to selected rows button
        var unpairButton = $('<button/>',
            {
                class: "tiny ui basic red button",
                type: "button",
                html: '<i class="fa fa-chain-broken" aria-hidden="true" style=" font-size: 12px !important; padding-right: 5px;"></i>Unpair selected records',
                click: function (event) {
                    event.preventDefault();
                    unpair_datafiles(table);
                }
            });

        customButtons.append(unpairButton);

        refresh_tool_tips();

        messageDiv.show();
    }

    function generate_datafile_edit_table(stage) {
        //function provides stage information for datafile attributes editing

        var btnNext = $(".btn-next");
        btnNext.addClass("loading");
        btnNext.prop('disabled', true);

        var tableID = stage.ref + "_table";
        var stageHTML = $('<div/>', {"class": "alert alert-default"});

        var messageDiv = $('<a/>',
            {
                html: '<i class="fa fa-2x fa-info-circle text-info"></i><span class="action-label" style="padding-left: 8px;">Metadata review tips...</span>',
                class: "text-info",
                style: "line-height: 150%; display:none;",
            });


        // refresh dynamic content
        $('#custom-renderer_' + stage.ref).find(".stage-content")
            .html('')
            .append(stageHTML);

        stageHTML.append($('<div/>', {style: "margin-bottom: 10px;"}).append(messageDiv));

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

        loaderHTML.append('<i class="fa fa-spinner fa-spin text-info" style="font-size:30px; margin-right: 6px;" aria-hidden="true"></i><span class="text-info" style="font-size: 15px;">Generating datafile attributes. This might take a while...</span>');
        stageHTML.append(loaderHTML);

        $.ajax({
            url: wizardURL,
            data: {
                'request_action': "get_discrete_attributes",
                "description_token": datafileDescriptionToken
            },
            type: "POST",
            beforeSend: function (xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrftoken);
            },
            success: function (data) {

                loaderHTML.html('');
                messageDiv.show();

                messageDiv.webuiPopover('destroy');
                messageDiv.webuiPopover({
                    content: '<div class="webpop-content-div limit-text">' + stage.message + '</div>',
                    arrow: true,
                    width: 400,
                    trigger: 'hover',
                });


                dtColumns = data.table_data.columns;
                dtRows = data.table_data.rows;

                render_datafile_attributes_table(tableID);

                btnNext.removeClass("loading");
                btnNext.prop('disabled', false);

            }
        });

    } //end of function

    function render_datafile_attributes_table(tableID) {
        var table = null;

        if ($.fn.dataTable.isDataTable('#' + tableID)) {
            //if table instance already exists, then do refresh
            table = $('#' + tableID).DataTable();
        }

        if (table) {
            //clear old, set new data
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
            table = $('#' + tableID).DataTable({
                data: dtRows,
                dom: 'Bfr<"row"><"row info-rw" i>tlp',
                searchHighlight: true,
                lengthChange: true,
                select: {
                    style: 'multi',
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
                        extend: 'csv',
                        text: 'Export CSV',
                        title: null,
                        filename: "copo_datafiles_" + String(datafileDescriptionToken)
                    }
                ],
                language: {
                    "info": " _START_ to _END_ of _TOTAL_ datafiles",
                    buttons: {
                        selectAll: "Select all",
                        selectNone: "Select none"
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
            $('#' + tableID + '_wrapper').css({"margin-top": "10px"});
            $('#' + tableID + '_wrapper').find(".info-rw").css({"margin-top": "10px"});

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

            // //add event for enter key press and cell double-click
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

            //add event for column highlighting and tooltip
            $('#' + tableID + ' tbody')
                .on('mouseenter', 'td', function () {
                    var colIdx = table.cell(this).index().column;
                    var message = '<div class="webpop-content-div limit-text">' + "<strong>Datafile</strong>: " + dtRows[table.cell(this).index().row].name + "<br/><strong>Attribute</strong>: " + dtColumns[colIdx].title + '</div>';

                    var infoPanelElement = trigger_global_notification();
                    infoPanelElement.find(".cell-data-position").remove();

                    var alertElement = $(".alert-templates").find(".alert-info").clone();
                    alertElement.addClass("cell-data-position");
                    alertElement.find(".alert-message").html(message);
                    infoPanelElement.prepend(alertElement);
                });
        }
    } // end of function


    function manage_cell_edit(table, cell) {
        // function handles editing of cell

        var node = cell.node();

        //does cell have 'focus'?
        var nodeClass = node.className.split(" ");

        if (nodeClass.indexOf("focus") == -1) {
            return false;
        }

        //is cell locked from edit?
        if (nodeClass.indexOf("locked-column") > -1) {
            show_locked_cell_message(cell);

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
                } catch (err) {
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
                    'target_id': recordID,
                    'auto_fields': JSON.stringify(form_values),
                    'description_token': datafileDescriptionToken

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
            $(node)
                .html('')
                .append(cell_loader_icon());
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
                    'target_id': recordID,
                    'description_token': datafileDescriptionToken

                },
                success: function (data) {
                    var formElem = data.cell_control.control_schema;
                    var elemValue = data.cell_control.schema_data;
                    var htmlCtrl = dispatchFormControl[controlsMapping[formElem.control.toLowerCase()]](formElem, elemValue);
                    // htmlCtrl.find("label").remove();

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
                    toggle_display_help_tips($('input[name="' + wizhlptipchk + '"]').bootstrapSwitch('state'), wizardElement);

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

    function batch_update_records(table) {
        //function uses value from focused cell to update selected records
        var cells = table.cells('.focus');
        var cell = null;

        //get referenced cell
        if (cells && cells[0].length > 0) {
            cell = cells[0];
            cell = table.cell(cell[0].row, cell[0].column);
        } else {
            $("#updating_cell_button").removeClass('updating');
            return false;
        }

        var node = cell.node();

        //does cell have 'focus'?
        var nodeClass = node.className.split(" ");

        //is cell locked from edit?
        if (nodeClass.indexOf("locked-column") > -1) {
            show_locked_cell_message(cell);
            table.rows().deselect();

            $("#updating_cell_button").removeClass('updating');
            return false;
        }

        //get record id of target cell
        var recordID = table.row(cell.index().row).id().split("row_")[1];

        //get selected rows ids for batch update
        var target_rows = table.rows('.selected').ids().toArray();


        if (target_rows.length == 0) {
            BootstrapDialog.show({
                title: "Batch update action",
                message: "Select one or more records to update corresponding cells",
                // cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [{
                    label: 'OK',
                    cssClass: 'tiny ui basic orange button',
                    action: function (dialogRef) {
                        dialogRef.close();

                        $("#updating_cell_button").removeClass('updating');
                        return false;
                    }
                }]
            });

            $("#updating_cell_button").removeClass('updating');
            return false;
        }

        //ask user confirmation
        if (target_rows.length > 0) {
            BootstrapDialog.show({
                title: "Confirm batch update",
                message: "Corresponding cells in column <span style='color: #ff0000;'>" + dtColumns[cell.index().column].title + "</span> for the selected records will be assigned the value: <span style='color: #ff0000;'>" + dtRows[cell.index().row][dtColumns[cell.index().column].data] + "</span>.<div style='margin-top: 10px;'>Do you want to continue?</div>",
                // cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [
                    {
                        label: 'Cancel',
                        cssClass: 'tiny ui basic button',
                        action: function (dialogRef) {
                            table.rows().deselect();
                            $("#updating_cell_button").removeClass('updating');
                            dialogRef.close();
                            return false;
                        }
                    },
                    {
                        label: 'Continue',
                        cssClass: 'tiny ui basic orange button',
                        action: function (dialogRef) {
                            dialogRef.close();

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
                                    'target_id': recordID,
                                    'description_targets': JSON.stringify(target_rows),
                                    'description_token': datafileDescriptionToken

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

                                    $("#updating_cell_button").removeClass('updating');
                                },
                                error: function () {
                                    alert("Batch update error!");
                                    table.keys.enable();

                                    $("#updating_cell_button").html("");
                                    $("#updating_cell_button").append("<span>Update selected records</span>");
                                    $("#updating_cell_button").removeClass('updating');
                                }
                            });
                        }
                    }
                ]
            });
        }
    }

    function cell_loader_icon() {
        var loaderObject = $('<div>', {
            style: 'text-align: center; margin-top: 3px;',
            id: "cell-loader",
            html: "<span class='fa fa-spinner fa-pulse fa-2x'></span>"
        });

        return loaderObject;
    }

    function get_cell_edit_panel() {
        var attributesPanel = $('<div/>', {
            class: "cell-edit-panel",
            style: "min-width:450px; border:none; margin-bottom:0px; padding:5px;"
        });

        return $('<div>').append(attributesPanel).append(cell_loader_icon());
    }

    function show_locked_cell_message(cell) {
        var stageRef = dtColumns[cell.index().column].data.split(key_split)[0];
        var stageTile = '';
        var stageIndex = -1;

        wizardElement.find('.steps li').each(function () {
            if ($(this).find(".wiz-title").attr("data-stage") == stageRef) {
                stageTile = $(this).find(".wiz-title").html();
                stageIndex = $(this).attr("data-step");
                return false;
            }
        });

        BootstrapDialog.show({
            title: "Update action",
            message: "<div style='color:#ff0000;'>The selected attribute can only be updated using the stage form! </div><div style='margin-top: 20px; font-size: 12px;'>Selected attribute can potentially alter the course of the wizard, and hence the description metadata template. Please use the appropriate wizard stage form to update this attribute.</div>",
            // cssClass: 'copo-modal3',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_WARNING,
            buttons: [
                {
                    label: 'Cancel',
                    cssClass: 'tiny ui basic button',
                    action: function (dialogRef) {
                        dialogRef.close();
                        return false;
                    }
                },
                {
                    label: 'Navigate to: ' + stageTile,
                    cssClass: 'tiny ui basic orange button',
                    action: function (dialogRef) {
                        WebuiPopovers.hideAll();
                        wizardElement.wizard('selectedItem', {
                            step: stageIndex
                        });
                        dialogRef.close();
                        return false;
                    }
                }]
        });
    } //end of function


    function unpair_datafiles(parentTable) {
        //function manages the unpairing and manual pairing of datafiles

        if (!parentTable.rows('.selected').data().length) {
            return false;
        }

        var unpairedCandidates = parentTable.rows('.selected').data().toArray();
        parentTable
            .rows('.selected')
            .remove()
            .draw();


        var form_values = {};
        var activeStageIndx = wizardElement.wizard('selectedItem').step;
        $('#wizard_form_' + activeStageIndx).find(":input").each(function () {
            form_values[this.id] = $(this).val();
        });

        form_values.pairing_info = unpairedCandidates;

        var tableID = 'unpairing_tbl';
        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        var $dialogContent = $('<div/>');
        var table_div = $('<div/>').append(tbl);
        var filter_message = $('<div style="margin-bottom: 20px;"><div style="font-weight: bold; margin-bottom: 5px;">Click any two files to pair</div>');
        var spinner_div = $('<div/>', {style: "margin-left: 40%; padding-top: 15px; padding-bottom: 15px;"}).append($('<div class="copo-i-loader"></div>'));

        var dialog = new BootstrapDialog({
            type: BootstrapDialog.TYPE_PRIMARY,
            size: BootstrapDialog.SIZE_NORMAL,
            title: "Datafiles pairing",
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
                        'request_action': 'get_unpaired_datafiles',
                        'description_token': datafileDescriptionToken,
                        'auto_fields': JSON.stringify(form_values)
                    },
                    success: function (data) {
                        spinner_div.remove();

                        var dtd = data.result.data_set;

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
                                style: 'multi'
                            },
                            columns: cols,
                            dom: 'lfit<"row">rp'
                        });

                        $('#' + tableID + '_wrapper')
                            .find(".dataTables_filter")
                            .find("input")
                            .removeClass("input-sm")
                            .attr("placeholder", "Search datafiles");

                        //pairing event

                        table
                            .off('select')
                            .on('select', function (e, dt, type, indexes) {
                                var selectedRows = dt.rows({
                                    selected: true
                                }).data();

                                if (selectedRows.length == 2) {//pair selected datafiles
                                    var dialog2 = new BootstrapDialog({
                                        // title: "Datafiles pairing",
                                        message: 'Do you want to pair the selected datafiles?',
                                        cssClass: 'copo-modal3',
                                        closable: false,
                                        animate: true,
                                        type: BootstrapDialog.TYPE_PRIMARY,
                                        buttons: [{
                                            label: 'Cancel',
                                            cssClass: 'tiny ui basic button',
                                            action: function (dialogRef2) {
                                                table.rows('.selected').deselect();
                                                dialogRef2.close();
                                            }
                                        }, {
                                            label: '<i class="copo-components-icons fa fa-link"></i> Pair',
                                            cssClass: 'tiny ui basic primary button',
                                            action: function (dialogRef2) {
                                                var $button2 = this;
                                                $button2.disable();
                                                $button2.spin();

                                                var form_values = {};
                                                var activeStageIndx = wizardElement.wizard('selectedItem').step;
                                                $('#wizard_form_' + activeStageIndx).find(":input").each(function () {
                                                    form_values[this.id] = $(this).val();
                                                });

                                                form_values.unpaired_datafiles = table.rows().ids().toArray();
                                                form_values.pairing_targets = table.rows('.selected').ids().toArray();

                                                $.ajax({
                                                    url: wizardURL,
                                                    type: "POST",
                                                    headers: {
                                                        'X-CSRFToken': csrftoken
                                                    },
                                                    data: {
                                                        'request_action': 'pair_datafiles',
                                                        'description_token': datafileDescriptionToken,
                                                        'auto_fields': JSON.stringify(form_values)
                                                    },
                                                    success: function (data) {

                                                        parentTable.rows().deselect();
                                                        parentTable
                                                            .clear()
                                                            .draw();
                                                        parentTable
                                                            .rows
                                                            .add(data.result.paired_dataset);
                                                        parentTable
                                                            .columns
                                                            .adjust()
                                                            .draw();
                                                        parentTable
                                                            .search('')
                                                            .columns()
                                                            .search('')
                                                            .draw();

                                                        if (data.result.unpaired_dataset.length > 0) {
                                                            table.rows().deselect();
                                                            table
                                                                .clear()
                                                                .draw();
                                                            table
                                                                .rows
                                                                .add(data.result.unpaired_dataset);
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
                                                            dialog.close();
                                                        }

                                                        dialogRef2.close();
                                                    },
                                                    error: function () {
                                                        console.log("Couldn't complete datafiles pairing!");
                                                        dialogRef2.close();
                                                    }
                                                });

                                            }
                                        }]
                                    });

                                    dialog2.realize();
                                    dialog2.getModalHeader().hide();
                                    dialog2.open();
                                }
                            });

                    },
                    error: function () {
                        alert("Couldn't display datafiles!");
                        dialogRef.close();
                    }
                });
            },
            buttons: [{
                label: 'OK',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    dialogRef.close();
                }
            }]
        });


        $dialogContent.append(filter_message).append(table_div).append(spinner_div);
        dialog.realize();
        dialog.setMessage($dialogContent);
        dialog.open();
    }


}); //end document ready


