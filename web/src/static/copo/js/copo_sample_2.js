var wizardMessages;
var samplesGenerated = false; //flag to indicate if samples have been generated
var wizardStages;
var stagesFormValues = {};
var formEditableElements = {};
var validateSetter = {};
var negotiatedStages = []; //holds info about stages resolved to be rendered
var sampleHowtos = null;
var currentIndx = 0;
var generatedSamples = [];
var tableID = null; //rendered table handle
var stepIntercept = false; //flag indicates if activation of the last stage of the wizard has been intercepted
var descriptionWizSummary = {}; //wizard summary stage content
var tempWizStore = null; // for holding wizard-related data pending wizard load event
var initialSampleAttributes = {}; //holds initial attributes shared by all samples before editing
var dataTableDataSource = []; // the data-source used for sample table generation
var dataTableTriggerSave = false; //flag for determining the state of datatables keys state

$(document).ready(function () {
        //****************************** Event Handlers Block *************************//

        //page global variables
        var csrftoken = $.cookie('csrftoken');
        var component = "sample";
        var wizardURL = "/rest/sample_wiz/";
        var copoVisualsURL = "/copo/copo_visualize/";
        var copoFormsURL = "/copo/copo_forms/";


        //test
        // $(document).on("click", ".ontology-field", function (event) {
        //     var data = Object();
        //     data["component_label"] = this.id;
        //     var gAttrib = build_element_lookup(data);
        //     $("#copo_instant_info").html(gAttrib);
        // });
        //end test

        //on the fly info element
        var onTheFlyElem = $("#copo_instant_info");

        //help table
        var pageHelpTable = "sample_help_table"; //help pane table handle

        //handle hover info for copo-select control types

        $(document).on("mouseenter", ".selectize-dropdown-content .active", function (event) {
            if ($(this).closest(".copo-multi-search").length) {
                var recordId = $(this).attr("data-value"); // the id of the hovered-on option
                var associatedComponent = ""; //the form control with which the event is associated

                //get the associated component
                var clss = $($(event.target)).closest(".input-copo").attr("class").split(" ");
                $.each(clss, function (key, val) {
                    var cssSplit = val.split("copo-component-control-");
                    if (cssSplit.length > 1) {
                        associatedComponent = cssSplit.slice(-1)[0];

                        resolve_element_view(recordId, associatedComponent, $($(event.target)).closest(".input-copo"));
                        return false;
                    }
                });

            }
        });


        //handle inspect, describe - tabs
        $('#sample-display-tabs.nav-tabs a').on('shown.bs.tab', function (event) {
            var componentSelected = $(event.target).attr("data-component"); // active tab

            $("#sampleHelpSection").find(".component-help").removeClass("disabled");
            $("#sampleHelpSection").find(".component-help[data-component='" + componentSelected + "']").addClass("disabled");

            set_component_help($(this).attr("data-component"), pageHelpTable, sampleHowtos);

            //check for temp data
            if (componentSelected == "descriptionWizardComponent" && tempWizStore) {
                do_post_stage_retrieval2(tempWizStore);
                tempWizStore = null;
            }
        });

        //set help context
        $(document).on("click", ".component-help", function () {
            $(this).closest("ul").find(".component-help").removeClass("disabled");
            $(this).addClass("disabled");

            set_component_help($(this).attr("data-component"), pageHelpTable, sampleHowtos);
        });

        //handle add sample button
        $('#wizard_fire_button').on('click', function (event) {
            $(this).closest("div").hide();
            var target_button_action = "new_samples"
            $(document).find(".copo-dt[data-record-action='" + target_button_action + "']").addClass("disabled");
            add_new_samples();
        });


        //handle popover close button
        $(document).on("click", ".popover .copo-close", function () {
            $(this).parents(".popover").popover('destroy');
        });

        // get table data to display via the DataTables API
        var tableLoader = get_spinner_image();
        $("#data_all_data").append(tableLoader);

        //call for table data
        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'task': 'table_data',
                'component': component
            },
            success: function (data) {
                do_render_table(data);
                tableLoader.remove();
            },
            error: function () {
                alert("Couldn't retrieve samples!");
            }
        });

        //call for help...

        //loader image for help pane
        var helpLoader = get_spinner_image();
        $("#helptipsDiv").append(helpLoader);

        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'task': 'help_messages',
                'component': component
            },
            success: function (data) {
                sampleHowtos = data.help_messages;
                build_help_pane_menu(sampleHowtos, $("#sampleHelpSection").find(".componentHelpList"));
                set_component_help('', pageHelpTable, sampleHowtos);
                helpLoader.remove();
            },
            error: function () {
                alert("Couldn't retrieve page help!");
            }
        });


        //******************************* wizard events *******************************//

        //handle event for exiting current description...
        $('#remove_act').on('click', function (event) {
            //confirm user decision
            var dialog = new BootstrapDialog({
                buttons: [
                    {
                        label: 'Cancel',
                        action: function (dialogRef) {
                            dialogRef.close();
                        }
                    },
                    {
                        label: 'Exit Wizard',
                        cssClass: 'btn-danger',
                        action: function (dialogRef) {
                            dialogRef.close();
                            window.location.reload();
                        }
                    }
                ]
            });

            dialog_display(dialog, wizardMessages.exit_wizard_message.title, wizardMessages.exit_wizard_message.text, "danger");

        });


        //handle event for clicking an previously visited step, intercept here to save entries
        $('#sampleWizard').on('stepclicked.fu.wizard', function (evt, data) {
            evt.preventDefault();

            // get the proposed or intended state for which action is intercepted
            before_step_back(data.step);
        });

        //handle events for step change
        $('#sampleWizard').on('actionclicked.fu.wizard', function (evt, data) {
            $(self).data('step', data.step);

            stage_navigate(evt, data);
        });

        //handle events for step change
        $('#sampleWizard').on('changed.fu.wizard', function (evt, data) {
            var currentStep = data.step;
            if (currentStep > 0
                && $('#wizard_form_' + currentStep).length
                && $('#wizard_form_' + currentStep).find("#current_stage").length) {
                var current_stage = $('#wizard_form_' + currentStep).find("#current_stage").val();

                for (var i = 0; i < negotiatedStages.length; ++i) {
                    if (current_stage == negotiatedStages[i].ref) {
                        display_stage_message(negotiatedStages[i].message, negotiatedStages[i].title);
                        break;
                    }
                }
            }
        });

        // handle/attach events to table buttons
        $('body').on('addbuttonevents', function (event) {
            tableID = event.tableID;

            $(document).on("click", ".copo-dt", function (event) {
                do_record_task($(this));
            });

        });


        //instantiate/refresh tooltips
        refresh_tool_tips();


        //****************************** Functions Block ******************************//
        function add_step(auto_fields) {
            //step being requested
            currentIndx += 1;

            //first, make call to resolve the active stage data
            var stage_data = collate_stage_data();

            do_post_stage_retrieval(stage_data);

            //if no data, just go ahead and retrieve stage

        }

        function stage_navigate(evt, data) {

            if (data.direction == 'next') {
                // empty info element
                onTheFlyElem.html('');

                //trigger form validation
                if ($("#wizard_form_" + data.step).length) {
                    $('#wizard_form_' + data.step).trigger('submit');

                    if ($('#wizard_form_' + data.step).find("#bcopovalidator").val() == "false") {
                        $('#wizard_form_' + data.step).find("#bcopovalidator").val("true");
                        evt.preventDefault();
                        return false;
                    }
                }


                var lastElementIndx = $('.steps li').last().index() + 1;
                var activeElementIndx = $('#sampleWizard').wizard('selectedItem').step; //active stage index

                stepIntercept = false;

                if (lastElementIndx - activeElementIndx == 1) {
                    evt.preventDefault();
                    stepIntercept = true;
                }

                // get form inputs
                var form_values = Object();

                $('#wizard_form_' + data.step).find(":input").each(function () {
                    form_values[this.id] = $(this).val();
                });

                //trigger event for setting initial sample attributes
                if (form_values.hasOwnProperty("current_stage") && form_values["current_stage"] == "sample_attributes") {
                    initialSampleAttributes = form_values;
                }

                var auto_fields = JSON.stringify(form_values);

                //trap review stage here, which, in essence, provides a signal to wrap up the wizard
                var reviewElem = $('.steps li:last-child');

                if (reviewElem.hasClass('active')) {
                    evt.preventDefault();
                    //finalise

                    //interrupt, nay, refuse if there is an active cell edit
                    if ($.fn.dataTable.isDataTable('#generated_samples_table')) {
                        var table = $('#generated_samples_table').DataTable();
                        var cells = table.cells('.cell-currently-engaged');

                        if (cells && cells[0].length > 0) {
                            var dialog = new BootstrapDialog({
                                buttons: [
                                    {
                                        label: 'OK',
                                        action: function (dialogRef) {
                                            dialogRef.close();
                                        }
                                    }
                                ]
                            });

                            //dialog_display(dialog, "Active Edit", wizardMessages.save_cell_message.text, "danger");
                            return false;
                        }
                    }

                    //if it reaches here, then all is clear to quit the wizard

                    window.location.reload();
                    return false;
                }

                //set current stage
                currentIndx = data.step;
                add_step(auto_fields);

            } else if (data.direction == 'previous') {
                // get the proposed or intended state, for which action is intercepted
                evt.preventDefault();

                before_step_back(data.step - 1);
            }

        }

        //trigger save action before navigating back a stage
        function before_step_back(proposedState) {
            $('#sampleWizard').wizard('selectedItem', {
                step: proposedState
            });

            return;

        }


        function do_post_stage_retrieval2(data) {
            if (!data.stage_ref) {//this should indicate call to display first stage of the wizard
                if (currentIndx > 0) {
                    if (($('#sampleWizard').is(":visible"))) {
                        reset_wizard();
                    }
                } else {
                    currentIndx += 1;
                    initiate_wizard();
                }

            }

            // wizard 'staging' process
            if (!($('#sampleWizard').is(":visible"))) {


                $('#sampleWizard').show();

                $('.steps li:last-child').hide(); //hide the last (static) stage of the wizard

                //show wizard exit button
                $('#remove_act').parent().show();
            }

            process_wizard_stage(data);


            //toggle show 'Review' stage
            var elem = $('.steps li:last-child');

            if (elem.hasClass('active') && !samplesGenerated) {
                //call to set description summary data...

                //but first, interrupt and, ask for confirmation

                $('#sampleWizard').wizard('selectedItem', {
                    step: currentIndx - 1
                });


                var dialog = new BootstrapDialog({
                    buttons: [
                        {
                            label: 'Review',
                            action: function (dialogRef) {
                                dialogRef.close();
                                return false;
                            }
                        },
                        {
                            label: 'Continue',
                            cssClass: 'btn-primary',
                            action: function (dialogRef) {
                                $('#sampleWizard').wizard('selectedItem', {
                                    step: currentIndx
                                });

                                elem.show();
                                onTheFlyElem.html('');

                                set_generated_samples();
                                samplesGenerated = true;
                                dialogRef.close();
                            }
                        }
                    ]
                });

                dialog_display(dialog, wizardMessages.confirm_initial_sample_generation.title, wizardMessages.confirm_initial_sample_generation.text, "info");

            } else {
                elem.hide();
            }

            //form controls help tip
            setup_element_hint();

            //autocomplete
            auto_complete();
        }

        function do_post_stage_retrieval(data) {
            //update items with data

            if (($('#sampleWizard').is(":visible")) || $('#sample-display-tabs.nav-tabs .active').text().trim() == "Describe") {
                do_post_stage_retrieval2(data);
            } else {
                //store data pending tab shown
                tempWizStore = data;
                $('#sample-display-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show');
            }


        }

        function process_wizard_stage(data) {
            var stage = Object();
            if (data.hasOwnProperty("stage_ref")) {
                var stage = stage_description(data.stage_ref);
            }

            var stageCopy = Object();


            if (stage.hasOwnProperty("ref")) {
                stageCopy = $.extend(true, Object(), stage);
                var stage_pane = get_pane_content(wizardStagesForms(stage), currentIndx, stage.message);

                $('#sampleWizard').wizard('addSteps', currentIndx, [
                    {
                        badge: ' ',
                        label: '<span class=wiz-title>' + stage.title + '</span>',
                        pane: stage_pane
                    }
                ]);

                //give focus to the added step
                $('#sampleWizard').wizard('selectedItem', {
                    step: currentIndx
                });

                //delay validation activation for stages that may need to rebuild their forms
                var delayValArray = ["sample_attributes", "assigned_sample_name"];

                if (delayValArray.indexOf(stage.ref) === -1) {
                    set_up_validator($("#wizard_form_" + currentIndx));
                }

                //form controls help tip
                setup_element_hint();

                //refresh tooltips
                refresh_tool_tips();

            } else {
                if (stepIntercept) {
                    $('#sampleWizard').wizard('selectedItem', {
                        step: $('#sampleWizard').wizard('selectedItem').step + 1
                    });
                }
            }

            //refresh tooltips
            refresh_tool_tips();

            //we might need to rebuild stage form for certain stages...
            if (stage.hasOwnProperty("ref")) {
                if (stage.ref == "sample_attributes") {
                    if (get_clone_data()) {
                        //rebuild stage form with data from the cloned target
                        var clone_record_id = get_clone_data(); //check for clone data

                        $("#wizard_form_" + currentIndx).html(get_spinner_image());

                        //fetch record and rebuild stage form...this time with data
                        $.ajax({
                            url: copoFormsURL,
                            type: "POST",
                            headers: {'X-CSRFToken': csrftoken},
                            data: {
                                'task': "component_record",
                                'component': component,
                                'target_id': clone_record_id
                            },
                            success: function (data) {
                                stageCopy["data"] = data.component_record;
                                $("#wizard_form_" + currentIndx).html(wizardStagesForms(stageCopy));
                                //
                                setup_element_hint();
                                refresh_tool_tips();

                                set_up_validator($("#wizard_form_" + currentIndx));
                            },
                            error: function () {
                                alert("Couldn't retrieve clone record!");
                            }
                        });
                    } else {
                        stageCopy["data"] = null;
                        $("#wizard_form_" + currentIndx).html(wizardStagesForms(stageCopy));
                        //
                        setup_element_hint();
                        refresh_tool_tips();

                        set_up_validator($("#wizard_form_" + currentIndx));
                    }
                } else if (stage.ref == "assigned_sample_name") {
                    //rebuild stage form with generated names

                    $("#wizard_form_" + currentIndx).html(get_spinner_image());

                    //get required number of samples to generate
                    var requestedNumberOfSamples = get_stage_inputs_by_ref("number_of_samples");

                    if ($.isEmptyObject(requestedNumberOfSamples)) {
                        requestedNumberOfSamples = 1;
                    } else {
                        requestedNumberOfSamples = parseInt(requestedNumberOfSamples["number_of_samples"]);
                    }

                    //get bundle name
                    var bundleName = get_stage_inputs_by_ref("sample_name");
                    if ($.isEmptyObject(bundleName)) {
                        bundleName = "";
                    } else {
                        bundleName = bundleName["bundle_name"];
                    }

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: {
                            'request_action': 'sample_name_schema'
                        },
                        success: function (data) {
                            $("#wizard_form_" + currentIndx).html('');
                            stageCopy.items = generate_sample_names(data.sample_name_schema, requestedNumberOfSamples, bundleName);

                            //refresh negotiated stages with new stage items
                            for (var i = 0; i < negotiatedStages.length; ++i) {
                                if (negotiatedStages[i].ref == stage.ref) {
                                    negotiatedStages[i].items = stageCopy.items;
                                    break;
                                }
                            }

                            //generate controls based on stage items and append to the stage form
                            $("#wizard_form_" + currentIndx).html(wizardStagesForms(stageCopy));

                            setup_element_hint();
                            refresh_tool_tips();

                            set_up_validator($("#wizard_form_" + currentIndx));
                        },
                        error: function () {
                            alert("Couldn't generate sample names!");
                        }
                    });
                }
            }


        } //end of func

        function generate_sample_names(sampleSchema, requestedNumberOfSamples, bundleName) {
            var generatedSampleNames = [];

            for (var i = 1; i < requestedNumberOfSamples + 1; ++i) {
                var schemaCopy = $.extend(true, Object(), sampleSchema);
                schemaCopy.id = "assigned_sample_" + i.toString();
                if (bundleName) {
                    schemaCopy.default_value = bundleName + "_" + i.toString();
                }
                schemaCopy.control_meta.input_group_addon_label = i.toString() + ".";

                generatedSampleNames.push(schemaCopy);
            }

            return generatedSampleNames
        }


        function set_up_validator(theForm) {
            if (theForm.find("#current_stage").length) {

                var current_stage = theForm.find("#current_stage").val();

                if (!validateSetter.hasOwnProperty(current_stage)) {

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

                    validateSetter[current_stage] = "1";
                }

            }

        }

        var dispatchStageCallback = {
            get_sample_type_stages: function (param) {
                var stages = null;

                if (stagesFormValues.hasOwnProperty(param)) {
                    stages = wizardStages[stagesFormValues[param][param]];
                }

                return stages;
            },
            display_sample_clone: function (param) {
                //param is confirmation of sample clone
                //function decides whether to display the clone stage given user's choice
                var displayStage = false;

                if (stagesFormValues.hasOwnProperty(param)) {
                    displayStage = stagesFormValues[param][param];

                    if (displayStage == "yes") {
                        displayStage = true;
                    } else {
                        displayStage = false;
                    }
                }

                return displayStage;
            },
            confirm_sample_clone: function (param) {
                //function decides if sample-clone-confirmation stage should be displayed or not
                //should this be based on the presence of samples in the profile?
                //suppressing this condition for now...as one might want to resolve/clone a sample from
                //remote sources like, say, biosample

                var displayStage = true;

                return displayStage;
            }
        }; //end of dispatchStageCallback

        function stage_description(current_stage) {
            var stage = null;
            if (current_stage == "") {
                //start first stage in the description process
                $.each(wizardStages.start, function (key, val) {
                    negotiatedStages.push(val);
                });

                stage = negotiatedStages[0];
                negotiatedStages[0].activated = true;

            } else {
                //there is a previous stage, use this to resolve next stage

                //...but, has this stage been previously rendered?

                var currIndx = -1;
                for (var i = 0; i < negotiatedStages.length; ++i) {
                    if (current_stage == negotiatedStages[i].ref) {
                        currIndx = i + 1;
                        break;
                    }
                }

                if (currIndx < negotiatedStages.length) {
                    if (negotiatedStages[currIndx].hasOwnProperty("activated") && negotiatedStages[currIndx].activated) {
                        stage = Object(); //no stage to return
                    } else {
                        stage = negotiatedStages[currIndx];
                        negotiatedStages[currIndx].activated = true;

                        //check if it is a stage stub
                        if (stage.hasOwnProperty("is_stage_stub") && stage.is_stage_stub) {
                            var new_stages = dispatchStageCallback[stage.callback.function](stage.callback.parameter);
                            if (new_stages) {
                                new_stages.forEach(function (item) {
                                    negotiatedStages.push(item);
                                });
                            }

                            //verify next stage validity...again!
                            if ((currIndx + 1) < negotiatedStages.length) {
                                currIndx = currIndx + 1;
                                stage = negotiatedStages[currIndx];
                                negotiatedStages[currIndx].activated = true;
                            } else {
                                stage = Object(); //no stage to return
                            }
                        }

                        //check for conditional stage
                        if (stage.hasOwnProperty("is_conditional_stage") && stage.is_conditional_stage) {
                            var flag = dispatchStageCallback[stage.callback.function](stage.callback.parameter);

                            if (!flag) {
                                //move one step forward
                                if ((currIndx + 1) < negotiatedStages.length) {
                                    currIndx = currIndx + 1;
                                    stage = negotiatedStages[currIndx];
                                    negotiatedStages[currIndx].activated = true;
                                } else {
                                    stage = Object(); //no stage to return
                                }
                            }
                        }
                    }
                } else {
                    //this should signal end of stages

                    stage = Object(); //no stage to return
                }
            }

            if (stage.hasOwnProperty("ref")) {

                stage.data = Object(); //no data needed...at least for now

            }

            return stage;
        }

        function get_clone_data() {
            var sample_clone = get_stage_inputs_by_ref("sample_clone");
            var record_id = null;

            if (sample_clone.hasOwnProperty("sample_clone")) {
                record_id = sample_clone["sample_clone"];
            }

            return record_id
        }

        function get_pane_content(stage_content, currentIndx, stage_message) {
            var stageHTML = $('<div/>');

            //form controls
            var formPanel = $('<div/>', {
                class: "panel panel-copo-data",
                style: "margin-top: 5px; font-size: 14px;"
            });


            stageHTML.append(formPanel);

            var formPanelBody = $('<div/>', {
                class: "panel-body"
            });

            formPanel.append(formPanelBody);

            var formDiv = $('<div/>', {
                style: "margin-top: 20px;"
            });

            formPanelBody.append(formDiv);

            var formCtrl = $('<form/>',
                {
                    id: "wizard_form_" + currentIndx
                });

            formCtrl.append(stage_content);

            formDiv.append(formCtrl);

            return stageHTML;
        }

        function initiate_wizard() {
            $('#sampleWizard').wizard();

            //add review step, then other steps
            $('#sampleWizard').wizard('addSteps', -1, [
                descriptionWizSummary
            ]);
        }

        function reset_wizard() {//resets wizard
            $('#sampleWizard').wizard('removeSteps', 1, currentIndx + 1);

            //add review step, then other steps
            $('#sampleWizard').wizard('addSteps', -1, [
                descriptionWizSummary
            ]);

            currentIndx = 1;
        }

        function collate_stage_data() {
            //get active stage
            var activeStageIndx = $('#sampleWizard').wizard('selectedItem').step; //active stage index

            if (activeStageIndx == -1) {
                return false;
            }


            //get form elements for current stage
            var form_values = Object();

            $('#wizard_form_' + activeStageIndx).find(":input").each(function () {
                form_values[this.id] = $(this).val();
            });

            var data = {"stage_ref": ""};

            if (form_values.hasOwnProperty("current_stage")) {
                stagesFormValues[form_values.current_stage] = form_values;
                data = {"stage_ref": form_values.current_stage};
            }

            return data;

        }


        function add_new_samples() {
            //set in motion the wizard process...

            // retrieve wizard messages
            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'request_action': 'sample_wizard_components'
                },
                success: function (data) {
                    wizardStages = data.wizard_stages;
                    wizardMessages = data.wiz_message;
                    set_wizard_summary();

                    //load stages
                    do_post_stage_retrieval({"stage_ref": ""});
                },
                error: function () {
                    alert("Couldn't retrieve wizard components!");
                }
            });
        }


        //handles button events on a record or group of records
        function do_record_task(elem) {
            var task = elem.attr('data-record-action').toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
            var taskTarget = elem.attr('data-action-target'); //is the task targeting a single 'row' or group of 'rows'?

            var ids = [];
            var records = [];
            var table = null;


            //retrieve event targets
            if ($.fn.dataTable.isDataTable('#' + tableID)) {
                table = $('#' + tableID).DataTable();

                if (taskTarget == 'row') {
                    ids = [elem.attr('data-record-id')];
                } else {
                    ids = $.map(table.rows('.selected').data(), function (item) {
                        return item[item.length - 1];
                    });
                }

                var records = []; //richer information context, retained for other purposes, e.g., description batch
                $.map(table.rows('.selected').data(), function (item) {
                    records.push(item);
                });

            }

            //handle button action
            if (task == "new_samples") {//event for creating new sample(s)
                //disable the add buttons
                elem.addClass("disabled");
                $("#wizard_fire_button").closest("div").hide();
                add_new_samples();

            } else if (task == "delete" && ids.length > 0) { //handles delete, allows multiple row delete
                var deleteParams = {component: component, target_ids: ids};
                do_component_delete_confirmation(deleteParams);

            } else if (task == "edit" && ids.length > 0) { //handles edit
                $.ajax({
                    url: copoFormsURL,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    data: {
                        'task': 'form',
                        'component': component,
                        'target_id': ids[0] //only allowing row action for edit, hence first record taken as target
                    },
                    success: function (data) {
                        json2HtmlForm(data);
                    },
                    error: function () {
                        alert("Couldn't build " + component + " form!");
                    }
                });

            }
            else if (task == "info" && ids.length > 0) {
                var tr = elem.closest('tr');
                var row = table.row(tr);

                if (row.child.isShown()) {
                    //row is already open - close it
                    row.child.hide();
                } else {
                    var contentHtml = "<div style='text-align: center'><i class='fa fa-spinner fa-pulse fa-2x'></i></div>";
                    row.child(contentHtml).show();

                    $.ajax({
                        url: copoVisualsURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: {
                            'task': 'attributes_display',
                            'component': component,
                            'target_id': ids[0]
                        },
                        success: function (data) {
                            row.child(build_attributes_display(data).html()).show();
                        },
                        error: function () {
                            alert("Couldn't retrieve sample attributes!");
                            return '';
                        }
                    });
                }
            }

        } //end of func

        function resolve_element_view(recordId, associatedComponent, eventTarget) {
            //maps form element by id to component type e.g source, sample

            if (associatedComponent == "") {
                return false;
            }

            onTheFlyElem.append(get_spinner_image());

            $.ajax({
                url: copoVisualsURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': "attributes_display",
                    'component': associatedComponent,
                    'target_id': recordId
                },
                success: function (data) {
                    var gAttrib = build_attributes_display(data);
                    onTheFlyElem.html(gAttrib);
                },
                error: function () {
                    onTheFlyElem.html('');
                    onTheFlyElem.append("Couldn't retrieve attributes!");
                }
            });
        }


        function setup_element_hint() {
            $(":input").focus(function () {
                var elem = $(this).closest(".copo-form-group");
                if (elem.length) {

                    var title = elem.find("label").html();
                    var content = "";
                    if (elem.find(".form-input-help").length) {
                        content = (elem.find(".form-input-help").html());
                    }

                    $('.popover').popover('hide'); //hide any shown popovers


                    var pop = elem.popover({
                        title: title,
                        content: content,
                        // container: 'body',
                        trigger: 'hover',
                        placement: 'right',
                        template: '<div class="popover copo-popover-popover1"><div class="arrow">' +
                        '</div><div class="popover-inner"><h3 class="popover-title copo-popover-title1">' +
                        '</h3><div class="popover-content"><p></p></div></div></div>'
                    });

                }

            });
        }//end of function

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

                //any triggers?
                if (formElem.trigger) {
                    try {
                        dispatchSampleEventHandler[formElem.trigger.callback.function](formElem);
                    }
                    catch (err) {
                    }
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


        var dispatchSampleEventHandler = {
            place_holder: function (formElem) {
                var previousValue = null;

                $(document)
                    .off("focus", "#" + formElem.id)
                    .on("focus", "#" + formElem.id, function () {
                        previousValue = this.value;
                    });

                $(document)
                    .off(formElem.trigger.type, "#" + formElem.id)
                    .on(formElem.trigger.type, "#" + formElem.id, function () {
                        ;//call to a function here
                    });
            }
        };


        function set_wizard_summary() {
            descriptionWizSummary = {
                badge: ' ',
                label: '<span class=wiz-title>Review</span>',
                pane: '<div class="alert alert-default">' +
                '<div style="line-height: 150%;" class="' + wizardMessages.review_message.text_class + '">' +
                wizardMessages.review_message.text + '</div><div id="summary_stage_loader"></div>' +
                '<div style="margin-top: 10px; max-width: 100%; overflow-x: auto;">' +
                '<table id="generated_samples_table" class="table table-striped table-bordered order-column hover copo-datatable copo-table-header" width="100%"></table>' +
                '</div></div>'
            };
        }

        function do_generated_samples_display(data) {
            //builds generated sample display

            generatedSamples = data.generated_samples.generated_samples;
            formEditableElements = data.generated_samples.form_elements;

            //generate table columns
            var sampleTableColumns = generate_sample_table_columns(generatedSamples);

            //set up data source
            dataTableDataSource = generate_sample_table_data_source(generatedSamples);

            //remove loader
            $("#summary_stage_loader").html('');

            var table = null;
            if ($.fn.dataTable.isDataTable('#generated_samples_table')) {
                //if table instance already exists, then do refresh
                table = $('#generated_samples_table').DataTable();
            }


            if (table) {
                //clear old, set new data
                table
                    .clear()
                    .draw();
                table
                    .rows
                    .add(dataTableDataSource);
                table
                    .columns
                    .adjust()
                    .draw();
                table
                    .search('')
                    .columns()
                    .draw();
            } else {
                table = $('#generated_samples_table').DataTable({
                    data: dataTableDataSource,
                    "dom": '<"top"if>rt<"bottom"p><"clear">',
                    select: {
                        style: 'multi'
                    },
                    language: {
                        "info": " _START_ to _END_ of _TOTAL_ samples",
                    },
                    order: [[0, "asc"]],
                    columns: sampleTableColumns,
                    "columnDefs": [
                        {"orderData": 0,}
                    ],
                    keys: {
                        columns: ':not(:first-child)',
                        focus: ':eq(2)', // cell that will receive focus when the table is initialised, set to the first editable cell defined
                        keys: [9, 13, 37, 39, 38, 40],
                        blurable: false
                    },
                    scrollX: true,
                    scroller: true,
                    scrollY: 300,
                });

                table
                    .on('key', function (e, datatable, key, cell, originalEvent) {
                        if (key == 13) {//trap enter key for editing a cell
                            var node = cell.node();

                            //bypass non-editable cells or ones that are currently being edited
                            if (!$(node).hasClass('copo-editable-cell')) {
                                return false;
                            }

                            table.keys.disable();
                            dataTableTriggerSave = false;
                            $(node).addClass('cell-currently-engaged'); //cell locked for edit, unlock with the TAB key

                            //get cell's derived id
                            var derived_id = cell.data();

                            //get cell's actual id
                            var rowMeta = table.row(cell.index().row).data().attributes._recordMeta;
                            var rowMetaResult = $.grep(rowMeta, function (e) {
                                return e.derived_id == derived_id;
                            });

                            //get spec for the cell form element
                            var formEditableElementsCopy = $.extend(true, Object(), formEditableElements);
                            var formElem = formEditableElementsCopy[rowMetaResult[0].actual_id];
                            var control = formElem.control;

                            //in certain cases with object type kind of controls,
                            //only some entities generated via formElem spec might need to be displayed
                            //the presence of such will be flagged by 'meta'
                            if (rowMetaResult[0].hasOwnProperty("meta")) {
                                formElem["_displayOnlyThis"] = rowMetaResult[0].meta;
                            }

                            //get element value
                            var rowAttributes = $.extend(true, Object(), table.row(cell.index().row).data().attributes);
                            var elemValue = rowAttributes[rowMetaResult[0].actual_id];

                            //get specific index to pass through
                            var removeAddButton = false;
                            if (rowMetaResult[0].hasOwnProperty("indx") && Object.prototype.toString.call(elemValue) === '[object Array]') {
                                var newElemValue = [];
                                newElemValue.push(elemValue[parseInt(rowMetaResult[0].indx)]);
                                elemValue = newElemValue;
                                removeAddButton = true; //remove add button for array type elements
                            }

                            var htmlCtrl = dispatchFormControl[controlsMapping[control.toLowerCase()]](formElem, elemValue);
                            htmlCtrl.find("label").remove();

                            if (removeAddButton) {
                                htmlCtrl.find(".array-add-new-button-div").remove();
                            }

                            //create cell edit panel
                            var cellEditPanel = get_cell_edit_panel();

                            //set cell edit data
                            cellEditPanel.find(".panel-body").append(htmlCtrl).append(set_error_div()); //attach form control
                            cellEditPanel.find(".panel-footer").append(set_dynamic_cell_data()); //attach action buttons

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

                            //set focus to selectize control
                            if (selectizeObjects.hasOwnProperty(formElem.id)) {
                                var selectizeControl = selectizeObjects[formElem.id];
                                selectizeControl.focus();
                            }


                            //build cell edit function parameter object
                            var cellParams = Object();
                            cellParams["datatable"] = datatable;
                            cellParams["cell"] = cell;
                            cellParams["action"] = "current";

                            cellEditPanel.find(".cell-apply").click(function () {
                                cellParams["action"] = $(this).attr("data-action");
                                cellParams["selectedRows"] = table.rows('.selected').indexes();
                                cellParams["allRows"] = table.rows().indexes();
                                cellEditPanel.find(".cell-apply").popover('destroy');

                                var form_values = Object();
                                cellEditPanel.find(":input").each(function () {
                                    try {
                                        form_values[this.id] = $(this).val().trim();
                                    }
                                    catch (err) {
                                        form_values[this.id] = $(this).val();
                                    }
                                });
                                cellParams["form_values"] = form_values;

                                set_cell_dynamic(cellParams);
                            });
                        }
                    });

                //also, use ENTER key to signal end of cell update...
                table.on("keyup", function (e) {
                    var code = (e.keyCode ? e.keyCode : e.which);
                    if (code == 13 && table && !dataTableTriggerSave) {
                        dataTableTriggerSave = true; //first time is to build control, only react at the second time
                        return false;
                    } else if (code == 13 && table && dataTableTriggerSave) {
                        var cells = table.cells('.cell-currently-engaged');

                        if (cells && cells[0].length > 0) {
                            var cell = cells[0];
                            var targetCell = table.cell(cell[0].row, cell[0].column);
                            var node = targetCell.node();
                            $(node).find(".cell-apply").popover('destroy');

                            var cellParams = Object();
                            cellParams["datatable"] = table;
                            cellParams["cell"] = targetCell;
                            cellParams["action"] = "current";

                            var form_values = Object();
                            $(node).find(":input").each(function () {
                                try {
                                    form_values[this.id] = $(this).val().trim();
                                }
                                catch (err) {
                                    form_values[this.id] = $(this).val();
                                }
                            });
                            cellParams["form_values"] = form_values;

                            set_cell_dynamic(cellParams);
                        }

                    }
                });
            }
        }

        function set_generated_samples() {
            $("#summary_stage_loader").append(get_spinner_image());

            //get assigned sample name
            var assignedSampleName = get_stage_inputs_by_ref("assigned_sample_name");

            var generatedSampleNames = [];
            $.each(assignedSampleName, function (key, val) {
                var partSplit = key.split("assigned_sample_");
                if (partSplit.length > 1) {
                    generatedSampleNames.push(val);
                }
            });

            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'request_action': 'save_generated_samples',
                    'generated_samples': JSON.stringify(generatedSampleNames),
                    'sample_type': get_stage_inputs_by_ref("sample_type")["sample_type"],
                    'initial_sample_attributes': JSON.stringify(initialSampleAttributes)
                },
                success: function (data) {
                    do_generated_samples_display(data);
                },
                error: function () {
                    alert("Couldn't generate requested samples!");
                }
            });

        }//end of func

        function generate_sample_table_columns(generatedSamples) {
            //generates sample table column, beginning with static columns

            var sampleTableColumns = [
                {title: "S/N", data: 'rank', visible: true, name: "rank"},
                {title: "Attributes", data: 'attributes', visible: false, name: "attributes"},
            ];

            //now, set the dynamic columns

            // get a reference record in generated samples to use as basis for generating dynamic columns
            var referenceRecord = generatedSamples[0]._recordMeta;

            for (var i = 0; i < referenceRecord.length; ++i) {
                var col = referenceRecord[i];
                var dynamicCol = Object();

                dynamicCol["title"] = col.title;
                dynamicCol["data"] = col.derived_id;
                dynamicCol["render"] = function (data, type, row, meta) {
                    var displaYData = '';
                    var sampleCols = row.attributes._recordMeta;

                    for (var j = 0; j < sampleCols.length; ++j) {
                        if (sampleCols[j].derived_id == data) {
                            displaYData = sampleCols[j].data;
                            break;
                        }
                    }

                    return displaYData;
                }

                dynamicCol["className"] = "copo-editable-cell"; // column editable flag

                sampleTableColumns.push(dynamicCol);
            }

            return sampleTableColumns;
        }

        function generate_sample_table_data_source(generatedSamples) {
            //generates sample data source
            var sampleTableDataSource = [];

            for (var i = 0; i < generatedSamples.length; ++i) {

                var sample = generatedSamples[i];
                var option = Object();

                option["rank"] = i + 1;
                option["attributes"] = sample;

                //set dynamic
                var sampleCols = sample._recordMeta;

                for (var j = 0; j < sampleCols.length; ++j) {
                    option[sampleCols[j].derived_id] = sampleCols[j].derived_id;
                }

                sampleTableDataSource.push(option);
            }

            return sampleTableDataSource;
        }

        function set_error_div() {
            var ctrlsDiv = $('<div/>',
                {
                    class: "row",
                    style: "display:none; color:#a94442;"
                });

            var sp = $('<div/>',
                {
                    class: "col-sm-12 col-md-12 col-lg-12 error-div"
                });

            return ctrlsDiv.append(sp);
        }

        function set_dynamic_cell_data() {
            var parentObject = $('<div/>');

            var components = [
                {
                    title: "Apply to current",
                    action: "current",
                    description: "Apply this update to current cell.",
                    className: "btn btn-primary btn-xs",
                    style: "margin-right: 2px;"
                },
                {
                    title: "Apply to selected",
                    action: "selected",
                    description: "Apply this update to selected records. Do remember to highlight the records for which you intend to apply the update.",
                    className: "btn btn-primary btn-xs",
                    style: "margin-right: 2px;"
                },
                {
                    title: "Apply to all",
                    action: "all",
                    description: "Apply this update to all records.",
                    className: "btn btn-primary btn-xs",
                    style: "margin-right: 2px;"
                },
                {
                    title: "Cancel",
                    action: "cancel",
                    description: "Cancel this update.",
                    className: "btn btn-warning btn-xs pull-right",
                    style: ""
                }
            ];

            for (var i = 0; i < components.length; ++i) {
                var option = components[i];

                var elem = $('<button/>',
                    {
                        class: "cell-apply " + option.className,
                        style: "border-radius:0; background-image:none; " + option.style,
                        type: "button",
                        html: option.title,
                        "data-title": option.title,
                        "data-desc": option.description,
                        "data-action": option.action,
                        mouseenter: function (evt) {
                            $(this).popover({
                                title: $(this).attr("data-title"),
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
                        }
                    });

                parentObject.append(elem);
            }

            return parentObject;
        }

        function get_cell_edit_panel() {
            var attributesPanel = $('<div/>', {
                class: "panel panel-default cell-edit-panel",
                style: "min-width:450px;"
            });

            var attributesPanelBody = $('<div/>', {
                class: "panel-body"
            });

            var attributesPanelFooter = $('<div/>', {
                class: "panel-footer",
                style: "background-color: rgba(245, 245, 245, 0.4);"
            });

            attributesPanel.append(attributesPanelBody).append(attributesPanelFooter);

            return attributesPanel;
        }

        function set_cell_dynamic(cellParams) {
            var datatable = cellParams.datatable;
            var cell = cellParams.cell;
            var action = cellParams.action;

            var node = cell.node();

            //store the cell's current html state for future reference
            var cellHTMLClone = $(node).find(".cell-edit-panel").clone(true);

            $(node).html(get_spinner_image());

            var rowIndx = cell.index().row;

            $('.popover').remove();

            //perform action
            if (action == "cancel") {
                //re-enable keys
                datatable.keys.enable();
                dataTableTriggerSave = false;

                //remove cell's edit status
                $(node).removeClass('cell-currently-engaged'); //unlock cell

                //deselect previously selected rows
                datatable.rows('.selected').deselect();

                datatable
                    .row(rowIndx)
                    .invalidate()
                    .draw();
            } else {
                //get form values
                var form_values = cellParams.form_values;

                // get all target rows
                var targetRows = [];

                targetRows.push({rowID: rowIndx, recordID: dataTableDataSource[rowIndx].attributes._id});

                //get drilled-down save action
                var actionRows = [];
                if (action == "selected" && cellParams.hasOwnProperty("selectedRows")) {
                    actionRows = cellParams.selectedRows;
                } else if (action == "all" && cellParams.hasOwnProperty("allRows")) {
                    actionRows = cellParams.allRows;
                }

                for (var i = 0; i < actionRows.length; ++i) {
                    rowIndx = actionRows[i];
                    targetRows.push({rowID: rowIndx, recordID: dataTableDataSource[rowIndx].attributes._id});
                }

                //define metadata object and gather relevant information for save action
                var update_metadata = Object();

                //get cell's derived id
                var derived_id = cell.data();

                //get cell's actual id
                var rowMeta = datatable.row(cell.index().row).data().attributes._recordMeta;
                var rowMetaResult = $.grep(rowMeta, function (e) {
                    return e.derived_id == derived_id;
                });

                update_metadata["column_reference"] = rowMetaResult[0].actual_id; //id of the update element
                update_metadata["sample_type"] = get_stage_inputs_by_ref("sample_type")["sample_type"];

                if (rowMetaResult[0].hasOwnProperty("indx")) {
                    update_metadata["update_element_indx"] = rowMetaResult[0].indx; //in the case of arrays, index of the update element value
                    update_metadata["update_meta"] = rowMetaResult[0].meta; //the sub-key of the update element
                }

                update_metadata = JSON.stringify(update_metadata);

                $.ajax({
                    url: wizardURL,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    data: {
                        'request_action': 'sample_cell_update',
                        'target_rows': JSON.stringify(targetRows),
                        'update_metadata': update_metadata,
                        'auto_fields': JSON.stringify(form_values)
                    },
                    success: function (data) {
                        if (data.updated_samples.status && data.updated_samples.status == "error") {
                            $(node)
                                .html('')
                                .append(cellHTMLClone);

                            $(node).find(".error-div").html(data.updated_samples.message);
                            $(node).find(".error-div").closest(".row").css("display", "block");
                        } else {
                            //re-enable keys
                            datatable.keys.enable();
                            dataTableTriggerSave = false;

                            //remove cell's edit status
                            $(node).removeClass('cell-currently-engaged'); //unlock cell

                            //deselect previously selected rows
                            datatable.rows('.selected').deselect();


                            var updatedSamples = data.updated_samples.generated_samples;
                            formEditableElements = data.updated_samples.form_elements; //refresh form elements

                            //set updated and refresh display
                            for (var i = 0; i < updatedSamples.length; ++i) {
                                if (updatedSamples[i].hasOwnProperty("_cell_id")) {
                                    dataTableDataSource[updatedSamples[i]._cell_id].attributes = updatedSamples[i];

                                    datatable
                                        .row(updatedSamples[i]._cell_id)
                                        .invalidate()
                                        .draw();
                                }
                            }

                            //set focus on next row
                            datatable.cell(cell.index().row + 1, cell.index().column).focus();
                        }

                    },
                    error: function () {
                        alert("Couldn't update record!");
                    }
                });

            }
        }


        function get_stage_inputs_by_ref(ref) {
            var form_values = Object();

            if (stagesFormValues.hasOwnProperty(ref)) {
                form_values = stagesFormValues[ref];
            }

            return form_values;

        }

        function display_stage_message(stageMessage, stageTitle) {
            onTheFlyElem.empty();

            if (stageMessage) {
                var attributesPanel = $('<div/>', {
                    class: "panel panel-info",
                    style: "margin-top: 5px; font-size: 12px;"
                });

                var attributesPanelHeading = $('<div/>', {
                    class: "panel-heading",
                    style: "background-image: none; font-weight: 600;",
                    html:  stageTitle
                });

                attributesPanel.append(attributesPanelHeading);


                var attributesPanelBody = $('<div/>', {
                    class: "panel-body"
                });

                attributesPanelBody.append('<span style="line-height: 1.7;">' + stageMessage + '</span>');

                attributesPanel.append(attributesPanelBody);

                onTheFlyElem.append(attributesPanel);
            }
        }

    }
)//end document ready