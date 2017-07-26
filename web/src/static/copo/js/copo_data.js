var wizardMessages;
var datafileHowtos = null;
var currentIndx = 0;
var descriptionBundle = [];
var descriptionToken = null;
var tableID = null; //rendered table handle
var stage_objects = {}; //retains info about rendered stages
var stepIntercept = false; //flag indicates if activation of the last stage of the wizard has been intercepted
var silenceAlert = false; //use to temporary suppress stage alerts
var descriptionWizSummary = {}; //wizard summary stage content
var tempWizStore = null; // for holding wizard-related data pending wizard load event
var onGoingDescription = false; //informs wizard state refresh/exit
var setStageIndx = null; //moves the wizard to stage index specified


$(document).ready(function () {
    //****************************** Event Handlers Block *************************//

    var cyverse_files = $('#cyverse_file_data').val()
    if(cyverse_files != "None") {
        cyverse_files = JSON.parse(cyverse_files)
        $('#cyverse_files_link').on('click', function (e) {
            if (cyverse_files) {
                $('#file_tree').treeview({data: cyverse_files, showCheckbox: true});
                $('#file_tree').css('visibility', 'visible')
                e.preventDefault()
            }
        })
    }

    // firstly, if the url contains Figshare oauth return params and the selected_datafile is set, we are dealing with a
    // return from a Figshare oauth login, so attempt to load the datafile into the wizard

    // get url
    var url = window.location.search
    if( url.includes('state') && url.includes('code')){
        // now check for selected_datafile
        if ($('#selected_datafile').val() != '' || $('#selected_datafile').val() != undefined){
            alert('ask toni how we can load file ' + $('#selected_datafile').val() + ' into his wizard')
        }
    }



    var csrftoken = $.cookie('csrftoken');
    var component = "datafile";
    var wizardURL = "/rest/data_wiz/";
    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";


    //global_help_call
    do_global_help(component);


    //on the fly info element
    var onTheFlyElem = $("#copo_instant_info");

    //help table
    var pageHelpTable = "datafile_help_table"; //help pane table handle

    //handle UID - upload inspect describe - tabs
    $('#copo-datafile-tabs.nav-tabs a').on('shown.bs.tab', function (event) {
        var componentSelected = $(event.target).attr("data-component"); // active tab


        $("#datafileDataHelp").find(".component-help").removeClass("disabled");
        $("#datafileDataHelp").find(".component-help[data-component='" + componentSelected + "']").addClass("disabled");

        set_component_help($(this).attr("data-component"), pageHelpTable, datafileHowtos);

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

        set_component_help($(this).attr("data-component"), pageHelpTable, datafileHowtos);
    });

    //review-to-stage
    $(document).on("click", ".review-to-stage", function (event) {
        event.preventDefault();

        $('#dataFileWizard').wizard('selectedItem', {
            step: $(this).attr("data-stage-indx")
        });
    });

    //dismiss alerts
    $(document).on("click", ".control-message-trigger", function (event) {
        $(this).closest(".wizard-message-panel").find(".message-pane-collapse").collapse('toggle');
    });


    //show alerts

    $(document).on("click", ".close-stage-alert", function (event) {
        $(this).closest(".collapse").collapse('hide');
    });

    //metadata rating
    $(document).on("click", ".itemMetadata-flag", function (event) {
        update_itemMetadata_flag();
    });

    //disable alerts
    $(document).on("click", ".stage-alerts", function (event) {
        if ($(this).attr("data-alert-status") == "disable") {
            silenceAlert = true;

            $('.stage-alerts').each(function () {
                $(this).removeClass("btn-warning");
                $(this).addClass("btn-success");
                $(this).attr("data-alert-status", "enable");
                $(this).prop("title", wizardMessages.enable_alert_message.text);
                $(this).html("Enable");
            });

        } else {
            silenceAlert = false;

            $('.stage-alerts').each(function () {
                $(this).removeClass("btn-success");
                $(this).addClass("btn-warning");
                $(this).attr("data-alert-status", "disable");
                $(this).prop("title", wizardMessages.disable_alert_message.text);
                $(this).html("Disable");
            });
        }

        $('.wizard-message-panel').each(function () {
            $(this).find(".collapse").collapse('hide');
        });

    });

    //refresh metadata rating after table redraw
    $('body').on('refreshmetadataevents', function (event) {
        update_itemMetadata_flag();

        //check and refresh stage control if items are currently being described
        if (descriptionBundle.length > 0) {
            var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index
            refresh_inDescription_flag(activeStageIndx);
        } else {
            refresh_inDescription_flag(0);
        }

    });

    // get table data to display via the DataTables API
    var loaderObject = $('<div>',
        {
            style: 'text-align: center',
            html: "<span class='fa fa-spinner fa-pulse fa-3x'></span>"
        });


    // get table data to display via the DataTables API
    var tLoader = loaderObject.clone();
    $("#data_all_data").append(tLoader);

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
            alert("Couldn't retrieve datafiles!");
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
            datafileHowtos = data.help_messages;
            build_help_pane_menu(datafileHowtos, $("#datafileDataHelp").find(".componentHelpList"));
            set_component_help('', pageHelpTable, datafileHowtos);
            helpLoader.remove();
        },
        error: function () {
            alert("Couldn't retrieve page help!");
        }
    });


    // inform session of currently selected datafile id
    $(document).on('click', '.copo-dt', function(e){
        var datafile_id = $(e.currentTarget).attr("data-record-id")
        $.ajax(
            {
                url: '/rest/set_session_variable/',
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data:{
                    "key": "datafile_id",
                    "value": datafile_id
                },
                success: function(data){
                    console.log("sent data to session " + data)
                }
            })
        })


    //******************************* wizard events *******************************//

    // retrieve wizard messages
    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {'X-CSRFToken': csrftoken},
        data: {
            'task': 'wizard_messages',
            'component': component
        },
        success: function (data) {
            wizardMessages = data.wiz_message;
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
                    label: 'Continue Describing',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                },
                {
                    label: 'Exit Description',
                    cssClass: 'btn-primary',
                    action: function (dialogRef) {
                        dialogRef.close();
                        clear_wizard();
                    }
                }
            ]
        });

        dialog_display(dialog, "Exit Description", wizardMessages.exit_wizard_message.text, "warning");

    });

    //handle event for discarding description...
    $('#discard_act').on('click', function (event) {
        //this, basically, if seen through, will remove all description metadata from affected items
        var dialog = new BootstrapDialog({
            buttons: [
                {
                    label: 'Continue Describing',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                },
                {
                    label: 'Cancel Description',
                    cssClass: 'btn-danger',
                    action: function (dialogRef) {
                        dialogRef.close();

                        var request_params = {
                            'request_action': 'discard_description',
                            'description_token': descriptionToken,
                            'description_targets': JSON.stringify(descriptionBundle)
                        };

                        $.ajax({
                            url: wizardURL,
                            type: "POST",
                            headers: {'X-CSRFToken': csrftoken},
                            data: request_params,
                            success: function (data) {
                                clear_wizard();
                                update_itemMetadata_flag();
                            },
                            error: function () {
                                alert("Couldn't update metadata for targets!");
                            }
                        });
                    }
                }
            ]
        });

        dialog_display(dialog, "Cancel Description", wizardMessages.discard_description_message.text, "danger");

    });

    //handle event for saving subset of items in the description bundle
    $(document).on("click", ".apply-to-selected-btn", function (event) {
        event.preventDefault();
        var activeStageIndx = $(this).attr('data-stage-indx');

        if ($.fn.dataTable.isDataTable('#description_target_table_' + activeStageIndx)) {
            var table = $('#description_target_table_' + activeStageIndx).DataTable();

            var selectedRows = table.rows({selected: true}).data();

            if (selectedRows.length > 0) {
                var deTargs = [];
                for (var i = 0; i < selectedRows.length; ++i) {
                    descriptionBundle.forEach(function (item) {
                        if (selectedRows[i].target_id == item.recordID) {
                            deTargs.push(item);
                        }
                    });
                }

                var stage_data = collate_stage_data();
                stage_data.description_targets = JSON.stringify(deTargs);
                //also, get back empty stage form
                stage_data["default_stage_form"] = true;
                $.ajax({
                    url: wizardURL,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    data: stage_data,
                    success: function (data) {
                        //remove previous selections
                        table.rows('.selected').deselect();

                        //refresh batch data
                        if (data.targets_data) {
                            refresh_targets_data(data.targets_data);

                            //refresh description batch display
                            refresh_batch_display();
                        }

                        //refresh stage form, iff apply-to-all control is false
                        if (!get_apply_check_state(activeStageIndx)) {
                            $('#wizard_form_' + activeStageIndx).html(wizardStagesForms(data.stage.stage).html());

                            refresh_tool_tips();

                            //ontology autocomplete
                            auto_complete();
                        }
                    },
                    error: function () {
                        alert("Couldn't save some entries!");
                    }
                });
            }
        }

    });

    //key trigger to submit individual bundle item form
    $(document).on("keydown", ".wizard-items-form", function (event) {
        if (event.keyCode == 13 && event.metaKey) {
            var targetForm = $($(event.target)).closest('.wizard-items-form');
            if (targetForm.length) {
                var activeStageIndx = targetForm.attr('data-stage-indx');
                var descriptionTarget = targetForm.attr('data-description-target');

                save_bundle_item_form(activeStageIndx, descriptionTarget);
            }
        }
    });

    //handle event for saving a single item in the description bundle
    $(document).on("click", ".apply-to-item-btn", function (event) {
        event.preventDefault();

        var activeStageIndx = $(this).attr('data-stage-indx');
        var descriptionTarget = $(this).attr('data-description-target');

        save_bundle_item_form(activeStageIndx, descriptionTarget);
    });

    //handle event for clicking an previously visited step, intercept here to save entries
    $('#dataFileWizard').on('stepclicked.fu.wizard', function (evt, data) {
        evt.preventDefault();

        // get the proposed or intended state for which action is intercepted
        before_step_back(data.step);
    });

    $('#dataFileWizard').on('changed.fu.wizard', function (evt, data) {
        //negotiate alert for stage
        new_stage_alert();

        //refresh description batch display
        refresh_batch_display();
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

    //handle batch item events
    $(document).on("click", ".wiz-batch-item", function (event) {
        var task = $(this).attr("data-record-action").toLowerCase();
        var targetId = $(this).attr("data-record-id");

        if (task == "delete") {
            if (descriptionBundle.length == 1) {//trying to remove last item from description bundle
                BootstrapDialog.show({
                    title: 'Description Action Required!',
                    message: wizardMessages.empty_bundle_message.text,
                    type: BootstrapDialog.TYPE_PRIMARY,
                    animate: true,
                    buttons: [
                        {
                            label: 'Cancel',
                            action: function (dialogRef) {
                                dialogRef.close();
                            }
                        },
                        {
                            label: 'Continue',
                            cssClass: 'btn-primary',
                            action: function (dialogRef) {
                                $(this).tooltip('destroy');

                                clear_wizard();

                                dialogRef.close();
                            }
                        }
                    ]
                });
            } else {
                $(this).tooltip('destroy');
                for (i = 0; i < descriptionBundle.length; ++i) {
                    if (targetId == descriptionBundle[i].recordID) {
                        do_deque(descriptionBundle[i]);
                        break;
                    }
                }
            }

        }
    });


    //****************************** Functions Block ******************************//
    function add_step(auto_fields) {
        //step being requested
        currentIndx += 1;

        var retrieval_params = {
            'request_action': "get_next_stage",
            'description_token': descriptionToken,
            'auto_fields': auto_fields,
            'description_targets': JSON.stringify(descriptionBundle),
            'description_bundle': JSON.stringify(descriptionBundle)
        };

        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index

        //first, make call to resolve the active stage data
        var stage_data = collate_stage_data();

        //if no data, just go ahead and retrieve stage
        if (!stage_data) {
            retrieve_stage(retrieval_params);
        } else {//verify what needs to be saved here...
            if (!get_apply_check_state(activeStageIndx)) {//apply-to-selected:
                // saving of data is handled per sub items in the bundle,
                // only check that all items have metadata for this stage
                var countMetadata = 0;
                descriptionBundle.forEach(function (item) {
                    if (item["attributes"][stage_objects[activeStageIndx].ref]) {
                        ++countMetadata;
                    }
                });

                if (descriptionBundle.length != countMetadata) {
                    //some items in bundle may be lacking metadata

                    var dialog = new BootstrapDialog({
                        buttons: [
                            {
                                label: 'Describe',
                                cssClass: 'btn-primary',
                                action: function (dialogRef) {
                                    dialogRef.close();
                                    $('#dataFileWizard').wizard('selectedItem', {
                                        step: activeStageIndx
                                    });
                                }
                            },
                            {
                                label: 'Continue',
                                cssClass: 'btn-default',
                                action: function (dialogRef) {
                                    retrieve_stage(retrieval_params);
                                    dialogRef.close();
                                }
                            }
                        ]
                    });

                    dialog_display(dialog, "Description Alert", wizardMessages.no_metadata_selected_bundle_items.text, "warning");

                } else {
                    //make call to retrieve stage
                    retrieve_stage(retrieval_params);
                }

            } else {//apply-to-all:
                //ascertain any mismatch between items' metadata and current stage description

                //but first, if no metadata for all bundle items, continue rather silently
                var countMetadata = 0;
                descriptionBundle.forEach(function (item) {
                    if (item["attributes"][stage_objects[activeStageIndx].ref]) {
                        ++countMetadata;
                    }
                });

                if (countMetadata == 0) {//no metadata for all bundle items, save and load next stage...

                    //display dialog for stage save
                    var dialogHandle = processing_request_dialog('Saving Stage Data...');

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: stage_data,
                        success: function (data) {
                            //make call to retrieve stage
                            retrieve_stage(retrieval_params);
                            dialogHandle.close();
                        },
                        error: function () {
                            alert("Couldn't save description entries!");
                        }
                    });
                } else if (descriptionBundle.length == countMetadata) {
                    //all items have metadata, but is there a mismatch with the current stage entries

                    stage_data.request_action = 'is_description_mismatch';
                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: stage_data,
                        success: function (data) {
                            if (data.state) {
                                //there is a mismatch, confirm user's action
                                var opts = wizardMessages.metadata_bundle_items.text_options;
                                var displayHTML = '<div class="list-group">';
                                displayHTML += '<div class="list-group-item">';
                                displayHTML += '<div class="wizard-alert-options">' + wizardMessages.metadata_bundle_items.text + '</div>';
                                var checked;
                                opts.forEach(function (opt) {
                                    checked = "";
                                    if (opt.value == "overwrite") {//do overwrite, if entries change, by default
                                        checked = " checked";
                                    }
                                    displayHTML += '<div class="radio wizard-alert-radio">';
                                    displayHTML += '<label><input type="radio" name="metadata_bundle_items" value="' + opt.value + '"' + checked + '>' + opt.label + '</label>';
                                    displayHTML += '</div>';
                                });
                                displayHTML += '</div>';
                                displayHTML += '</div>';

                                var dialog = new BootstrapDialog({
                                    buttons: [
                                        {
                                            label: 'OK',
                                            cssClass: 'btn-primary',
                                            action: function (dialogRef) {
                                                var selectedOption = $('input[name=metadata_bundle_items]:checked').val();
                                                if (selectedOption == "donotoverwrite") {//do not overwrite
                                                    retrieve_stage(retrieval_params);
                                                } else {
                                                    stage_data.request_action = 'save_stage_data';
                                                    //display dialog for stage save
                                                    var dialogHandle = processing_request_dialog('Saving Stage Data...');

                                                    $.ajax({
                                                        url: wizardURL,
                                                        type: "POST",
                                                        headers: {'X-CSRFToken': csrftoken},
                                                        data: stage_data,
                                                        success: function (data) {
                                                            //make call to retrieve stage
                                                            retrieve_stage(retrieval_params);
                                                            dialogHandle.close();
                                                        },
                                                        error: function () {
                                                            alert("Couldn't save some entries!");
                                                        }
                                                    });
                                                }

                                                dialogRef.close();
                                            }
                                        }
                                    ]
                                });

                                dialog_display(dialog, "Description Action Required", displayHTML, "warning");

                            } else {
                                //no mismatch, just go ahead and load next stage
                                retrieve_stage(retrieval_params);
                            }
                        },
                        error: function () {
                            alert("Couldn't verify metadata mismatch!");
                        }
                    });
                }
            }
        }
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

                //are all items in bundle good to go?
                var datafile_ids = []; //for metadata rating
                descriptionBundle.forEach(function (item) {
                    datafile_ids.push(item.recordID);
                });

                var dialogHandle = processing_request_dialog('Validating description bundle...');

                $.ajax({
                    url: copoVisualsURL,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    data: {
                        'task': 'metadata_ratings',
                        'component': component,
                        'datafile_ids': JSON.stringify(datafile_ids)
                    },
                    success: function (data) {
                        if (data.metadata_ratings) {
                            var currentMetadataRating = data.metadata_ratings;

                            var isAllValid = true;

                            for (var i = 0; i < currentMetadataRating.length; ++i) {
                                if (currentMetadataRating[i].item_rating.hasOwnProperty("rating_level")) {
                                    if (currentMetadataRating[i].item_rating.rating_level != "good") {
                                        isAllValid = false;
                                        break;
                                    }
                                }
                            }

                            dialogHandle.close();

                            //display dialog based on validation result

                            if (isAllValid) {
                                var dialog = new BootstrapDialog({
                                    buttons: [
                                        {
                                            label: 'Exit Wizard',
                                            action: function (dialogRef) {
                                                clear_wizard();
                                                dialogRef.close();
                                            }
                                        },
                                        {
                                            label: 'Initiate',
                                            cssClass: 'btn-primary',
                                            action: function (dialogRef) {

                                                dialogRef.getModalFooter().hide();
                                                dialogRef.getModalBody().find(".copo-custom-modal-message").html('<div class="loading">Redirecting</div>');

                                                $.ajax({
                                                    url: copoFormsURL,
                                                    type: "POST",
                                                    headers: {'X-CSRFToken': csrftoken},
                                                    data: {
                                                        'task': 'initiate_submission',
                                                        'component': "submission",
                                                        'datafile_ids': JSON.stringify(datafile_ids)
                                                    },
                                                    success: function (data) {
                                                        //if successful, redirect to submissions
                                                        var locus = $("#submission_url").val();
                                                        window.location.replace(locus);
                                                    },
                                                    error: function () {
                                                        alert("Couldn't initiate submission!");
                                                    }
                                                });
                                            }
                                        }
                                    ]
                                });

                                dialog_display(dialog, "Initiate Submission", wizardMessages.confirm_initiate_submission.text, "info");

                            } else {
                                var dialog = new BootstrapDialog({
                                    buttons: [
                                        {
                                            label: 'Exit Wizard',
                                            action: function (dialogRef) {
                                                clear_wizard();
                                                dialogRef.close();
                                            }
                                        },
                                        {
                                            label: 'Describe',
                                            cssClass: 'btn-primary',
                                            action: function (dialogRef) {
                                                dialogRef.close();
                                            }
                                        }
                                    ]
                                });

                                dialog_display(dialog, "Description Alert", wizardMessages.metadata_validation_failed.text, "warning");

                            }
                        }
                    },
                    error: function () {
                        alert("Couldn't validate bundle!");
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

    function isInArray(value, array) {
        return array.indexOf(value) > -1;
    }

    function get_apply_check_state(activeStageIndx) {//function returns the state of the apply-to-all control
        var chkState; //apply-to-all checkbox state

        try {
            chkState = $("[name='apply-scope-chk-" + activeStageIndx + "']").bootstrapSwitch('state');
        }
        catch (err) {
            chkState = true;
        }

        return chkState;
    }

    function set_apply_check_state(activeStageIndx) {//function determines whether all items in the bundle have same metadata
        if (activeStageIndx == -1) {
            return true;
        }

        var request_params = {
            'request_action': 'is_same_metadata',
            'description_token': descriptionToken,
            'stage_ref': stage_objects[activeStageIndx].ref,
            'description_targets': JSON.stringify(bundle_without_data())
        };

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: request_params,
            success: function (data) {
                var btnState = false;
                if (data.state) {
                    btnState = data.state;
                }

                if (!btnState) {
                    $("[name='apply-scope-chk-" + activeStageIndx + "']").bootstrapSwitch('state', false);
                }
            },
            error: function () {
                alert("Couldn't retrieve data for targets!");
            }
        });
    }

    function refresh_targets_data(targets_data) {
        //update bundle items with corresponding data
        if (targets_data) {
            for (var k in targets_data) {
                descriptionBundle.forEach(function (item) {
                    if (targets_data[k].recordID == item.recordID) {
                        item["attributes"] = targets_data[k]["attributes"];
                    }
                });
            }
        }

        //refresh visual cues for items' metadata
        update_itemMetadata_flag();
    }

    function retrieve_stage(retrieval_params) {
        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: retrieval_params,
            success: function (data) {
                do_post_stage_retrieval(data);
            },
            error: function () {
                alert("Couldn't retrieve wizard stage!");
            }
        });
    }

    function do_post_stage_retrieval2(data) {
        //update description token
        if (data.description_token) {

            descriptionToken = data.description_token;

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
            //call to set description summary data

            set_summary_data();
            elem.show();
        } else {
            elem.hide();
        }

        refresh_tool_tips();

        //autocomplete
        auto_complete();
    }

    function do_post_stage_retrieval(data) {
        //update items with data
        if (data.targets_data) {
            refresh_targets_data(data.targets_data);
        }


        if (($('#dataFileWizard').is(":visible"))) {
            do_post_stage_retrieval2(data);
        } else {
            //store data pending tab shown
            tempWizStore = data;

            $('#copo-datafile-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show');
        }


    }

    function process_wizard_stage(data) {
        if (data.stages) {
            var selStep = currentIndx;
            var panes = [];
            for (var i = 0; i < data.stages.length; ++i) {
                if (data.stages[i].stage.title) {
                    stage_objects[currentIndx] = data.stages[i].stage;
                    panes.push({
                        badge: ' ',
                        label: '<span class=wiz-title>' + data.stages[i].stage.title + '</span>',
                        pane: get_pane_content(wizardStagesForms(data.stages[i].stage), currentIndx)
                    });

                    ++currentIndx;
                }
            }

            $('#dataFileWizard').wizard('addSteps', selStep, panes);

            $('#dataFileWizard').wizard('selectedItem', {
                step: currentIndx - 1
            });

            //move wizard's focus to stage; usually called upon by a refresh action (e.g., value change)
            if (setStageIndx) {

                $('#dataFileWizard').wizard('selectedItem', {
                    step: setStageIndx
                });

                setStageIndx = null;
            }

            refresh_tool_tips();

            //setup fast nav for the stages
            //steps_fast_nav();


        } else if (data.stage.stage) {
            stage_objects[currentIndx] = data.stage.stage;
            $('#dataFileWizard').wizard('addSteps', currentIndx, [
                {
                    badge: ' ',
                    label: '<span class=wiz-title>' + data.stage.stage.title + '</span>',
                    pane: get_pane_content(wizardStagesForms(data.stage.stage), currentIndx)
                }
            ]);

            //give focus to the added step
            $('#dataFileWizard').wizard('selectedItem', {
                step: currentIndx
            });

            refresh_tool_tips();

        } else {
            if (stepIntercept) {
                $('#dataFileWizard').wizard('selectedItem', {
                    step: $('#dataFileWizard').wizard('selectedItem').step + 1
                });
            }

            refresh_tool_tips();
        }

        //refresh tooltips
        refresh_tool_tips();

    } //end of func

    function get_pane_content(stage_content, currentIndx) {
        var stageHTML = $('<div/>', {
            id: "stage-controls-div-" + currentIndx
        });

        //'apply to all', alert trigger controls, and description context message

        var panelGroup = $('<div/>', {
            class: "panel-group wizard-message-panel",
            id: "alert_placeholder_" + currentIndx
        });

        stageHTML.append(panelGroup);

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

        var showApplyTo = "";

        if (stage_objects[currentIndx].is_singular_stage) {
            spanMessage = $('<span/>', {
                html: "<strong>This description will apply to all items in the description bundle</strong>"
            });

            showApplyTo = " display: none;";
        }

        var spanInput = $('<span/>', {
            style: "font-weight: bold; margin-left: 5px;" + showApplyTo,
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
            class: "panel panel-copo-data",
            style: "margin-top: 5px; font-size: 12px;"
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

        var formButton = $('<button/>',
            {
                id: "apply_to_btn_" + currentIndx,
                class: "apply-to-selected-btn btn btn-sm btn-primary",
                html: "Apply to selected items in bundle",
                "data-stage-indx": currentIndx
            });

        formDiv.append(formCtrl).append(formButton);

        //description bundle
        var descriptionBundlePanel = $('<div/>', {
            class: "panel panel-copo-data",
            style: "margin-top: 25px; font-size: 12px;"
        });

        stageHTML.append(descriptionBundlePanel);

        var descriptionBundlePanelBody = $('<div/>', {
            class: "panel-body"
        });

        descriptionBundlePanel.append(descriptionBundlePanelBody);

        var descriptionBundleTableHTML = "";
        descriptionBundleTableHTML += '<table id="description_target_table_' + currentIndx + '" class="display copo-datatable copo-table-header" cellspacing="0" width="100%">';
        descriptionBundleTableHTML += '<thead><tr><th></th><th>Description Bundle</th><th>&nbsp;</th>';
        descriptionBundleTableHTML += '</tr> </thead></table>';

        descriptionBundlePanelBody.html(descriptionBundleTableHTML);

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
        //decommission wizard
        $('#dataFileWizard').wizard('removeSteps', 1, currentIndx + 1);
        $('#dataFileWizard').hide();

        descriptionBundle = []; //clear bundle
        descriptionToken = "";//discard description token
        stage_objects = {}; //clear stage objects

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
        onTheFlyElem.empty();

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

        var auto_fields = JSON.stringify(form_values);

        if (auto_fields == '{}') {
            return false;
        }

        return {
            'request_action': 'save_stage_data',
            'description_token': descriptionToken,
            'auto_fields': auto_fields,
            'description_targets': JSON.stringify(descriptionBundle),
            'description_bundle': JSON.stringify(descriptionBundle)
        };

    }

    //trigger save action before navigating back a stage
    function before_step_back(proposedState) {
        $('#dataFileWizard').wizard('selectedItem', {
            step: proposedState
        });

        //stop execution
        if (1 == 1) {
            return false;
        }


        var stage_data = collate_stage_data();
        if (!stage_data) {//if no data, just go ahead and display stage
            $('#dataFileWizard').wizard('selectedItem', {
                step: proposedState
            });
        } else {
            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: stage_data,
                success: function (data) {
                    //update batch with data
                    if (data.targets_data) {
                        refresh_targets_data(data.targets_data);
                    }

                    $('#dataFileWizard').wizard('selectedItem', {
                        step: proposedState
                    });
                },
                error: function () {
                    alert("Couldn't save some entries!");
                }
            });
        }
    }

    function do_undescribe_confirmation(targetIds) {
        //Impose number of constraints here...
        //1. items currently being described
        //2. items already submitted? not sure of this, relaxed for the time being

        var candidates = [];
        targetIds.forEach(function (item) {
            if (!isIn_descriptionBundle_Id(item)) {
                candidates.push(item);
            }
        });

        if (candidates.length == 0) {
            return false;
        }

        var dialog = new BootstrapDialog({
            buttons: [
                {
                    label: 'Cancel',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                },
                {
                    label: 'Discard',
                    cssClass: 'btn-danger',
                    action: function (dialogRef) {
                        dialogRef.close();

                        var request_params = {
                            'task': 'un_describe',
                            'datafile_ids': JSON.stringify(candidates)
                        };

                        $.ajax({
                            url: copoVisualsURL,
                            type: "POST",
                            headers: {'X-CSRFToken': csrftoken},
                            data: request_params,
                            success: function (data) {
                                update_itemMetadata_flag();
                            },
                            error: function () {
                                alert("Couldn't update metadata for targets!");
                            }
                        });
                    }
                }
            ]
        });

        dialog_display(dialog, "Discard Description", wizardMessages.delete_description_message.text, "danger");
    }

    function add_to_batch(batchTargets, silence) {
        // validate items in batchTargets before adding them.
        // one reason is to avoid duplication of items in the description bundle.
        // but also, can the items be bundled together (e.g., going to same repo)?
        // what of inheriting metadata from already existing bundle items?

        // one can also 'silence' if you are only refreshing the wizard without necessarily
        // altering items in the bundle. if silence = false, then all validation steps will be performed/enforced
        // before engaging the description bundle


        var candidates = [];
        batchTargets.forEach(function (item) {
            if (!isIn_descriptionBundle(item)) {
                candidates.push(item);
            }
        });

        if (candidates.length == 0) {
            return false;
        }

        var request_params = {
            'request_action': "validate_bundle_candidates",
            'description_token': descriptionToken,
            'description_targets': JSON.stringify(candidates),
            'description_bundle': JSON.stringify(descriptionBundle)
        };

        var dialogHandle = processing_request_dialog('Validating description targets...');

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: request_params,
            success: function (data) {
                if (data.description_token) {
                    descriptionToken = data.description_token;
                }

                dialogHandle.close();

                if (data.validatation_results.validation_code == "100") {
                    // Targets are compatible, and may be described as a bundle!
                    if (descriptionBundle.length > 0) {
                        candidates.forEach(function (item) {
                            descriptionBundle.push(item);
                        });

                        //update added items with data
                        refresh_targets_data(data.validatation_results.extra_information.candidates_data);

                    } else {
                        if (candidates.length > 1) {
                            if (silence) {
                                descriptionBundle = candidates;
                                //update added items with data
                                refresh_targets_data(data.validatation_results.extra_information.candidates_data);
                                do_post_stage_retrieval(data);
                                refresh_batch_display();

                            } else {
                                var dialog = new BootstrapDialog({
                                    buttons: [
                                        {
                                            label: 'Cancel',
                                            action: function (dialogRef) {
                                                descriptionToken = null;
                                                dialogRef.close();
                                            }
                                        },
                                        {
                                            label: 'Continue',
                                            cssClass: 'btn-primary',
                                            action: function (dialogRef) {
                                                descriptionBundle = candidates;
                                                //update added items with data
                                                refresh_targets_data(data.validatation_results.extra_information.candidates_data);
                                                do_post_stage_retrieval(data);
                                                refresh_batch_display();
                                                dialogRef.close();
                                            }
                                        }
                                    ]
                                });

                                dialog_display(dialog, "Description Information", wizardMessages.confirm_bundling_action.text, "info");
                            }

                        } else {
                            //set bundle to candidates
                            descriptionBundle = candidates;
                            refresh_targets_data(data.validatation_results.extra_information.candidates_data);
                            do_post_stage_retrieval(data);
                            refresh_batch_display();
                        }
                    }

                } else if (data.validatation_results.validation_code == "101") {
                    //some candidates are ahead of others! inherit metadata?

                    var dialog = new BootstrapDialog({
                        buttons: [
                            {
                                label: 'No ',
                                action: function (dialogRef) {
                                    descriptionToken = null;
                                    dialogRef.close();
                                }
                            },
                            {
                                label: 'Yes ',
                                cssClass: 'btn-primary',
                                action: function (dialogRef) {
                                    var request_action = "inherit_metadata";
                                    if (descriptionBundle.length == 0) {
                                        request_action = "inherit_metadata_refresh";
                                    }

                                    $.ajax({
                                        url: wizardURL,
                                        type: "POST",
                                        headers: {'X-CSRFToken': csrftoken},
                                        data: {
                                            'request_action': request_action,
                                            'target_id': data.validatation_results.extra_information.target.recordID,
                                            'description_token': descriptionToken,
                                            'description_targets': JSON.stringify(candidates),
                                            'description_bundle': JSON.stringify(candidates)
                                        },
                                        success: function (data) {
                                            if (descriptionBundle.length > 0) {
                                                candidates.forEach(function (item) {
                                                    descriptionBundle.push(item);
                                                });

                                                //update added items with data
                                                if (data.targets_data) {
                                                    refresh_targets_data(data.targets_data);
                                                }

                                            } else {
                                                descriptionBundle = candidates;
                                                do_post_stage_retrieval(data);
                                            }

                                            refresh_batch_display();

                                            dialogRef.close();
                                        },
                                        error: function () {
                                            alert("Couldn't inherit metadata!");
                                            return '';
                                        }
                                    });
                                }
                            }
                        ]
                    });

                    var dialog_message = wizardMessages.inherit_metadata_message.text;
                    dialog_message += '<div class="radio wizard-alert-radio">' + show_description_metadata(data.validatation_results.extra_information.summary) + '</div>';

                    dialog_display(dialog, "Description Information", dialog_message, "warning");

                } else if (data.validatation_results.validation_code == "102") {
                    var dialog = new BootstrapDialog({
                        buttons: [
                            {
                                label: 'OK',
                                cssClass: 'btn-primary',
                                action: function (dialogRef) {
                                    descriptionToken = null;
                                    dialogRef.close();
                                }
                            }
                        ]
                    });

                    dialog_display(dialog, "Description Information", wizardMessages.incompatible_metadata_message.text, "danger");
                } else if (data.validatation_results.validation_code == "103") {
                    //some candidates are ahead of items in the description bundle! inherit metadata?

                    var dialog = new BootstrapDialog({
                        buttons: [
                            {
                                label: 'No ',
                                action: function (dialogRef) {
                                    descriptionToken = null;
                                    dialogRef.close();
                                }
                            },
                            {
                                label: 'Yes ',
                                cssClass: 'btn-primary',
                                action: function (dialogRef) {
                                    candidates.forEach(function (item) {
                                        descriptionBundle.push(item);
                                    });

                                    var tempDescriptionBundle = descriptionBundle;

                                    $.ajax({
                                        url: wizardURL,
                                        type: "POST",
                                        headers: {'X-CSRFToken': csrftoken},
                                        data: {
                                            'request_action': "inherit_metadata_refresh",
                                            'target_id': data.validatation_results.extra_information.target.recordID,
                                            'description_token': descriptionToken,
                                            'description_targets': JSON.stringify(descriptionBundle),
                                            'description_bundle': JSON.stringify(descriptionBundle)
                                        },
                                        success: function (data) {
                                            clear_wizard();
                                            descriptionBundle = tempDescriptionBundle;
                                            do_post_stage_retrieval(data);
                                            refresh_batch_display();

                                            dialogRef.close();
                                        },
                                        error: function () {
                                            alert("Couldn't inherit metadata!");
                                            return '';
                                        }
                                    });
                                }
                            }
                        ]
                    });

                    var dialog_message = wizardMessages.inherit_metadata_103_message.text;
                    dialog_message += '<div class="radio wizard-alert-radio">' + show_description_metadata(data.validatation_results.extra_information.summary) + '</div>';

                    dialog_display(dialog, "Description Information", dialog_message, "warning");
                }


                refresh_batch_display();
            },
            error: function () {
                alert("Couldn't retrieve data for targets!");
            }
        });
    }

    function show_description_metadata(data) {
        var descriptionDiv = $('<div></div>');

        for (var j = 0; j < data.length; ++j) {
            var Ddata = data[j];

            var i = 0; //need to change this to reflect stage index...

            var level1Div = $('<div/>', {
                style: 'padding: 5px; border: 1px solid #ddd; border-radius:2px; margin-bottom:3px;'
            });

            var level2Anchor = $('<a/>', {
                class: "review-to-stage",
                "data-stage-indx": i,
                "data-sel-target": '',
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

        if (data.length) {
            descriptionHtml = descriptionDiv.html();
        }

        var descriptionInfoPanel = $('<div/>', {
            class: "panel panel-info",
            style: 'margin-top:1px;'
        });

        var descriptionInfoPanelPanelHeading = $('<div/>', {
            class: "panel-heading",
            style: "background-image: none;",
            html: "Description Metadata"
        });

        var descriptionInfoPanelPanelBody = $('<div/>', {
            class: "panel-body",
            style: "overflow:scroll",
            html: descriptionHtml
        });

        descriptionInfoPanel.append(descriptionInfoPanelPanelHeading).append(descriptionInfoPanelPanelBody);

        return $('<div></div>').append(descriptionInfoPanel).html();
    }

    function isIn_descriptionBundle(candidate) {
        var isInBundle = false;

        for (var i = 0; i < descriptionBundle.length; ++i) {
            if (descriptionBundle[i].recordID == candidate.recordID) {
                isInBundle = true;
                break;
            }
        }

        return isInBundle;
    }

    function isIn_descriptionBundle_Id(Id) {
        var isInBundle = false;

        for (var i = 0; i < descriptionBundle.length; ++i) {
            if (descriptionBundle[i].recordID == Id) {
                isInBundle = true;
                break;
            }
        }

        return isInBundle;
    }

    function bundle_without_data() {
        var bundle = [];

        descriptionBundle.forEach(function (item) {
            var option = {};
            option["recordLabel"] = item.recordLabel;
            option["recordID"] = item.recordID;
            bundle.push(option);

        });

        return bundle;
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
        if (task == "describe" && records.length > 0) {
            //remove highlight from selected rows
            table.rows('.selected').deselect();

            //append to batch
            var batchTargets = [];
            for (var i = 0; i < records.length; ++i) {
                var item = records[i];
                var option = {};
                option["recordLabel"] = item[0];
                option["recordID"] = item[item.length - 1];
                option["attributes"] = {};
                batchTargets.push(option);
            }

            add_to_batch(batchTargets, false);


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


    function do_deque(item) {//removes item from the batch
        var position = -1;

        for (i = 0; i < descriptionBundle.length; ++i) {
            if (item.recordID == descriptionBundle[i].recordID) {
                position = i;
                break;
            }
        }

        if (position != -1) {
            descriptionBundle.splice(position, 1);
        }

        //refresh description batch display
        refresh_batch_display();

    } //end of function


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
                            var batchTargets = [];
                            descriptionBundle.forEach(function (item) {
                                batchTargets.push(item);
                            });
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
                                        setStageIndx = $('#dataFileWizard').wizard('selectedItem').step;
                                        add_to_batch(batchTargets, true);
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

        var triggerMessage = '';

        try {
            triggerMessage = formElem.trigger.message;
        }
        catch (err) {
            ;
        }

        dialog_display(dialog, messageTitle, triggerMessage, "warning");
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
                    element_value_change(formElem, previousValue, formElem.label + " Change");
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
                    element_value_change(formElem, previousValue, formElem.label + " Change");
                });
        },
        growth_facility_change: function (formElem) {
            var previousValue = null;
            $(document)
                .off("focus", "#" + formElem.id)
                .on("focus", "#" + formElem.id, function () {
                    previousValue = this.value;
                });
            $(document)
                .off(formElem.trigger.type, "#" + formElem.id)
                .on(formElem.trigger.type, "#" + formElem.id, function () {
                    element_value_change(formElem, previousValue, formElem.label + " Change");
                });
        },
        get_nutrient_controls: function (formElem) {
            var previousValue = null;
            $(document)
                .off("focus", "#" + formElem.id)
                .on("focus", "#" + formElem.id, function () {
                    previousValue = this.value;
                });
            $(document)
                .off(formElem.trigger.type, "#" + formElem.id)
                .on(formElem.trigger.type, "#" + formElem.id, function () {
                    element_value_change(formElem, previousValue, formElem.label + " Change");
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
            '<div style="margin-top: 10px; max-width: 100%; overflow-x: auto;">' +
            '<table id="description_summary_table" class="display copo-datatable copo-table-header" cellspacing="0" width="100%">' +
            '<thead><tr><th></th><th>File</th><th>Rating</th>' +
            '</tr> </thead></table>' +
            '</div></div>'
        };
    }

    function set_summary_data() {

        //set up data source
        var dtd = [];

        var datafile_ids = []; //for metadata rating

        descriptionBundle.forEach(function (item) {
            var option = {};
            option["target"] = item.recordLabel;
            option["target_id"] = item.recordID;
            option["attributes"] = item.attributes;
            dtd.push(option);

            datafile_ids.push(item.recordID);
        });

        //set data
        var table = null;
        if ($.fn.dataTable.isDataTable('#description_summary_table')) {
            //if table instance already exists, then do refresh
            table = $('#description_summary_table').DataTable();
        }

        if (table) {
            //clear old, set new data
            table.clear().draw();
            table.rows.add(dtd);
            table.columns.adjust().draw();
        } else {
            table = $('#description_summary_table').DataTable({
                "data": dtd,
                "columns": [
                    {
                        "className": 'summary-details-control',
                        "orderable": false,
                        "data": null,
                        "defaultContent": ''
                    },
                    {"data": "target"},
                    {
                        "orderable": false,
                        data: "target_id",
                        render: function (rdata) {
                            var metadataClass = 'itemMetadata-flag-ind poor';
                            var metadataRating = 'None';

                            var headingRowIconSpan = $('<span/>', {
                                id: "summary_tbl_rating_span_" + rdata,
                                class: "pull-right " + metadataClass,
                                style: "width: 15px; height: 15px; border: 1px solid #ddd;"
                            });

                            var headingRowIconDiv = $('<div/>', {
                                id: "summary_tbl_rating_div_" + rdata,
                                class: "itemMetadata-flag",
                                title: "Rating level = " + metadataRating
                            }).append(headingRowIconSpan);


                            return $('<div></div>').append(headingRowIconDiv).html();

                        }
                    }
                ]
            });


            // handle opening and closing summary details
            $('#description_summary_table tbody').on('click', 'td.summary-details-control', function () {
                var tr = $(this).closest('tr');
                var row = table.row(tr);

                if (row.child.isShown()) {
                    // This row is already open - close it
                    row.child.hide();
                    tr.removeClass('shown');
                }
                else {
                    // expand row
                    var contentHtml = "<div style='text-align: center'><i class='fa fa-spinner fa-pulse fa-2x'></i></div>";
                    row.child(contentHtml).show();
                    tr.addClass('shown');

                    $.ajax({
                        url: copoVisualsURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: {
                            'task': 'description_summary',
                            'component': component,
                            'target_id': row.data().target_id
                        },
                        success: function (data) {
                            row.child(summary_format(data, row.data().target_id)).show();
                        },
                        error: function () {
                            alert("Couldn't retrieve description attributes!");
                            return '';
                        }
                    });
                }
            });
        }

        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'task': 'metadata_ratings',
                'component': component,
                'datafile_ids': JSON.stringify(datafile_ids)
            },
            success: function (data) {
                if (data.metadata_ratings) {

                    var currentMetadataRating = data.metadata_ratings;

                    for (var i = 0; i < currentMetadataRating.length; ++i) {
                        if (currentMetadataRating[i].item_rating.hasOwnProperty("rating_level")) {
                            var metadataClass = "itemMetadata-flag-ind " + currentMetadataRating[i].item_rating.rating_level + " meta-active";
                            var metadataRating = currentMetadataRating[i].item_rating.rating_level;
                            if ($("#summary_tbl_rating_span_" + currentMetadataRating[i].item_id).length) {
                                $("#summary_tbl_rating_span_" + currentMetadataRating[i].item_id).attr("class", "pull-right " + metadataClass);
                            }

                            if ($("#summary_tbl_rating_div_" + currentMetadataRating[i].item_id).length) {
                                $("#summary_tbl_rating_div_" + currentMetadataRating[i].item_id).prop("title", "Rating level = " + metadataRating);
                            }
                        }
                    }

                }
            },
            error: function () {
                alert("Couldn't resolve metadata ratings!");
            }
        });


    }//end of func

    function summary_format(data, target_id) {
        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index, which, in this context is the summary (final) stage

        var descriptionDiv = $('<div></div>');
        for (var i = 1; i < activeStageIndx; ++i) {
            if ($("#wizard_form_" + i).length) {
                var currentStage = $('#wizard_form_' + i).find("#current_stage").val();
                if (currentStage.length) {

                    for (var j = 0; j < data.description.length; ++j) {
                        var Ddata = data.description[j];

                        if (Ddata.ref == currentStage) {
                            var level1Div = $('<div/>', {
                                style: 'padding: 5px; border: 1px solid #ddd; border-radius:2px; margin-bottom:3px;'
                            });

                            var level2Anchor = $('<a/>', {
                                class: "review-to-stage",
                                title: "Jump to stage",
                                "data-stage-indx": i,
                                "data-sel-target": target_id,
                                style: "cursor: pointer; cursor: hand;",
                                html: Ddata.title
                            });

                            var level2Div = $('<div/>', {
                                style: 'padding-bottom: 7px;'
                            }).append($('<span></span>').append(level2Anchor));

                            level1Div.append(level2Div);

                            for (var k = 0; k < Ddata.data.length; ++k) {
                                var Mdata = Ddata.data[k];

                                var mDataDiv = $('<div/>', {
                                    style: 'padding-bottom: 7px;'
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
                                level1Div.append(mDataDiv);

                            }

                            descriptionDiv.append(level1Div);
                            break;

                        }
                    }

                }
            }
        }

        var descriptionHtml = "No description!";

        if (data.description.length) {
            descriptionHtml = descriptionDiv.html();
        }

        var descriptionInfoPanel = $('<div/>', {
            class: "panel panel-default",
            style: 'margin-top:1px;'
        });

        var descriptionInfoPanelPanelHeading = $('<div/>', {
            class: "panel-heading",
            style: "background-image: none;",
            html: "Description Summary"
        });

        var descriptionInfoPanelPanelBody = $('<div/>', {
            class: "panel-body",
            style: "overflow:scroll",
            html: descriptionHtml
        });

        descriptionInfoPanel.append(descriptionInfoPanelPanelHeading).append(descriptionInfoPanelPanelBody);

        return $('<div></div>').append(descriptionInfoPanel).html();

    } //end of func


    function refresh_batch_display() {
        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index

        //clear stage message
        onTheFlyElem.empty();

        //get last stage index
        var lastElementIndx = $('.steps li').last().index() + 1;

        //last stage, i.e., the summary stage, shouldn't come in here...

        if (activeStageIndx >= lastElementIndx) {
            return false;
        }

        //if no stage...
        if (activeStageIndx == -1) {
            return false;
        }

        //set stage message
        if (stage_objects && stage_objects[activeStageIndx].hasOwnProperty("message")) {
            onTheFlyElem.empty();

            if (stage_objects[activeStageIndx].message) {
                var attributesPanel = $('<div/>', {
                    class: "panel panel-info",
                    style: "margin-top: 5px; font-size: 12px;"
                });

                var attributesPanelHeading = $('<div/>', {
                    class: "panel-heading",
                    style: "background-image: none; font-weight: 600;",
                    html: stage_objects[activeStageIndx].title
                });

                attributesPanel.append(attributesPanelHeading);


                var attributesPanelBody = $('<div/>', {
                    class: "panel-body"
                });

                attributesPanelBody.append('<span style="line-height: 1.5;">' + stage_objects[activeStageIndx].message + '</span>');

                attributesPanel.append(attributesPanelBody);

                onTheFlyElem.append(attributesPanel);
            }
        }

        //set up data source
        var dtd = [];

        descriptionBundle.forEach(function (item) {
            var option = {};
            option["target"] = [item.recordLabel, item.recordID];
            option["target_id"] = item.recordID;
            option["attributes"] = item.attributes;
            option["buttons"] = item.recordID;
            dtd.push(option);

        });

        var buttons = [];
        buttons.push({
            'text': 'Remove from description bundle',
            'className': 'wiz-batch-item btn btn-danger',
            'iconClass': 'fa fa-trash-o',
            'btnAction': 'delete'
        });

        var colDefs = [
            {
                targets: -1,
                data: null,
                searchable: false,
                orderable: false,
                render: function (rdata) {
                    var rndHTML = "";

                    var bTns = buttons;
                    rndHTML = '<span style="white-space: nowrap;">';
                    for (var i = 0; i < bTns.length; ++i) {
                        rndHTML += '<a data-action-target="row" data-record-action="'
                            + bTns[i].btnAction + '" data-record-id="'
                            + rdata
                            + '" data-toggle="tooltip" style="display: inline-block; white-space: normal;" title="'
                            + bTns[i].text + '" class="' + bTns[i].className + ' btn-xs"><i class="'
                            + bTns[i].iconClass + '"> </i><span></span></a>&nbsp;';
                    }
                    rndHTML += '</span>';

                    return rndHTML;
                }
            },
            {
                targets: 1,
                data: null,
                render: function (rdata) {
                    var rndHTML = rdata[0] + '<span data-toggle="tooltip" ' +
                        'style="white-space: nowrap; display: none;" ' +
                        'class="inDescription-flag-1" ' +
                        'title="Has metadata" ' +
                        'data-record-id="' + rdata[1] + '">' +
                        '<i style="padding-left: 5px;" class="fa fa-tags"></i><span>';
                    return rndHTML;
                }

            }
        ];

        //set data
        var table = null;
        var filterDivObject = null;
        if ($.fn.dataTable.isDataTable('#description_target_table_' + activeStageIndx)) {
            //if table instance already exists, then do refresh
            table = $('#description_target_table_' + activeStageIndx).DataTable();
        }

        if (table) {
            //clear old, set new data
            table.clear().draw();
            table.rows.add(dtd);
            table.columns.adjust().draw();
        } else {
            var tableElem = $('#description_target_table_' + activeStageIndx);
            var table = tableElem.DataTable({
                "data": dtd,
                "lengthChange": false,
                buttons: [
                    'selectAll',
                    'selectNone'
                ],
                language: {
                    buttons: {
                        selectAll: "Select all",
                        selectNone: "Deselect all"
                    },
                    select: {
                        rows: {
                            _: "Current description will apply to %d files in bundle ",
                            0: "Click a row to select it",
                            1: "Current description will apply to 1 file in bundle"
                        }
                    }
                },
                "columns": [
                    {
                        "className": 'summary-details-control',
                        "orderable": false,
                        "data": null,
                        "defaultContent": ''
                    },
                    {"data": "target"},
                    {"data": "buttons"}
                ],
                "fnDrawCallback": function (oSettings) {
                    refresh_tool_tips();


                    $('.dataTables_filter').each(function () {
                        if ($(this).attr("id") == 'description_target_table_' + activeStageIndx + "_filter") {
                            filterDivObject = $(this);
                            return false;
                        }
                    });

                    // refresh show hide stage controls
                    show_hide_stage_ctrl(get_apply_check_state(activeStageIndx), activeStageIndx);


                },
                columnDefs: colDefs,
                //scrollY: "200px",
                scrollCollapse: true,
                select: {
                    style: 'multi'
                },
                dom: 'r<"top description-bundle-table"i>ftp'
            });

            table
                .buttons()
                .nodes()
                .each(function (value) {
                    $(this).addClass(' btn-sm');
                });

            $(table.buttons().container()).insertBefore(filterDivObject);


            // handle opening and closing summary details
            $('#description_target_table_' + activeStageIndx + ' tbody').on('click', 'td.summary-details-control', function () {
                var tr = $(this).closest('tr');
                var row = table.row(tr);

                $('#description_target_table_' + activeStageIndx + ' tbody').find('tr').each(function () {

                    var row_all = table.row($(this));

                    if (row_all.child.isShown()) {
                        // This row is already open - close it
                        if (row_all.data().target_id != row.data().target_id) {
                            row_all.child('');
                            row_all.child.hide();
                            $(this).removeClass('shown');
                        }
                    }
                });

                if (row.child.isShown()) {
                    // This row is already open - close it
                    row.child('');
                    row.child.hide();
                    tr.removeClass('shown');
                }
                else {
                    // expand row
                    var contentHtml = "<div style='text-align: center'><i class='fa fa-spinner fa-pulse fa-2x'></i></div>";
                    row.child(contentHtml).show();
                    tr.addClass('shown');

                    var descripTarget;
                    descriptionBundle.forEach(function (item) {
                        if (item.recordID == row.data().target_id) {
                            descripTarget = item;
                        }
                    });

                    var request_params = {
                        'request_action': 'get_item_stage_display',
                        'component': component,
                        'stage_id': stage_objects[activeStageIndx].ref,
                        'description_token': descriptionToken,
                        'description_targets': JSON.stringify([descripTarget]),
                        'description_bundle': JSON.stringify([])
                    };

                    var requestURL = wizardURL;
                    var appliedToAllFlag = false;

                    //only show metadata, without the form, when applying to all
                    if (get_apply_check_state(activeStageIndx)) {
                        request_params = {
                            'task': 'description_summary',
                            'component': component,
                            'target_id': row.data().target_id
                        };

                        requestURL = copoVisualsURL;

                        appliedToAllFlag = true;
                    }

                    $.ajax({
                        url: requestURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: request_params,
                        success: function (data) {
                            //display stage metadata for item

                            contentHtml = '';

                            if (!appliedToAllFlag) {
                                var applyToItemBtn = '<button type="button" data-stage-indx="' + activeStageIndx + '" data-description-target="' + row.data().target_id + '"  class="apply-to-item-btn btn btn-sm btn-primary">Apply to item</button><span style="margin-left: 4px; font-weight: 600;" class="text-default">[CTRL + ENTR]</span>';
                                if (stage_objects[activeStageIndx].is_singular_stage || get_apply_check_state(activeStageIndx)) {
                                    applyToItemBtn = '';
                                }

                                contentHtml += '<div class="panel panel-default" style="margin-top: 5px;">';
                                contentHtml += '<div class="panel-heading" style="background-image: none;"><strong></strong></div>';
                                contentHtml += '<div class="panel-body">';
                                contentHtml += '<div class="item-form-controls"><form class="wizard-items-form" data-description-target="' + row.data().target_id + '" data-stage-indx="' + activeStageIndx + '" role="form" id="wizard_item_form_' + activeStageIndx + '">';
                                contentHtml += wizardStagesForms(data.stage.stage).html();
                                contentHtml += '</form>';
                                contentHtml += '</div>';
                                contentHtml += '</div>';
                                contentHtml += '<div class="panel-footer">';
                                contentHtml += applyToItemBtn;
                                contentHtml += '</div>';
                                contentHtml += '</div>';

                                row.child(contentHtml).show();

                                $('html, body').animate({
                                    scrollTop: $("#wizard_item_form_" + activeStageIndx).offset().top
                                }, 100);


                                $(".item-form-controls").find(".form-group").each(function () { //makes for a better layout
                                    $(this).removeClass("form-group");
                                    $(this).css("margin-bottom", "10px");
                                });


                                refresh_tool_tips();

                                //ontology autocomplete
                                auto_complete();
                            } else {

                                if (data.description.length) {
                                    for (var i = 0; i < data.description.length; ++i) {
                                        if (data.description[i].ref == stage_objects[activeStageIndx].ref) {
                                            var Ddata = data.description[i].data;
                                            for (var j = 0; j < Ddata.length; ++j) {
                                                contentHtml += '<tr>';
                                                contentHtml += '<td>' + Ddata[j].label + '</td>';
                                                contentHtml += '<td>' + Ddata[j].data + '</td>';
                                                contentHtml += '</tr>';
                                            }
                                            break;
                                        }
                                    }

                                }

                                if (!contentHtml) {
                                    contentHtml += '<tr><td>No recorded metadata!<td></tr>';
                                }

                                row.child(contentHtml).show();
                            }

                        },
                        error: function () {
                            alert("Couldn't retrieve item's metadata!");
                        }
                    });
                }
            });

            //set up description-apply checkbox
            $("[name='apply-scope-chk-" + activeStageIndx + "']").bootstrapSwitch({});

            $("[name='apply-scope-chk-" + activeStageIndx + "']").on('switchChange.bootstrapSwitch', function (event, state) {
                //deselect any selected rows
                table.rows('.selected').deselect();

                //close all expanded rows' metadata
                $('#description_target_table_' + activeStageIndx + ' tbody').find('tr').each(function () {

                    var row_all = table.row($(this));

                    if (row_all.child.isShown()) {
                        row_all.child('');
                        row_all.child.hide();
                        $(this).removeClass('shown');
                    }
                });

                if (!state) {//when the apply-to button is set to false, reset form
                    var request_params = {
                        'request_action': 'get_item_stage_display',
                        'stage_id': stage_objects[activeStageIndx].ref,
                        'description_token': descriptionToken
                    };

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: request_params,
                        success: function (data) {
                            //display stage
                            $('#wizard_form_' + activeStageIndx).empty();
                            $('#wizard_form_' + activeStageIndx).append(wizardStagesForms(data.stage.stage));

                            refresh_tool_tips();

                            //ontology autocomplete
                            auto_complete();
                        },
                        error: function () {
                            alert("Couldn't retrieve stage information!");
                        }
                    });
                } else {
                    var request_params = {
                        'request_action': 'is_same_metadata',
                        'description_token': descriptionToken,
                        'stage_ref': stage_objects[activeStageIndx].ref,
                        'description_targets': JSON.stringify(bundle_without_data())
                    };

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {'X-CSRFToken': csrftoken},
                        data: request_params,
                        success: function (data) {
                            if (data.state) {
                                var request_params = {
                                    'request_action': 'get_item_stage_display',
                                    'stage_id': stage_objects[activeStageIndx].ref,
                                    'description_token': descriptionToken,
                                    'description_targets': JSON.stringify([descriptionBundle[0]])
                                };

                                $.ajax({
                                    url: wizardURL,
                                    type: "POST",
                                    headers: {'X-CSRFToken': csrftoken},
                                    data: request_params,
                                    success: function (data) {
                                        //display stage
                                        $('#wizard_form_' + activeStageIndx).empty();
                                        $('#wizard_form_' + activeStageIndx).append(wizardStagesForms(data.stage.stage));

                                        refresh_tool_tips();

                                        //ontology autocomplete
                                        auto_complete();
                                    },
                                    error: function () {
                                        alert("Couldn't retrieve stage information!");
                                    }
                                });
                            }
                        },
                        error: function () {
                            alert("Couldn't retrieve data for targets!");
                        }
                    });
                }

                //trigger alert
                if (state) {
                    set_stage_alerts(wizardMessages.apply_to_all_message, activeStageIndx);
                } else {
                    set_stage_alerts(wizardMessages.description_bundle_select_message, activeStageIndx);
                }

                show_hide_stage_ctrl(state, activeStageIndx);
            });
        }

        //'disable' row selection for cases where is-singular-stage and apply-to-all
        if (table) {

            table.on('select', function (e, dt, type, indexes) {
                var selectedRows = table.rows({selected: true}).count();

                //apply to button toggle enable
                if ($('#apply_to_btn_' + activeStageIndx).is(":visible")) {
                    if (selectedRows > 0) {
                        $('#apply_to_btn_' + activeStageIndx).prop('disabled', false);
                    } else {
                        $('#apply_to_btn_' + activeStageIndx).prop('disabled', true);
                    }
                }
            });

            table.on('deselect', function (e, dt, type, indexes) {
                var selectedRows = table.rows({selected: true}).count();

                //apply to button toggle enable
                if ($('#apply_to_btn_' + activeStageIndx).is(":visible")) {
                    if (selectedRows > 0) {
                        $('#apply_to_btn_' + activeStageIndx).prop('disabled', false);
                    } else {
                        $('#apply_to_btn_' + activeStageIndx).prop('disabled', true);
                    }
                }

                //'disable' row selection for cases where is-singular-stage and apply-to-all
                var allRows = table.rows().count();

                //row selection
                if ((stage_objects[activeStageIndx].is_singular_stage || get_apply_check_state(activeStageIndx))
                    && (selectedRows != allRows)) {
                    table.rows('.selected').deselect();
                    table.rows().select();
                }

            });
        }

        show_hide_stage_ctrl(get_apply_check_state(activeStageIndx), activeStageIndx);

    } //end of func

    function save_bundle_item_form(activeStageIndx, descriptionTarget) {
        var deTargs = [];

        descriptionBundle.forEach(function (item) {
            if (descriptionTarget == item.recordID) {
                deTargs.push(item);
                return false;
            }
        });


        //get form elements for item
        var form_values = Object();

        $('#wizard_item_form_' + activeStageIndx).find(":input").each(function () {
            form_values[this.id] = $(this).val();
        });

        var auto_fields = JSON.stringify(form_values);

        if (auto_fields == '{}') {
            return false;
        }

        var request_params = {
            'request_action': 'save_stage_data',
            'description_token': descriptionToken,
            'auto_fields': auto_fields,
            'description_targets': JSON.stringify(deTargs),
            'description_bundle': JSON.stringify(descriptionBundle)
        };

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: request_params,
            success: function (data) {
                //refresh bundle
                if (data.targets_data) {
                    refresh_targets_data(data.targets_data);

                    //refresh description batch display
                    refresh_batch_display();

                    //get the next item in line
                    if ($.fn.dataTable.isDataTable('#description_target_table_' + activeStageIndx)) {
                        var table = $('#description_target_table_' + activeStageIndx).DataTable();

                        var foundCurrentRow = false;

                        $('#description_target_table_' + activeStageIndx + ' tbody').find('tr').each(function () {
                            var row_ll = table.row($(this));

                            if (row_ll.data()) {
                                if (foundCurrentRow) {
                                    $(this).find('td.summary-details-control').trigger("click");
                                    return false;
                                }

                            }

                            if (row_ll.data()) {
                                if (row_ll.data().target_id == descriptionTarget) {
                                    foundCurrentRow = true;
                                    row_ll.child('');
                                    row_ll.child.hide();
                                    $(this).removeClass('shown');
                                    table.rows('.selected').deselect();
                                }
                            }

                        });

                    }
                }
            },
            error: function () {
                alert("Couldn't save entries!");
            }
        });
    }

    function update_itemMetadata_flag() {
        //function sets/updates metadata flag for datafiles
        var datafile_ids = [];
        $('.itemMetadata-flag').each(function () {
            if ($(this).attr("data-record-id")) {
                datafile_ids.push($(this).attr("data-record-id"));
            }
        });

        if (datafile_ids.length) {
            $.ajax({
                url: copoVisualsURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': 'metadata_ratings',
                    'component': component,
                    'datafile_ids': JSON.stringify(datafile_ids)
                },
                success: function (data) {
                    if (data.metadata_ratings) {
                        for (var i = 0; i < data.metadata_ratings.length; ++i) {
                            $('.itemMetadata-flag').each(function () {
                                if ($(this).attr("data-record-id")) {
                                    var rating_object = data.metadata_ratings[i];
                                    if (rating_object.item_id == $(this).attr("data-record-id")) {
                                        $(this).find(".itemMetadata-flag-ind").removeClass("meta-active");

                                        var metadataDescription = "Couldn't resolve metadata rating!";

                                        if (rating_object.item_rating.hasOwnProperty("rating_level")) {
                                            $(this).find("." + rating_object.item_rating.rating_level).addClass("meta-active");
                                        }

                                        if (rating_object.item_rating.hasOwnProperty("rating_level_description")) {
                                            metadataDescription = rating_object.item_rating.rating_level_description;
                                        }

                                        metadataDescription += '<div style="margin-top: 10px;">Click the <span class="btn btn-info btn-xs"><i class="fa fa-info-circle"> </i></span> button on the right for more details.</div>';


                                        $(this).webuiPopover('destroy');
                                        refresh_webpop($(this), 'Metadata Rating', metadataDescription, {width: 300});

                                        return false;
                                    }
                                }
                            });
                        }
                    }
                },
                error: function () {
                    alert("Couldn't resolve metadata ratings!");
                }
            });
        }
    }

    function refresh_inDescription_flag(activeStageIndx) {
        //reset inDescription flag
        $('.inDescription-flag').each(function () { //main datafile table
            $(this).hide();
        });

        $('.inDescription-flag-1').each(function () {//description bundle
            $(this).hide();
        });

        descriptionBundle.forEach(function (item) {
            //set inDescription flag
            $('.inDescription-flag').each(function () {
                if ($(this).attr("data-record-id") == item.recordID) {
                    $(this).show();
                }
            });
        });

        descriptionBundle.forEach(function (item) {
            $('.inDescription-flag-1').each(function () {
                if ($(this).attr("data-record-id") == item.recordID) {
                    try {
                        if (item["attributes"][stage_objects[activeStageIndx].ref]) {
                            $(this).show();
                        }
                    } catch (err) {

                    }
                }
            });
        });
    }

    function show_hide_stage_ctrl(applyToAll, activeStageIndx) {
        refresh_inDescription_flag(activeStageIndx);

        //get table reference
        var table = null;
        if ($.fn.dataTable.isDataTable('#description_target_table_' + activeStageIndx)) {
            var table = $('#description_target_table_' + activeStageIndx).DataTable();
        }

        //decide which controls to display

        //apply-to-all checkbox flag
        var showChk = true;
        if (descriptionBundle.length <= 1) {
            showChk = false;
        }

        if ((stage_objects[activeStageIndx] && stage_objects[activeStageIndx].is_singular_stage) || applyToAll) {
            if ((stage_objects[activeStageIndx] && stage_objects[activeStageIndx].is_singular_stage)) {
                showChk = false;
            }

            //highlight all items in the bundle
            if (table) {
                table.rows('.selected').deselect();
                table.rows().select();
            }

        }


        if (showChk) {//apply to all check button activated
            $("[name='apply-scope-chk-" + activeStageIndx + "']").bootstrapSwitch('readonly', false);
            if (get_apply_check_state(activeStageIndx)) {
                set_apply_check_state(activeStageIndx);
            }
        } else {
            $("[name='apply-scope-chk-" + activeStageIndx + "']").bootstrapSwitch('state', true);
            $("[name='apply-scope-chk-" + activeStageIndx + "']").bootstrapSwitch('readonly', true);
        }

        if (table) {
            table.buttons().disable();

            $('#apply_to_btn_' + activeStageIndx).hide();
        }

        if (!applyToAll && showChk) {
            if (table) {
                table.buttons().enable();

                $('#apply_to_btn_' + activeStageIndx).show();
                $('#apply_to_btn_' + activeStageIndx).prop('disabled', true);
            }
        }

        new_stage_alert();

    }//end of func

    function new_stage_alert() {
        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index

        //get last stage index
        var lastElementIndx = $('.steps li').last().index() + 1;

        //last stage, i.e., the summary stage, shouldn't come in here...

        if (activeStageIndx >= lastElementIndx) {
            return false;
        }


        if (activeStageIndx == -1) {
            return false;
        }

        if (stage_objects[activeStageIndx].is_singular_stage) {//singular stage
            set_stage_alerts(wizardMessages.singular_stage_message, activeStageIndx);
        } else if (descriptionBundle.length == 1) {//only one item being described
            set_stage_alerts(wizardMessages.singleton_item_alert_message, activeStageIndx);
        } else {
            if (get_apply_check_state(activeStageIndx)) {
                set_stage_alerts(wizardMessages.apply_to_all_message, activeStageIndx);
            } else {
                set_stage_alerts(wizardMessages.description_bundle_select_message, activeStageIndx);
            }
        }

    }


    function set_stage_alerts(message_object, activeStageIndx) {
        var elem = $('#alert_placeholder_' + activeStageIndx);
        var contentHtml = '<i class="fa fa-exclamation-circle fa-3x fa-pull-left copo-icon-info"></i><span class="' + message_object.text_class + '">' + message_object.text + '</span>';
        var footerHtml = '<div style="text-align: right;">';
        footerHtml += '<span style="margin-right: 5px;" title="' + wizardMessages.dismiss_alert_message.text + '" class="btn btn-primary btn-xs close-stage-alert">Dismiss</span>';

        var btnClass = " btn-warning ";
        var alertStatus = "disable";
        var alertHtml = "Disable";
        var alertTitle = wizardMessages.disable_alert_message.text;

        if (silenceAlert) {
            btnClass = "btn-success";
            alertStatus = "enable";
            alertHtml = "Enable";
            alertTitle = wizardMessages.enable_alert_message.text;
        }

        footerHtml += '<span title="' + alertTitle + '" data-alert-status="' + alertStatus + '" class="btn ' + btnClass + ' btn-xs stage-alerts">' + alertHtml + '</span>';
        footerHtml += '</div>';

        elem.find(".panel-body").html(contentHtml);
        elem.find(".panel-footer").html(footerHtml);

        if (silenceAlert) {
            return false;
        }

        elem.find(".collapse").collapse('show');
    }

})//end document ready
