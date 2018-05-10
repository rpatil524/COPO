var wizardMessages;
var currentIndx = 0; //holds index of the current stage
var descriptionBundle = []; //datafiles currently being described
var descriptionToken = null;
var stage_objects = {}; //retains info about rendered stages
var stepIntercept = false; //flag indicates if activation of the last stage of the wizard has been intercepted
var silenceAlert = false; //use to temporary suppress stage alerts
var descriptionWizSummary = {}; //wizard summary stage content
var onGoingDescription = false; //informs wizard state refresh/exit
var displayedMessages = {}; //holds stage messages already displayed
var tabShownStore = Object();
var setTargetStageRef = ''; //if loading batch stages, set current stage to 'setTargetStageRef'


$(document).ready(function () {
    //****************************** Event Handlers Block *************************//


    var cyverse_files = $('#cyverse_file_data').val()
    if (cyverse_files != "") {
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
    if (url.includes('state') && url.includes('code')) {
        // now check for selected_datafile
        if ($('#selected_datafile').val() != '' || $('#selected_datafile').val() != undefined) {
            //alert('ask toni how we can load file ' + $('#selected_datafile').val() + ' into his wizard')
        }
    }


    var csrftoken = $('[name="csrfmiddlewaretoken"]').val();

    var component = "datafile";
    var wizardURL = "/rest/data_wiz/";
    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";
    var samples_from_study_url = "/rest/samples_from_study/"

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


    //review-to-stage
    $(document).on("click", ".review-to-stage", function (event) {
        event.preventDefault();

        $('#dataFileWizard').wizard('selectedItem', {
            step: $(this).attr("data-stage-indx")
        });
    });

    //refresh metadata rating after table redraw
    $('body').on('posttablerefresh', function (event) {
        update_itemMetadata_flag();
        refresh_inDescription_flag();
    });

    //stop automatic form submit
    $(document).on("submit", "form", function (event) {
        event.preventDefault();

        return false;
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
        })
    })


    //form control events
    $(document).on('change', '.copo-select-control', function (e) {
        do_handle_select_events(e);
    });


    //******************************* wizard events *******************************//

    //description tab loading event
    $('#copo-datafile-tabs.nav-tabs a').on('shown.bs.tab', function (event) {
        if ($(event.target).attr("href") == "#descriptionWizardComponent") {
            if (tabShownStore) {
                if (tabShownStore.method == "do_post_stage_retrieval2") {
                    $("#description_panel").css("display", "block");
                    do_post_stage_retrieval2(tabShownStore.data);

                    tabShownStore = null;
                }
            }
        }
    });


    // retrieve wizard messages
    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
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


    //handle event for exiting current description...this will retain already added metadata
    $('#exit_act').on('click', function (event) {
        //confirm user decision

        BootstrapDialog.show({
            title: "Exit Description",
            message: wizardMessages.exit_wizard_message.text,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_WARNING,
            buttons: [{
                label: 'Cancel',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    dialogRef.close();
                }
            }, {
                label: '<i class="copo-components-icons fa fa-power-off"></i> Exit',
                cssClass: 'tiny ui basic orange button',
                action: function (dialogRef) {
                    dialogRef.close();
                    clear_wizard();
                }
            }]
        });

    });

    $('#info_act').on('click', function (event) {
        //user wants information on current stage
        var item = $(this);
        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index

        var messageTitle = "Undocumented stage";
        var messageContent = "There is currently no information for this stage";

        var reviewElem = $('.steps li:last-child');
        if (reviewElem.hasClass('active')) {
            //last stage of the wizard
            messageTitle = "Review";
            messageContent = "Review and modify your entries as required. Click 'Finish!' when done.";
        } else {
            var current_stage_object = get_current_stage_object();
            if (current_stage_object) {
                messageTitle = current_stage_object.title;
                messageContent = current_stage_object.message;
            }
        }

        item.webuiPopover('destroy');
        item.webuiPopover({
            title: messageTitle,
            content: '<div class="webpop-content-div">' + messageContent + '</div>',
            trigger: 'sticky',
            width: 300,
            arrow: false,
            closeable: true,
            placement: 'right',
            backdrop: false,
        });
    });

    //handle event for discarding description...
    $('#discard_act').on('click', function (event) {
        //this, basically, if seen through, will remove all description metadata from affected items

        BootstrapDialog.show({
            title: "Discard Description",
            message: wizardMessages.discard_description_message.text,
            cssClass: 'copo-modal3',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            buttons: [{
                label: 'Cancel',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    dialogRef.close();
                }
            }, {
                label: '<i class="copo-components-icons fa fa-times"></i> Discard',
                cssClass: 'tiny ui basic red button',
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
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: request_params,
                        success: function (data) {
                            clear_wizard();
                            update_itemMetadata_flag();
                        },
                        error: function () {
                            alert("Couldn't discard description metadata!");
                        }
                    });
                }
            }]
        });

    });

    //handle event for saving subset of items in the description bundle
    $(document).on("click", ".apply-to-selected-btn", function (event) {
        event.preventDefault();
        var activeStageIndx = $(this).attr('data-stage-indx');

        var table = $('#description_target_table_' + activeStageIndx).DataTable();
        var selectedRows = [];

        selectedRows = table.rows({
            selected: true
        }).data();

        if (selectedRows.length == 0) {
            return false;
        }

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
            headers: {
                'X-CSRFToken': csrftoken
            },
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

    //event for unpairing datafiles
    $(document).on("click", ".unpair-datafiles", function (event) {
        event.preventDefault();

        do_datafile_unpairing($(this));
    });

    //handle event for clicking an previously visited step, intercept here to save entries
    $('#dataFileWizard').on('stepclicked.fu.wizard', function (evt, data) {
        evt.preventDefault();

        // get the proposed or intended state for which action is intercepted
        before_step_back(data.step);
    });

    $('#dataFileWizard').on('changed.fu.wizard', function (evt, data) {
        //display alert for stage
        new_stage_alert();

        //refresh description batch display
        refresh_batch_display();
    });


    //handle events for step change
    $('#dataFileWizard').on('actionclicked.fu.wizard', function (evt, data) {
        $(self).data('step', data.step);
        stage_navigate(evt, data);
    });


    //instantiate/refresh tooltips
    refresh_tool_tips();

    //handle batch item events
    $(document).on("click", ".wiz-batch-item", function (event) {
        var task = $(this).attr("data-record-action").toLowerCase();
        var targetId = $(this).attr("data-record-id");

        if (task == "delete") {
            BootstrapDialog.show({
                title: wizardMessages.empty_bundle_message.title,
                message: wizardMessages.empty_bundle_message.text,
                cssClass: 'copo-modal2',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_DANGER,
                buttons: [{
                    label: 'Cancel',
                    cssClass: 'tiny ui basic button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                }, {
                    label: '<i class="copo-components-icons fa fa-trash-o"></i> Remove',
                    cssClass: 'tiny ui basic red button',
                    action: function (dialogRef) {
                        $(this).tooltip('destroy');

                        if (descriptionBundle.length == 1) { //trying to remove last item from description bundle
                            clear_wizard();
                        } else {
                            for (var i = 0; i < descriptionBundle.length; ++i) {
                                if (targetId == descriptionBundle[i].recordID) {
                                    do_deque(descriptionBundle[i]);
                                    break;
                                }
                            }
                        }

                        dialogRef.close();

                    }
                }]
            });
        }
    });

    //handle annotation wizard study dropdown onchange
    $(document).on('change', '#study_copo', handle_wizard_study_dropdown_onchange)


    //****************************** Functions Block ******************************//
    function handle_wizard_study_dropdown_onchange(event) {
        var val = $(event.currentTarget).val()
        if (val == "none") {
            $('#sample_copo').find('option').remove().end().append('<option value="none"></option>')
            $('#sample_copo').attr('disabled', 'disabled')
            $('#study_ena').removeAttr('disabled')
            $('#sample_ena').removeAttr('disabled')
        }
        else {

            $('#study_ena').attr('disabled', 'disabled')
            $('#sample_ena').attr('disabled', 'disabled')
            $('#sample_copo').removeAttr('disabled')
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
                    })

                    $('#sample_copo').append(option)
                })

            }).fail(function (data) {
                console.log('error')
            })
        }
    }

    function add_step(auto_fields) {
        //step being requested
        currentIndx += 1;

        var retrieval_params = {
            'request_action': "get_next_stage",
            'description_token': descriptionToken,
            'auto_fields': auto_fields,
            'description_targets': JSON.stringify(descriptionBundle),
            'description_bundle': JSON.stringify(descriptionBundle),
            'rendered_stages': get_rendered_stages()
        };

        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index

        //first, make call to resolve the active stage data
        var stage_data = collate_stage_data();
        var current_stage_object = get_current_stage_object();

        //if no data, just go ahead and retrieve stage
        if (!stage_data) {
            retrieve_stage(retrieval_params);
            return false;
        }

        //next, notify user of the potential changes to be made, and give opportunity to retract

        // record the number of bundle items that have metadata for this stage
        var countMetadata = 0;
        descriptionBundle.forEach(function (item) {
            if (current_stage_object && item["attributes"][current_stage_object.ref]) {
                ++countMetadata;
            }
        });

        if (!get_apply_check_state(activeStageIndx)) { //if apply-to-selected button is unchecked ('unbundled'):
            // saving of data is handled per item in the bundle,

            if (descriptionBundle.length != countMetadata) {
                //some items in bundle may be lacking metadata

                BootstrapDialog.show({
                    title: "Unassigned Metadata",
                    message: wizardMessages.no_metadata_selected_bundle_items.text,
                    cssClass: 'copo-modal2',
                    closable: false,
                    animate: true,
                    type: BootstrapDialog.TYPE_WARNING,
                    buttons: [{
                        label: 'Describe',
                        cssClass: 'tiny ui basic button',
                        action: function (dialogRef) {
                            dialogRef.close();
                            $('#dataFileWizard').wizard('selectedItem', {
                                step: activeStageIndx
                            });
                        }
                    }, {
                        label: 'Next Stage',
                        cssClass: 'tiny ui basic orange button',
                        action: function (dialogRef) {
                            retrieve_stage(retrieval_params);
                            dialogRef.close();
                        }
                    }]
                });

            } else {
                //make call to retrieve stage
                retrieve_stage(retrieval_params);
            }

        } else { //apply-to-all:
            //ascertain any mismatch between items' metadata and current stage description

            //but..., if no metadata for all bundle items, continue rather silently
            if (countMetadata == 0) { //no metadata for all bundle items, save and load next stage...

                //display dialog for stage save
                var dialogHandle = processing_request_dialog('Saving stage data...');

                $.ajax({
                    url: wizardURL,
                    type: "POST",
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
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
                    headers: {
                        'X-CSRFToken': csrftoken
                    },
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
                                if (opt.value == "overwrite") { //do overwrite, if entries change, by default
                                    checked = " checked";
                                }
                                displayHTML += '<div class="radio wizard-alert-radio">';
                                displayHTML += '<label><input type="radio" name="metadata_bundle_items" value="' + opt.value + '"' + checked + '>' + opt.label + '</label>';
                                displayHTML += '</div>';
                            });
                            displayHTML += '</div>';
                            displayHTML += '</div>';


                            BootstrapDialog.show({
                                title: "Description Action Required",
                                message: displayHTML,
                                cssClass: 'copo-modal2',
                                closable: false,
                                animate: true,
                                type: BootstrapDialog.TYPE_WARNING,
                                buttons: [{
                                    label: 'OK',
                                    cssClass: 'tiny ui orange basic button',
                                    action: function (dialogRef) {
                                        var selectedOption = $('input[name=metadata_bundle_items]:checked').val();
                                        if (selectedOption == "donotoverwrite") { //do not overwrite
                                            retrieve_stage(retrieval_params);
                                        } else {
                                            stage_data.request_action = 'save_stage_data';
                                            //display dialog for stage save
                                            var dialogHandle = processing_request_dialog('Saving Stage Data...');

                                            $.ajax({
                                                url: wizardURL,
                                                type: "POST",
                                                headers: {
                                                    'X-CSRFToken': csrftoken
                                                },
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
                                }]
                            });

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

    function get_rendered_stages() {
        var rendered_stages = [];

        var goOn = true;
        var i = 1;

        while (goOn) {
            if ($('#wizard_form_' + i).length && $('#wizard_form_' + i).find("#current_stage").length) {
                var current_stage = $('#wizard_form_' + i).find("#current_stage").val();
                if (stage_objects.hasOwnProperty(current_stage)) {
                    var stage = stage_objects[current_stage];

                    var stage_items = [];
                    stage.items.forEach(function (item) {
                        stage_items.push(item.id);
                    });

                    var stage_object = {
                        "ref": stage.ref,
                        "item": stage_items
                    };

                    rendered_stages.push(stage_object);
                }

                goOn = true;
                ++i;
            } else {
                break;
            }
        }

        return JSON.stringify(rendered_stages);
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
                do_last_stage();
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

    function do_last_stage() {
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
            headers: {
                'X-CSRFToken': csrftoken
            },
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
                        BootstrapDialog.show({
                            title: "Initiate Submission",
                            message: wizardMessages.confirm_initiate_submission.text,
                            cssClass: 'copo-modal2',
                            closable: false,
                            animate: true,
                            type: BootstrapDialog.TYPE_INFO,
                            buttons: [
                                {
                                    label: '<i class="copo-components-icons fa fa-power-off"></i> Exit',
                                    cssClass: 'tiny ui basic orange button',
                                    action: function (dialogRef) {
                                        clear_wizard();
                                        dialogRef.close();
                                    }
                                },
                                {
                                    label: 'Initiate',
                                    cssClass: 'tiny ui basic primary button',
                                    action: function (dialogRef) {
                                        dialogRef.getModalFooter().hide();
                                        dialogRef.getModalBody().find(".bootstrap-dialog-message").html("Initiating submission...");
                                        dialogRef.getModalBody().find(".bootstrap-dialog-message").append($('<div style="margin-left: 40%; margin-top: 30px;" class="copo-i-loader"></div>'));

                                        setTimeout(function () {
                                            $.ajax({
                                                url: copoFormsURL,
                                                type: "POST",
                                                headers: {
                                                    'X-CSRFToken': csrftoken
                                                },
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
                                                    window.location.reload();
                                                }
                                            });
                                        }, 500);


                                    }
                                }
                            ]
                        });

                    } else {
                        BootstrapDialog.show({
                            title: "Metadata Validation",
                            message: wizardMessages.metadata_validation_failed.text,
                            cssClass: 'copo-modal2',
                            closable: false,
                            animate: true,
                            type: BootstrapDialog.TYPE_WARNING,
                            buttons: [
                                {
                                    label: '<i class="copo-components-icons fa fa-power-off"></i> Exit',
                                    cssClass: 'tiny ui basic orange button',
                                    action: function (dialogRef) {
                                        clear_wizard();
                                        dialogRef.close();
                                    }
                                },
                                {
                                    label: 'Describe',
                                    cssClass: 'tiny ui basic primary button',
                                    action: function (dialogRef) {
                                        dialogRef.close();
                                    }
                                }
                            ]
                        });
                    }
                }
            },
            error: function () {
                alert("Couldn't validate bundle!");
            }
        });
    }

    function processing_request_dialog(message) {
        var $textAndPic = $('<div></div>');
        $textAndPic.append($('<div style="margin-left: 40%; margin-top: 30px;" class="copo-i-loader"></div>'));

        var dialogInstance = new BootstrapDialog({cssClass: 'copo-modal2'})
            .setTitle(message)
            .setMessage($textAndPic)
            .setType(BootstrapDialog.TYPE_INFO)
            .setClosable(false)
            .open();

        return dialogInstance
    }

    function isInArray(value, array) {
        return array.indexOf(value) > -1;
    }

    function get_apply_check_state(activeStageIndx) { //function returns the state of the apply-to-all control
        var chkState; //apply-to-all checkbox state

        try {
            chkState = $("[name='apply-scope-chk-" + activeStageIndx + "']").bootstrapSwitch('state');
        } catch (err) {
            chkState = true;
        }

        return chkState;
    }

    function set_apply_check_state(activeStageIndx) { //function determines whether all items in the bundle have same metadata
        if (activeStageIndx == -1) {
            return true;
        }

        var current_stage_object = get_current_stage_object();
        var stage_ref = '';
        if (current_stage_object) {
            stage_ref = current_stage_object.ref;
        }

        var request_params = {
            'request_action': 'is_same_metadata',
            'description_token': descriptionToken,
            'stage_ref': stage_ref,
            'description_targets': JSON.stringify(bundle_without_data())
        };

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
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

        //refresh items' metadata flags
        update_itemMetadata_flag();
    }

    function retrieve_stage(retrieval_params) {
        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: retrieval_params,
            success: function (data) {
                //do we still have a valid stage sequence?
                try {
                    var validation_dict = data.validation_dict;
                    if (validation_dict.is_valid_stage_sequence) {
                        do_post_stage_retrieval(data);
                    } else {
                        //wizard stages need to be re-aligned to reflect current description sequence
                        stage_objects = {}; //clear stage objects
                        displayedMessages = {};

                        //remove previously displayed stages
                        $('#dataFileWizard').wizard('removeSteps', 1, 1000); //set to arbitrary large number of steps

                        //reset index
                        currentIndx = 1;
                        $('#dataFileWizard').wizard();

                        //add review step, then call to add other steps
                        $('#dataFileWizard').wizard('addSteps', -1, [
                            descriptionWizSummary
                        ]);

                        process_wizard_stage({"stages": data.validation_dict.stages});

                        //refresh data
                        if (data.targets_data) {
                            refresh_targets_data(data.targets_data);
                        }

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
                } catch (err) {
                    ;
                }
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
            $('#copo-datafile-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show');
        }

        //hide wizard getting started
        $(".page-wizard-message").hide();

        tabShownStore.data = data;
        tabShownStore.method = "do_post_stage_retrieval2";
    }


    function process_wizard_stage(data) {
        if (data.stages) {
            var selStep = currentIndx;
            var selectedStage = null; //stage to focus on
            var panes = [];
            for (var i = 0; i < data.stages.length; ++i) {
                if (data.stages[i].stage.title) {
                    stage_objects[data.stages[i].stage.ref] = data.stages[i].stage;
                    panes.push({
                        label: '<span class=wiz-title>' + data.stages[i].stage.title + '</span>',
                        pane: get_pane_content(data.stages[i].stage, currentIndx)
                    });

                    ++currentIndx;

                    if (setTargetStageRef && data.stages[i].stage.ref == setTargetStageRef) {
                        selectedStage = currentIndx;
                    }
                }
            }

            $('#dataFileWizard').wizard('addSteps', selStep, panes);
            setTargetStageRef = '';

            var currentStep = currentIndx - 1;

            if (selectedStage) {
                currentStep = selectedStage - 1;
            }

            $('#dataFileWizard').wizard('selectedItem', {
                step: currentStep
            });

            refresh_tool_tips();

            //setup fast nav for the stages
            //steps_fast_nav();


        } else if (data.stage && data.stage.stage) {
            stage_objects[data.stage.stage.ref] = data.stage.stage;
            $('#dataFileWizard').wizard('addSteps', currentIndx, [{
                label: '<span class=wiz-title>' + data.stage.stage.title + '</span>',
                pane: get_pane_content(data.stage.stage, currentIndx)
            }]);

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

    function get_pane_content(stage, currentIndx) {
        var stage_content = wizardStagesForms(stage);

        var stageHTML = $('<div/>', {
            id: "stage-controls-div-" + currentIndx
        });

        //form row
        var formRow = $('<div/>', {
            class: "row",
        });

        //description bundle row
        var descriptionBundleRow = $('<div/>', {
            class: "row",
        });

        //description bundle row
        var applyToAllRow = $('<div/>', {
            class: "row",
        });

        stageHTML.append(applyToAllRow).append(formRow).append(descriptionBundleRow);


        //'apply to all', alert trigger controls, and description context message
        var applyToAllPanel = get_panel("dtables");
        applyToAllPanel.attr("id", "alert_placeholder_" + currentIndx);
        applyToAllPanel.find(".panel-body").addClass("webpop-content-div");

        applyToAllPanel.find(".panel-heading").remove();

        var applyToAllMessageDiv = $('<div/>', {
            style: "margin-top: 15px;",
            class: "apply-to-all-message",
        });

        var applyToHeader = $('<div/>');

        var noticeIcon = $('<i class="fa fa-info-circle text-primary" style="padding-right: 10px; vertical-align: middle; font-size: 24px"></i>');

        var spanMessage = $('<span/>', {
            style: "font-weight: bold; font-size: 14px; vertical-align: middle;",
            class: "text-info",
            html: 'Do you want to apply the same metadata in this stage to all the items in the description bundle?'
        });


        var showApplyTo = "";

        if (stage.hasOwnProperty('is_singular_stage') && stage.is_singular_stage) {
            spanMessage.html('The metadata supplied in this stage will apply to all the items in the description bundle');
            showApplyTo = " display: none;";
        }

        //pairing message
        if (stage.ref == "datafiles_pairing") {
            spanMessage.html('Please define datafile pairing for items in the description bundle');
            showApplyTo = " display: none;";
        }


        var spanInput = $('<span/>', {
            style: "font-weight: bold; margin-left: 5px;" + showApplyTo,
            html: '<input type="checkbox" name="apply-scope-chk-' + currentIndx + '" checked data-size="mini" data-on-color="primary" data-off-color="default" data-on-text="Yes" data-off-text="No">'
        });

        applyToHeader.append(noticeIcon).append(spanMessage).append(spanInput);

        applyToAllPanel.find(".panel-body").append(applyToHeader).append(applyToAllMessageDiv);


        var formColumn = $('<div/>', {
            class: "col-sm-12 col-md-12 col-lg-12"
        });

        //'apply-to-all controls placement
        var applyToColumn = $('<div/>', {
            class: "col-sm-12 col-md-12 col-lg-12",
        }).append(applyToAllPanel);

        applyToAllRow.append(applyToColumn);
        formRow.append(formColumn);

        var formCtrl = $('<form/>', {
            id: "wizard_form_" + currentIndx
        });

        formCtrl.append(stage_content);

        var formButton = $('<button/>', {
            id: "apply_to_btn_" + currentIndx,
            class: "apply-to-selected-btn tiny ui primary button",
            html: "Apply to selected items in bundle",
            "data-stage-indx": currentIndx
        });

        var formControlsPanel = get_panel("primary");
        formControlsPanel.attr("id", "stage_form_panel_" + currentIndx);
        formControlsPanel.find(".panel-heading").append("<strong>Description Metadata</strong>");
        formControlsPanel.find(".panel-body").append(formCtrl).append(formButton);
        formControlsPanel.find(".panel-heading");

        formColumn.append(formControlsPanel);


        //description bundle

        var descriptionBundleCol = $('<div/>', {
            class: "col-sm-12 col-md-12 col-lg-12",
        });

        descriptionBundleRow.append(descriptionBundleCol);

        var descriptionBundleTableHTML = "";
        descriptionBundleTableHTML += '<table id="description_target_table_' + currentIndx + '" class="ui celled table hover copo-noborders-table" cellspacing="0" width="100%">';
        descriptionBundleTableHTML += '<thead><tr><th></th><th>Datafiles</th><th>&nbsp;</th>';
        descriptionBundleTableHTML += '</tr> </thead></table>';

        var bundlePanel = get_panel("primary");
        bundlePanel.attr("id", "bundlepanel_" + currentIndx);
        bundlePanel.find(".panel-heading").html("<strong>Description Bundle</strong>");
        bundlePanel.find(".panel-body").html(descriptionBundleTableHTML);
        bundlePanel.find(".panel-heading");

        //render datafiles pairing table differently
        var current_stage_object = get_current_stage_object();
        if (stage.ref == "datafiles_pairing") {
            descriptionBundleTableHTML = "";
            descriptionBundleTableHTML += '<table id="description_target_table_' + currentIndx + '" class="ui celled table hover copo-noborders-table" cellspacing="0" width="100%">';
            descriptionBundleTableHTML += '<thead><tr><th>Description Bundle</th><th>&nbsp;</th>';
            descriptionBundleTableHTML += '</tr> </thead></table>';

            var datafilePairTableHTML = "";
            datafilePairTableHTML += '<table id="datafile_pairing_table_' + currentIndx + '" class="ui celled table hover copo-noborders-table" cellspacing="0" width="100%">';
            datafilePairTableHTML += '<thead><tr><th>Paired Datafiles</th>';
            datafilePairTableHTML += '</tr> </thead></table>';

            var pairingLeft = $('<div/>', {
                class: "col-sm-6 col-md-6 col-lg-6",
                html: descriptionBundleTableHTML
            });

            var pairingRight = $('<div/>', {
                class: "col-sm-6 col-md-6 col-lg-6",
                html: datafilePairTableHTML
            });

            var pairingRow = $('<div/>', {
                class: "row",
            });

            pairingRow.append(pairingLeft).append(pairingRight);

            bundlePanel.find(".panel-heading").html("<strong><span id='paired-message-" + currentIndx + "'></span>Description Bundle & Datafiles Pairing</strong>");
            bundlePanel.find(".panel-body").html('').append(pairingRow);
        }


        descriptionBundleCol.html(bundlePanel);

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
        $('#dataFileWizard').wizard('removeSteps', 1, 1000); //set to arbitrary large number of steps
        $('#dataFileWizard').hide();


        //reset wizard parameters
        descriptionBundle = []; //clear bundle
        descriptionToken = ""; //discard description token
        stage_objects = {}; //clear stage objects

        refresh_inDescription_flag(); //refresh description flag
        silenceAlert = false;
        displayedMessages = {};

        //reset index
        currentIndx = 0;

        setTimeout(function () {
            if (onGoingDescription) {
                $('#copo-datafile-tabs.nav-tabs a[href="#emptyTab"]').tab('show');
            } else {
                $('#copo-datafile-tabs.nav-tabs a[href="#fileListComponent"]').tab('show');
            }

            onGoingDescription = false;
            $("#description_panel").css("display", "none");
            $(".page-wizard-message").show();

        }, 500);

    }

    function reset_wizard() { //resets wizard without all the hassle of clear_wizard()
        $('#dataFileWizard').wizard('removeSteps', 1, 1000); //set to arbitrary large number of steps

        //add review step, then other steps
        $('#dataFileWizard').wizard('addSteps', -1, [
            descriptionWizSummary
        ]);

        currentIndx = 1;
    }

    function get_current_stage_object() {
        var stage = null;
        //get active stage
        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index

        if (activeStageIndx == -1) {
            return stage;
        }

        var current_stage = $('#wizard_form_' + activeStageIndx).find("#current_stage").val();
        if (stage_objects.hasOwnProperty(current_stage)) {
            stage = stage_objects[current_stage];
        }

        return stage;

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


    function before_step_back(proposedState) {
        //trigger save action before navigating back a stage
        $('#dataFileWizard').wizard('selectedItem', {
            step: proposedState
        });

        //stop execution
        if (1 == 1) {
            return false;
        }


        var stage_data = collate_stage_data();
        if (!stage_data) { //if no data, just go ahead and display stage
            $('#dataFileWizard').wizard('selectedItem', {
                step: proposedState
            });
        } else {
            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
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

    function do_undescribe_confirmation(records, describedRecords) {
        //alert the user to items currently being described

        var candidates = [];

        for (var i = 0; i < records.length; ++i) {
            candidates.push(records[i].record_id);
        }

        if (candidates.length == 0) {
            return false;
        }

        var describedAlert = '';

        if (describedRecords.length > 0) {
            //make sure focus is given to wizard view to avoid conflict if eventually removing wizard
            $('#copo-datafile-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show');
            var describedAlert = $('<div/>', {
                style: "margin-top: 15px; color:red;",
                html: "Please note: " + describedRecords.length + " of the selected datafile(s) are currently being described and will be affected by this action. What do you want to do?"
            });
        }

        var taskMessage = '<div>' + wizardMessages.delete_description_message.text + '</div>' + $('<div/>').append(describedAlert).html();

        BootstrapDialog.show({
            title: "Discard Description Metadata",
            message: taskMessage,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            buttons: [{
                label: 'Cancel',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    $('#copo-datafile-tabs.nav-tabs a[href="#fileListComponent"]').tab('show');
                    dialogRef.close();
                }
            }, {
                label: '<i class="copo-components-icons fa fa-times"></i> Discard',
                cssClass: 'tiny ui basic red button',
                action: function (dialogRef) {
                    dialogRef.close();

                    var request_params = {
                        'task': 'un_describe',
                        'datafile_ids': JSON.stringify(candidates)
                    };

                    $.ajax({
                        url: copoVisualsURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: request_params,
                        success: function (data) {
                            //update description bundle
                            if (describedRecords.length > 0) {
                                describedRecords.forEach(function (item) {
                                    for (var i = 0; i < descriptionBundle.length; ++i) {
                                        if (item.record_id == descriptionBundle[i].recordID) {
                                            do_deque(descriptionBundle[i]);
                                            break;
                                        }
                                    }
                                });
                            }

                            display_copo_alert("info", "Description metadata discarded", 20000);
                            update_itemMetadata_flag();

                            deselect_records(componentMeta.tableID);

                            if (describedRecords.length > 0 && descriptionBundle.length == 0) {
                                clear_wizard();
                                update_itemMetadata_flag();
                            }

                        },
                        error: function () {
                            alert("Couldn't discard description for selected records!");
                        }
                    });
                }
            }]
        });
    }

    function add_to_batch(batchTargets, silence) {
        // validate items in batchTargets before adding them to the description bundle.
        // one reason is to avoid duplication of items in the description bundle.
        // but also, can the items be bundled together (e.g., having similar metadata (stages), and going to same repo)?
        // what of inheriting metadata from already existing bundle items?

        // one can also 'silence' if you are only refreshing the wizard without necessarily
        // altering items in the bundle. if silence = false, then all validation steps will be performed/enforced
        // before engaging the description bundle


        var candidates = [];
        batchTargets.forEach(function (item) { //candidates are items not already in the description bundle
            if (!isInList(item, descriptionBundle)) {
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

        setTimeout(function () {
            $.ajax({
                url: wizardURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: request_params,
                success: function (data) {
                    if (data.description_token) {
                        descriptionToken = data.description_token;
                    }

                    dialogHandle.close();

                    if (data.validatation_results.validation_code == "100") {
                        //  compatible description targets which can be described as a bundle!
                        do_validate_100(candidates, data, silence);

                    } else if (data.validatation_results.validation_code == "101") {
                        //some candidates are ahead of others! inherit metadata?
                        do_validate_101(candidates, data);

                    } else if (data.validatation_results.validation_code == "102") {
                        //candidates have incompatible metadata
                        do_validate_102();
                    } else if (data.validatation_results.validation_code == "103") {
                        //some candidates are ahead of items in the description bundle! inherit metadata?
                        do_validate_103(candidates, data);
                    } else {
                        refresh_batch_display();
                    }
                },
                error: function () {
                    alert("Couldn't retrieve data for targets!");
                }
            });
        }, 500);

    }


    function do_validate_100(candidates, data, silence) { // compatible description targets which can be described as a bundle!
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
                    BootstrapDialog.show({
                        title: "Description Information",
                        message: wizardMessages.confirm_bundling_action.text,
                        cssClass: 'copo-modal2',
                        closable: false,
                        animate: true,
                        type: BootstrapDialog.TYPE_INFO,
                        buttons: [{
                            label: 'Cancel',
                            cssClass: 'tiny ui basic button',
                            action: function (dialogRef) {
                                descriptionToken = null; //invalidate the description
                                dialogRef.close();
                            }
                        }, {
                            label: '<i class="copo-components-icons fa fa-check"></i> Continue',
                            cssClass: 'tiny ui basic teal button',
                            action: function (dialogRef) {
                                descriptionBundle = candidates;
                                //update added items with data
                                refresh_targets_data(data.validatation_results.extra_information.candidates_data);
                                do_post_stage_retrieval(data);
                                refresh_batch_display();
                                dialogRef.close();
                            }
                        }]
                    });
                }

            } else {
                //set bundle to candidates
                descriptionBundle = candidates;
                refresh_targets_data(data.validatation_results.extra_information.candidates_data);
                do_post_stage_retrieval(data);
                refresh_batch_display();
            }
        }

        refresh_batch_display();
    }

    function do_validate_101(candidates, data) { //some description candidates are ahead of others! inherit metadata?
        var dialog_message = wizardMessages.inherit_metadata_message.text;
        dialog_message += '<div class="radio wizard-alert-radio">' + show_description_metadata(data.validatation_results.extra_information.summary) + '</div>';

        BootstrapDialog.show({
            title: "Inherit Metadata",
            message: dialog_message,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_WARNING,
            buttons: [{
                label: 'No',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    descriptionToken = null;
                    dialogRef.close();
                }
            }, {
                label: '<i class="copo-components-icons fa fa-check"></i> Yes',
                cssClass: 'tiny ui basic orange button',
                action: function (dialogRef) {
                    var request_action = "inherit_metadata";
                    if (descriptionBundle.length == 0) {
                        request_action = "inherit_metadata_refresh";
                    }

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
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
            }]
        });

        refresh_batch_display();
    }

    function do_validate_102() { //candidates have incompatible metadata
        BootstrapDialog.show({
            title: "Incompatible Metadata",
            message: wizardMessages.incompatible_metadata_message.text,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            buttons: [{
                label: 'OK',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    descriptionToken = null;
                    dialogRef.close();
                }
            }]
        });

        refresh_batch_display();
    }

    function do_validate_103(candidates, data) { //candidates ahead of items in the description bundle! inherit metadata?
        var dialog_message = wizardMessages.inherit_metadata_103_message.text;
        dialog_message += '<div class="radio wizard-alert-radio">' + show_description_metadata(data.validatation_results.extra_information.summary) + '</div>';

        $('#copo-datafile-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show'); //display to description pane

        BootstrapDialog.show({
            title: "Inherit Metadata",
            message: dialog_message,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_WARNING,
            buttons: [{
                label: 'No',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    descriptionToken = null;
                    dialogRef.close();
                }
            }, {
                label: '<i class="copo-components-icons fa fa-check"></i> Yes',
                cssClass: 'tiny ui basic orange button',
                action: function (dialogRef) {
                    candidates.forEach(function (item) {
                        descriptionBundle.push(item);
                    });

                    var tempDescriptionBundle = descriptionBundle;

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: {
                            'request_action': "inherit_metadata_refresh",
                            'target_id': data.validatation_results.extra_information.target.recordID,
                            'description_token': descriptionToken,
                            'description_targets': JSON.stringify(descriptionBundle),
                            'description_bundle': JSON.stringify(descriptionBundle)
                        },
                        success: function (data2) {
                            clear_wizard();
                            descriptionBundle = tempDescriptionBundle;
                            dialogRef.close();
                            setTimeout(function () {
                                do_post_stage_retrieval(data2);
                                refresh_batch_display();
                            }, 500);
                        },
                        error: function () {
                            alert("Couldn't inherit metadata!");
                            return '';
                        }
                    });
                }
            }]
        });

        refresh_batch_display();
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

    function isInList(candidate, theList) {//checks if a datafile (candidate) is in a list of datafiles
        var isInBundle = false;

        for (var i = 0; i < theList.length; ++i) {
            if (theList[i].recordID == candidate.recordID) {
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
    function do_record_task(event) {
        var task = event.task.toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var tableID = event.tableID; //get target table
        var taskLabel = event.title;

        //holds selected records that are also currently being described
        var describedRecords = [];

        //retrieve target records and execute task
        var table = $('#' + tableID).DataTable();
        var records = []; //
        $.map(table.rows('.selected').data(), function (item) {
            records.push(item);
            if (isIn_descriptionBundle_Id(item.record_id)) {
                describedRecords.push(item);
            }
        });

        if (records.length == 0) {
            return false;
        }

        if (task == "describe") {
            //append to batch
            var batchTargets = [];
            for (var i = 0; i < records.length; ++i) {
                var item = records[i];
                var option = {};
                option["recordLabel"] = item.name;
                option["recordID"] = item.record_id;
                option["attributes"] = {};
                batchTargets.push(option);
            }

            add_to_batch(batchTargets, false);
            table.rows().deselect();

        } else if (task == "discard") {
            do_undescribe_confirmation(records, describedRecords);
        } else if (task == "edit") {
            $.ajax({
                url: copoFormsURL,
                type: "POST",
                headers: {
                    'X-CSRFToken': csrftoken
                },
                data: {
                    'task': 'form',
                    'component': component,
                    'target_id': records[0].record_id //only allowing row action for edit, hence first record taken as target
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

        //table.rows().deselect(); //deselect all rows

    } //end of func

    function do_deque(item) { //removes item from the batch
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
            } catch (err) {
                formDiv.append('<div class="form-group copo-form-group"><span class="text-danger">Form Control Error</span> (' + formElem.label + '): Cannot resolve form control!</div>');
            }

            //any triggers?
            if (formElem.trigger) {
                try {
                    dispatchEventHandler[formElem.trigger.callback.function](formElem);
                } catch (err) {
                }
            }

        }

        //add current stage to form
        var hiddenCtrl = $('<input/>', {
            type: "hidden",
            id: "current_stage",
            name: "current_stage",
            value: stage.ref
        });

        formDiv.append(hiddenCtrl);

        return formDiv;
    }

    function do_handle_select_events(event) {
        var current_stage_object = get_current_stage_object();

        if (current_stage_object && current_stage_object.ref == "library_construction" && $(event.target).attr("id") == "library_layout") {
            //refresh wizard to normalise stages display
        }
    }

    function element_value_change_modified(formElem, messageTitle) {
        var triggerMessage = '';

        try {
            triggerMessage = formElem.trigger.message;
        } catch (err) {
            ;
        }

        BootstrapDialog.show({
            title: messageTitle,
            message: '<div class=modal-content-div">' + triggerMessage + '</div>',
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_WARNING,
            buttons: [{
                label: 'OK',
                cssClass: 'tiny ui basic orange button',
                action: function (dialogRef) {
                    dialogRef.close();
                }
            }]
        });
    }

    function element_value_change(formElem, elemValue, messageTitle) {
        var triggerMessage = '';

        try {
            triggerMessage = formElem.trigger.message;
        } catch (err) {
            ;
        }


        BootstrapDialog.show({
            title: messageTitle,
            message: triggerMessage,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_WARNING,
            buttons: [{
                label: 'Cancel',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    //set back to previous value
                    $("#" + formElem.id).val(elemValue);

                    dialogRef.close();
                }
            }, {
                label: 'Continue',
                cssClass: 'tiny ui basic orange button',
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
                                headers: {
                                    'X-CSRFToken': csrftoken
                                },
                                data: stage_data,
                                success: function (data) {
                                    onGoingDescription = true;
                                    clear_wizard();
                                    silenceAlert = silnAlert;
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
            }]
        });

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
                    element_value_change_modified(formElem, formElem.label + " Change");
                });
        },
        target_repo_change: function (formElem) {
            $(document)
                .off(formElem.trigger.type, "#" + formElem.id)
                .on(formElem.trigger.type, "#" + formElem.id, function () {
                    element_value_change_modified(formElem, formElem.label + " Change");
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
                    var current_stage_object = get_current_stage_object();
                    if (current_stage_object) {
                        setTargetStageRef = current_stage_object.ref
                    }

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
                    var current_stage_object = get_current_stage_object();
                    if (current_stage_object) {
                        setTargetStageRef = current_stage_object.ref
                    }
                    element_value_change(formElem, previousValue, formElem.label + " Change");
                });
        }
    };

    function set_wizard_summary() {
        descriptionWizSummary = {
            label: '<span class=wiz-title>Review</span>',
            pane: '<div class="alert alert-default">' +
            '<div style="line-height: 150%;" class="' + wizardMessages.review_message.text_class + '">' +
            wizardMessages.review_message.text + '</div>' +
            '<div style="margin-top: 10px; max-width: 100%; overflow-x: auto;">' +
            '<table id="description_summary_table" class="ui celled table hover copo-noborders-table" cellspacing="0" width="100%">' +
            '<thead><tr><th></th><th>Datafiles</th><th>Rating</th>' +
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
                    {
                        "data": "target"
                    },
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
                    }],
                dom: 'fr<"row"><"row description-rw" i>tlp'
            });

            $('#description_summary_table_wrapper')
                .find(".dataTables_filter")
                .find("input")
                .removeClass("input-sm")
                .attr("placeholder", "Search Datafiles")
                .attr("size", 25);


            // handle opening and closing summary details
            $('#description_summary_table tbody').on('click', 'td.summary-details-control', function (event) {
                event.preventDefault();
                var tr = $(this).closest('tr');
                var row = table.row(tr);

                if (row.child.isShown()) {
                    // This row is already open - close it
                    row.child.hide();
                    tr.removeClass('shown');
                } else {
                    // expand row
                    var contentHtml = "<div style='text-align: center'><i class='fa fa-spinner fa-pulse fa-2x'></i></div>";
                    row.child(contentHtml).show();
                    tr.addClass('shown');

                    $.ajax({
                        url: copoVisualsURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
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
            headers: {
                'X-CSRFToken': csrftoken
            },
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


    } //end of func

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

        //render differently for some stages
        var current_stage_object = get_current_stage_object();
        if (current_stage_object && current_stage_object.ref == "datafiles_pairing") {
            refresh_paired_files_display();
            return false;
        }


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

        var colDefs = [{
            targets: -1,
            width: "5%",
            data: null,
            searchable: false,
            orderable: false,
            render: function (rdata) {
                var rndHTML = "";

                var bTns = buttons;
                rndHTML = '<span style="white-space: nowrap;">';
                for (var i = 0; i < bTns.length; ++i) {
                    rndHTML += '<a data-action-target="row" data-record-action="' +
                        bTns[i].btnAction + '" data-record-id="' +
                        rdata +
                        '" data-toggle="tooltip" style="display: inline-block; white-space: normal; background-image: none; border: none;" title="' +
                        bTns[i].text + '" class="' + bTns[i].className + ' btn-xs"><i class="' +
                        bTns[i].iconClass + '"> </i><span></span></a>&nbsp;';
                }
                rndHTML += '</span>';

                return rndHTML;
            }
        }, {
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

        },
            {
                "width": "5%",
                "targets": 0
            }];

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
                "lengthChange": true,
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
                    'selectNone'
                ],
                language: {
                    buttons: {
                        selectAll: "Select all",
                        selectNone: "Select none"
                    },
                    select: {
                        multi: {
                            _: "Current description will apply to %d files in bundle <span style='padding-left: 10px;'>Click <span class='fa-stack' style='color:green; font-size:11px;'><i class='fa fa-circle fa-stack-2x'></i><i class='fa fa-plus fa-stack-1x fa-inverse'></i></span> beside a datafile to view details</span>",
                            0: "Click a row to select it <span style='padding-left: 10px;'>Click <span class='fa-stack' style='color:green; font-size:11px;'><i class='fa fa-circle fa-stack-2x'></i><i class='fa fa-plus fa-stack-1x fa-inverse'></i></span> beside a datafile to view details</span>",
                            1: "Current description will apply to 1 file in bundle <span style='padding-left: 10px;'>Click <span class='fa-stack' style='color:green; font-size:11px;'><i class='fa fa-circle fa-stack-2x'></i><i class='fa fa-plus fa-stack-1x fa-inverse'></i></span> beside a datafile to view details</span>"
                        }
                    }
                },
                "columns": [{
                    "className": 'summary-details-control',
                    "orderable": false,
                    "data": null,
                    "defaultContent": ''
                }, {
                    "data": "target"
                }, {
                    "data": "buttons"
                }],
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
                dom: 'Bfr<"row"><"row description-rw" i>tlp'
            });

            $(table.buttons().container()).insertBefore(filterDivObject);

            table
                .buttons()
                .nodes()
                .each(function (value) {
                    $(this)
                        .removeClass("btn btn-default")
                        .addClass('tiny ui basic button');
                });


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
                } else {
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

                    var current_stage_object = get_current_stage_object();
                    var stage_id = '';
                    if (current_stage_object) {
                        stage_id = current_stage_object.ref;
                    }

                    var request_params = {
                        'request_action': 'get_item_stage_display',
                        'component': component,
                        'stage_id': stage_id,
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
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: request_params,
                        success: function (data) {
                            //display stage metadata for item

                            contentHtml = '';

                            if (!appliedToAllFlag) {
                                var current_stage_object = get_current_stage_object();
                                var applyToItemBtn = '<button tabindex="0" type="button" data-stage-indx="' + activeStageIndx + '" data-description-target="' + row.data().target_id + '"  class="apply-to-item-btn tiny ui primary button">Apply to item</button><span style="margin-left: 4px; font-weight: 600;" class="text-default"></span>';
                                if (current_stage_object && current_stage_object.hasOwnProperty("is_singular_stage") && current_stage_object.is_singular_stage || get_apply_check_state(activeStageIndx)) {
                                    applyToItemBtn = '';
                                }

                                contentHtml += '<div class="panel panel-primary" style="margin-top: 5px;">';
                                contentHtml += '<div class="panel-heading" style="background-image: none;"><strong>Metadata</strong></div>';
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
                                var current_stage_object = get_current_stage_object();
                                var stage_ref = '';
                                if (current_stage_object) {
                                    stage_ref = current_stage_object.ref;
                                }

                                if (data.description.length) {
                                    for (var i = 0; i < data.description.length; ++i) {
                                        if (data.description[i].ref == stage_ref) {
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

                if (!state) { //when the apply-to button is set to false, reset form
                    var current_stage_object = get_current_stage_object();
                    var stage_id = '';
                    if (current_stage_object) {
                        stage_id = current_stage_object.ref;
                    }

                    var request_params = {
                        'request_action': 'get_item_stage_display',
                        'stage_id': stage_id,
                        'description_token': descriptionToken
                    };

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
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
                    var current_stage_object = get_current_stage_object();
                    var stage_ref = '';
                    if (current_stage_object) {
                        stage_ref = current_stage_object.ref;
                    }
                    var request_params = {
                        'request_action': 'is_same_metadata',
                        'description_token': descriptionToken,
                        'stage_ref': stage_ref,
                        'description_targets': JSON.stringify(bundle_without_data())
                    };

                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: request_params,
                        success: function (data) {
                            if (data.state) {
                                var current_stage_object = get_current_stage_object();
                                var stage_id = '';
                                if (current_stage_object) {
                                    stage_id = current_stage_object.ref;
                                }
                                var request_params = {
                                    'request_action': 'get_item_stage_display',
                                    'stage_id': stage_id,
                                    'description_token': descriptionToken,
                                    'description_targets': JSON.stringify([descriptionBundle[0]])
                                };

                                $.ajax({
                                    url: wizardURL,
                                    type: "POST",
                                    headers: {
                                        'X-CSRFToken': csrftoken
                                    },
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

        $('#description_target_table_' + activeStageIndx + '_wrapper')
            .find(".dataTables_filter")
            .find("input")
            .removeClass("input-sm")
            .attr("placeholder", "Search bundle")
            .attr("size", 25);

        //'disable' row selection for cases where is-singular-stage and apply-to-all
        if (table) {

            table.on('select', function (e, dt, type, indexes) {
                var selectedRows = table.rows({
                    selected: true
                }).count();

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
                var selectedRows = table.rows({
                    selected: true
                }).count();

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
                var current_stage_object = get_current_stage_object();
                if (((current_stage_object && current_stage_object.hasOwnProperty("is_singular_stage") && current_stage_object.is_singular_stage) || (get_apply_check_state(activeStageIndx))) &&
                    (selectedRows != allRows)) {
                    table.rows('.selected').deselect();
                    table.rows().select();
                }

            });
        }

        show_hide_stage_ctrl(get_apply_check_state(activeStageIndx), activeStageIndx);

        if (activeStageIndx >= 1 && !(($('#dataFileWizard').is(":visible")))) {
            $('#copo-datafile-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show'); //set display to description pane
        }

    } //end of func

    function update_paired_display(data) {
        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index
        var unpaired_list = data.pairing_info.unpaired_list; //pairable candidates - will make up the description bundle
        var paired_list = data.pairing_info.paired_list; //already paired - will make up the pairedTable
        var add_to_bundle = data.pairing_info.add_to_bundle; //used to update description bundle to satisfy existing pairing
        var do_not_pair_list = data.pairing_info.do_not_pair_list; //not to be paired (i.e., having library layout!='PAIRED')


        if (add_to_bundle.length > 0 || do_not_pair_list.length > 0 || (unpaired_list.length > 0 && unpaired_list.length % 2 != 0)) {
            var message = '';
            var alertElem = $('#paired-message-' + activeStageIndx);
            alertElem.webuiPopover('destroy');


            if (add_to_bundle.length > 0) {
                var tempMessage = "<div>" + add_to_bundle.length + " datafile(s) have been added to the description bundle to satisfy existing pairing:";

                tempMessage += '<ol>';
                for (var i = 0; i < add_to_bundle.length; ++i) {
                    tempMessage += '<li>' + add_to_bundle[i].recordLabel + '</li>';
                }

                tempMessage += '</ol></div>';

                message += tempMessage;

            }

            if (do_not_pair_list.length > 0) {
                var tempMessage = "<div>" + do_not_pair_list.length + " datafile(s) that do not require pairing have been temporary removed from the description bundle: ";

                tempMessage += '<ol>';
                for (var i = 0; i < do_not_pair_list.length; ++i) {
                    tempMessage += '<li>' + do_not_pair_list[i].recordLabel + '</li>';
                }

                tempMessage += '</ol></div>';

                message += tempMessage;

            }

            if (unpaired_list.length > 0 && unpaired_list.length % 2 != 0) {
                var tempMessage = '<div><i class="fa fa-exclamation-circle" aria-hidden="true" style="color: red; font-size: 15px !important; padding-right: 10px;"></i> Please ensure you have an even number of datafiles in the bundle in order to successfully conduct datafiles pairing.';

                message += tempMessage;
            }

            BootstrapDialog.show({
                title: "Pairing Alert",
                message: message,
                cssClass: 'copo-modal2',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [{
                    label: 'OK',
                    cssClass: 'tiny ui basic orange button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                }]
            });
        }


        //set up data source
        var dtd = []; //description bundle data source (datafiles not yet paired)
        var dtdPaired = []; //define pairedTable data source

        //compose pairedTable data source
        for (var i = 0; i < paired_list.length; ++i) { //paired data source
            var pair = paired_list[i];
            var option = {};
            option["target"] = [pair[0].recordLabel, pair[1].recordLabel];
            option["target_id"] = [pair[0].recordID, pair[1].recordID];

            dtdPaired.push(option);
        }

        //compose bundle data source
        for (var i = 0; i < unpaired_list.length; ++i) {
            var item = unpaired_list[i];
            var option = {};
            option["target"] = [item.recordLabel, item.recordID];
            option["target_id"] = item.recordID;
            option["attributes"] = item.attributes;
            option["buttons"] = item.recordID;
            dtd.push(option);
        }


        var buttons = [];
        buttons.push({
            'text': 'Remove from description bundle',
            'className': 'wiz-batch-item btn btn-danger',
            'iconClass': 'fa fa-trash-o',
            'btnAction': 'delete'
        });

        var colDefs = [{
            targets: -1,
            width: "5%",
            data: null,
            searchable: false,
            orderable: false,
            render: function (rdata) {
                var rndHTML = "";

                var bTns = buttons;
                rndHTML = '<span style="white-space: nowrap;">';
                for (var i = 0; i < bTns.length; ++i) {
                    rndHTML += '<a data-action-target="row" data-record-action="' +
                        bTns[i].btnAction + '" data-record-id="' +
                        rdata +
                        '" data-toggle="tooltip" style="display: inline-block; white-space: normal; background-image: none; border: none;" title="' +
                        bTns[i].text + '" class="' + bTns[i].className + ' btn-xs"><i class="' +
                        bTns[i].iconClass + '"> </i><span></span></a>&nbsp;';
                }
                rndHTML += '</span>';

                return rndHTML;
            }
        }, {
            targets: 0,
            data: null,
            render: function (rdata) {
                var rndHTML = rdata[0];
                return rndHTML;
            }

        }];

        //set data
        var table = null;
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
            table = tableElem.DataTable({
                "data": dtd,
                "lengthChange": true,
                "columns": [{
                    "data": "target"
                }, {
                    "data": "buttons"
                }],
                "fnDrawCallback": function (oSettings) {
                    refresh_tool_tips();

                    // refresh show hide stage controls
                    var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step;
                    $("[name='apply-scope-chk-" + activeStageIndx + "']").bootstrapSwitch('state', false);

                    $("#stage_form_panel_" + activeStageIndx).hide();
                    set_stage_alerts(wizardMessages.datafiles_pairing_message, activeStageIndx);
                    refresh_inDescription_flag();
                },
                columnDefs: colDefs,
                //scrollY: "200px",
                scrollCollapse: true,
                select: {
                    style: 'multi'
                },
                buttons: [
                    {
                        text: 'Suggest pairings',
                        action: function (e, dt, node, config) {
                            refresh_paired_files_display();
                        }
                    }
                ],
                dom: 'Bfr<"row"><"row description-rw" i>tlp'
            });

            table
                .buttons()
                .nodes()
                .each(function (value) {
                    $(this)
                        .removeClass("btn btn-default")
                        .addClass('tiny ui basic primary button');
                });
        }

        $('#description_target_table_' + activeStageIndx + '_wrapper')
            .find(".dataTables_filter")
            .find("input")
            .removeClass("input-sm")
            .attr("placeholder", "Search bundle")
            .attr("size", 25);

        if (table) {

            table
                .off('select')
                .on('select', function (e, dt, type, indexes) {
                    var selectedRows = dt.rows({
                        selected: true
                    }).data();

                    if (selectedRows.length == 2) {//pair selected datafiles
                        BootstrapDialog.show({
                            title: "Datafiles pairing",
                            message: 'Do you want to pair the selected datafiles?',
                            cssClass: 'copo-modal3',
                            closable: false,
                            animate: true,
                            type: BootstrapDialog.TYPE_PRIMARY,
                            buttons: [{
                                label: 'Cancel',
                                cssClass: 'tiny ui basic button',
                                action: function (dialogRef) {
                                    table.rows('.selected').deselect();
                                    dialogRef.close();
                                }
                            }, {
                                label: '<i class="copo-components-icons fa fa-link"></i> Pair',
                                cssClass: 'tiny ui basic primary button',
                                action: function (dialogRef) {
                                    dialogRef.close();
                                    var deTargs = [];
                                    for (var i = 0; i < selectedRows.length; ++i) {
                                        descriptionBundle.forEach(function (item) {
                                            if (selectedRows[i].target_id == item.recordID) {
                                                deTargs.push(item);
                                            }
                                        });
                                    }

                                    var request_params = {
                                        'request_action': 'datafile_pairing',
                                        'description_token': descriptionToken,
                                        'description_targets': JSON.stringify(deTargs),
                                        'description_bundle': JSON.stringify(descriptionBundle)
                                    };

                                    $.ajax({
                                        url: wizardURL,
                                        type: "POST",
                                        headers: {
                                            'X-CSRFToken': csrftoken
                                        },
                                        data: request_params,
                                        success: function (data) {
                                            if (data.targets_data) {
                                                refresh_targets_data(data.targets_data);
                                            }
                                            refresh_paired_files_display();
                                        },
                                        error: function () {
                                            alert("Couldn't pair datafiles!");
                                        }
                                    });
                                }
                            }]
                        });
                    }
                });

        }

        if (activeStageIndx >= 1 && !(($('#dataFileWizard').is(":visible")))) {
            $('#copo-datafile-tabs.nav-tabs a[href="#descriptionWizardComponent"]').tab('show'); //set display to description pane
        }


        //initialise paired datafile table

        var pairedTable = null;
        if ($.fn.dataTable.isDataTable('#datafile_pairing_table_' + activeStageIndx)) {
            //if table instance already exists, then do refresh
            pairedTable = $('#datafile_pairing_table_' + activeStageIndx).DataTable();
        }

        if (pairedTable) {
            //clear old, set new data
            pairedTable.clear().draw();
            pairedTable.rows.add(dtdPaired);
            pairedTable.columns.adjust().draw();
        } else {
            var tableElem = $('#datafile_pairing_table_' + activeStageIndx);
            pairedTable = tableElem.DataTable({
                "data": dtdPaired,
                "lengthChange": true,
                "columns": [
                    {
                        "data": "target",
                        "render": function (rdata) {
                            var rowObject = $('<div/>',
                                {
                                    style: "display: table; width: 100%; border: 1px solid rgba(229, 239, 255, 1.0); border-radius: 4px; background: rgba(229, 239, 255, 0.3);"
                                });

                            var col1Object = $('<div/>',
                                {
                                    style: "display: table-cell; vertical-align: middle; padding: 5px;"
                                }).append('<ol><li>' + rdata[0] + '</li><li>' + rdata[1] + '</li></ol>');

                            rowObject.append(col1Object);

                            var unpairButton = $('<a/>',
                                {
                                    href: "#",
                                    class: "btn btn-xs btn-danger unpair-datafiles",
                                    style: "display: inline-block; white-space: normal; background-image: none; border: none;",
                                    title: "Unpair datafiles",
                                    "data-toggle": "tooltip",
                                    html: '<i class="fa fa-chain-broken" aria-hidden="true" style=" font-size: 12px !important;"></i>'
                                });

                            var col2Object = $('<div/>',
                                {
                                    style: "display: table-cell; vertical-align: middle; padding: 5px; width: 2%; text-align: right; border-left: 1px solid rgba(229, 239, 255, 1.0);"
                                }).append(unpairButton);

                            rowObject.append(col2Object);

                            return $('<div/>').append(rowObject).html();
                        }
                    },
                    {
                        "data": "target_id",
                        "visible": false
                    },
                ],
                "fnDrawCallback": function (oSettings) {
                    refresh_tool_tips();
                },
                scrollCollapse: true,
                selectable: true,
                dom: 'fr<"row"><"row description-rw" i>tlp'
            });
        }

        $('#datafile_pairing_table_' + activeStageIndx + '_wrapper')
            .find(".dataTables_filter")
            .find("input")
            .removeClass("input-sm")
            .attr("placeholder", "Search paired")
            .attr("size", 25);

        refresh_inDescription_flag();
        set_stage_message();
    } //end update_paired_display

    function refresh_paired_files_display() {
        var request_params = {
            'request_action': 'negotiate_datafile_pairing',
            'description_token': descriptionToken,
            'description_targets': JSON.stringify(descriptionBundle)
        };

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: request_params,
            success: function (data) {
                var new_addition = null;
                try {
                    new_addition = data.pairing_info.add_to_bundle;
                } catch (err) {
                    ;
                }
                if (new_addition && new_addition.length > 0) {
                    //update description bundle
                    for (var i = 0; i < new_addition.length; ++i) {
                        descriptionBundle.push(new_addition[i]);
                    }
                }

                if (data.targets_data) {
                    refresh_targets_data(data.targets_data);
                }
                update_paired_display(data);
                suggest_pairing_action(data);
            },
            error: function () {
                alert("Couldn't obtain pairing information!");
            }
        });
    }


    function save_bundle_item_form(activeStageIndx, descriptionTarget) {
        //get form elements for item
        var form_values = Object();

        $('#wizard_item_form_' + activeStageIndx).find(":input").each(function () {
            form_values[this.id] = $(this).val();
        });

        var deTargs = []; //description targets

        descriptionBundle.forEach(function (item) {
            if (descriptionTarget == item.recordID) {
                deTargs.push(item);
                return false;
            }
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
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: request_params,
            success: function (data) {
                //refresh bundle
                if (data.targets_data) {
                    refresh_targets_data(data.targets_data);

                    //refresh description batch display
                    refresh_batch_display();

                    //get the next item in line
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
            },
            error: function () {
                alert("Couldn't save entries!");
            }
        });
    }

    function do_datafile_unpairing(elem) {
        //function unpair paired datafiles
        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index
        var table = $('#datafile_pairing_table_' + activeStageIndx).DataTable();
        var tr = elem.closest('tr');
        var row = table.row(tr);


        var deTargs = [];

        descriptionBundle.forEach(function (item) {
            if ((item.recordID == row.data().target_id[0]) || (item.recordID == row.data().target_id[1])) {
                deTargs.push(item);
            }
        });


        if (deTargs.length != 2) {//two files needed for pairing
            return false;
        }

        var request_params = {
            'request_action': 'datafile_unpairing',
            'description_token': descriptionToken,
            'description_targets': JSON.stringify(deTargs),
            'description_bundle': JSON.stringify(descriptionBundle)
        };

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: request_params,
            success: function (data) {
                if (data.result == true) {
                    if (data.targets_data) {
                        refresh_targets_data(data.targets_data);
                    }
                    refresh_paired_files_display();
                } else {
                    ;
                }
            },
            error: function () {
                alert("Couldn't unpair datafiles!");
            }
        });
    }


    function update_itemMetadata_flag() {
        //function sets/updates metadata flag for datafiles
        var tableID = componentMeta.tableID;
        var table = $('#' + tableID).DataTable();

        var datafile_ids = []; //
        $.map(table.rows({page: 'current'}).data(), function (item) {
            datafile_ids.push(item.record_id);
        });

        if (datafile_ids.length == 0) {
            return false;
        }


        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'task': 'metadata_ratings',
                'component': component,
                'datafile_ids': JSON.stringify(datafile_ids)
            },
            success: function (data) {
                if (!data.metadata_ratings) {
                    return false;
                }

                for (var i = 0; i < data.metadata_ratings.length; ++i) {
                    var rating_object = data.metadata_ratings[i];

                    if ($('#' + tableID).find('.' + tableID + rating_object.item_id).length) {
                        var targetObject = $('#' + tableID).find('.' + tableID + rating_object.item_id).find(".metadata-rating");
                        targetObject.removeClass("uncertain poor fair good");


                        var metadataDescription = "";
                        if (rating_object.item_rating.hasOwnProperty("rating_level")) {
                            targetObject.addClass(rating_object.item_rating.rating_level);
                            metadataDescription = rating_object.item_rating.rating_level_description;
                        } else {
                            targetObject.addClass("uncertain");
                            metadataDescription = "Couldn't resolve metadata rating!";
                        }

                        targetObject.webuiPopover('destroy');
                        targetObject.webuiPopover({
                            title: "Metadata Rating",
                            content: '<div class="webpop-content-div">' + metadataDescription + '</div>',
                            trigger: 'hover',
                            width: 300,
                            arrow: true,
                            closeable: true,
                            placement: 'auto',
                            backdrop: false,
                        });

                    }
                }

            },
            error: function () {
                alert("Couldn't resolve metadata ratings!");
            }
        });

    }

    function refresh_inDescription_flag() {
        var activeStageIndx = 0;

        if (descriptionBundle.length > 0) {
            activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index
        }


        var tableID = componentMeta.tableID;
        var table = $('#' + tableID).DataTable();

        //remove previous highlights
        table.columns('.describe-status').every(function () {
            var node = this.nodes();
            $(node)
                .removeClass('row-describing-highlight')
                .attr("title", "");
        });

        //highlight currently described records
        descriptionBundle.forEach(function (item) {
            table.rows('.' + tableID + item.recordID).every(function (rowIdx, tableLoop, rowLoop) {
                var node = this.node();
                $(node).find('.describe-status')
                    .addClass('row-describing-highlight')
                    .attr("title", "Currently being described");
            });
        });

        $(".description-count").remove();

        if (descriptionBundle.length > 0) {
            $('<span class="description-count row-describing-highlight badge" style="margin-left: 10px; font-size: 13px; padding: 5px;">' + descriptionBundle.length + ' record(s) currently being described</span>').insertAfter('.extra-table-info');
        }


        //reset inDescription flag
        $('.inDescription-flag').each(function () { //main datafile table
            $(this).hide();
        });

        $('.inDescription-flag-1').each(function () { //description bundle
            $(this).hide();
        });

        var current_stage_object = get_current_stage_object();
        var stage_ref = '';
        if (current_stage_object) {
            stage_ref = current_stage_object.ref;
        }
        descriptionBundle.forEach(function (item) {
            $('.inDescription-flag-1').each(function () {
                if ($(this).attr("data-record-id") == item.recordID) {
                    try {
                        if (item["attributes"][stage_ref]) {
                            $(this).show();
                        }
                    } catch (err) {

                    }
                }
            });
        });
    }

    function show_hide_stage_ctrl(applyToAll, activeStageIndx) {

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

        var current_stage_object = get_current_stage_object();

        if (((current_stage_object && current_stage_object.hasOwnProperty("is_singular_stage") && current_stage_object.is_singular_stage)) || applyToAll) {
            if (current_stage_object && current_stage_object.hasOwnProperty("is_singular_stage") && current_stage_object.is_singular_stage) {
                showChk = false;
            }

            //highlight all items in the bundle
            if (table) {
                table.rows('.selected').deselect();
                table.rows().select();
            }

        }


        if (showChk) { //apply to all check button activated
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
        refresh_inDescription_flag();
        set_stage_message();


    } //end of func

    function set_stage_message() {
        var activeStageIndx = $('#dataFileWizard').wizard('selectedItem').step; //active stage index
        //set stage message
        var current_stage_object = get_current_stage_object();
        if (current_stage_object) {
            if (current_stage_object && current_stage_object.hasOwnProperty("message")) {

                if (!displayedMessages.hasOwnProperty(current_stage_object.ref)) {
                    var alertType = "info";
                    var alertMessage = "<div style='margin-bottom: 10px;'><strong>" + current_stage_object.title + "</strong></div><div>" + current_stage_object.message + "</div>";
                    display_copo_alert(alertType, alertMessage, 20000);
                    displayedMessages[current_stage_object.ref] = 1;
                }
            }
        }
    }

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

        //handle custom cases e.g., datafiles pairing
        var current_stage_object = get_current_stage_object();
        if (current_stage_object && current_stage_object.ref == "datafiles_pairing") {
            return false;
        }

        $('#alert_placeholder_' + activeStageIndx).show();

        if (descriptionBundle.length == 1) { //only one item being described
            set_stage_alerts(wizardMessages.singleton_item_alert_message, activeStageIndx);
            $('#alert_placeholder_' + activeStageIndx).hide();
        } else if (current_stage_object && current_stage_object.hasOwnProperty("is_singular_stage") && current_stage_object.is_singular_stage) { //singular stage
            set_stage_alerts(wizardMessages.singular_stage_message, activeStageIndx);
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
        var contentHtml = '<span class="' + message_object.text_class + '">' + message_object.text + '</span>';
        elem.find(".apply-to-all-message").html(contentHtml);
    }

    function suggest_pairing_action(data) {
        var suggested_pairings = data.pairing_info.suggested_pairings; //pairable candidates to be suggested

        if (suggested_pairings.length == 0) {
            return false;
        }

        var dtdPaired = []; //define suggestion table data source
        for (var i = 0; i < suggested_pairings.length; ++i) { //suggestion data source
            var pair = suggested_pairings[i];
            var option = {};
            option["target"] = [pair[0].recordLabel, pair[1].recordLabel];
            option["target_id"] = [pair[0].recordID, pair[1].recordID];

            dtdPaired.push(option);
        }

        var suggestionLoader = $('<div style="margin-left: 40%; margin-top: 30px;" class="copo-i-loader"></div>');
        var suggestionTable = null;

        BootstrapDialog.show({
            title: "Suggested datafiles pairing",
            message: $('<div></div>').append('<table id="datafiles_pairing_suggestion" class="ui celled stripe table hover copo-noborders-table" cellspacing="0" width="100%"></table>').append(suggestionLoader),
            cssClass: 'copo-modal4',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_PRIMARY,
            onshown: function (dialogRef) {
                suggestionLoader.remove();
                //display suggestions
                var tableID = 'datafiles_pairing_suggestion';
                if ($.fn.dataTable.isDataTable('#' + tableID)) {
                    //if table instance already exists, then destroy in order to successfully re-initialise
                    $('#' + tableID).destroy();
                }

                var dataSet = dtdPaired;
                suggestionTable = $('#' + tableID).DataTable({
                    data: dataSet,
                    "columns": [
                        {
                            "data": "target",
                            "title": "Suggested pair",
                            "render": function (rdata) {
                                var rowObject = $('<div/>');

                                var col1Object = $('<div/>',
                                    {
                                        style: "padding: 5px;"
                                    }).append('<div style="padding-bottom: 5px;">1. ' + rdata[0] + '</div><div>2. ' + rdata[1] + '</div>');

                                rowObject.append(col1Object);

                                return $('<div/>').append(rowObject).html();
                            }
                        },
                        {
                            "data": "target_id",
                            "visible": false
                        },
                    ],
                    language: {
                        select: {
                            rows: {
                                _: "<strong>%d pairing suggestions selected. Click 'Apply' to confirm</strong>",
                                0: "<strong>Click a row or the 'Select all' button to accept suggested pairings</strong>",
                                1: "<strong>1 pairing suggestion selected. Click 'Apply' to confirm</strong>"
                            }
                        },
                    },
                    "fnDrawCallback": function (oSettings) {
                        refresh_tool_tips();
                    },
                    scrollCollapse: true,
                    select: {
                        style: 'multi', //os, multi, api
                    },
                    buttons: [
                        'selectAll',
                        'selectNone'
                    ],
                    dom: 'Bfr<"row"><"row description-rw" i>tlp'
                });

                suggestionTable
                    .buttons()
                    .nodes()
                    .each(function (value) {
                        $(this)
                            .removeClass("btn btn-default")
                            .addClass('tiny ui basic primary button');
                    });

                // suggestionTable.rows().select();
            },
            buttons: [
                {
                    label: 'Cancel',
                    cssClass: 'tiny ui basic button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                },
                {
                    label: 'Apply',
                    cssClass: 'tiny ui basic primary button',
                    action: function (dialogRef) {
                        var selectedRows = suggestionTable.rows({
                            selected: true
                        }).data();

                        if (selectedRows.length > 0) {
                            var description_targets = [];
                            for (var i = 0; i < selectedRows.length; ++i) {
                                var deTargs = [];
                                var pair = selectedRows[i]
                                descriptionBundle.forEach(function (item) {
                                    if ((item.recordID == pair.target_id[0]) || (item.recordID == pair.target_id[1])) {
                                        deTargs.push(item);
                                    }
                                });

                                if (deTargs.length == 2) {//two files needed for pairing
                                    var description_targets = description_targets.concat(deTargs);
                                }
                            }

                            var request_params = {
                                'request_action': 'datafile_pairing',
                                'description_token': descriptionToken,
                                'description_targets': JSON.stringify(description_targets),
                                'description_bundle': JSON.stringify(descriptionBundle)
                            };

                            $.ajax({
                                url: wizardURL,
                                type: "POST",
                                headers: {
                                    'X-CSRFToken': csrftoken
                                },
                                data: request_params,
                                success: function (data) {
                                    if (data.targets_data) {
                                        refresh_targets_data(data.targets_data);
                                    }
                                    refresh_paired_files_display();
                                },
                                error: function () {
                                    alert("Couldn't pair datafiles!");
                                }
                            });

                            dialogRef.close();
                        } else {
                            alert("Please select one or more rows!");
                        }
                    }
                }
            ]
        });
    }


    function load_datafile_records(componentMeta) {
    var csrftoken = $.cookie('csrftoken');

    //loader
    var tableLoader = null;
    if ($("#component_table_loader").length) {
        tableLoader = $('<div class="copo-i-loader"></div>');
        $("#component_table_loader").append(tableLoader);
    }

    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'task': 'table_data',
            'component': componentMeta.component
        },
        success: function (data) {
            do_render_component_table(data, componentMeta);
            //remove loader
            if (tableLoader) {
                tableLoader.remove();
            }
        },
        error: function () {
            alert("Couldn't retrieve " + componentMeta.component + " data!");
        }
    });
}

}) //end document ready