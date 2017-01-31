var wizardMessages;
var sampleComponentRecords;
var wizardStages;
var wizardStagesMain;
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

        var component = "sample";
        var wizardURL = "/rest/sample_wiz/";
        var copoVisualsURL = "/copo/copo_visualize/";

        //test
        //end test

        //on the fly info element
        var onTheFlyElem = $("#on_the_fly_info");

        //handle hover info for copo-select control types

        $(document).on("mouseenter", ".selectize-dropdown-content .active", function (event) {
            if ($(this).closest(".copo-multi-search").length) {
                var recordId = $(this).attr("data-value"); // the id of the hovered-on option
                var associatedComponent = ""; //form control the event is associated

                //get the associated component
                var clss = $($(event.target)).closest(".input-copo").attr("class").split(" ");
                $.each(clss, function (key, val) {
                    var cssSplit = val.split("copo-component-control-");
                    if (cssSplit.length > 1) {
                        associatedComponent = cssSplit.slice(-1)[0];
                    }
                });

                resolve_element_view(recordId, associatedComponent);
            }
        });


        //handle inspect, describe - tabs
        $('#copo-datafile-tabs.nav-tabs a').on('shown.bs.tab', function (event) {
            var componentSelected = $(event.target).attr("data-component"); // active tab

            $("#copoSampleHelp").find(".component-help").removeClass("disabled");
            $("#copoSampleHelp").find(".component-help[data-component='" + componentSelected + "']").addClass("disabled");


            $("#generatedSamplesDiv").css("display", "none");
            $("#helptipsDiv").css("display", "block");
            set_samples_how_tos($(this).attr("data-component"));

            //check for temp data
            if (componentSelected == "descriptionWizardComponent" && tempWizStore) {
                do_post_stage_retrieval2(tempWizStore);
                tempWizStore = null;
            }
        });

        //handle help context
        $("#copoSampleHelp").find(".component-help").on("click", function (event) {
            event.preventDefault();

            $("#copoSampleHelp").find(".component-help").removeClass("disabled");

            $(this).addClass("disabled");

            var componentSelected = $(this).attr("data-component");

            $("#helptipsDiv").css("display", "block");
            set_samples_how_tos(componentSelected);
        });


        //handle popover close button
        $(document).on("click", ".popover .copo-close", function () {
            $(this).parents(".popover").popover('destroy');
        });

        // get table data to display via the DataTables API
        var loaderObject = $('<div>',
            {
                style: 'text-align: center',
                html: "<span class='fa fa-spinner fa-pulse fa-3x'></span>"
            });


        var tLoader = loaderObject.clone();
        $("#data_all_data").append(tLoader);

        csrftoken = $.cookie('csrftoken');

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
                tLoader.remove();
            },
            error: function () {
                alert("Couldn't retrieve samples!");
            }
        });

        //review-to-stage
        $(document).on("click", ".review-to-stage", function (event) {
            event.preventDefault();

            $('#sampleWizard').wizard('selectedItem', {
                step: $(this).attr("data-stage-indx")
            });
        });


        //******************************* wizard events *******************************//

        // retrieve wizard messages
        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'request_action': 'sample_wizard_components'
            },
            success: function (data) {
                sampleHowtos = data.wiz_howtos;
                wizardStagesMain = data.wizard_stages;
                wizardStages = data.wizard_stages;
                wizardMessages = data.wiz_message;
                sampleComponentRecords = data.component_records;
                set_samples_how_tos("generalHelpTips");
                set_wizard_summary();

            },
            error: function () {
                alert("Couldn't retrieve wizard message!");
            }
        });


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
                        cssClass: 'btn-primary',
                        action: function (dialogRef) {
                            dialogRef.close();
                            clear_wizard();
                        }
                    }
                ]
            });

            dialog_display(dialog, "Wizard Exit Alert", wizardMessages.exit_wizard_message.text, "warning");

        });


        //handle event for clicking an previously visited step, intercept here to save entries
        $('#sampleWizard').on('stepclicked.fu.wizard', function (evt, data) {
            evt.preventDefault();

            // get the proposed or intended state for which action is intercepted
            before_step_back(data.step);
        });

        $('#sampleWizard').on('changed.fu.wizard', function (evt, data) {
            //set up / refresh form validator
            set_up_validator();
        });


        //handle events for step change
        $('#sampleWizard').on('actionclicked.fu.wizard', function (evt, data) {
            $(self).data('step', data.step);

            stage_navigate(evt, data);
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
                onTheFlyElem.empty();

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

                    var dialogHandle = processing_request_dialog('<span class="loading">Generating Samples. Please wait...</span>');

                    var generated_samples = [];
                    for (var i = 0; i < dataTableDataSource.length; ++i) {
                        generated_samples.push(dataTableDataSource[i].attributes._id);
                    }

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: {
                            'request_action': 'finalise_description',
                            'generated_samples': JSON.stringify(generated_samples)
                        },
                        success: function (data) {
                            //clear_wizard(); no point...if we are reloading the page
                            window.location.reload();
                        },
                        error: function () {
                            alert("Couldn't save samples!");
                        }
                    });

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

            //setup steps fast navigation
            //steps_fast_nav();
        }

        function processing_request_dialog(message) {
            var $textAndPic = $('<div></div>');
            $textAndPic.append("<div style='text-align: center'><i class='fa fa-spinner fa-pulse fa-2x'></i></div>");

            var dialogInstance = new BootstrapDialog()
                .setTitle(message)
                .setMessage($textAndPic)
                .setType(BootstrapDialog.TYPE_INFO)
                .setSize(BootstrapDialog.SIZE_NORMAL)
                .setClosable(false)
                .open();

            return dialogInstance
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

            if (elem.hasClass('active')) {
                //call to set description summary data

                set_generated_samples();
                elem.show();
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

            if (($('#sampleWizard').is(":visible"))) {
                do_post_stage_retrieval2(data);
            } else {
                //store data pending tab shown
                tempWizStore = data;

                $('#copo-datafile-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show');
            }


        }

        function process_wizard_stage(data) {
            var stage = Object();
            if (data.hasOwnProperty("stage_ref")) {
                var stage = stage_description(data.stage_ref);
            }

            if (stage.hasOwnProperty("ref")) {

                $('#sampleWizard').wizard('addSteps', currentIndx, [
                    {
                        badge: ' ',
                        label: '<span class=wiz-title>' + stage.title + '</span>',
                        pane: get_pane_content(wizardStagesForms(stage), currentIndx, stage.message)
                    }
                ]);

                //give focus to the added step
                $('#sampleWizard').wizard('selectedItem', {
                    step: currentIndx
                });

                //refresh tooltips
                auto_complete();

            } else {
                if (stepIntercept) {
                    $('#sampleWizard').wizard('selectedItem', {
                        step: $('#sampleWizard').wizard('selectedItem').step + 1
                    });
                }
            }

            //refresh tooltips
            refresh_tool_tips();

        } //end of func


        function set_up_validator() {
            $(document).find("form").each(function () {
                var theForm = $(this);
                var formJSON = Object();

                if (theForm.find("#current_stage").length) {

                    var current_stage = theForm.find("#current_stage").val();

                    for (var i = 0; i < negotiatedStages.length; ++i) {
                        if (current_stage == negotiatedStages[i].ref) {
                            formJSON = negotiatedStages[i].items;
                            break;
                        }
                    }

                    if (!validateSetter.hasOwnProperty(current_stage)) {

                        refresh_validator($(this));

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

                                if (!global_form_validate(formJSON, theForm)) {
                                    $(this).find("#bcopovalidator").val("false");
                                    return false;
                                }
                            }
                        });

                        validateSetter[current_stage] = "1";
                    }

                }
            });

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
                //function decides whether to display the clone stage given user's choice or
                // the existence (lack of i.e) candidate samples
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
                //this is based on the presence of samples in the profile

                var displayStage = false;
                if (sampleComponentRecords.length > 0) {
                    displayStage = true;
                }

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

                stage.data = Object(); //no data needed

                if (stage.ref == "sample_attributes") {
                    var cloneRecord = get_clone_data();
                    if (!$.isEmptyObject(cloneRecord)) {
                        stage.data = cloneRecord;
                    }
                }
            }

            return stage;
        }

        function get_clone_data() {
            var cloneRecordID = get_stage_inputs_by_ref("sample_clone");
            cloneRecordID = cloneRecordID["sample_clone"];

            var cloneRecord = Object();
            var dataCopy = $.extend(true, Object(), sampleComponentRecords);

            $.each(dataCopy, function (key, val) {
                if (val._id == cloneRecordID) {
                    cloneRecord = val;
                    return false;
                }
            });

            return cloneRecord;

        }

        function get_pane_content(stage_content, currentIndx, stage_message) {
            var stageHTML = $('<div/>');

            //form controls
            var formPanel = $('<div/>', {
                class: "panel panel-copo-data panel-primary",
                style: "margin-top: 5px; font-size: 12px;"
            });

            var formPanelHeading = $('<div/>', {
                class: "panel-heading",
                style: "background-image: none; font-size: 14px;",
                html: stage_message
            });

            formPanel.append(formPanelHeading);

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

        //functions clears the wizard and either exits or loads next item in batch
        function clear_wizard() {
            //todo: need to decide what to save here before quitting the wizard

            //decommission wizard
            $('#sampleWizard').wizard('removeSteps', 1, currentIndx + 1);
            $('#sampleWizard').hide();

            //clear wizard buttons
            $('#wizard_steps_buttons').html('');


            //reset index
            currentIndx = 0;

            //hide discard button
            $('#remove_act').parent().hide();

            //clear generated sample table
            if ($.fn.dataTable.isDataTable('#generated_samples_table')) {
                //if table instance already exists, then do refresh
                var table = $('#generated_samples_table').DataTable();

                table
                    .clear()
                    .draw();
                table
                    .rows
                    .add([]);
                table
                    .columns
                    .adjust()
                    .draw();
                table
                    .search('')
                    .columns()
                    .search('')
                    .draw();
            }

            //remove negotiated stages and samples data
            negotiatedStages = [];
            generatedSamples = [];

            //switch info context
            $("#copoSampleHelp").find(".component-help").removeClass("disabled");
            $("#copoSampleHelp").find(".component-help[data-component='fileListComponent']").addClass("disabled");
            $("#generatedSamplesDiv").css("display", "none");
            $("#helptipsDiv").css("display", "block");

            //switch from wizard panel
            tempWizStore = null;

            //switch to file list context
            $('#copo-datafile-tabs.nav-tabs a[href="#fileListComponent"]').tab('show');

            //clear on the fly help
            $("#on_the_fly_info").empty();

            stagesFormValues = {};
            validateSetter = {};
            stepIntercept = false;
        }

        function reset_wizard() {//resets wizard without all the hassle of clear_wizard()
            $('#sampleWizard').wizard('removeSteps', 1, currentIndx + 1);

            //clear wizard buttons
            $('#wizard_steps_buttons').html('');

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
            var data = {"stage_ref": ""};

            //refresh wizard stages
            wizardStages = $.extend(true, Object(), wizardStagesMain);

            do_post_stage_retrieval(data);
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

        function resolve_element_view(recordId, associatedComponent) {
            //maps form element by id to component type e.g source, sample

            if (associatedComponent == "") {
                return false;
            }

            onTheFlyElem.append(tLoader);

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
                    onTheFlyElem.empty();
                    onTheFlyElem.append(build_attributes_display(data));
                },
                error: function () {
                    onTheFlyElem.empty();
                    onTheFlyElem.append("Couldn't retrieve attributes!");
                }
            });
        }


        function build_attributes_display(data) {
            //build view
            var attributesPanel = $('<div/>', {
                class: "panel panel-copo-data panel-default",
                style: "margin-top: 5px; font-size: 12px;"
            });

            var attributesPanelHeading = $('<div/>', {
                class: "panel-heading",
                style: "background-image: none;",
                html: "<strong>Sample Attributes</strong>"
            });

            attributesPanel.append(attributesPanelHeading);


            var attributesPanelBody = $('<div/>', {
                class: "panel-body"
            });

            var notAssignedSpan = $('<span/>', {
                class: "text-danger",
                html: "Attributes not assigned!"
            });

            attributesPanelBody.append(notAssignedSpan);


            if (data.hasOwnProperty("sample_attributes")) {
                //clear panel for new information
                attributesPanelBody.html('');

                //get schema
                var schema = data.sample_attributes.schema;

                //get record
                var record = data.sample_attributes.record;

                for (var i = 0; i < schema.length; ++i) {
                    var currentItem = schema[i];

                    var itemLabel = $('<div/>', {
                        html: currentItem.label,
                        style: "font-size:12px; font-weight:bold"
                    });

                    var itemDiv = $('<div/>', {
                        style: "padding: 5px; border: 1px solid #ddd; border-radius:2px; margin-bottom:3px;"
                    }).append(itemLabel).append(get_item_value_2(currentItem, record));

                    attributesPanelBody.append(itemDiv);

                }
            }


            attributesPanel.append(attributesPanelBody);

            var ctrlDiv = $('<div/>').append(attributesPanel);

            return ctrlDiv;
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
                        container: 'body',
                        trigger: 'hover',
                        placement: 'right',
                        template: '<div class="popover copo-popover-popover1"><div class="arrow">' +
                        '</div><div class="popover-inner"><h3 class="popover-title copo-popover-title1">' +
                        '</h3><div class="popover-content"><p></p></div></div></div>'
                    });

                }

            });
        }//end of function

        function steps_fast_nav() {
            $('#wizard_steps_buttons').html('');

            $('#wizard_steps_buttons').append('<span class="glyphicon glyphicon-arrow-right" style="font-size: 20px; ' +
                'vertical-align: text-bottom;"></span><span><label>Quick jump to step: &nbsp; </label></span>');

            var steps = $(".steps li:not(li:last-child)");
            steps.each(function (idx, li) {
                var lbl = idx + 1;
                var stp = $('<button/>',
                    {
                        text: lbl,
                        class: "btn btn-default copo-wiz-button",
                        title: $(li).find('.wiz-title').html(),
                        click: function () {
                            $('#sampleWizard').wizard('selectedItem', {
                                step: idx + 1
                            });
                            var elems = $('.copo-wiz-button');
                            elems.removeClass();
                            elems.addClass('btn btn-default copo-wiz-button');
                            stp.removeClass();
                            stp.addClass('btn btn-primary copo-wiz-button');
                        }
                    });

                stp.tooltip();

                $('#wizard_steps_buttons').append(stp);

            });
        }

        function wizardStagesForms(stage) {
            var formValue = stage.data;

            var formDiv = $('<div/>');

            //build form elements
            for (var i = 0; i < stage.items.length; ++i) {
                var formElem = stage.items[i];
                var control = formElem.control;

                var elemValue = null;

                if (formValue) {
                    if (formValue[formElem.id]) {
                        elemValue = formValue[formElem.id];

                        if (!elemValue) {
                            if (formElem.default_value) {
                                elemValue = formElem.default_value;
                            } else {
                                elemValue = "";
                            }
                        }
                    }
                }

                if (formElem.hidden == "true") {
                    control = "hidden";
                }

                try {
                    formDiv.append(dispatchFormControl[controlsMapping[control.toLowerCase()]](formElem, elemValue));
                }
                catch (err) {
                    console.log(control.toLowerCase());
                    formDiv.append('<div class="form-group copo-form-group"><span class="text-danger">Form Control Error</span> (' + formElem.label + '): Cannot resolve form control!</div>');
                    console.log(err);
                }

                //any triggers?
                if (formElem.trigger) {
                    try {
                        dispatchEventHandler[formElem.trigger.callback.function](formElem);
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

        function element_value_change(formElem, elemValue, messageTitle) {
            var dialog = new BootstrapDialog({
                buttons: [
                    {
                        label: 'Cancel',
                        cssClass: 'btn-default',
                        action: function (dialogRef) {
                            //set back to previous value
                            $("#" + formElem.id).val(elemValue);

                            dialogRef.close();
                        }
                    },
                    {
                        label: 'Continue',
                        cssClass: 'btn-primary',
                        action: function (dialogRef) {
                            setTimeout(function () {
                                //reset the wizard...

                                if (stage_data) {
                                    $.ajax({
                                        url: wizardURL,
                                        type: "POST",
                                        headers: {'X-CSRFToken': csrftoken},
                                        data: stage_data,
                                        success: function (data) {
                                            clear_wizard();
                                        },
                                        error: function () {
                                            alert("Couldn't save entries!");
                                        }
                                    });
                                }

                            }, 1000);

                            dialogRef.close();
                        }
                    }
                ]
            });

            dialog_display(dialog, messageTitle, wizardMessages.stage_dependency_message.text, "warning");

        }


        var dispatchEventHandler = {
            study_type_change: function (formElem) {
                var previousValue = null;

                $(document)
                    .off("focus", "#" + formElem.id)
                    .on("focus", "#" + formElem.id, function () {
                        previousValue = this.value;
                    });

                $(document)
                    .off(formElem.trigger.type, "#" + formElem.id)
                    .on(formElem.trigger.type, "#" + formElem.id, function () {
                        element_value_change(formElem, previousValue, "Study Type Change");
                    });
            },
            target_repo_change: function (formElem) {
                var previousValue = null;

                $(document)
                    .off("focus", "#" + formElem.id)
                    .on("focus", "#" + formElem.id, function () {
                        previousValue = this.value;
                    });

                $(document)
                    .off(formElem.trigger.type, "#" + formElem.id)
                    .on(formElem.trigger.type, "#" + formElem.id, function () {
                        element_value_change(formElem, previousValue, "Target Repo Change");
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
            var sampleTableColumns = generate_sample_table_columns();

            //set up data source
            dataTableDataSource = generate_sample_table_data_source();

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
                        //columns: ':not(:first-child)',
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

                            //get spec for the cell form element
                            var formElem = formEditableElements[cell.data()];
                            var control = formElem.control;

                            //get element value
                            var elemValue = table.row(cell.index().row).data().attributes[cell.data()];

                            var htmlCtrl = dispatchFormControl[controlsMapping[control.toLowerCase()]](formElem, elemValue);
                            htmlCtrl.find("label").remove();

                            //create cell edit panel
                            var cellEditPanel = get_cell_edit_panel();

                            //set cell edit data
                            cellEditPanel.find(".panel-body").append(htmlCtrl); //attach form control
                            cellEditPanel.find(".panel-footer").append(set_dynamic_cell_data()); //attach action buttons

                            $(node)
                                .html('')
                                .append(cellEditPanel)
                                .find(".input-copo").focus();


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
                                    form_values[this.id] = $(this).val();
                                });
                                cellParams["form_values"] = form_values;

                                set_cell_dynamic(cellParams);
                            });

                            var returnedObject = refresh_tool_tips();
                            if (returnedObject.hasOwnProperty("copoMultiSearch")) {
                                if (returnedObject.copoMultiSearch) {
                                    returnedObject.copoMultiSearch.focus();
                                }

                            }
                        }
                    });

                //also, use ENTER key to signal end of cell update...
                $(document).on("keyup", function (e) {
                    var code = (e.keyCode ? e.keyCode : e.which);
                    if (code == 13 && table && !dataTableTriggerSave) {
                        dataTableTriggerSave = true; //first time is to build control, only react at the second time
                        return false;
                    } else if (code == 13 && table && dataTableTriggerSave) {
                        var cells = table.cells('.cell-currently-engaged');

                        if (cells) {
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
                                form_values[this.id] = $(this).val();
                            });
                            cellParams["form_values"] = form_values;

                            set_cell_dynamic(cellParams);
                        }

                    }
                });
            }
        }

        function set_generated_samples() {
            var tLoader = loaderObject.clone();
            $("#summary_stage_loader").append(tLoader);

            //save generate requested number of samples
            var generatedSamples = [];

            var namePrefix = get_stage_inputs_by_ref("sample_name");
            if ($.isEmptyObject(namePrefix)) {
                namePrefix = "no_name";
            } else {
                namePrefix = namePrefix["name"];
            }

            var option = {};
            option["name"] = namePrefix;
            option["attributes"] = initialSampleAttributes;
            generatedSamples.push(option);

            var requestedNumberOfSamples = get_stage_inputs_by_ref("number_of_samples");

            if ($.isEmptyObject(requestedNumberOfSamples)) {
                requestedNumberOfSamples = 1;
            } else {
                requestedNumberOfSamples = parseInt(requestedNumberOfSamples["number_of_samples"]);
            }

            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'request_action': 'save_temp_samples',
                    'generated_samples': JSON.stringify(generatedSamples),
                    'sample_type': get_stage_inputs_by_ref("sample_type")["sample_type"],
                    'number_to_generate': requestedNumberOfSamples
                },
                success: function (data) {
                    do_generated_samples_display(data);
                },
                error: function () {
                    alert("Couldn't generate requested samples!");
                }
            });

        }//end of func

        function generate_sample_table_columns() {
            //generates sample table column, beginning with static columns

            var sampleTableColumns = [
                {title: "Rank", data: 'rank', visible: false, name: "rank"},
                {title: "Attributes", data: 'attributes', visible: false, name: "attributes"},
            ];

            //now, set the dynamic columns

            // get a reference sample entry in generated sample to use as basis for generating dynamic columns
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
                        }
                    }

                    return displaYData;
                }

                dynamicCol["className"] = "copo-editable-cell"; // column editable flag

                sampleTableColumns.push(dynamicCol);
            }

            return sampleTableColumns;
        }

        function generate_sample_table_data_source() {
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

        function set_dynamic_cell_data() {
            var parentObject = $('<div/>');

            var components = [
                {
                    title: "Apply to current",
                    action: "current",
                    description: "Click to apply this update to current cell.",
                    className: "btn btn-success btn-xs",
                    style: "margin-right: 2px;"
                },
                {
                    title: "Apply to selected",
                    action: "selected",
                    description: "Click to apply this update to selected records. Do remember to highlight the records for which you intend to apply the update.",
                    className: "btn btn-success btn-xs",
                    style: "margin-right: 2px;"
                },
                {
                    title: "Apply to all",
                    action: "all",
                    description: "Click to apply this update to all records.",
                    className: "btn btn-success btn-xs",
                    style: "margin-right: 2px;"
                },
                {
                    title: "Cancel",
                    action: "cancel",
                    description: "Click to cancel the update.",
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
                class: "panel panel-default",
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
            var form_values = cellParams.form_values;

            var auto_fields = JSON.stringify(form_values);

            //re-enable keys
            datatable.keys.enable();
            dataTableTriggerSave = false;

            //deselect previously selected rows
            datatable.rows('.selected').deselect();


            //remove cell's edit status
            var node = cell.node();
            $(node).removeClass('cell-currently-engaged'); //unlock cell

            var rowIndx = cell.index().row;

            //perform action
            if (action == "cancel") {
                datatable
                    .row(rowIndx)
                    .invalidate()
                    .draw();
            } else {
                // get all target rows
                var targetRows = [];

                targetRows.push({rowID: rowIndx, recordID: dataTableDataSource[rowIndx].attributes._id});

                //get action
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

                $.ajax({
                    url: wizardURL,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    data: {
                        'request_action': 'sample_cell_update',
                        'target_rows': JSON.stringify(targetRows),
                        'column_reference': cell.data(),
                        'sample_type': get_stage_inputs_by_ref("sample_type")["sample_type"],
                        'auto_fields': auto_fields
                    },
                    success: function (data) {
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

                    },
                    error: function () {
                        alert("Couldn't update record!");
                    }
                });

            }
        }


        function get_item_value_2(item, record) {
            //sort out item value

            var itemValue = $('<div/>',
                {
                    class: "ctrlDIV"
                });

            var valObject = record[item.id];

            if (item.type == "array") {
                //group items based on similarity of suffix

                for (var i = 0; i < valObject.length; ++i) {

                    try {
                        var objectHTML = dispatchViewControl[controlsViewMapping[item.control.toLowerCase()]](valObject[i], item);
                        itemValue.append(objectHTML);
                    }
                    catch (err) {
                        console.log(err + item.control);
                    }
                }

            } else {
                try {
                    var objectHTML = dispatchViewControl[controlsViewMapping[item.control.toLowerCase()]](valObject, item);
                    itemValue.append(objectHTML);
                }
                catch (err) {
                    console.log(err + item.control);
                }
            }

            return itemValue;
        }


        var controlsViewMapping = {
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
            "copo-sample-source-2": "do_copo_sample_source_ctrl_2",
            "oauth_required": "do_oauth_required",
            "copo-button-list": "do_copo_button_list_ctrl",
            "copo-item-count": "do_copo_item_count_ctrl"
        };


        var dispatchViewControl = {
            do_text_ctrl: function (relevantObject, item) {
                var ctrlsDiv = get_attributes_outer_div();

                ctrlsDiv.append(get_attributes_inner_div_1().append(relevantObject));

                return ctrlsDiv;
            },
            do_textarea_ctrl: function (relevantObject, item) {
                var ctrlsDiv = get_attributes_outer_div();

                ctrlsDiv.append(get_attributes_inner_div_1().append(relevantObject));

                return ctrlsDiv;
            },
            do_copo_select_ctrl: function (relevantObject, item) {
                return Object();
            },
            do_select_ctrl: function (relevantObject, item) {
                return Object();
            },
            do_copo_multi_search_ctrl: function (relevantObject, item) {
                return "";
            },
            do_copo_multi_select_ctrl: function (relevantObject, item) {
                return "";
            },
            do_copo_sample_source_ctrl_2: function (relevantObject, item) {
                var ctrlsDiv = get_attributes_outer_div();

                try {
                    var theValueObject = item.option_values;

                    for (var j = 0; j < theValueObject.options.length; ++j) {
                        if (relevantObject == theValueObject.options[j][theValueObject.value_field]) {
                            ctrlsDiv.append(get_attributes_inner_div_1().append(theValueObject.options[j][theValueObject.label_field]));
                        }
                    }
                }
                catch (err) {
                    console.log(err.name);
                }


                return ctrlsDiv;
            },
            do_copo_button_list_ctrl: function (relevantObject, item) {
                return "";
            },
            do_copo_item_count_ctrl: function (relevantObject, item) {
                return "";
            },
            do_copo_characteristics_ctrl: function (relevantObject, item) {
                var characteristicsSchema = copoSchemas.characteristics_schema;

                var ctrlsDiv = get_attributes_outer_div();

                for (var i = 0; i < characteristicsSchema.length; ++i) {

                    var currentItem = characteristicsSchema[i];

                    if (!currentItem.hasOwnProperty("show_in_table") || !currentItem["show_in_table"]) {
                        continue;
                    }

                    var scID = currentItem.id.split(".").slice(-1)[0];
                    var subValObject = Object();

                    if (relevantObject.hasOwnProperty(scID)) {
                        subValObject = relevantObject[scID];
                    }

                    $.each(subValObject, function (key, val) {
                        if (key == "annotationValue") {

                            if (val == "") {
                                val = "-"
                            }

                            if (i == 0) {
                                ctrlsDiv.append(get_attributes_inner_div_1().append(val));
                            } else {
                                ctrlsDiv.append(get_attributes_inner_div().append(val));
                            }
                        }
                    });

                }

                return ctrlsDiv;
            },
            do_copo_comment_ctrl: function (relevantObject, item) {
                var commentSchema = copoSchemas.comment_schema;

                var ctrlsDiv = get_attributes_outer_div();

                for (var i = 0; i < commentSchema.length; ++i) {

                    var currentItem = commentSchema[i];

                    if (!currentItem.hasOwnProperty("show_in_table") || !currentItem["show_in_table"]) {
                        continue;
                    }

                    var scID = currentItem.id.split(".").slice(-1)[0];
                    var val = "";
                    if (relevantObject.hasOwnProperty(scID)) {
                        val = relevantObject[scID];

                        if (val == "") {
                            val = "-"
                        }

                        if (i == 0) {
                            ctrlsDiv.append(get_attributes_inner_div_1().append(val));
                        } else {
                            ctrlsDiv.append(get_attributes_inner_div().append(val));
                        }
                    }

                }

                return ctrlsDiv;
            },
            do_ontology_term_ctrl: function (relevantObject, item) {
                var ontologySchema = copoSchemas.ontology_schema;

                var ctrlsDiv = get_attributes_outer_div();

                for (var i = 0; i < ontologySchema.length; ++i) {

                    var currentItem = ontologySchema[i];

                    if (!currentItem.hasOwnProperty("show_in_table") || !currentItem["show_in_table"]) {
                        continue;
                    }

                    var scID = currentItem.id.split(".").slice(-1)[0];
                    var val = "";
                    if (relevantObject.hasOwnProperty(scID)) {
                        val = relevantObject[scID];

                        if (val == "") {
                            val = "-"
                        }

                        if (i == 0) {
                            ctrlsDiv.append(get_attributes_inner_div_1().append(val));
                        } else {
                            ctrlsDiv.append(get_attributes_inner_div().append(val));
                        }
                    }

                }

                return ctrlsDiv;

            }
        };

        function get_stage_inputs_by_ref(ref) {
            var form_values = Object();

            if (stagesFormValues.hasOwnProperty(ref)) {
                form_values = stagesFormValues[ref];
            }

            return form_values;

        }


        function dialog_display(dialog, dTitle, dMessage, dType) {
            var dTypeObject = {
                "warning": "fa fa-exclamation-circle copo-icon-warning",
                "danger": "fa fa-times-circle copo-icon-danger",
                "info": "fa fa-exclamation-circle copo-icon-info"
            };

            var dTypeClass = "fa fa-exclamation-circle copo-icon-default";

            if (dTypeObject.hasOwnProperty(dType)) {
                dTypeClass = dTypeObject[dType];
            }

            var iconElement = $('<div/>', {
                class: dTypeClass + " wizard-alert-icon"
            });


            var $dialogContent = $('<div></div>');
            $dialogContent.append($('<div/>').append(iconElement));
            $dialogContent.append('<div class="copo-custom-modal-message">' + dMessage + '</div>');
            dialog.realize();
            dialog.setClosable(false);
            dialog.setSize(BootstrapDialog.SIZE_NORMAL);
            dialog.getModalHeader().hide();
            dialog.setTitle(dTitle);
            dialog.setMessage($dialogContent);
            dialog.getModalBody().prepend('<div class="copo-custom-modal-title">' + dialog.getTitle() + '</div>');
            dialog.getModalBody().addClass('copo-custom-modal-body');
            //dialog.getModalContent().css('border', '4px solid rgba(255, 255, 255, 0.3)');
            dialog.open();
        }


        function set_samples_how_tos(component) {

            if (!sampleHowtos.hasOwnProperty(component)) {
                component = "generalHelpTips"; //general help tips
            }


            var dataSet = []; //sampleHowtos[component].properties;

            $.each(sampleHowtos[component].properties, function (key, val) {
                var option = {};
                option["rank"] = key + 1;
                option["title"] = val.title;
                option["content"] = val.content;
                dataSet.push(option);
            });


            //set data
            var table = null;

            if ($.fn.dataTable.isDataTable('#datafile_howtos')) {
                //if table instance already exists, then do refresh
                table = $('#datafile_howtos').DataTable();
            }

            if (table) {
                //clear old, set new data
                table
                    .clear()
                    .draw();
                table
                    .rows
                    .add(dataSet);
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
                table = $('#datafile_howtos').DataTable({
                    data: dataSet,
                    searchHighlight: true,
                    "lengthChange": false,
                    order: [[0, "asc"]],
                    language: {
                        "info": " _START_ to _END_ of _TOTAL_ help tips",
                        "lengthMenu": "_MENU_ tips",
                    },
                    columns: [
                        {
                            "data": "rank",
                            "visible": false
                        },
                        {
                            "data": null,
                            "title": "Tips",
                            "render": function (data, type, row, meta) {
                                var aLink = $('<a/>', {
                                    "data-toggle": "collapse",
                                    href: "#helpcentretips" + meta.row,
                                    html: data.title
                                });

                                var aDiv = $('<div/>', {
                                    "class": "collapse help-centre-content",
                                    id: "helpcentretips" + meta.row,
                                    html: data.content,
                                    style: "background-color: #fff; margin-top: 10px; border-radius: 4px;"
                                });
                                return $('<div></div>').append(aLink).append(aDiv).html();
                            }
                        },
                        {
                            "data": "content",
                            "visible": false
                        }
                    ],
                    "columnDefs": [
                        {"orderData": 0,}
                    ]
                });
            }

            $('#datafile_howtos tr:eq(0) th:eq(0)').text(sampleHowtos[component].title + " Tips");
        }

    }
)//end document ready