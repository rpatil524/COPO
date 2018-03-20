var wizardMessages;
var samplesGenerated = false; //flag to indicate if samples have been generated
var wizardStages;
var stagesFormValues = {};
var formEditableElements = {};
var validateSetter = {};
var negotiatedStages = []; //holds info about stages resolved to be rendered
var currentIndx = 0;
var generatedSamples = [];
var activeDescription = false; //whether there's an active description
var stepIntercept = false; //flag indicates if activation of the last stage of the wizard has been intercepted
var descriptionWizSummary = {}; //wizard summary stage content
var initialSampleAttributes = {}; //holds initial attributes shared by all samples before editing
var dataTableDataSource = []; // the data-source used for sample table generation
var displayedMessages = {}; //holds stage messages already displayed
var tabShownStore = Object();

$(document).ready(function () {
        //****************************** Event Handlers Block *************************//

        //page global variables
        var csrftoken = $('[name="csrfmiddlewaretoken"]').val();
        var component = "sample";
        var wizardURL = "/rest/sample_wiz/";
        var copoFormsURL = "/copo/copo_forms/";
        var resolvedAccessionData = null; //holds data from sample accession resolution

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

        //add new component button
        $(document).on("click", ".new-samples-template", function (event) {
            add_new_samples();
        });

        //details button hover
        $(document).on("mouseover", ".detail-hover-message", function (event) {
            $(this).prop('title', 'Click to view ' + component + ' details');
        });

        //description tab loading event
        $('#sample-display-tabs.nav-tabs a').on('shown.bs.tab', function (event) {
            if ($(event.target).attr("href") == "#descriptionWizardComponent") {
                if (!$.isEmptyObject(tabShownStore)) {
                    if (tabShownStore.method == "do_post_stage_retrieval2") {
                        $("#description_panel").css("display", "block");
                        do_post_stage_retrieval2(tabShownStore.data);

                        tabShownStore = Object();
                    }
                }
            }
        });


        //test

        //end test


        //******************************* wizard events *******************************//

        //handle event for discarding current description...
        $('#remove_act').on('click', function (event) {
            //confirm user decision
            BootstrapDialog.show({
                title: wizardMessages.exit_wizard_message.title,
                message: wizardMessages.exit_wizard_message.text,
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
                            dialogRef.close();
                            window.location.reload();
                        }
                    }
                ]
            });

        });

        $('#info_act').on('click', function (event) {
            //user wants information on current stage
            var item = $(this);
            var activeStageIndx = $('#sampleWizard').wizard('selectedItem').step; //active stage index

            var messageTitle = "Undocumented stage";
            var messageContent = "There is currently no information for this stage";

            var reviewElem = $('.steps li:last-child');
            if (reviewElem.hasClass('active')) {
                //last stage of the wizard
                messageTitle = "Review";
                messageContent = "Review and modify your samples as appropriate. Click 'Finish!' when done.";
            } else {
                var current_stage = $('#wizard_form_' + activeStageIndx).find("#current_stage").val();
                if (current_stage) {
                    for (var i = 0; i < negotiatedStages.length; ++i) {
                        if (negotiatedStages[i].ref == current_stage) {
                            messageTitle = negotiatedStages[i].title;
                            messageContent = negotiatedStages[i].message;
                            break;
                        }
                    }
                }
            }

            item.webuiPopover('destroy');
            item.webuiPopover({
                title: messageTitle,
                content: '<div class="webpop-content-div">' + messageContent + '</div>',
                trigger: 'sticky',
                width: 300,
                arrow: true,
                closeable: true,
                placement: 'auto-right',
                backdrop: true,
            });
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
                var current_stage_object = null;

                for (var i = 0; i < negotiatedStages.length; ++i) {
                    if (current_stage == negotiatedStages[i].ref) {
                        display_stage_message(negotiatedStages[i].message, negotiatedStages[i].title, negotiatedStages[i].ref);
                        current_stage_object = negotiatedStages[i];
                        break;
                    }
                }

                //some initial 'reactions' here; first for sample clone stage
                if (current_stage == "sample_clone") {
                    var radios = document.getElementsByName("sample_clone_route_input");
                    var existingRadioObject = null; //keep a reference to the existing and resolve radio button for further validation down the line
                    var resolveRadioObject = null;

                    for (var i = 0; i < radios.length; ++i) {
                        $('#wizard_form_' + currentStep).find("#" + radios[i].value).closest(".copo-form-group").hide();

                        if (radios[i].value == "clone_existing") {
                            existingRadioObject = radios[i];
                        }

                        if (radios[i].value == "clone_resolved") {
                            resolveRadioObject = radios[i];
                        }
                    }

                    //disable option if no existing samples to clone
                    var disableExistingOption = false;
                    for (var i = 0; i < current_stage_object.items.length; ++i) {
                        if (current_stage_object.items[i].id == "clone_existing" && (current_stage_object.items[i].option_values.options.length == 0)) {
                            disableExistingOption = true;
                        }
                    }

                    if (disableExistingOption) {
                        existingRadioObject.disabled = true;

                        //default to another radio option
                        resolveRadioObject.checked = true;
                        $('#wizard_form_' + currentStep).find("#sample_clone_route").val(resolveRadioObject.value);
                    }

                    //show corresponding form element
                    $('#wizard_form_' + currentStep).find("#" + $('#wizard_form_' + currentStep).find("#sample_clone_route").val()).closest(".copo-form-group").show();

                } else if (current_stage == "sample_name") {
                    var radios = document.getElementsByName("sample_name_route_input");
                    for (var i = 0; i < radios.length; ++i) {
                        $('#wizard_form_' + currentStep).find("#" + radios[i].value).closest(".copo-form-group").hide();
                    }

                    //show corresponding form element
                    $('#wizard_form_' + currentStep).find("#" + $('#wizard_form_' + currentStep).find("#sample_name_route").val()).closest(".copo-form-group").show();
                }
            }
        });


        //toggle show radio buttons corresponding input
        $(document).on("click", ".copo-radio-option", function (event) {

            if ($(this).attr("name") == "sample_clone_route_input") {
                var radios = document.getElementsByName("sample_clone_route_input");
                for (var i = 0; i < radios.length; i++) {
                    $(this).closest("form").find("#" + radios[i].value).closest(".copo-form-group").hide();
                }

                $(this).closest("form").find("#" + $(this).val()).closest(".copo-form-group").show();
            }

            if ($(this).attr("name") == "sample_name_route_input") {
                var radios = document.getElementsByName("sample_name_route_input");
                for (var i = 0; i < radios.length; i++) {
                    $(this).closest("form").find("#" + radios[i].value).closest(".copo-form-group").hide();
                }

                $(this).closest("form").find("#" + $(this).val()).closest(".copo-form-group").show();
            }
        });

        //sample accession resolution
        $(document).on("click", ".resolver-submit", function (event) {
            event.preventDefault();

            var dataElem = $(this).closest(".input-group").find(".resolver-data");
            var resolverValue = dataElem.val();
            resolverValue = resolverValue.replace(/^\s+|\s+$/g, '');
            dataElem.val('');

            var parentElem = $(this).closest(".copo-form-group");

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

            parentElem.find(".resolver-feedback").remove(); //remove feedback element

            var rFeedback = $('<i class="fa fa-commenting-o resolver-feedback" aria-hidden="true" style="padding-left: 5px; font-size: 20px;"></i>');
            var meta_extra = {placement: "auto-right", height: 300};

            if (resolverComponent.toLowerCase() == "sample") {
                $.ajax({
                    url: resolverURL,
                    type: 'GET',
                    dataType: 'json',
                    data: {
                        // name: query,
                    },
                    success: function (data) {
                        resolvedAccessionData = data;
                        var resolvedData = build_resolved_data(data);
                        parentElem.webuiPopover('destroy');
                        refresh_webpop(parentElem, "Resolved Sample [" + resolverValue + "]", resolvedData, meta_extra);
                        parentElem.webuiPopover('show');

                        rFeedback.insertAfter(parentElem.find("label"));
                        rFeedback.css("color", "green");

                        refresh_webpop(rFeedback, "Resolved Sample [" + resolverValue + "]", resolvedData, meta_extra);

                        //remove visual cues
                        spinnerElem.remove();
                        parentElem.removeClass("has-error has-danger");
                        parentElem.find(".help-block").html("");
                    },
                    error: function () {
                        spinnerElem.remove();
                        parentElem.addClass("has-error has-danger");
                        parentElem.find(".help-block").html("Couldn't resolve " + resolverValue + "!");
                        resolvedAccessionData = null;

                        rFeedback.insertAfter(parentElem.find("label"));
                        rFeedback.css("color", "red");
                        meta_extra.height = 100;

                        refresh_webpop(rFeedback, "Sample [" + resolverValue + "]", "Couldn't resolve the target sample accession!", meta_extra);
                    }
                });
            }//end of sample resolver

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


                BootstrapDialog.show({
                    title: wizardMessages.confirm_initial_sample_generation.title,
                    message: wizardMessages.confirm_initial_sample_generation.text,
                    cssClass: 'copo-modal2',
                    closable: false,
                    animate: true,
                    type: BootstrapDialog.TYPE_INFO,
                    buttons: [
                        {
                            label: 'Review',
                            cssClass: 'tiny ui basic button',
                            action: function (dialogRef) {
                                dialogRef.close();
                                return false;
                            }
                        },
                        {
                            label: '<i class="copo-components-icons fa fa-check"></i> Continue',
                            cssClass: 'tiny ui basic teal button',
                            action: function (dialogRef) {
                                $('#sampleWizard').wizard('selectedItem', {
                                    step: currentIndx
                                });

                                elem.show();

                                set_generated_samples();
                                samplesGenerated = true;
                                dialogRef.close();
                            }
                        }
                    ]
                });
            } else {
                elem.hide();
            }

            //form controls help tip
            refresh_tool_tips()

            //autocomplete
            auto_complete();
        }

        function do_post_stage_retrieval(data) {
            //update items with data

            if (($('#sampleWizard').is(":visible"))) {
                do_post_stage_retrieval2(data);
            } else {
                var tabShown = false; //check if describe tab is already visible
                $('#sample-display-tabs > li').each(function () {
                    if ($(this).hasClass("active") && $(this).find('a:first').attr("href") == "#descriptionWizardComponent") {
                        tabShown = true;
                        return false;
                    }
                });

                //hide wizard getting started
                $(".page-wizard-message").hide();

                if (tabShown) {//tab already shown, go ahead and display display wizard
                    $("#description_panel").css("display", "block");
                    do_post_stage_retrieval2(data);
                } else {//display tab, add loader, and go ahead to display wizard
                    $('#sample-display-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show');
                    tabShownStore.data = data;
                    tabShownStore.method = "do_post_stage_retrieval2";
                }
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
                    var clone_data = get_clone_data();
                    if (clone_data) {
                        //rebuild stage form with data from the cloned target

                        var ajaxData = {
                            'task': "component_record",
                            'component': component,
                            'target_id': clone_data
                        };
                        var ajaxUrl = copoFormsURL;

                        if (Object.prototype.toString.call(clone_data) === '[object Object]') {
                            //possibly dealing with a resolved sample; the resolved data is provided

                            ajaxData = {
                                'request_action': "resolved_object",
                                'component': component,
                                'resolved_object': JSON.stringify(clone_data)
                            }

                            ajaxUrl = wizardURL;
                        }

                        $("#wizard_form_" + currentIndx).html(get_spinner_image());

                        //fetch record and rebuild stage form...this time with data
                        $.ajax({
                            url: ajaxUrl,
                            type: "POST",
                            headers: {'X-CSRFToken': csrftoken},
                            data: ajaxData,
                            success: function (data) {
                                stageCopy["data"] = data.component_record;
                                $("#wizard_form_" + currentIndx).html(wizardStagesForms(stageCopy));
                                //
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

                    //get sample name
                    var sampleName = get_stage_inputs_by_ref("sample_name");
                    var genNameObject = '';

                    if (!$.isEmptyObject(sampleName) && (sampleName.hasOwnProperty('sample_name_route'))) {
                        if (sampleName['sample_name_route'].trim().toString() == "bundle_name"
                            && (sampleName.hasOwnProperty('bundle_name'))) {
                            var bundle_name = sampleName['bundle_name'].trim().toString();
                            if (bundle_name) {
                                genNameObject = bundle_name;
                            }
                        } else if (sampleName['sample_name_route'].trim().toString() == "provided_names"
                            && (sampleName.hasOwnProperty('provided_names'))) {
                            var provided_names = sampleName['provided_names'].trim().toString();

                            if (provided_names) {
                                if (provided_names.indexOf(',') != -1) {//it is comma separated...
                                    genNameObject = provided_names.split(',');
                                } else {// tab separated
                                    genNameObject = provided_names.split(/\s+/);
                                }
                            }
                        }
                    }

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: {
                            'request_action': 'sample_name_schema',
                            'profile_id': $('#profile_id').val()
                        },
                        success: function (data) {
                            $("#wizard_form_" + currentIndx).html('');
                            stageCopy.items = generate_sample_names(data.sample_name_schema, requestedNumberOfSamples, genNameObject);

                            //refresh negotiated stages with new stage items
                            for (var i = 0; i < negotiatedStages.length; ++i) {
                                if (negotiatedStages[i].ref == stage.ref) {
                                    negotiatedStages[i].items = stageCopy.items;
                                    break;
                                }
                            }

                            //generate controls based on stage items and append to the stage form
                            $("#wizard_form_" + currentIndx).html(wizardStagesForms(stageCopy));

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

        function generate_sample_names(sampleSchema, requestedNumberOfSamples, genNameObject) {
            var generatedSampleNames = [];

            for (var i = 1; i < requestedNumberOfSamples + 1; ++i) {
                var schemaCopy = $.extend(true, Object(), sampleSchema);
                schemaCopy.id = "assigned_sample_" + i.toString();
                if (genNameObject) {
                    if (Object.prototype.toString.call(genNameObject) === '[object String]') {
                        schemaCopy.default_value = genNameObject + "_" + i.toString();
                    } else if (Object.prototype.toString.call(genNameObject) === '[object Array]' && genNameObject[i - 1] !== undefined) {
                        schemaCopy.default_value = genNameObject[i - 1].trim();
                    }
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
            var sampleClone = get_stage_inputs_by_ref("sample_clone");
            var genCloneObject = null;

            if (!$.isEmptyObject(sampleClone) && (sampleClone.hasOwnProperty('sample_clone_route'))) {
                if (sampleClone['sample_clone_route'].trim().toString() == "clone_existing"
                    && (sampleClone.hasOwnProperty('clone_existing'))) {
                    var clone_existing = sampleClone['clone_existing'];
                    if (clone_existing) {
                        genCloneObject = clone_existing;
                    }
                } else if (sampleClone['sample_clone_route'].trim().toString() == "clone_resolved"
                    && (resolvedAccessionData)) {
                    genCloneObject = resolvedAccessionData;
                }
            }

            return genCloneObject;
        }

        function get_pane_content(stage_content, currentIndx, stage_message) {
            var stageHTML = $('<div/>');

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

            if (activeDescription) {
                $('#sample-display-tabs a[href="#descriptionWizardComponent"]').tab('show');
                return false;
            }

            activeDescription = true;

            // retrieve wizard messages
            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'request_action': 'sample_wizard_components',
                    'profile_id': $('#profile_id').val()
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
        function do_record_task(event) {
            var task = event.task.toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
            var tableID = event.tableID; //get target table

            //retrieve target records and execute task
            var table = $('#' + tableID).DataTable();
            var records = []; //
            $.map(table.rows('.selected').data(), function (item) {
                records.push(item);
            });

            //add task
            if (task == "describe") {
                add_new_samples();
                return false;
            }

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
                label: '<span class=wiz-title>Review</span>',
                pane: '<div class="alert alert-default">' +
                '<div style="line-height: 150%;" class="' + wizardMessages.review_message.text_class + '">' +
                wizardMessages.review_message.text + '</div><div id="summary_stage_loader"></div>' +
                '<div style="margin-top: 10px; max-width: 100%; overflow-x: auto;">' +
                '<table id="generated_samples_table" class="ui celled table hover copo-noborders-table" cellspacing="0" width="100%"></table>' +
                '</div></div>'
            };
        }

        function do_generated_samples_display(data) {
            //builds generated sample display

            generatedSamples = data.generated_samples.generated_samples;
            formEditableElements = data.generated_samples.form_elements;

            //flag error if no samples were generated
            if (generatedSamples.length < 1) {
                BootstrapDialog.show({
                    title: 'Sample Generation Error!',
                    message: "Couldn't generate samples. Possible duplicates in provided names.",
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
                            $(node).addClass('cell-currently-engaged'); //cell locked for edit, unlock with the TAB key

                            //set cell edit form
                            set_cell_form(node, cell, table, '');
                        }
                    });
            }

            //Enter-key event for table cell update...
            $(document).on('keypress', '.copo-form-group', function (event) {
                var code = (event.keyCode ? event.keyCode : event.which);
                if (code == 13 && ($($(event.target)).closest("#generated_samples_table").length)) {
                    var table = $('#generated_samples_table').DataTable();

                    var cells = table.cells('.cell-currently-engaged');

                    if (cells && cells[0].length > 0) {
                        $(document).find(".copo-form-group").webuiPopover('destroy');

                        var cell = cells[0];
                        var targetCell = table.cell(cell[0].row, cell[0].column);
                        var node = targetCell.node();
                        $(node).find(".cell-apply").webuiPopover('destroy');

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
                    'initial_sample_attributes': JSON.stringify(initialSampleAttributes),
                    'profile_id': $('#profile_id').val()
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

        function set_error_div(error_message) {
            if (!error_message) {
                return false;
            }

            var ctrlsDiv = $('<div/>',
                {
                    class: "row",
                    style: "color:#a94442;"
                });

            var sp = $('<div/>',
                {
                    class: "col-sm-12 col-md-12 col-lg-12 error-div",
                    html: error_message
                });

            return ctrlsDiv.append(sp);
        }

        function set_dynamic_cell_data(formElem) {
            var parentObject = $('<div/>');

            var violationList = []; //list allows button display filtering

            //unique violation
            if (formElem.hasOwnProperty("unique") && (formElem.unique.toString().toLowerCase() == "true")) {
                violationList.push('unique');
            }

            var components = [
                {
                    title: "Apply to current",
                    action: "current",
                    description: "Apply this update to current cell.",
                    className: "btn btn-primary btn-xs",
                    style: "margin-right: 2px;",
                    violations: []
                },
                {
                    title: "Apply to selected",
                    action: "selected",
                    description: "Apply this update to selected records. Do remember to highlight the records for which you intend to apply the update.",
                    className: "btn btn-primary btn-xs",
                    style: "margin-right: 2px;",
                    violations: ['unique']
                },
                {
                    title: "Apply to all",
                    action: "all",
                    description: "Apply this update to all records.",
                    className: "btn btn-primary btn-xs",
                    style: "margin-right: 2px;",
                    violations: ['unique']
                },
                {
                    title: "Cancel",
                    action: "cancel",
                    description: "Cancel this update.",
                    className: "btn btn-warning btn-xs pull-right",
                    style: "",
                    violations: []
                }
            ];

            for (var i = 0; i < components.length; ++i) {
                var option = components[i];

                var render = true;

                violationList.forEach(function (item) {
                    if ($.inArray(item, option.violations) !== -1) {
                        render = false;
                        return false;
                    }
                });

                if (!render) {
                    continue;
                }

                var elem = $('<button/>',
                    {
                        class: "cell-apply " + option.className,
                        style: "border-radius:0; background-image:none; " + option.style,
                        type: "button",
                        html: option.title,
                        "data-title": option.title,
                        "data-desc": option.description,
                        "data-action": option.action,
                    });

                elem.webuiPopover('destroy');
                var meta_extra = {width: 300, placement: 'bottom'};
                refresh_webpop(elem, elem.attr("data-title"), elem.attr("data-desc"), meta_extra);

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

        function set_cell_form(node, cell, table, error_message) {
            //get cell's derived id
            var derived_id = cell.data();

            //get cell's actual id
            var rowMeta = table.row(cell.index().row).data().attributes._recordMeta;
            var rowMetaResult = $.grep(rowMeta, function (e) {
                return e.derived_id == derived_id;
            });

            //get record id
            var recordId = table.row(cell.index().row).data().attributes._id;

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

            //retrieve record to obtain element value
            $.ajax({
                url: copoFormsURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': "component_record",
                    'component': component,
                    'target_id': recordId
                },
                success: function (data) {
                    //get element value
                    var rowAttributes = data.component_record;
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
                    cellEditPanel.find(".panel-body").append(htmlCtrl).append(set_error_div(error_message)); //attach form control
                    cellEditPanel.find(".panel-footer").append(set_dynamic_cell_data(formElem)); //attach action buttons

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
                    cellParams["datatable"] = table;
                    cellParams["cell"] = cell;
                    cellParams["action"] = "current";

                    cellEditPanel.find(".cell-apply").click(function () {
                        $(document).find(".copo-form-group").webuiPopover('destroy');

                        cellParams["action"] = $(this).attr("data-action");
                        cellParams["selectedRows"] = table.rows('.selected').indexes();
                        cellParams["allRows"] = table.rows().indexes();
                        cellEditPanel.find(".cell-apply").webuiPopover('destroy');

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
                },
                error: function () {
                    alert("Couldn't retrieve cell value!");
                }
            });

        }

        function set_cell_dynamic(cellParams) {
            var datatable = cellParams.datatable;
            var cell = cellParams.cell;
            var action = cellParams.action;

            var node = cell.node();

            $(node).html(get_spinner_image());

            var rowIndx = cell.index().row;

            //perform action
            if (action == "cancel") {
                //re-enable keys
                datatable.keys.enable();

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
                        'auto_fields': JSON.stringify(form_values),
                        'profile_id': $('#profile_id').val()
                    },
                    success: function (data) {
                        if (data.updated_samples.status && data.updated_samples.status == "error") {
                            //re-display edit form with error message
                            set_cell_form(node, cell, datatable, data.updated_samples.message);
                        } else {
                            //re-enable keys
                            datatable.keys.enable();

                            //remove cell's edit status
                            $(node).removeClass('cell-currently-engaged'); //unlock cell

                            //deselect previously selected rows
                            datatable.rows('.selected').deselect();

                            var updatedSamples = data.updated_samples.generated_samples;
                            formEditableElements = data.updated_samples.form_elements; //refresh form elements

                            //set updated and refresh display
                            for (var i = 0; i < targetRows.length; ++i) {
                                dataTableDataSource[targetRows[i].rowID].attributes._recordMeta[cell.index().columnVisible - 1] = updatedSamples[0]._recordMeta[cell.index().columnVisible - 1];

                                datatable
                                    .row(targetRows[i].rowID)
                                    .invalidate()
                                    .draw();

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

        function display_stage_message(stageMessage, stageTitle, stageRef) {
            if (stageMessage && !displayedMessages.hasOwnProperty(stageRef)) {
                var alertType = "info";
                var alertMessage = "<div style='margin-bottom: 10px;'><strong>" + stageTitle + "</strong></div><div>" + stageMessage + "</div>";
                display_copo_alert(alertType, alertMessage, 20000);
                displayedMessages[stageRef] = 1;
            }
        }

        function build_resolved_data(data) {
            var resolvedDiv = $('<div/>');

            var omitList = ["_links", "accession"]; //keys to omit from the report

            $.each(data, function (k, v) {

                if (!(omitList.indexOf(k) === -1)) {
                    return true;
                }

                if (Object.prototype.toString.call(v) === '[object String]') {
                    var iRow = $('<div/>',
                        {
                            class: "row",
                            style: "border-bottom: 1px solid #ddd;"
                        });

                    resolvedDiv.append(iRow);

                    var labelCol = $('<div/>',
                        {
                            class: "col-sm-5 col-md-5 col-lg-5"
                        });

                    var valueCol = $('<div/>',
                        {
                            class: "col-sm-7 col-md-7 col-lg-7"
                        });

                    iRow.append(labelCol);
                    iRow.append(valueCol);

                    labelCol.append(format_camel_case(k));
                    valueCol.append(v);
                } else if (Object.prototype.toString.call(v) === '[object Object]') {
                    if (k == "characteristics") {
                        $.each(v, function (key, val) {
                            var iRow = $('<div/>',
                                {
                                    class: "row",
                                    style: "border-bottom: 1px solid #ddd;"
                                });

                            resolvedDiv.append(iRow);

                            var labelCol = $('<div/>',
                                {
                                    class: "col-sm-5 col-md-5 col-lg-5"
                                });

                            var valueNode = [];

                            if (Object.prototype.toString.call(val) === '[object Array]') {
                                val.forEach(function (item) {
                                    if (Object.prototype.toString.call(item) === '[object Object]') {
                                        $.each(item, function (key22, val22) {
                                            if (key22 == "text") {
                                                valueNode.push(val22);
                                            }
                                        });
                                    } else if (Object.prototype.toString.call(val2) === '[object String]') {
                                        ;
                                    } else if (Object.prototype.toString.call(val2) === '[object Array]') {
                                        ;
                                    }
                                });
                            }

                            var valueCol = $('<div/>',
                                {
                                    class: "col-sm-7 col-md-7 col-lg-7"
                                });

                            labelCol.append(format_camel_case(key));

                            var breakr = $('<div/>',
                                {
                                    style: "border-top: 1px solid #e2e2e2;"
                                });

                            if (valueNode.length > 1) {
                                valueCol.append(valueNode[0]);
                                for (var i = 1; i < valueNode.length; ++i) {
                                    valueCol.append(breakr.clone().append(valueNode[i]));
                                }
                            } else {
                                valueCol.append(valueNode.join("<br/>"));
                            }

                            iRow.append(labelCol);
                            iRow.append(valueCol);
                        });
                    }

                } else if (Object.prototype.toString.call(v) === '[object Array]') {
                    var iRow = $('<div/>',
                        {
                            class: "row",
                            style: "border-bottom: 1px solid #ddd;"
                        });
                    resolvedDiv.append(iRow);

                    var labelCol = $('<div/>',
                        {
                            class: "col-sm-5 col-md-5 col-lg-5"
                        });
                    labelCol.append(format_camel_case(k));
                    iRow.append(labelCol);

                    var valueNode = [];
                    if (Object.prototype.toString.call(v) === '[object Array]') {
                        v.forEach(function (item) {
                            if (Object.prototype.toString.call(item) === '[object Object]') {
                                $.each(item, function (key22, val22) {
                                    valueNode.push(format_camel_case(key22) + ":  " + val22);
                                });
                            } else if (Object.prototype.toString.call(val2) === '[object String]') {
                                ;
                            } else if (Object.prototype.toString.call(val2) === '[object Array]') {
                                ;
                            }
                        });
                    }

                    var valueCol = $('<div/>',
                        {
                            class: "col-sm-7 col-md-7 col-lg-7"
                        });

                    var breakr = $('<div/>',
                        {
                            style: "border-top: 1px solid #e2e2e2;"
                        });

                    if (valueNode.length > 1) {
                        valueCol.append(valueNode[0]);
                        for (var i = 1; i < valueNode.length; ++i) {
                            valueCol.append(breakr.clone().append(valueNode[i]));
                        }
                    } else {
                        valueCol.append(valueNode.join("<br/>"));
                    }

                    iRow.append(valueCol);
                }
            });

            return resolvedDiv.html();
        }

    }
)//end document ready