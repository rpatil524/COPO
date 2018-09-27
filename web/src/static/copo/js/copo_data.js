var wizardMessages;
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

    //load description bundles
    load_description_bundles();


    //get component metadata
    var componentMeta = get_component_meta(component);
    componentMeta.table_columns = JSON.parse($("#table_columns").val());
    do_render_server_side_table(componentMeta);

    //load records
    //load_records(componentMeta);


    // handle/attach events to table buttons
    $('body').on('addbuttonevents', function (event) {
        do_record_task(event);
    });

    //trigger refresh of table
    $('body').on('refreshtable', function (event) {
        do_render_component_table(globalDataBuffer, componentMeta);
    });

    //refresh metadata rating after table redraw
    $('body').on('posttablerefresh', function (event) {
        refresh_inDescription_flag();
    });

    //details button hover
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view ' + component + ' details');
    });

    //metadata-info
    $('body').on('showrecordbundleinfo', function (event) {
        show_record_bundle_info(event);
    });

    //reload description 1
    $(document).on("click", ".reload-description-i", function (event) {
        event.preventDefault();
        WebuiPopovers.hideAll();
        initiate_datafile_description({'description_token': $(this).attr("data-record")});
    });

    //reload description 2
    $(document).on("click", ".bundle-name-i", function (event) {
        event.preventDefault();
        WebuiPopovers.hideAll();
        initiate_datafile_description({'description_token': $(this).closest(".bundle-action-btn").attr("data-record")});
    });

    //show bundle details
    $(document).on("click", ".bundle-more-info", function (event) {
        event.preventDefault();
        WebuiPopovers.hideAll();
        show_bundle_details($(this), $(this).closest(".bundle-action-btn").attr("data-record"));
    });

    //description bundle view
    $(document).on("click", ".bundle-view", function (event) {
        event.preventDefault();
        do_view_description($(this).attr("data-target"));
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

    //description-bundle-explained
    $(document).on("click", ".description-bundle-explained", function (event) {
        event.preventDefault();
        var item = $(this);
        item.webuiPopover('destroy');

        item.webuiPopover({
            content: '<div class="webpop-content-div limit-text">A description bundle is a collection of datafiles with similar attributes, which can potentially be described as a single unit.</div>',
            trigger: 'sticky',
            width: 300,
            arrow: true,
            placement: 'right',
            dismissible: true,
            closeable: true
        });
    });

    //handle event for adding datafiles to a description bundle
    $('#bundle_add_act').on('click', function (event) {
        event.preventDefault();

        var tableID = 'bundle_add_view_tbl';
        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        var $dialogContent = $('<div/>');
        var table_div = $('<div/>').append(tbl);
        var filter_message = $('<div style="margin-bottom: 20px; font-weight: bold;">Note: Listed datafiles are those that do not belong to any description bundle!</div>');
        var spinner_div = $('<div/>', {style: "margin-left: 40%; padding-top: 15px; padding-bottom: 15px;"}).append($('<div class="copo-i-loader"></div>'));

        var dialog = new BootstrapDialog({
            type: BootstrapDialog.TYPE_PRIMARY,
            size: BootstrapDialog.SIZE_NORMAL,
            title: function () {
                return $('<span>Datafiles</span>');
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
                        'request_action': 'get_unbundled_datafiles',
                        'description_token': datafileDescriptionToken,
                        'profile_id': $('#profile_id').val()
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
                                style: 'multi',
                                selector: 'td:first-child'
                            },
                            columns: cols,
                            dom: 'lfit<"row">rp'
                        });

                        $('#' + tableID + '_wrapper')
                            .find(".dataTables_filter")
                            .find("input")
                            .removeClass("input-sm")
                            .attr("placeholder", "Search datafiles");

                    },
                    error: function () {
                        alert("Couldn't display datafiles!");
                        dialogRef.close();
                    }
                });
            },
            buttons: [{
                label: 'Cancel',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    dialogRef.close();
                }
            },
                {
                    label: 'Add selected',
                    cssClass: 'tiny ui basic teal button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                }]
        });


        $dialogContent.append(filter_message).append(table_div).append(spinner_div);
        dialog.realize();
        dialog.setMessage($dialogContent);
        dialog.open();
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
            size: BootstrapDialog.SIZE_NORMAL,
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
                            dom: 'lfit<"row">rp'
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

    //custom stage renderers
    var dispatchStageRenderer = {
        perform_datafile_generation: function (stage) {
            generate_datafile_edit_table(stage);
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
    $('#reload_act').on('click', function (event) {
        window.location.reload();
    });

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
                    $("#datafile_description_panel_title").html(" - " + wizard_components.description_label);
                }

                //refresh description bundles display
                load_description_bundles();
                refresh_inDescription_flag();

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
        var row = $('<div/>', {
            class: "row"
        });

        var left = $('<div/>', {
            class: "col-sm-8"
        });

        var right = $('<div/>', {
            class: "col-sm-4"
        });

        var message = $('<div/>', {class: "webpop-content-div"});
        message.append(stage_message);

        var panel = get_panel('info');
        panel.find('.panel-body').append(message);
        panel.find('.panel-heading')
            .append('<i style="font-size: 20px;" class="fa fa-info-circle text-info"></i>')
            .css({"padding-top": "5px", "padding-bottom": "5px"});
        panel.find(".panel-footer").remove();
        right.append(panel);

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
        } else if (task == "describe") {
            initiate_datafile_description({'​description_targets': records});
        } else if (task == "unbundle") {
            unbundle_datafiles(records);
        } else if (task == "discard") {
            do_undescribe_confirmation(records);
        }

    } //end of func

    function initiate_datafile_description(parameters) {
        $('[data-toggle="tooltip"]').tooltip('destroy');

        if (!$("#wizard_toggle").is(":visible")) {

            // //display wizard
            // $("#wizard_toggle").collapse("toggle");
            //
            // //hide the review stage -- to be redisplayed when all the dynamic stages are displayed
            // wizardElement.find('.steps li:last-child').hide();
            //
            // set_up_validator($("#wizard_form_1"));
            // toggle_disable_next();
            //
            // return false;


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

                                //check for description name
                                if (data.result.hasOwnProperty('description_label') && data.result.description_label.trim() != '') {
                                    $("#datafile_description_panel_title").html(" - " + data.result.description_label);
                                }

                                set_up_validator($("#wizard_form_1"));

                                dialogRef.close();

                            } else {
                                var $feeback = $('<div/>', {
                                    "class": "webpop-content-div",
                                    style: "padding-bottom: 15px;"
                                }).html("Please resolve the following issue.<div style='margin-top: 10px; margin-bottom: 15px;'>" + data.result.message + "</div>");

                                dialog.setType(BootstrapDialog.TYPE_DANGER);
                                dialog.getModalBody().html('').append($feeback);
                                $($(dialog.getModalFooter()).find("#btn-resolve-issue")[0])
                                    .removeClass('primary')
                                    .addClass('red')
                                    .html('Resolve issue');
                            }

                        },
                        error: function () {
                            alert("Error instantiating description!");
                        }
                    });
                },
                buttons: [{
                    id: 'btn-resolve-issue',
                    label: 'OK',
                    cssClass: 'tiny ui basic primary button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                }]
            });

            $dialogContent.append(notice_div).append(spinner_div);
            dialog.realize();
            dialog.setMessage($dialogContent);
            dialog.open();

        } else {//wizard is already visible
            var message = "There's an ongoing description. <ul><li>Exit the current description before initiating another</li><li>Use the <strong>Add to bundle</strong> button on the description wizard panel to add datafiles to the current description</li></ul>";

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
                        label: 'OK',
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

    function do_undescribe_confirmation(records) {
        //function deletes description metadata from datafiles

        var tableID = componentMeta.tableID;
        var table = $('#' + tableID).DataTable();

        BootstrapDialog.show({
            title: "Discard description metadata",
            message: "Are you sure you want to remove description metadata for the <strong>" + records.length + "</strong> datafiles selected?",
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            size: BootstrapDialog.SIZE_NORMAL,
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
                                table.rows().deselect(); //deselect all rows
                                server_side_select[component] = [];
                            },
                            error: function () {
                                alert("Couldn't discard description for selected records!");
                                table.rows().deselect(); //deselect all rows
                                server_side_select[component] = [];
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
        $('#custom-renderer_' + stage.ref).find(".stage-content")
            .html('')
            .append(stageHTML);

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

                dtColumns = data.table_data.columns;
                dtRows = data.table_data.rows;

                render_datafile_attributes_table(tableID);

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
                        extend: 'excel',
                        text: 'Export',
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

    function show_bundle_details(item, target_id) {
        item.webuiPopover('destroy');

        item.webuiPopover({
            title: "Details",
            content: '<div class="webpop-content-div limit-text">A description bundle is a collection of datafiles with similar attributes, which can potentially be described as a single unit.</div>',
            trigger: 'sticky',
            width: 300,
            arrow: true,
            placement: 'right',
            dismissible: true,
            closeable: true
        });
    }

    function load_description_bundles() {
        WebuiPopovers.hideAll();

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': "get_description_records",
                'profile_id': $('#profile_id').val()
            },
            success: function (data) {
                if (data.records && data.records.dataSet) {

                    var dtd = data.records.dataSet;
                    // var cols = data.records.columns;

                    if (dtd.length > 0) {
                        $(".desc-bundle-display-div").show();
                        $(".desc-bundle-display-div").find(".desc-bundle-display-div-2").html('');

                        for (var i = 0; i < dtd.length; ++i) {
                            var Ddata = dtd[i];

                            var actionBTN = $(".record-action-templates").find(".description_bundle_button").clone();
                            actionBTN.removeClass("description_bundle_button");
                            actionBTN.addClass("bundle-action-btn");
                            actionBTN.find(".bundle-name-i").find("span").html(Ddata.name);
                            // actionBTN.find(".bundle-count").find("span").html(Ddata.number_of_datafiles);
                            actionBTN.attr("data-record", Ddata.id);
                            $(".desc-bundle-display-div").find(".desc-bundle-display-div-2").append(actionBTN);
                            //
                            // actionBTN.on("click", ".bundle-name", function (event) {
                            //     var bundleID = $(this).closest(".bundle-action-btn").attr("data-record");
                            //     initiate_datafile_description({'description_token': bundleID});
                            // });
                            //
                            // actionBTN.on("click", ".bundle-count", function (event) {
                            //     var bundleID = $(this).closest(".bundle-action-btn").attr("data-record");
                            //     do_view_description(bundleID);
                            // });
                            //
                            // actionBTN.on("click", ".bundle-cut", function (event) {
                            //     var bundleID = $(this).closest(".bundle-action-btn").attr("data-record");
                            //     $(this).find("i").addClass("fa-spin red");
                            //     delete_description_record(bundleID, $(this));
                            // });

                        }
                    } else {
                        $(".desc-bundle-display-div").find(".desc-bundle-display-div-2").html('');
                        $(".desc-bundle-display-div").hide();
                    }
                } else {
                    $(".desc-bundle-display-div").find(".desc-bundle-display-div-2").html('');
                    $(".desc-bundle-display-div").hide();
                }
            },
            error: function () {
                console.log("Couldn't complete request for description bundles");
            }
        });
    } //end of function

    function do_view_description(description_token) {
        //show description bundle

        var tableID = 'description_view_tbl';
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
            size: BootstrapDialog.SIZE_NORMAL,
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
                        'description_token': description_token
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
                                style: 'multi',
                                selector: 'td:first-child'
                            },
                            columns: cols,
                            dom: 'lfit<"row">rp'
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
    } // end of function


    function refresh_inDescription_flag() {
        var tableID = componentMeta.tableID;
        var table = $('#' + tableID).DataTable();

        var shownRows = table.rows({page: 'current'}).nodes().toArray();
        var target_rows = table.rows({page: 'current'}).ids().toArray();

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': 'match_to_description',
                'profile_id': $('#profile_id').val(),
                'description_targets': JSON.stringify(target_rows)
            },
            success: function (data) {
                var result = data.result;

                for (var i = 0; i < shownRows.length; ++i) {
                    var metaElem = $(shownRows[i]).find(".metadata-rating");
                    metaElem.removeClass('in-desc');
                    metaElem.addClass('uncertain');
                    metaElem.attr("data-target", "");

                    var rowID = $(shownRows[i]).attr("id");

                    var index = $.inArray(rowID, result);

                    if (index > -1) {
                        metaElem.removeClass('uncertain');
                        metaElem.addClass('in-desc');
                    }
                }
            },
            error: function () {
                alert("Couldn't retrieve bundling information!");
            }
        });
    } //end of function

    function show_record_bundle_info(eventTarget) {
        var table = $('#' + eventTarget.tableID).DataTable();
        var rowData = table.row("#" + eventTarget.rowId).data();

        var recordID = eventTarget.rowId.split("row_")[1];

        var item = $('#' + eventTarget.tableID).find($("#" + eventTarget.rowId)).find("td.describe-status");
        item.find(".fa").addClass("fa-spin");
        item.webuiPopover('destroy');

        console.log(item.html())

        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'task': "description_summary",
                'component': component,
                'target_id': recordID
            },
            success: function (data) {
                var gAttrib = {};
                gAttrib = build_description_display(data);

                var message = 'Datafile does not belong to any description bundle.';
                message = '<div style="color: #c93c00; margin-bottom: 10px;">' + message + '</div>';

                if (data.description.description_record.name) {
                    message = 'Datafile is part of <span style="font-weight: bold;">' + data.description.description_record.name + '</span> bundle.';

                    var reloaddesc = $('<div/>',
                        {
                            style: "margin-top: 5px; margin-bottom: 10px;"
                        });

                    var reloader = $('<a/>',
                        {
                            "class": "reload-description-i",
                            style: "text-decoration: none; color: #2a66a2;",
                            "data-record": data.description.description_record.id,
                            "role": "button",
                            title: "reload description",
                            "aria-haspopup": "true",
                            "aria-expanded": "false"
                        }).append('<i class="fa fa-refresh" aria-hidden="true"></i>&nbsp; Reload bundle');

                    reloaddesc.append(reloader).append("<hr/>");

                    message += $('<div/>').append(reloaddesc).html();
                }

                item.webuiPopover({
                    title: rowData.name,
                    content: '<div class="webpop-content-div limit-text">' + message + $('<div/>').append(gAttrib).html() + '</div>',
                    trigger: 'sticky',
                    width: 300,
                    arrow: true,
                    placement: 'right',
                    dismissible: true,
                    closeable: true
                });

                item.find(".fa").removeClass("fa-spin");
            },
            error: function () {
                item.find(".fa").removeClass("fa-spin");
                var message = "Couldn't retrieve datafile attributes!";

                item.webuiPopover({
                    title: rowData.name,
                    content: '<div class="webpop-content-div">' + message + '</div>',
                    trigger: 'sticky',
                    width: 300,
                    arrow: true,
                    placement: 'right',
                    dismissible: true,
                    closeable: true
                });
            }
        });

    } //end of function

    function unbundle_datafiles(records) {
        //function unbundles datafiles

        var tableID = componentMeta.tableID;
        var table = $('#' + tableID).DataTable();

        //should be able to unbundle if there's a current description
        if ($("#wizard_toggle").is(":visible")) {
            BootstrapDialog.show({
                title: "[Un]bundle action",
                message: "<div style='color: #ff0000;'>[Un]bundle action not allowed with a running description session! Please retry this action when not describing.</div>",
                // cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [
                    {
                        label: 'OK',
                        cssClass: 'tiny ui basic button',
                        action: function (dialogRef) {
                            table.rows().deselect(); //deselect all rows
                            server_side_select[component] = [];
                            dialogRef.close();
                            return false;
                        }
                    }]
            });

            return false;
        } else {
            BootstrapDialog.show({
                title: "[Un]bundle action",
                message: "Are you sure you want to remove bundling information for the selected datafiles? <div style='margin-top: 20px; color: #ff0000;'>This action might impact referenced components if you choose to continue.</div>",
                // cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_DANGER,
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
                        label: '<i class="fa fa-times-circle" aria-hidden="true"></i> [Un]bundle',
                        cssClass: 'tiny ui basic red button',
                        action: function (dialogRef) {
                            $.ajax({
                                url: wizardURL,
                                type: "POST",
                                headers: {
                                    'X-CSRFToken': csrftoken
                                },
                                data: {
                                    'request_action': 'unbundle_datafiles',
                                    'description_targets': JSON.stringify(records)
                                },
                                success: function (data) {
                                    load_description_bundles();
                                    refresh_inDescription_flag();
                                    table.rows().deselect(); //deselect all rows
                                    server_side_select[component] = [];
                                },
                                error: function () {
                                    alert("Couldn't complete request to [un]bundle");
                                    table.rows().deselect(); //deselect all rows
                                    server_side_select[component] = [];
                                }
                            });

                            dialogRef.close();
                            return false;
                        }
                    }
                ]
            });
        }

    }

    function delete_description_record(bundle_id, elem) {
        //function deletes a description record - participating datafiles keep their metadata though

        //shouldn't be able to delete current description
        if (bundle_id == datafileDescriptionToken) {
            BootstrapDialog.show({
                title: "[Un]bundle",
                message: "Can't [Un]bundle a current description!",
                cssClass: 'copo-modal3',
                closable: false,
                animate: true,
                type: BootstrapDialog.TYPE_WARNING,
                buttons: [
                    {
                        label: 'OK',
                        cssClass: 'tiny ui basic button',
                        action: function (dialogRef) {
                            elem.find("i").removeClass("fa-spin red");
                            dialogRef.close();
                            return false;
                        }
                    }]
            });

            return false;
        }

        BootstrapDialog.show({
            title: "Remove bundle",
            message: "Are you sure you want to remove bundling information for the selected description record? <div style='margin-top: 20px; color: #ff0000;'>This action might impact referenced components if you choose to continue.</div>",
            // cssClass: 'copo-modal3',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            buttons: [
                {
                    label: 'Cancel',
                    cssClass: 'tiny ui basic button',
                    action: function (dialogRef) {
                        elem.find("i").removeClass("fa-spin red");
                        dialogRef.close();
                        return false;
                    }
                },
                {
                    label: '<i class="cut icon" aria-hidden="true"></i> Remove',
                    cssClass: 'tiny ui basic red button',
                    action: function (dialogRef) {
                        $.ajax({
                            url: wizardURL,
                            type: "POST",
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                            data: {
                                'request_action': 'delete_description_record',
                                'description_token': bundle_id
                            },
                            success: function (data) {
                                load_description_bundles();
                                refresh_inDescription_flag();
                            },
                            error: function () {
                                alert("Couldn't remove bundling information!");
                            }
                        });

                        dialogRef.close();
                        return false;
                    }
                }
            ]
        });
    }

}); //end document ready