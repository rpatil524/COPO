var wizardMessages;
var wizardStages;
var stagesFormValues = {};
var negotiatedStages = []; //holds info about stages resolved to be rendered
var sampleHowtos = null;
var currentIndx = 0;
var generatedSamples = [];
var tableID = null; //rendered table handle
var stepIntercept = false; //flag indicates if activation of the last stage of the wizard has been intercepted
var silenceAlert = false; //use to temporary suppress stage alerts
var descriptionWizSummary = {}; //wizard summary stage content
var tempWizStore = null; // for holding wizard-related data pending wizard load event
var onGoingDescription = false; //informs wizard state refresh/exit

$(document).ready(function () {
        //****************************** Event Handlers Block *************************//

        var component = "sample";
        var wizardURL = "/rest/sample_wiz/";
        var copoFormsURL = "/copo/copo_forms/";
        var copoVisualsURL = "/copo/copo_visualize/";

        //test
        //end test

        //handle UID - upload inspect describe - tabs
        $('#copo-datafile-tabs.nav-tabs a').on('shown.bs.tab', function (event) {
            var x = $(event.target).attr("data-component"); // active tab

            //check for temp data
            if (x == "descriptionWizardComponent" && tempWizStore) {
                do_post_stage_retrieval2(tempWizStore);
                tempWizStore = null;
            }
        });


        //handle popover close button
        $(document).on("click", ".popover .copo-close", function () {
            $(this).parents(".popover").popover('destroy');
        });


        //sample attributes flags
        var assignedFlag = '<i class="fa fa-thumbs-up copo-icon-success" title="attributes assigned" aria-hidden="true"></i>';
        var unassignedFlag = '<i class="fa fa-thumbs-down copo-icon-danger" title="no attributes" aria-hidden="true"></i>';

        //handle sample attributes assignment
        $(document).on("click", ".sample-assign-button", function () {
            do_attributes_assignment($(this));
        });

        //handle sample attributes view
        $(document).on("click", ".sample-view-button", function () {
            get_row_attributes($(this));
        });

        //handle keyboard strokes to advance through wizard

        //check if the control has focus
        $('#dataFileWizard').on('keypress', function (event, data) {

            if (event.keyCode == 13) {
                event.preventDefault();
                //here do the stage advance call
            }
            else if (event.keyCode == 39) {
                var d = {'step': $('#dataFileWizard').data('fu.wizard').currentStep, 'direction': 'next'};
                //d.step = $('#dataFileWizard').data('fu.wizard').currentStep
                //d.direction = 'next'
                $('#dataFileWizard').trigger('actionclicked.fu.wizard', d)
            }
            else if (event.keyCode == 37) {
                var d = {'step': $('#dataFileWizard').data('fu.wizard').currentStep, 'direction': 'previous'};
                //d.step = $('#dataFileWizard').data('fu.wizard').currentStep
                //d.direction = 'next'
                $('#dataFileWizard').trigger('actionclicked.fu.wizard', d)
            }
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

            $('#dataFileWizard').wizard('selectedItem', {
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
                wizardStages = data.wizard_stages;
                wizardMessages = data.wiz_message;
                set_samples_how_tos();
                set_wizard_summary();

            },
            error: function () {
                alert("Couldn't retrieve wizard message!");
            }
        });


        //handle event for description batch
        $('body').on('addtoqueue', function (event) {
            //add item to batch
            var batchTargets = [];
            var option = {};

            option["recordLabel"] = event.recordLabel;
            option["recordID"] = event.recordID;
            option["attributes"] = {};

            batchTargets.push(option);
            //add_to_batch(batchTargets, true); suspending this, as it becomes problematic for bundle validation
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
        $('#dataFileWizard').on('stepclicked.fu.wizard', function (evt, data) {
            evt.preventDefault();

            // get the proposed or intended state for which action is intercepted
            before_step_back(data.step);
        });

        $('#dataFileWizard').on('changed.fu.wizard', function (evt, data) {

            //set up apply to all button
            set_up_apply_button();


            //set up / refresh form validator
            set_up_validator();
        });


        //handle events for step change
        $('#dataFileWizard').on('actionclicked.fu.wizard', function (evt, data) {
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

            //call to update generated samples
            set_summary_data();

            do_post_stage_retrieval(stage_data);

            //if no data, just go ahead and retrieve stage

        }

        function stage_navigate(evt, data) {

            if (data.direction == 'next') {
                var lastElementIndx = $('.steps li').last().index() + 1;
                var activeElementIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index


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

                var auto_fields = JSON.stringify(form_values);

                //trap review stage here, which, in essence, provides a signal to wrap up the wizard
                var reviewElem = $('.steps li:last-child');

                if (reviewElem.hasClass('active')) {
                    //validate description for completeness; get submission decision; and, consequently, initiate submission

                    alert("last stage reached!!!");

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
            steps_fast_nav();
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
            $('#dataFileWizard').wizard('selectedItem', {
                step: proposedState
            });

            return;

        }

        function isInArray(value, array) {
            return array.indexOf(value) > -1;
        }


        function do_post_stage_retrieval2(data) {
            if (!data.stage_ref) {//this should indicate call to display first stage of the wizard
                if (currentIndx > 0) {
                    if (($('#dataFileWizard').is(":visible"))) {
                        reset_wizard();
                    }
                } else {
                    currentIndx += 1;
                    initiate_wizard();
                }

            }

            // wizard 'staging' process
            if (!($('#dataFileWizard').is(":visible"))) {


                $('#dataFileWizard').show();

                $('.steps li:last-child').hide(); //hide the last (static) stage of the wizard

                //show wizard exit button
                $('#remove_act').parent().show();
            }

            process_wizard_stage(data);


            //toggle show 'Review' stage
            var elem = $('.steps li:last-child');

            if (elem.hasClass('active')) {
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

            if (($('#dataFileWizard').is(":visible"))) {
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

                $('#dataFileWizard').wizard('addSteps', currentIndx, [
                    {
                        badge: ' ',
                        label: '<span class=wiz-title>' + stage.title + '</span>',
                        pane: get_pane_content(wizardStagesForms(stage), currentIndx, stage.message)
                    }
                ]);

                //give focus to the added step
                $('#dataFileWizard').wizard('selectedItem', {
                    step: currentIndx
                });

            } else {
                if (stepIntercept) {
                    $('#dataFileWizard').wizard('selectedItem', {
                        step: $('#dataFileWizard').wizard('selectedItem').step + 1
                    });
                }
            }

            //refresh tooltips
            refresh_tool_tips();

        } //end of func

        function set_up_apply_button() {
            var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index

            //get form elements for current stage
            var form_values = Object();

            if ($('#wizard_form_' + activeStageIndx).length) {
                $('#wizard_form_' + activeStageIndx).find(":input").each(function () {
                    form_values[this.id] = $(this).val();
                });

                if (form_values.hasOwnProperty("current_stage") && form_values.current_stage == "sample_attributes") {
                    $('#wizard_form_' + activeStageIndx).find(".applyToAllButton").css("display", "block");
                }
            }
        }

        function set_up_validator() {
            var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index, which, in this context is the summary (final) stage

            for (var i = 1; i < (activeStageIndx + 1); ++i) {
                if ($("#wizard_form_" + i).length) {
                    refresh_validator($("#wizard_form_" + i));
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

                            stage = negotiatedStages[currIndx + 1];
                            negotiatedStages[currIndx + 1].activated = true;
                        }
                    }
                } else {
                    //this should signal end of stages

                    stage = Object(); //no stage to return
                }
            }

            if (stage.hasOwnProperty("ref")) {
                stage.data = Object(); //no data needed
            }

            return stage;
        }

        function get_pane_content(stage_content, currentIndx, stage_message) {
            var stageHTML = $('<div/>', {
                id: "stage-controls-div-" + currentIndx
            });

            //'apply to all', alert trigger controls, and description context message

            var panelGroup = $('<div/>', {
                class: "panel-group wizard-message-panel",
                id: "alert_placeholder_" + currentIndx
            });

            //stageHTML.append(panelGroup);

            var panelPrimary = $('<div/>', {
                class: "panel panel-primary",
                style: "border: 2px solid #3278b4;"
            });

            var panelHeading = $('<div/>', {
                class: "panel-heading",
                style: "background-image: none; padding: 5px 15px;"
            });

            var headerRow = $('<div/>', {
                class: "row"
            });

            var spanMessage = $('<span/>', {
                html: "<strong>Apply this description to all items in the description bundle?</strong>"
            });

            var spanInput = $('<span/>', {
                style: "font-weight: bold; margin-left: 5px;",
                html: '<input type="checkbox" name="apply-scope-chk-' + currentIndx + '" checked data-size="mini" data-on-color="primary" data-off-color="default" data-on-text="Yes" data-off-text="No">'
            });

            var leftColumn = $('<div/>', {
                class: "col-sm-11 col-md-11 col-lg-11"
            });

            leftColumn.append(spanMessage).append(spanInput);

            var rightColumn = $('<div/>', {
                class: "col-sm-1 col-md-1 col-lg-1",
                html: '<a data-toggle="collapse" href="#collapseAlert" title="Toggle display" class="fa fa-bell pull-right control-message-trigger" style="text-decoration: none; color: white; font-weight: 800;"></a>'
            });

            headerRow.append(leftColumn).append(rightColumn);
            panelHeading.append(headerRow);

            var panelCollapse = $('<div/>', {
                class: "panel-collapse collapse message-pane-collapse",
                id: "collapseAlert"
            });

            var panelBody = $('<div/>', {
                class: "panel-body wizard-control-message",
            });

            var panelFooter = $('<div/>', {
                class: "panel-footer"
            });

            panelCollapse.append(panelBody).append(panelFooter);
            panelPrimary.append(panelHeading).append(panelCollapse);
            panelGroup.append(panelPrimary);


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

            var formButton = $('<button/>',
                {
                    style: "display:none;",
                    class: "btn btn-sm btn-primary applyToAllButton pull-right",
                    html: "Apply to Generated Samples",
                    click: function (event) {
                        event.preventDefault();

                        //set attribute for all samples
                        do_attributes_assignment_all();
                    }
                });

            var buttonRowDiv = $('<div/>', {
                class: "row"
            });

            var buttonColDiv = $('<div/>', {
                class: "col-sm-12 col-md-12 col-lg-12"
            });

            buttonColDiv.append(formButton);

            buttonRowDiv.append(buttonColDiv)

            formCtrl.append(stage_content).append(buttonRowDiv);


            formDiv.append(formCtrl);

            return stageHTML;
        }

        function initiate_wizard() {
            $('#dataFileWizard').wizard();

            //add review step, then other steps
            $('#dataFileWizard').wizard('addSteps', -1, [
                descriptionWizSummary
            ]);
        }

        //functions clears the wizard and either exits or loads next item in batch
        function clear_wizard() {
            //todo: need to decide what to save here before quitting the wizard

            //decommission wizard
            $('#dataFileWizard').wizard('removeSteps', 1, currentIndx + 1);
            $('#dataFileWizard').hide();

            //reset inDescription flag
            $('.inDescription-flag').each(function () { //main datafile table
                $(this).hide();
            });

            silenceAlert = false;


            //clear wizard buttons
            $('#wizard_steps_buttons').html('');


            //reset index
            currentIndx = 0;

            //hide discard button
            $('#remove_act').parent().hide();

            //switch from wizard panel
            tempWizStore = null;

            if (onGoingDescription) {
                $('#copo-datafile-tabs.nav-tabs a[href="#emptyTab"]').tab('show');
            } else {
                $('#copo-datafile-tabs.nav-tabs a[href="#fileListComponent"]').tab('show');
            }

            onGoingDescription = false;

            //clear stage message on help centre
            $("#on_the_fly_info").empty();

        }

        function reset_wizard() {//resets wizard without all the hassle of clear_wizard()
            $('#dataFileWizard').wizard('removeSteps', 1, currentIndx + 1);

            //clear wizard buttons
            $('#wizard_steps_buttons').html('');

            //add review step, then other steps
            $('#dataFileWizard').wizard('addSteps', -1, [
                descriptionWizSummary
            ]);

            currentIndx = 1;
        }

        function collate_stage_data() {
            //get active stage
            var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index

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

            } else if (task == "undescribe" && ids.length > 0) { //handles description metadata delete
                do_undescribe_confirmation(ids);

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
                            'task': 'description_summary',
                            'component': "datafile",
                            'target_id': ids[0]
                        },
                        success: function (data) {
                            var descriptionDiv = $('<div></div>');

                            for (var j = 0; j < data.description.length; ++j) {
                                var Ddata = data.description[j];

                                var i = 0; //need to change this to reflect stage index...

                                var level1Div = $('<div/>', {
                                    style: 'padding: 5px; border: 1px solid #ddd; border-radius:2px; margin-bottom:3px;'
                                });

                                var level2Anchor = $('<a/>', {
                                    class: "review-to-stage",
                                    "data-stage-indx": i,
                                    "data-sel-target": ids[0],
                                    style: "cursor: pointer; cursor: hand;",
                                    html: Ddata.title
                                });

                                var level2Div = $('<div/>', {
                                    style: 'padding-bottom: 5px;'
                                }).append($('<span></span>').append(level2Anchor));

                                level1Div.append(level2Div);

                                for (var k = 0; k < Ddata.data.length; ++k) {
                                    var Mdata = Ddata.data[k];

                                    var mDataDiv = $('<div/>', {
                                        style: 'padding-bottom: 5px;'
                                    });

                                    var mDataLabelSpan = $('<span/>', {
                                        style: 'margin-right: 10px;',
                                        html: Mdata.label + ":"
                                    });

                                    var displayedValue = "";

                                    if (Object.prototype.toString.call(Mdata.data) === '[object Array]') {
                                        Mdata.data.forEach(function (vv) {
                                            displayedValue += "<div style='padding-left: 25px; padding-top: 3px;'>" + vv + "</div>";
                                        });
                                    } else if (Object.prototype.toString.call(Mdata.data) === '[object String]') {
                                        displayedValue = String(Mdata.data);
                                    }

                                    var mDataDataSpan = $('<span/>', {
                                        html: displayedValue
                                    });

                                    mDataDiv.append(mDataLabelSpan).append(mDataDataSpan);
                                    level1Div.append(mDataDiv)
                                }

                                descriptionDiv.append(level1Div);
                            }

                            var descriptionHtml = "No description!";

                            if (data.description.length) {
                                descriptionHtml = descriptionDiv.html();
                            }

                            var descriptionInfoPanel = $('<div/>', {
                                class: "panel panel-default",
                                style: 'margin-top:1px;'
                            });

                            var headingRow = $('<div/>', {
                                class: "row"
                            });

                            var headingRowTxt = $('<div/>', {
                                class: "col-sm-11 col-md-11 col-lg-11",
                                html: '<span style="font-weight: bold; margin-left: 5px;">Description Metadata</span>'
                            });

                            var metadataClass = 'itemMetadata-flag-ind poor';

                            if (tr.find('.itemMetadata-flag').find('.meta-active').length) {
                                metadataClass = tr.find('.itemMetadata-flag').find('.meta-active').attr("class");
                            }

                            var headingRowIconSpan = $('<span/>', {
                                class: "pull-right " + metadataClass,
                                style: "width: 15px; height: 15px; border: 1px solid #ddd;"
                            });

                            var headingRowIconDiv = $('<div/>', {
                                class: "itemMetadata-flag",
                                title: "Metadata Rating"
                            }).append(headingRowIconSpan);

                            var headingRowIcon = $('<div/>', {
                                class: "col-sm-1 col-md-1 col-lg-1",
                                style: "padding-left: 5px;"
                            }).append(headingRowIconDiv);

                            headingRow.append(headingRowTxt).append(headingRowIcon);

                            var descriptionInfoPanelPanelHeading = $('<div/>', {
                                class: "panel-heading",
                                style: "background-image: none;"
                            }).append(headingRow);

                            var descriptionInfoPanelPanelBody = $('<div/>', {
                                class: "panel-body",
                                style: "overflow:scroll",
                                html: descriptionHtml
                            });

                            descriptionInfoPanel.append(descriptionInfoPanelPanelHeading).append(descriptionInfoPanelPanelBody);

                            row.child($('<div></div>').append(descriptionInfoPanel).html()).show();
                        },
                        error: function () {
                            alert("Couldn't retrieve description attributes!");
                            return '';
                        }
                    });
                }
            }

        } //end of func


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
                            $('#dataFileWizard').wizard('selectedItem', {
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

                                //call to save
                                var stage_data = collate_stage_data();
                                //remember user's choice for alerts
                                var silnAlert = silenceAlert;
                                if (stage_data) {
                                    $.ajax({
                                        url: wizardURL,
                                        type: "POST",
                                        headers: {'X-CSRFToken': csrftoken},
                                        data: stage_data,
                                        success: function (data) {
                                            onGoingDescription = true;
                                            clear_wizard();
                                            silenceAlert = silnAlert;
                                            add_new_samples(batchTargets, true);
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
                wizardMessages.review_message.text + '</div>' +
                '<div style="margin-top: 10px; max-width: 100%; overflow-x: auto;">'
            };
        }

        function set_summary_data() {
            //check if sample name has been entered before proceeding with sample display

            var namePrefix = get_stage_inputs_by_ref("sample_name");


            if ($.isEmptyObject(namePrefix)) {
                return false;
            } else {
                namePrefix = namePrefix["name"];
            }

            //show generated sample pane
            $('#copo-sample-tabs.nav-tabs a[href="#generatedSamples"]').tab('show');

            //set up data source
            var dtd = [];

            var requestedNumberOfSamples = get_stage_inputs_by_ref("number_of_samples");

            if ($.isEmptyObject(requestedNumberOfSamples)) {
                requestedNumberOfSamples = 0;
            } else {
                requestedNumberOfSamples = requestedNumberOfSamples["number_of_samples"];
            }

            requestedNumberOfSamples = parseInt(requestedNumberOfSamples);


            if (generatedSamples.length == 0) {
                //no sample generated. auto generate samples based on description metadata

                var newNames = generate_sample_names(1, requestedNumberOfSamples, namePrefix);


                for (var i = 0; i < newNames.length; ++i) {
                    var option = {};
                    option["name"] = newNames[i];
                    option["attributes"] = Object();
                    generatedSamples.push(option);
                }

                $.each(generatedSamples, function (key, val) {
                    var option = {};
                    option["rank"] = key + 1;
                    option["name"] = val.name;
                    option["attributes"] = val.attributes;
                    dtd.push(option);
                });
            } else if (requestedNumberOfSamples > generatedSamples.length) {
                var newNames = generate_sample_names((generatedSamples.length + 1), (requestedNumberOfSamples - generatedSamples.length ), namePrefix);

                for (var i = 0; i < newNames.length; ++i) {
                    var option = {};
                    option["name"] = newNames[i];
                    option["attributes"] = Object();
                    generatedSamples.push(option);
                }

                $.each(generatedSamples, function (key, val) {
                    var option = {};
                    option["rank"] = key + 1;
                    option["name"] = val.name;
                    option["attributes"] = val.attributes;
                    dtd.push(option);
                });
            } else if (requestedNumberOfSamples < generatedSamples.length) {
                var tempGenerated = [];
                for (var i = 0; i < requestedNumberOfSamples; ++i) {
                    tempGenerated.push(generatedSamples[i]);

                }

                generatedSamples = tempGenerated;

                $.each(generatedSamples, function (key, val) {
                    var option = {};
                    option["rank"] = key + 1;
                    option["name"] = val.name;
                    option["attributes"] = val.attributes;
                    dtd.push(option);
                });
            } else if (requestedNumberOfSamples == generatedSamples.length) {
                $.each(generatedSamples, function (key, val) {
                    var option = {};
                    option["rank"] = key + 1;
                    option["name"] = val.name;
                    option["attributes"] = val.attributes;
                    dtd.push(option);
                });
            }

            $("#generatedSamplesPara").html("Generated Samples");


            //set data

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
                    .add(dtd);
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
                table = $('#generated_samples_table').DataTable({
                    data: dtd,
                    "dom": '<"top"if>rt<"bottom"lp><"clear">',
                    searchHighlight: true,
                    language: {
                        "info": " _START_ to _END_ of _TOTAL_ samples",
                        "lengthMenu": "_MENU_ samples",
                    },
                    order: [[0, "asc"]],
                    columns: [
                        {
                            "data": "rank",
                            "visible": false
                        },
                        {
                            "data": null,
                            "title": "Tips",
                            "render": function (data, type, row, meta) {
                                var ctrlDiv = $('<div/>',
                                    {
                                        class: "row sample-attributes-row"
                                    });

                                //set attributes flag
                                var toBeassigned;

                                if ($.isEmptyObject(data.attributes)) {
                                    toBeassigned = unassignedFlag
                                }

                                var flagDiv = $('<div/>',
                                    {
                                        class: "col-sm-1 col-md-1 col-lg-1"
                                    }).append($('<span/>',
                                    {
                                        class: "sample-assign-flag"
                                    }).append(toBeassigned));

                                var nameDiv = $('<div/>',
                                    {
                                        class: "col-sm-7 col-md-7 col-lg-7"
                                    }).append($('<span/>',
                                    {
                                        html: data.name
                                    }));

                                var buttonDiv = $('<div/>',
                                    {
                                        class: "col-sm-4 col-md-4 col-lg-4"
                                    });

                                ctrlDiv.append(flagDiv).append(nameDiv).append(buttonDiv);

                                var aLink = $('<button/>', {
                                    class: "btn btn-xs btn-info sample-view-button",
                                    "data-row-indx": meta.row,
                                    title: "Click to view current attribute values",
                                    html: "View"
                                });

                                var applyBtn = $('<button/>', {
                                    class: "btn btn-xs btn-primary sample-assign-button",
                                    style: "margin-right: 10px;",
                                    "data-row-indx": meta.row,
                                    id: "#generatedsample" + meta.row,
                                    title: "Click to assign attribute values",
                                    html: "Assign"
                                });

                                buttonDiv.append(applyBtn).append(aLink);


                                return $('<div></div>').append(ctrlDiv).html();

                            }
                        },
                        {
                            "data": "attributes",
                            "visible": false
                        }
                    ],
                    "columnDefs": [
                        {"orderData": 0,}
                    ]
                });

                $('#generated_samples_table tr:eq(0) th:eq(0)').text(" Generated Samples");
            }

        }//end of func

        function do_attributes_assignment_all() {
            //set attribute for all samples
            if ($.fn.dataTable.isDataTable('#generated_samples_table')) {
                var table = $('#generated_samples_table').DataTable();

                table.rows().iterator('row', function (context, index) {
                    do_attributes_assignment($(this.row(index).node()).find(".sample-assign-button"));
                });
            }
        }

        function do_attributes_assignment(elem) {
            //get attributes and assign
            //this will only be possible if the active stage is one with the attributes

            var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step;

            if ($('#wizard_form_' + activeStageIndx).length) {
                var form_values = Object();

                $('#wizard_form_' + activeStageIndx).find(":input").each(function () {
                    form_values[this.id] = $(this).val();
                });

                if (form_values.hasOwnProperty("current_stage") && form_values["current_stage"] == "sample_attributes") {
                    generatedSamples[parseInt(elem.attr("data-row-indx"))].attributes = form_values;

                    //set flag
                    elem.closest(".sample-attributes-row").find(".sample-assign-flag").html(assignedFlag);
                }

            }

            get_row_attributes(elem);

        }

        function get_row_attributes(elem) {
            var table = $('#generated_samples_table').DataTable();
            var tr = elem.closest('tr');
            var row = table.row(tr);

            if (row.child.isShown()) {
                // This row is already open - close it
                row.child('');
                row.child.hide();
                tr.removeClass('shown');
            }
            else {
                //build view
                var attributesPanel = $('<div/>', {
                    class: "panel panel-copo-data panel-default",
                    style: "margin-top: 5px; font-size: 12px;"
                });

                var attributesPanelHeading = $('<div/>', {
                    class: "panel-heading",
                    style: "background-image: none;",
                    html: "Sample Attributes"
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

                //get values
                var stageValueObject = generatedSamples[parseInt(elem.attr("data-row-indx"))].attributes;

                //get stage
                var targetStage = Object();
                for (var i = 0; i < negotiatedStages.length; ++i) {
                    if (negotiatedStages[i].ref == "sample_attributes") {
                        targetStage = negotiatedStages[i];
                        break;
                    }
                }

                if (!($.isEmptyObject(stageValueObject) || $.isEmptyObject(targetStage))) {
                    //clear panel for new information
                    attributesPanelBody.html('');

                    for (var i = 0; i < targetStage.items.length; ++i) {
                        var currentItem = targetStage.items[i];
                        if (currentItem.hasOwnProperty("show_in_form") && currentItem["show_in_form"]) {
                            if (currentItem.hasOwnProperty("hidden") && currentItem.hidden.toString() == "false") {

                                var itemLabel = $('<div/>', {
                                    // for: currentItem.id,
                                    html: currentItem.label,
                                    style: "font-size:12px; font-weight:bold"
                                });

                                var itemDiv = $('<div/>', {
                                    style: "padding: 5px; border: 1px solid #ddd; border-radius:2px; margin-bottom:3px;"
                                }).append(itemLabel).append(get_item_value(currentItem, stageValueObject));

                                attributesPanelBody.append(itemDiv);

                            }
                        }
                    }
                }


                attributesPanel.append(attributesPanelBody);

                var ctrlDiv = $('<div/>').append(attributesPanel);


                //add view
                row.child(ctrlDiv.html()).show();
                tr.addClass('shown');
            }
        }

        function get_item_value(item, valuesObject) {
            //sort out item value
            var itemValue = "";

            if (item.type == "string") {
                //now get control and resolve value...
                var itemValue = $('<div/>', {
                    // for: currentItem.id,
                    html: "here we go",
                    style: "padding-top:5px;"
                });
            }

            return itemValue;
        }

        function get_stage_inputs_by_ref(ref) {
            var form_values = Object();

            if (stagesFormValues.hasOwnProperty(ref)) {
                form_values = stagesFormValues[ref];
            }

            return form_values;

        }


        function generate_sample_names(startIndx, number_to_generate, namePrefix) {
            var generatedNames = [];

            var combinedName = namePrefix + "_" + Math.round(new Date().getTime() / 1000);

            startIndx = parseInt(startIndx);
            number_to_generate = parseInt(number_to_generate);

            for (var i = startIndx; i < (number_to_generate + startIndx); ++i) {
                generatedNames.push(combinedName + "_" + i);
            }

            return generatedNames;
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


        function set_samples_how_tos() {

            var availableTips = [
                {
                    htmlTableID: "samplelist_howtos",
                    propertyID: "fileListComponent",
                    component: "inspect"
                },
                {
                    htmlTableID: "describe_howtos",
                    propertyID: "descriptionWizardComponent",
                    component: "describe"
                }
            ];

            for (var i = 0; i < availableTips.length; ++i) {
                var dtd = [];

                var component = availableTips[i].component;

                $.each(sampleHowtos[availableTips[i].propertyID].properties, function (key, val) {
                    var option = {};
                    option["rank"] = key + 1;
                    option["title"] = val.title;
                    option["content"] = val.content;
                    dtd.push(option);
                });


                //set data
                var table = null;

                if ($.fn.dataTable.isDataTable('#' + availableTips[i].htmlTableID)) {
                    //if table instance already exists, then do refresh
                    table = $('#' + availableTips[i].htmlTableID).DataTable();
                }

                if (table) {
                    //clear old, set new data
                    table
                        .clear()
                        .draw();
                    table
                        .rows
                        .add(dtd);
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
                    table = $('#' + availableTips[i].htmlTableID).DataTable({
                        data: dtd,
                        searchHighlight: true,
                        "lengthChange": true,
                        order: [[0, "asc"]],
                        "dom": '<"top"if>rt<"bottom"lp><"clear">',
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
                                        href: "#helpCenterTips" + component + meta.row,
                                        html: data.title
                                    });

                                    var aDiv = $('<div/>', {
                                        "class": "collapse help-centre-content",
                                        id: "helpCenterTips" + component + meta.row,
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

                $('#' + availableTips[i].htmlTableID + ' tr:eq(0) th:eq(0)').text(sampleHowtos[availableTips[i].propertyID].title + " Tips");
            }
        }


    }
)//end document ready