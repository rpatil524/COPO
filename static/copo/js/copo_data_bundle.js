$(document).ready(function () {
    //****************************** Event Handlers Block *************************//


    //page global variables
    var csrftoken = $('[name="csrfmiddlewaretoken"]').val();
    var component = "datafile";
    var wizardURL = "/rest/data_wiz/";
    var copoFormsURL = "/copo/copo_forms/";

    //get component metadata
    var componentMeta = get_component_meta(component);
    componentMeta.table_columns = JSON.parse($("#table_columns").val());
    var bundleTableId = "copo_datafiles_bundle_table";

    //load description bundle
    load_description_bundles();

    //show bundle color code
    show_bundle_code();

    //show datafiles workflow
    show_datafiles_workflow();


    //bundle tasks
    $(document).on('click', '.bundlemenu', function (event) {
        event.preventDefault();
        dispatch_bundle_events($(this));
    });

    //create bundle
    $(document).on("click", ".create-bundle-btn, .mirror-create-bundle", function (event) {
        event.preventDefault();
        create_edit_description_bundle();
    });

    $('body').on('posttablerefresh', function (event) {
        add_draggable_event();
        add_droppable_event();
    });

    $(document).on("mouseover", ".draggable_tr", function (event) {
        $(this).addClass("dragcandidate");
    });

    $(document).on("mouseout", ".draggable_tr", function (event) {
        $(this).removeClass("dragcandidate");
    });

    //instantiate/refresh tooltips
    refresh_tool_tips();

    //****************************** Functions Block ******************************//

    function add_draggable_event() {
        $("#datafile_col_table_div .draggable-table tr").draggable({
            helper: function () {
                var selected = $('.draggable-table tr.selected, tr.dragcandidate');
                var container = $('<div/>').attr('class', 'draggingContainer');
                container.css({"z-index": 9000});
                container.append(selected.clone());
                container.find("td:first-child").remove();
                return container;
            }
        });
    }

    function add_droppable_event() {
        $("#datafile_col_table_div .draggable-table").droppable({
            drop: function (event, ui) {
                $(this).append(ui.helper.children());
                var pElem = $(this);
                var target_rows = [];
                var bundle_id = '';

                //get dropped rows
                pElem.find('.selected, .dragcandidate').each(function () {
                    target_rows.push($(this).attr("id"));
                });

                pElem.find('.pparent').each(function () {
                    bundle_id = $(this).attr("id");
                });

                if (bundle_id) {
                    $.ajax({
                        url: wizardURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: {
                            'request_action': 'unbundle_datafiles',
                            'description_targets': JSON.stringify(target_rows)
                        },
                        success: function (data) {
                            show_bundle_datafiles(bundle_id);
                            do_render_server_side_table(componentMeta);
                        },
                        error: function () {
                            alert("Couldn't complete request to unbundle!");
                        }
                    });
                } else {
                    //just refresh anyway to maintain valid state
                    //$('#' + componentMeta.tableID).DataTable().rows().deselect();
                    //server_side_select[component] = [];
                    do_render_server_side_table(componentMeta);
                }
            }
        });
    }

    function clone_bundle(bundle_id) {
        var bundleName = '';
        var displayTitle = "Create New Bundle [clone]";

        var dialog = new BootstrapDialog({
            type: BootstrapDialog.TYPE_PRIMARY,
            cssClass: 'copo-modal2',
            title: displayTitle,
            closable: false,
            animate: true,
            draggable: true,
            onshown: function (dialogRef) {
                form_body_div.find("#bundle_name_input").focus();
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
                    label: '<i class="copo-components-icons glyphicon glyphicon-save"></i> Save',
                    cssClass: 'tiny ui basic primary button',
                    action: function (dialogRef) {
                        var new_bundle_name = form_body_div.find("#bundle_name_input").val().replace(/^\s+|\s+$/g, '');

                        if (!new_bundle_name) {
                            form_message_div.html('<span class="text-danger">Please enter a bundle name</span>');
                            form_body_div.find("#bundle_name_input").focus();
                        } else {
                            $.ajax({
                                url: copoFormsURL,
                                type: "POST",
                                headers: {
                                    'X-CSRFToken': csrftoken
                                },
                                data: {
                                    'task': "clone_description_bundle",
                                    'bundle_name': new_bundle_name,
                                    'component': component,
                                    'target_id': bundle_id,
                                    'profile_id': $('#profile_id').val()
                                },
                                success: function (data) {
                                    if (data.result.status == "error") {
                                        form_message_div.html('<span class="text-danger">' + data.result.message + '</span>');
                                    } else {
                                        load_description_bundles();
                                        dialogRef.close();
                                    }
                                },
                                error: function () {
                                    form_message_div.html('<span class="text-danger">Couldn\'t create description bundle due to a system error!</span>');
                                }
                            });
                        }
                    }
                }
            ]
        });

        var $dialogContent = $('<div/>');

        var form_body_div = $('<div class="ui form" style="font-size: inherit;">\n' +
            '  <div class="inline field">\n' +
            '    <label>Bundle name</label>\n' +
            '    <input id="bundle_name_input" type="text" value="' + bundleName + '">\n' +
            '  </div>\n' +
            '</div>');

        var form_message_div = $('<div/>', {
            class: "webpop-content-div",
            style: "margin-bottom: 20px;",
            html: "Please provide a name for your bundle",
        });

        $dialogContent.append(form_message_div).append(form_body_div);
        dialog.realize();
        dialog.setMessage($dialogContent);
        dialog.open();
    }


    function create_edit_description_bundle(bundle_id) {
        var bundleName = '';
        var parentElem = null;
        var displayTitle = "Create New Bundle";

        if (bundle_id) {
            parentElem = $('.description-bundle-panel[data-id="' + bundle_id + '"]');
            bundleName = parentElem.attr("data-bundlename");
            displayTitle = "Edit Bundle";
        } else {
            bundle_id = ''; //control what we are dealing with here
        }

        var dialog = new BootstrapDialog({
            type: BootstrapDialog.TYPE_PRIMARY,
            cssClass: 'copo-modal2',
            title: displayTitle,
            closable: false,
            animate: true,
            draggable: true,
            onshown: function (dialogRef) {
                form_body_div.find("#bundle_name_input").focus();
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
                    label: '<i class="copo-components-icons glyphicon glyphicon-save"></i> Save',
                    cssClass: 'tiny ui basic primary button',
                    action: function (dialogRef) {
                        var new_bundle_name = form_body_div.find("#bundle_name_input").val().replace(/^\s+|\s+$/g, '');

                        if (!new_bundle_name) {
                            form_message_div.html('<span class="text-danger">Please enter a bundle name</span>');
                            form_body_div.find("#bundle_name_input").focus();
                        } else if (new_bundle_name == bundleName) {
                            dialogRef.close();
                            return false;
                        } else {
                            $.ajax({
                                url: copoFormsURL,
                                type: "POST",
                                headers: {
                                    'X-CSRFToken': csrftoken
                                },
                                data: {
                                    'task': "create_rename_description_bundle",
                                    'bundle_name': new_bundle_name,
                                    'component': component,
                                    'target_id': bundle_id,
                                    'profile_id': $('#profile_id').val()
                                },
                                success: function (data) {
                                    if (data.result.status == "error") {
                                        form_message_div.html('<span class="text-danger">' + data.result.message + '</span>');
                                    } else if (bundle_id) {
                                        parentElem.attr("data-bundlename", new_bundle_name);
                                        parentElem.find(".bundlename").html(new_bundle_name);
                                        dialogRef.close();
                                    } else {
                                        load_description_bundles();
                                        dialogRef.close();
                                    }
                                },
                                error: function () {
                                    form_message_div.html('<span class="text-danger">Couldn\'t create description bundle due to a system error!</span>');
                                }
                            });
                        }
                    }
                }
            ]
        });

        var $dialogContent = $('<div/>');

        var form_body_div = $('<div class="ui form" style="font-size: inherit;">\n' +
            '  <div class="inline field">\n' +
            '    <label>Bundle name</label>\n' +
            '    <input id="bundle_name_input" type="text" value="' + bundleName + '">\n' +
            '  </div>\n' +
            '</div>');

        var form_message_div = $('<div/>', {
            class: "webpop-content-div",
            style: "margin-bottom: 20px;",
            html: "Please provide a name for your bundle",
        });

        $dialogContent.append(form_message_div).append(form_body_div);
        dialog.realize();
        dialog.setMessage($dialogContent);
        dialog.open();
    }

    function show_bundle_code() {
        var message = $('<div class="webpop-content-div"></div>');

        var infoPanelElement = trigger_global_notification();

        var codeList = '<div style="margin-top: 10px;"><ul class="list-group">\n' +
            '  <li class="list-group-item active" style="background: #CACBCD; text-shadow: none; border-color: #CACBCD; color: #000;">Bundle color codes</li>\n' +
            '  <li class="list-group-item"><i title="" class="big icon stop circle outline grey"></i>Bundle is yet to be described/submitted or has partial metadata</li>\n' +
            '  <li class="list-group-item"><i title="" class="big icon stop circle outline green"></i>Bundle has been submitted</li>\n' +
            '  <li class="list-group-item"><i title="" class="big icon stop circle outline orange"></i>Bundle is pending submission or its submission is currently being processed</li>\n' +
            '  <li class="list-group-item"><i title="" class="big icon stop circle outline red"></i>Bundle has issues</li>\n' +
            '</ul></div>'


        message.append(codeList);
        infoPanelElement.prepend(message);
    }

    function show_datafiles_workflow() {
        var message = $('<div class="webpop-content-div"></div>');

        var infoPanelElement = trigger_global_notification();

        var codeList = '<div style="margin-top: 10px;"><ul class="list-group">\n' +
            '  <li class="list-group-item active" style="background: #CACBCD; text-shadow: none; border-color: #CACBCD; color: #000;">Datafiles workflow</li>\n' +
            '  <li class="list-group-item">' +
            '      <div class="content">\n' +
            '           <div class="title"><h3 class="ui header">Upload datafiles</h3></div>\n' +
            '           <div class="description">Start by uploading one or more datafiles</div>\n' +
            '      </div>\n' +
            '  </li>\n' +
            '  <li class="list-group-item">' +
            '      <div class="content">\n' +
            '           <div class="title"><h3 class="ui header">Create a bundle</h3></div>\n' +
            '           <div class="description">A bundle groups one or more \'related\' datafiles. You can have as many bundles as required</div>\n' +
            '      </div>\n' +
            '  </li>\n' +
            '  <li class="list-group-item">' +
            '      <div class="content">\n' +
            '           <div class="title"><h3 class="ui header">Add datafiles to bundle</h3></div>\n' +
            '           <div class="description">You can drag and drop datafiles to a bundle</div>\n' +
            '      </div>\n' +
            '  </li>\n' +
            '  <li class="list-group-item">' +
            '      <div class="content">\n' +
            '           <div class="title"><h3 class="ui header">Add metadata</h3></div>\n' +
            '           <div class="description">Describe and submit datafiles in the bundle</div>\n' +
            '      </div>\n' +
            '  </li>\n' +
            '</ul></div>'


        message.append(codeList);
        infoPanelElement.prepend(message);
    }


    function load_description_bundles() {
        var loader = $('<div class="copo-i-loader" style="margin-left: 40%;"></div>');
        $("#cover-spin-bundle").html(loader);

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
                try {
                    loader.remove();
                } catch (err) {
                }

                var dtd = data.records;

                if (dtd.length == 0) {
                    return false;
                }

                var tableID = bundleTableId;

                //set data
                var table = null;

                if ($.fn.dataTable.isDataTable('#' + tableID)) {
                    //if table instance already exists, then do refresh
                    table = $('#' + tableID).DataTable();
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
                    table = $('#' + tableID).DataTable({
                        data: dtd,
                        searchHighlight: true,
                        ordering: true,
                        lengthChange: false,
                        buttons: [],
                        select: false,
                        language: {
                            "emptyTable": "No datafiles bundle available! Use the Create bundle button to add one.",
                        },
                        order: [
                            [1, "desc"]
                        ],
                        columns: [
                            {
                                "data": null,
                                "orderable": false,
                                "render": function (data) {
                                    var renderHTML = $(".description-bundle-template")
                                        .clone()
                                        .removeClass("datatables-panel-template")
                                        .addClass("description-bundle-panel")
                                        .attr({"data-id": data.id, "data-bundlename": data.name});


                                    //set bundle attributes
                                    renderHTML.find(".bundlename").html(data.name);
                                    renderHTML.find(".bundle-modified-date").html(data.created_on);

                                    //set bundle status
                                    var bundleStatus = renderHTML.find(".bundle-status");
                                    var submission_status = data.submission_status.toString().toLowerCase();

                                    var bundle_description = '';
                                    var exclusion_list = [];

                                    if (submission_status == 'submitted') {
                                        bundleStatus.addClass("stop circle outline green");
                                        bundle_description = 'Bundle has been submitted. Select view accessions for accessions and DOIs.';
                                        bundleStatus.prop('title', 'This bundle has been submitted. Select view accessions for accessions and DOIs.');
                                        exclusion_list = ["view_issues", "add_metadata", "edit_bundle", "delete_bundle", "submit_bundle", "add_datafiles"];

                                    } else if (submission_status == 'pending') {
                                        bundleStatus.addClass("stop circle outline orange");
                                        bundle_description = 'Bundle is pending submission or submission is currently being processed.'
                                        bundleStatus.prop('title', 'This bundle is pending submission. Use the submit option to continue with the submission.');
                                        exclusion_list = ["delete_bundle", "submit_bundle"];
                                    } else if (submission_status == 'error') {
                                        bundleStatus.addClass("stop circle outline red");
                                        bundle_description = 'There are issues with this bundle. Use the view issues option for more information.'
                                        bundleStatus.prop('title', 'There are issues with this bundle. Use the view issues option for more information.');
                                    } else {
                                        bundleStatus.addClass("stop circle outline grey");
                                        bundle_description = 'Please add/edit metadata for this bundle.'
                                        bundleStatus.prop('title', 'Bundle is yet to be described or has partial metadata. Use the actions menu to add/edit metadata or to submit bundle.');
                                        exclusion_list = ["view_accessions", "view_issues"];
                                    }

                                    //disable non-applicable bundle actions
                                    renderHTML.find(".bundlemenu").each(function (indx, menuitem) {
                                        if (exclusion_list.indexOf($(menuitem).attr("data-task")) > -1) {
                                            $(menuitem).addClass("disabled");
                                        }
                                    });

                                    return $('<div/>').append(renderHTML).html();
                                }
                            },
                            {
                                "data": "s_n",
                                "title": "S/N",
                                "visible": false
                            },
                            {
                                "data": "name",
                                "title": "Name",
                                "visible": false
                            },
                            {
                                "data": "id",
                                "visible": false
                            },
                        ],
                        "columnDefs": [],
                        fnDrawCallback: function () {
                            refresh_tool_tips();
                        },
                        createdRow: function (row, data, index) {
                            $(row).find(".description-bundle-panel").droppable({
                                activeClass: "dropActive",
                                hoverClass: "dropHover",
                                drop: function (event, ui) {
                                    $(this).append(ui.helper.children());
                                    var pElem = $(this);
                                    var target_rows = [];

                                    pElem.find('.selected, .dragcandidate').each(function () {
                                        target_rows.push($(this).attr("id"));
                                    });

                                    if (target_rows.length <= 0) {
                                        return false;
                                    }

                                    //remove draggable rows from panel
                                    pElem.find(".draggable_tr").remove();

                                    var bundle_id = pElem.attr("data-id");

                                    $.ajax({
                                        url: wizardURL,
                                        type: "POST",
                                        headers: {
                                            'X-CSRFToken': csrftoken
                                        },
                                        data: {
                                            'request_action': 'add_to_bundle',
                                            'description_token': bundle_id,
                                            'description_targets': JSON.stringify(target_rows)
                                        },
                                        success: function (data) {
                                            $('#' + componentMeta.tableID).DataTable().rows().deselect();
                                            server_side_select[component] = [];
                                            show_bundle_datafiles(bundle_id);

                                            //check where this parcel came from
                                            var sibling_bundle_id = '';

                                            pElem.find('.pparent').each(function () {
                                                sibling_bundle_id = $(this).attr("id");
                                            });

                                            if (sibling_bundle_id && sibling_bundle_id != bundle_id) {
                                                //came from sibling bundle, refresh the sibling's view
                                                show_bundle_datafiles(sibling_bundle_id);
                                            } else {
                                                //came from main datafile table
                                                do_render_server_side_table(componentMeta);
                                            }
                                        },
                                        error: function () {
                                            alert("Couldn't add datafiles to bundle!");
                                        }
                                    });
                                }
                            });
                        },
                        dom: 'Bfr<"row"><"row info-rw" i>tlp',
                    });

                    table
                        .buttons()
                        .nodes()
                        .each(function (value) {
                            $(this)
                                .removeClass("btn btn-default")
                                .addClass('tiny ui basic button');
                        });
                }

                $('#' + tableID + '_wrapper')
                    .find(".dataTables_filter")
                    .find("input")
                    .removeClass("input-sm")
                    .attr("placeholder", "Search bundles")
                    .attr("size", 20);

            },
            error: function () {
                try {
                    loader.remove();
                } catch (err) {
                }
                console.log("Couldn't complete request for description bundles");
            }
        });
    } //end of function

    function view_bundle_metadata(description_token) {

        var parentElem = $('.description-bundle-panel[data-id="' + description_token + '"]');
        var viewPort = parentElem.find(".pbody");

        var loader = $('<div class="copo-i-loader" style="margin-left: 40%;"></div>');
        viewPort.html(loader);


        var tableID = 'bundle_metadata_view_tbl' + description_token;
        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        var meta_div = $('<div/>', {
            "style": "margin-bottom: 20px;"
        });
        var table_div = $('<div/>').append(tbl);

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': 'get_description_bundle_details',
                'description_token': description_token
            },
            success: function (data) {
                loader.remove();
                viewPort.append(meta_div).append(table_div);

                // meta_div.append("<div class='webpop-content-div'><strong>Bundle Name:</strong> " + data.result.name + "</div>");
                meta_div.append("<div class='webpop-content-div'><strong>No. of datafiles:</strong> " + data.result.number_of_datafiles + "</div>");
                meta_div.append("<div class='webpop-content-div'><strong>Metadata Template:</strong> " + data.result.target_repository + "</div>");
                meta_div.append("<div class='webpop-content-div'><strong>Last Modified:</strong> " + data.result.created_on + "</div>");

                var dtd = data.result.data_set;
                var cols = [
                    {title: "s/n", visible: false},
                    {title: "Label"},
                    {title: "Value"}
                ];

                var table = $('#' + tableID).DataTable({
                    data: dtd,
                    searchHighlight: true,
                    "lengthChange": false,
                    order: [
                        [0, "asc"]
                    ],
                    buttons: [
                        {
                            extend: 'csv',
                            text: 'Export Metadata',
                            title: null,
                            filename: "metadata_" + String(description_token)
                        }
                    ],
                    scrollY: "300px",
                    scrollX: true,
                    scrollCollapse: true,
                    paging: false,
                    columns: cols,
                    dom: "<'row'<'col-md-12'Bl>>" +
                        "<'row'<'col-md-12'>>" +
                        "<'row'<'col-md-12'i>>" +
                        "<'row'<'col-md-6'><'col-md-6'f>>" +
                        "<'row'<'col-md-12't>>" +
                        "<'row'<'col-md-6'r><'col-md-6'p>>",
                });

                table
                    .buttons()
                    .nodes()
                    .each(function (value) {
                        $(this)
                            .removeClass("btn btn-default")
                            .addClass('tiny ui button');
                    });

                //add custom buttons

                var customButtons = $('<span/>', {
                    style: "padding-left: 5px;",
                    class: "copo-table-cbuttons"
                });


                $(table.buttons().container())
                    .css("padding-bottom", "10px;")
                    .append(customButtons);
                $('#' + tableID + '_wrapper').css({"margin-top": "10px"});
                $('#' + tableID + '_wrapper').find(".info-rw").css({"margin-top": "10px"});

                // var actionMenu = $('<div/>',
                //     {
                //         class: "ui compact menu",
                //     });
                //
                // customButtons.append(actionMenu);
                //
                // var actionDropdownItem = $('<div/>',
                //     {
                //         class: "ui simple dropdown item",
                //         style: "font-size: 12px;",
                //         html: "Actions"
                //     });
                //
                // actionMenu.append(actionDropdownItem);
                // actionDropdownItem.append('<i class="dropdown icon"></i>');
                //
                // var actionDropdownMenu = $('<div/>',
                //     {
                //         class: "menu",
                //     });

                // actionDropdownItem.append(actionDropdownMenu);

                //Remove metadata
                // var actionRemoveMetadata = $('<div data-html="Remove bundle metadata. Datafiles in bundle retain their respective metadata" data-position="right center" class="item copo-tooltip">Remove metadata</div>');
                // actionDropdownMenu.append(actionRemoveMetadata);
                // actionRemoveMetadata.click(function (event) {
                //     event.preventDefault();
                //     remove_bundle_metadata(description_token);
                // });


                $('#' + tableID + '_wrapper')
                    .find(".dataTables_filter")
                    .find("input")
                    .removeClass("input-sm")
                    .attr("placeholder", "Search metadata");

                refresh_tool_tips();

            },
            error: function () {
                alert("Couldn't display description bundle!");
            }
        });

    } // end of function

    function show_bundle_datafiles(description_token) {
        //show files in description bundle
        WebuiPopovers.hideAll();

        var parentElem = $('.description-bundle-panel[data-id="' + description_token + '"]');
        var viewPort = parentElem.find(".pbody");

        var loader = $('<div class="copo-i-loader" style="margin-left: 40%;"></div>');
        viewPort.html(loader);

        var tableID = 'description_view_tbl' + description_token;
        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        var table_div = $('<div/>').append(tbl);

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
                loader.remove();

                viewPort.append(table_div);

                var dtd = data.result;
                var cols2 = componentMeta.table_columns;

                var cols = [
                    {title: "", className: 'select-checkbox', data: "chk_box", orderable: false},
                ];

                for (var i = 0; i < cols2.length; ++i) {
                    cols.push(cols2[i])
                }

                if ($.fn.dataTable.isDataTable('#' + tableID)) {
                    //if table instance already exists, then destroy in order to successfully re-initialise
                    $('#' + tableID).destroy();
                }

                var table = $('#' + tableID).DataTable({
                    data: dtd,
                    searchHighlight: true,
                    "lengthChange": false,
                    order: [
                        [1, "asc"]
                    ],
                    buttons: [
                        'selectAll',
                        'selectNone',
                        'copy',
                        'csv',
                    ],
                    language: {
                        "info": " _START_ to _END_ of _TOTAL_ datafiles",
                        "search": " ",
                        buttons: {
                            selectAll: "Select all",
                            selectNone: "clear selection"
                        }
                    },
                    select: {
                        style: 'multi',
                        selector: 'td:not(.annotate-datafile, .summary-details-control, .detail-hover-message)'
                    },
                    columns: cols,
                    createdRow: function (row, data, index) {
                        $(row).addClass("draggable_tr");
                    },
                    columnDefs: [
                        {
                            render: function (data, type, full, meta) {
                                return "<div style='word-wrap: break-word; width:300px;'>" + data + "</div>";
                            },
                            targets: 3
                        }
                    ],
                    dom: "<'row'<'col-md-12'Bl>>" +
                        "<'row'<'col-md-12'>>" +
                        "<'row'<'col-md-12'i>>" +
                        "<'row'<'col-md-6'><'col-md-6'f>>" +
                        "<'row'<'col-md-12't>>" +
                        "<'row'<'col-md-6'r><'col-md-6'p>>",
                });

                table_div.closest(".description-bundle-panel").find("tr").draggable({
                    helper: function () {
                        var selected = table_div.find("tr.selected, tr.dragcandidate");
                        var container = $('<div/>').attr('class', 'draggingContainer');
                        container.css({"z-index": 9000});
                        container.append(selected.clone());
                        container.find("td:first-child").remove();
                        container.append($('<div/>').attr({'class': 'pparent', 'id': description_token}));
                        return container;
                    }
                });


                table
                    .buttons()
                    .nodes()
                    .each(function (value) {
                        $(this)
                            .removeClass("btn btn-default")
                            .addClass('tiny ui button');
                    });

                //add custom buttons

                var customButtons = $('<span/>', {
                    style: "padding-left: 5px;",
                    class: "copo-table-cbuttons"
                });


                $(table.buttons().container())
                    .css({"padding-bottom": "10px;"})
                    .append(customButtons);
                $('#' + tableID + '_wrapper').css({"margin-top": "10px"});
                $('#' + tableID + '_wrapper').find(".info-rw").css({"margin-top": "10px"});

                var actionMenu = $('<div/>',
                    {
                        class: "ui compact menu",
                    });

                customButtons.append(actionMenu);

                var actionDropdownItem = $('<div/>',
                    {
                        class: "ui simple dropdown item",
                        style: "font-size: 12px;",
                        html: "Actions"
                    });

                actionMenu.append(actionDropdownItem);
                actionDropdownItem.append('<i class="dropdown icon"></i>');

                var actionDropdownMenu = $('<div/>',
                    {
                        class: "menu",
                    });

                actionDropdownItem.append(actionDropdownMenu);

                //add datafiles
                var actionAddDatafiles = $('<div data-html="Add datafiles to bundle" data-position="right center" class="item copo-tooltip">Add datafiles</div>');
                actionDropdownMenu.append(actionAddDatafiles);
                actionAddDatafiles.click(function (event) {
                    event.preventDefault();
                    add_to_bundle(description_token);
                });

                //remove datafiles
                var actionRemoveDatafiles = $('<div data-html="Remove selected datafiles from bundle" data-position="right center" class="item copo-tooltip">Drop datafiles</div>');
                actionDropdownMenu.append(actionRemoveDatafiles);
                actionRemoveDatafiles.click(function (event) {
                    event.preventDefault();
                    var target_rows = table.rows('.selected').ids().toArray();

                    if (target_rows.length == 0) {

                        BootstrapDialog.show({
                            title: "Warning",
                            message: "No datafiles selected. Please select one or more datafiles to remove from this bundle.",
                            cssClass: 'copo-modal3',
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

                    } else {
                        $.ajax({
                            url: wizardURL,
                            type: "POST",
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                            data: {
                                'request_action': 'unbundle_datafiles',
                                'description_targets': JSON.stringify(target_rows)
                            },
                            success: function (data) {
                                show_bundle_datafiles(description_token);
                                do_render_server_side_table(componentMeta);
                            },
                            error: function () {
                                alert("Couldn't complete request to remove from bundle!");
                            }
                        });
                    }
                });


                //clear datafiles metadata
                var actionClearMetadata = $('<div data-html="Clear metadata for selected datafiles" data-position="right center" class="item copo-tooltip">Clear metadata</div>');
                actionDropdownMenu.append(actionClearMetadata);
                actionClearMetadata.click(function (event) {
                    event.preventDefault();

                    var target_rows = table.rows('.selected').ids().toArray();

                    if (target_rows.length == 0) {

                        BootstrapDialog.show({
                            title: "Warning",
                            message: "No datafiles selected. Please select one or more datafiles to clear metadata.",
                            cssClass: 'copo-modal3',
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

                    } else {
                        $.ajax({
                            url: wizardURL,
                            type: "POST",
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                            data: {
                                'request_action': 'un_describe',
                                'description_targets': JSON.stringify(target_rows)
                            },
                            success: function (data) {
                                show_bundle_datafiles(description_token);
                            },
                            error: function () {
                                alert("Couldn't discard description for selected records!");
                                table.rows().deselect(); //deselect all rows
                                server_side_select[component] = [];
                            }
                        });
                    }
                });

                refresh_tool_tips();

                $('#' + tableID + '_wrapper')
                    .find(".dataTables_filter")
                    .find("input")
                    .removeClass("input-sm")
                    .attr("placeholder", "Search files in bundle");

                //handle event for table details
                $('#' + tableID + ' tbody')
                    .off('click', 'td.summary-details-control')
                    .on('click', 'td.summary-details-control', function (event) {
                        event.preventDefault();

                        var tr = $(this).closest('tr');
                        var row = table.row(tr);
                        tr.addClass('showing');

                        if (row.child.isShown()) {
                            // This row is already open - close it
                            row.child('');
                            row.child.hide();
                            tr.removeClass('showing');
                            tr.removeClass('shown');
                        } else {
                            $.ajax({
                                url: copoVisualsURL,
                                type: "POST",
                                headers: {
                                    'X-CSRFToken': csrftoken
                                },
                                data: {
                                    'task': "attributes_display",
                                    'component': componentMeta.component,
                                    'target_id': row.data().record_id
                                },
                                success: function (data) {
                                    if (data.component_attributes.columns) {
                                        // expand row

                                        var contentHtml = $('<table/>', {
                                            cellspacing: "0",
                                            border: "0",
                                        });

                                        for (var i = 0; i < data.component_attributes.columns.length; ++i) {
                                            var colVal = data.component_attributes.columns[i];

                                            var colTR = $('<tr/>');
                                            contentHtml.append(colTR);

                                            colTR
                                                .append($('<td/>').append(colVal.title))
                                                .append($('<td/>').append("<div style='width:300px; word-wrap: break-word;'>" + data.component_attributes.data_set[colVal.data] + "</div>"));

                                        }

                                        row.child($('<div></div>').append(contentHtml).html()).show();
                                        tr.removeClass('showing');
                                        tr.addClass('shown');
                                    }
                                },
                                error: function () {
                                    alert("Couldn't retrieve " + component + " attributes!");
                                    return '';
                                }
                            });
                        }
                    });

                //handle event for datafile annotation
                $('#' + tableID + ' tbody')
                    .off('click', 'td.annotate-datafile')
                    .on('click', 'td.annotate-datafile', function (event) {
                        event.preventDefault();

                        var tr = $(this).closest('tr');
                        var record_id = tr.attr("id");
                        record_id = record_id.split("row_").slice(-1)[0];
                        var loc = $("#file_annotate_url").val().replace("999", record_id);
                        window.location = loc;
                    });


            },
            error: function () {
                alert("Couldn't display description bundle!");
                dialogRef.close();
            }
        });

    } // end of function


    function dispatch_bundle_events(elem) {
        var bundle_id = elem.closest(".description-bundle-panel").attr("data-id");
        var viewPort = elem.closest(".description-bundle-panel").find(".pbody");

        elem.addClass("active");
        var task = elem.data("task");


        elem.closest(".description-bundle-panel").find(".view-actions").html('');


        if (task == "add_metadata") {
            viewPort.html('');
            add_metadata_bundle(bundle_id);
        } else if (task == "edit_bundle") {
            create_edit_description_bundle(bundle_id);
        } else if (task == "add_datafiles") {
            add_to_bundle(bundle_id);
        } else if (task == "delete_bundle") {
            delete_description_bundle(bundle_id);
        } else if (task == "view_metadata") {
            view_bundle_metadata(bundle_id);
        } else if (task == "clone_bundle") {
            clone_bundle(bundle_id);
        } else if (task == "view_datafiles") {
            show_bundle_datafiles(bundle_id);
        } else if (task == "view_issues") {
            show_bundle_issues(bundle_id);
        } else if (task == "view_accessions") {
            view_accessions(bundle_id);
        } else if (task == "submit_bundle") {
            submit_bundle(bundle_id);
        }
    }

    function submit_bundle(bundle_id) {
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
                            'description_token': bundle_id,
                            'profile_id': $('#profile_id').val()
                        },
                        success: function (data) {
                            if (data.result.existing || false) {
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
                                var submission_id = data.result.submission_id || '';

                                if (submission_id) {
                                    dialogRef.close();
                                    window.location.replace($("#submission_url").val());
                                } else {
                                    BootstrapDialog.show({
                                        title: 'Submission Error!',
                                        message: "Couldn't initiate submission of bundle. No datafiles in bundle.",
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
                                                }
                                            }
                                        ]
                                    });
                                }

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

    function view_accessions(bundle_id) {
        var parentElem = $('.description-bundle-panel[data-id="' + bundle_id + '"]');
        var bundleName = parentElem.attr("data-bundlename");
        var viewPort = parentElem.find(".pbody");

        var loader = $('<div class="copo-i-loader" style="margin-left: 40%;"></div>');
        viewPort.html(loader);

        var tableID = 'bundle_accessions_view_tbl' + bundle_id;
        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        var meta_div = $('<div/>', {
            "style": "margin-bottom: 20px;"
        });
        var table_div = $('<div/>').append(tbl);


        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': 'get_bundle_accessions',
                'description_token': bundle_id
            },
            success: function (data) {
                loader.remove();
                viewPort.append(meta_div).append(table_div);

                if (!data.result.hasOwnProperty("dataSet")) {
                    viewPort.html('<div>\n' +
                        '  <p>No accessions found!</p>\n' +
                        '</div>');

                    return false;
                }

                var dataSet = data.result.dataSet;
                var columns = data.result.columns;

                var rowGroup = null;
                var groupAcessionRepos = ["ena"];

                if (data.result.hasOwnProperty('repository') && groupAcessionRepos.indexOf(data.result.repository) > -1) {
                    rowGroup = {dataSrc: 3};
                }


                BootstrapDialog.show({
                    title: "Accessions for items in bundle " + bundleName,
                    message: $('<div></div>').append('<table id="submission_accession_table_' + '" class="ui celled stripe table hover copo-noborders-table" cellspacing="0" width="100%"></table>'),
                    cssClass: 'copo-modal4',
                    closable: false,
                    animate: true,
                    type: BootstrapDialog.TYPE_SUCCESS,
                    onshown: function (dialogRef) {
                        //display accessions
                        var tableID = 'submission_accession_table_';
                        if ($.fn.dataTable.isDataTable('#' + tableID)) {
                            //if table instance already exists, then destroy in order to successfully re-initialise
                            $('#' + tableID).destroy();
                        }


                        var accessionTable = $('#' + tableID).DataTable({
                            data: dataSet,
                            columns: columns,
                            order: [[3, 'asc']],
                            rowGroup: rowGroup,
                            columnDefs: [
                                {
                                    "width": "10%",
                                    "targets": [1]
                                }
                            ],
                            buttons: [
                                'copy', 'csv',
                                {
                                    extend: 'excel',
                                    text: 'Spreadsheet',
                                    title: null
                                }
                            ],
                            dom: 'Bfr<"row"><"row info-rw" i>tlp',
                        });

                        accessionTable
                            .buttons()
                            .nodes()
                            .each(function (value) {
                                $(this)
                                    .removeClass("btn btn-default")
                                    .addClass('tiny ui button');
                            });
                    },
                    buttons: [
                        {
                            label: 'Close',
                            cssClass: 'tiny ui button',
                            action: function (dialogRef) {
                                dialogRef.close();
                            }
                        }
                    ]
                });
            },
            error: function () {
                alert("Couldn't retrieve accessions!");
            }
        });
    }

    function show_bundle_issues(bundle_id) {
        var parentElem = $('.description-bundle-panel[data-id="' + bundle_id + '"]');
        var viewPort = parentElem.find(".pbody");

        var loader = $('<div class="copo-i-loader" style="margin-left: 40%;"></div>');
        viewPort.html(loader);

        $.ajax({
            url: wizardURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'request_action': 'get_bundle_issues',
                'description_token': bundle_id
            },
            success: function (data) {
                loader.remove();
                var issues = data.result;

                if (issues.length == 0) {
                    viewPort.html('<div>\n' +
                        '  <p>No issues found!</p>\n' +
                        '</div>');
                } else {
                    viewPort.html('<div class="submission-issues text-danger">\n' +
                        '  <p>The following issues were found.</p>\n' +
                        '</div>');

                    var issuesList = $('<ul/>', {
                        class: "ui list",
                    });

                    for (var i = 0; i < issues.length; ++i) {
                        issuesList.append('<li class="text-danger">' + issues[i] + '</li>');
                    }

                    viewPort.find(".submission-issues").append(issuesList);
                }
            },
            error: function () {
                alert("Couldn't retrieve issues!");
            }
        });
    }

    function add_metadata_bundle(bundle_id) {
        var event = jQuery.Event("addmetadata");
        event.bundleID = bundle_id;
        $('body').trigger(event);

    }

    function delete_description_bundle(bundle_id) {
        //function deletes a description bundle - previous bundle datafiles retain their metadata

        var parentElem = $('.description-bundle-panel[data-id="' + bundle_id + '"]');

        var message = $('<div/>', {class: "webpop-content-div"});
        message.append("Are you sure you want to delete this bundle? Please note that this action might impact referenced objects.</div>");

        if (datafileDescriptionToken == bundle_id) {
            message.append("<div>Description of this bundle will be terminated as part of the process.</div>");
        }

        BootstrapDialog.show({
            title: "Delete bundle",
            message: message,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            // size: BootstrapDialog.SIZE_NORMAL,
            buttons: [
                {
                    label: 'Cancel',
                    cssClass: 'tiny ui basic button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                },
                {
                    id: "btn-remove-bundle",
                    label: '<i style="padding-right: 5px;" class="fa fa-trash-o" aria-hidden="true"></i> Delete',
                    cssClass: 'tiny ui basic red button',
                    action: function (dialogRef) {
                        var $button = this;
                        $button.disable();

                        $.ajax({
                            url: wizardURL,
                            type: "POST",
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                            data: {
                                'request_action': 'delete_description_bundle',
                                'description_token': bundle_id
                            },
                            success: function (data) {
                                if (data.result.hasOwnProperty("status") && data.result.status == "success") {
                                    //delete description if it exists
                                    if (datafileDescriptionToken == bundle_id) {
                                        var event = jQuery.Event("exitdescription");
                                        $('body').trigger(event);
                                    }

                                    // parentElem.remove();
                                    var tableID = bundleTableId;

                                    //set data
                                    var table = null;

                                    if ($.fn.dataTable.isDataTable('#' + tableID)) {
                                        table = $('#' + tableID).DataTable();
                                        table.row("#row_" + bundle_id).remove().draw();
                                    }

                                    do_render_server_side_table(componentMeta);

                                    dialogRef.close();

                                } else if (data.result.hasOwnProperty("status") && data.result.status == "error") {
                                    alert("Couldn't delete bundle: " + data.result.message);
                                    dialogRef.close();
                                }
                            },
                            error: function () {
                                alert("Couldn't delete bundle!");
                                dialogRef.close();
                            }
                        });

                        return false;
                    }
                }
            ]
        });
    }

    function remove_bundle_metadata(bundle_id) {
        //function clears bundle's metadata - bundle datafiles however maintain their metadata

        var parentElem = $('.description-bundle-panel[data-id="' + bundle_id + '"]');

        var message = $('<div/>', {class: "webpop-content-div"});
        message.append("Are you sure you want to remove this bundle's metadata? <br/><br/> Please note that datafiles in this bundle still get to retain their metadata.</div>");

        if (datafileDescriptionToken == bundle_id) {
            message.append("<div>Description of this bundle will be terminated as part of the process.</div>");
        }


        BootstrapDialog.show({
            title: "Remove bundle metadata",
            message: message,
            cssClass: 'copo-modal2',
            closable: false,
            animate: true,
            type: BootstrapDialog.TYPE_DANGER,
            // size: BootstrapDialog.SIZE_NORMAL,
            buttons: [
                {
                    label: 'Cancel',
                    cssClass: 'tiny ui basic button',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                },
                {
                    id: "btn-remove-bundle",
                    label: '<i style="padding-right: 5px;" class="fa fa-trash-o" aria-hidden="true"></i> Remove',
                    cssClass: 'tiny ui basic red button',
                    action: function (dialogRef) {
                        var $button = this;
                        $button.disable();

                        $.ajax({
                            url: wizardURL,
                            type: "POST",
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                            data: {
                                'request_action': 'remove_bundle_metadata',
                                'description_token': bundle_id
                            },
                            success: function (data) {
                                if (data.result.hasOwnProperty("status") && data.result.status == "success") {

                                    if (datafileDescriptionToken == bundle_id) {
                                        var event = jQuery.Event("exitdescription");
                                        $('body').trigger(event);
                                    }

                                    view_bundle_metadata(bundle_id);

                                    dialogRef.close();

                                } else if (data.result.hasOwnProperty("status") && data.result.status == "error") {
                                    var feedback = get_feedback_pane();
                                    feedback
                                        .removeClass("success")
                                        .addClass("negative");

                                    feedback.find(".header").html("Error");
                                    feedback.find("p").append(data.result.message);
                                    parentElem.find(".feedback-entry-pane")
                                        .html('')
                                        .append(feedback);

                                    dialogRef.close();
                                }
                            },
                            error: function () {
                                alert("Couldn't remove bundle's metadata!");
                                dialogRef.close();
                            }
                        });

                        return false;
                    }
                }
            ]
        });
    }

    function add_to_bundle(description_token) {
        var tableID = 'bundle_add_view_tbl';
        var table = null;
        var tbl = $('<table/>',
            {
                id: tableID,
                "class": "ui celled table hover copo-noborders-table",
                cellspacing: "0",
                width: "100%"
            });

        var $dialogContent = $('<div/>');
        var table_div = $('<div/>').append(tbl);
        var filter_message = $('<div style="margin-bottom: 20px;"><div style="font-weight: bold; margin-bottom: 5px;">Note: This list only contains unbundled datafiles</div><div style="color: orangered;"></div></div>');
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
                        'profile_id': $('#profile_id').val()
                    },
                    success: function (data) {
                        spinner_div.remove();

                        var dtd = data.result;
                        var cols = [
                            {title: "", className: 'select-checkbox', data: "chk_box", orderable: false},
                            {title: "Datafiles", data: "name"}
                        ];

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
                                'selectNone'
                            ],
                            language: {
                                "info": " _START_ to _END_ of _TOTAL_ datafiles",
                                "search": " "
                            },
                            select: {
                                style: 'multi',
                                // selector: 'td:first-child'
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
                            .attr("placeholder", "Search datafiles");

                    },
                    error: function () {
                        alert("Couldn't display datafiles!");
                        dialogRef.close();
                    }
                });
            },
            buttons: [{
                label: 'Add selected',
                cssClass: 'tiny ui basic button',
                action: function (dialogRef) {
                    var target_rows = table.rows('.selected').ids().toArray();

                    if (target_rows.length > 0) {
                        dialog.getModalBody().html('').append(spinner_div);

                        $.ajax({
                            url: wizardURL,
                            type: "POST",
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                            data: {
                                'request_action': 'add_to_bundle',
                                'description_token': description_token,
                                'description_targets': JSON.stringify(target_rows)
                            },
                            success: function (data) {
                                show_bundle_datafiles(description_token);
                                do_render_server_side_table(componentMeta);
                                dialogRef.close();
                            },
                            error: function () {
                                alert("Couldn't add datafiles to bundle!");
                                dialogRef.close();
                            }
                        });
                    }
                }
            }, {
                label: 'Cancel',
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



