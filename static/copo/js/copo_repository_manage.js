$(document).ready(function () {

    // test starts
    // test ends
    //******************************Event Handlers Block*************************//
    var componentMeta = {
        component: 'repository',
        title: 'Manage Repositories',
        iconClass: "fa fa-pencil",
        semanticIcon: "write",
        buttons: ["quick-tour-template"],
        sidebarPanels: ["copo-sidebar-info"],
        colorClass: "annotations_color",
        color: "violet",
        tableID: 'repository_table',
        visibleColumns: 10000
    }

    var component = componentMeta.component;

    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";
    var csrftoken = $.cookie('csrftoken');

    var repositorySchemaObject = null;

    generate_component_control(componentMeta);

    show_repository_info();

    load_repositories();


    //submission tasks
    $(document).on('click', '.repomenu', function (event) {
        event.preventDefault();
        dispatch_repositories_events($(this));
    });


    //add new profile button
    $(document).on("click", ".new-component-template", function (event) {
        initiate_form_call(component);
    });

    //handle event for repo type change
    $(document).on('new_repo_type_change', function (event) {
        handle_repo_type_change(event);
    });

    //handle dataverse/dataset value change
    $('body').on('postformload', function (event) {
        if (componentData) {
            repositorySchemaObject = componentData;
            handle_post_form_load();
        }
    });

    //refresh view after edit or insert
    $('body').on('refreshtable', function (event) {
        do_display_repositories(globalDataBuffer);
    });

    refresh_tool_tips();

    //******************************Functions Block******************************//

    function get_table_dataset(dtd) {
        var dataSet = [];

        for (var i = 0; i < dtd.length; ++i) {
            var data = dtd[i];

            //get s_n
            var s_n = '';
            if (data.hasOwnProperty("s_n")) {
                s_n = data.s_n;
            }

            //get submission id
            var record_id = '';
            if (data.hasOwnProperty("record_id")) {
                record_id = data.record_id;
            }

            //get row id
            var DT_RowId = '';
            if (data.hasOwnProperty("DT_RowId")) {
                DT_RowId = data.DT_RowId;
            }

            //get type
            var type = '';
            if (data.hasOwnProperty("type")) {
                type = data.type;
            }

            //get name
            var name = '';
            if (data.hasOwnProperty("name")) {
                name = data.name;
            }

            //get templates
            var templates = ''
            if (data.hasOwnProperty("templates")) {
                templates = data.templates;
            }

            //get visibility
            var visibility = '';
            if (data.hasOwnProperty("visibility")) {
                visibility = data.visibility;
            }

            //get url
            var url = '';
            if (data.hasOwnProperty("url")) {
                url = data.url;
            }


            //get date modified
            var date_modified = '';
            if (data.hasOwnProperty("date_modified")) {
                date_modified = data.date_modified;
            }


            if (record_id) {
                var option = {};
                option["s_n"] = s_n;
                option["DT_RowId"] = DT_RowId;
                option["type"] = type;
                option["name"] = name;
                option["templates"] = templates;
                option["date_modified"] = date_modified;
                option["record_id"] = record_id;
                option["url"] = url;
                option["visibility"] = visibility;
                dataSet.push(option);
            }
        }

        return dataSet;
    }

    function do_display_repositories(data) {
        var dtd = data.table_data.dataSet;
        set_empty_component_message(dtd.length); //display empty submission message.

        if (dtd.length == 0) {
            return false;
        }

        var dataSet = get_table_dataset(dtd);
        var tableID = componentMeta.tableID;

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
            table = $('#' + tableID).DataTable({
                data: dataSet,
                searchHighlight: true,
                ordering: true,
                lengthChange: false,
                buttons: [],
                select: false,
                language: {
                    "emptyTable": "No repositories data available.",
                },
                order: [
                    [1, "desc"]
                ],
                columns: [
                    {
                        "data": null,
                        "orderable": false,
                        "render": function (rowdata) {
                            var renderHTML = get_card_panel();

                            renderHTML
                                .find(".panel")
                                .removeClass("panel-dtables3")
                                .addClass("panel-dtables4");

                            renderHTML
                                .removeClass("component-type-panel")
                                .addClass("repository-panel")
                                .attr({"data-id": rowdata.record_id});


                            //set attributes
                            renderHTML.find(".panel-header-1").html(rowdata.name);

                            var attrHTML = renderHTML.find(".attr-placeholder").first().clone().css("display", "block");
                            attrHTML.find(".attr-key").html("Type:");
                            attrHTML.find(".attr-value").html(rowdata.type.toString());
                            renderHTML.find(".attr-placeholder").parent().append(attrHTML);

                            var attrHTML = renderHTML.find(".attr-placeholder").first().clone().css("display", "block");
                            attrHTML.find(".attr-key").html("Last modified:");
                            attrHTML.find(".attr-value").html(rowdata.date_modified);
                            renderHTML.find(".attr-placeholder").parent().append(attrHTML);

                            //define status
                            var visibility = rowdata.visibility.toLowerCase();

                            var disabled_items = [];
                            renderHTML.find(".bundle-status").remove();

                            //define menu
                            renderHTML
                                .find(".menu-label")
                                .removeClass("blue")
                                .addClass("brown");

                            renderHTML
                                .find(".menu-label-icon")
                                .removeClass("blue")
                                .addClass("brown");

                            renderHTML
                                .find(".copo-actions-dropdown")
                                .removeClass("copo-actions-dropdown")
                                .addClass("copo-actions-dropdown4");

                            var componentMenu = renderHTML.find(".component-menu");
                            componentMenu.html('');
                            componentMenu.append('<div data-task="add_submitters" class="item repomenu">Add/Remove Submitters</div>');
                            componentMenu.append('<div class="divider"></div>');
                            componentMenu.append('<div data-task="view_statistics" class="item repomenu">View Full Details</div>');

                            //process disabled item list
                            componentMenu.find(".repomenu").each(function (indx, menuitem) {
                                if (disabled_items.indexOf($(menuitem).attr("data-task")) > -1) {
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
                        "data": "record_id",
                        "visible": false
                    },
                    {
                        "data": "visibility",
                        "visible": false
                    },
                ],
                "columnDefs": [],
                fnDrawCallback: function () {
                    refresh_tool_tips();
                },
                createdRow: function (row, data, index) {
                },
                dom: 'Bfr<"row"><"row info-rw3" i>tlp',
            });

            table
                .buttons()
                .nodes()
                .each(function (value) {
                    $(this)
                        .removeClass("btn btn-default")
                        .addClass('tiny ui blue button');
                });
        }

        $('#' + tableID + '_wrapper')
            .find(".dataTables_filter")
            .find("input")
            .removeClass("input-sm")
            .attr("placeholder", "Search repositories")
            .attr("size", 20);
    }

    function show_repository_info() {
        var message = $('<div class="webpop-content-div"></div>');

        var infoPanelElement = trigger_global_notification();

        var codeList = '<div style="margin-top: 10px;"><ul class="list-group">\n' +
            '  <li class="list-group-item active" style="background: #31708f; text-shadow: none; border-color: #d9edf7; color: #fff;">Repositories - quick guide</li>\n' +
            '  <li class="list-group-item"><div><i class="icon info circle grey"></i> This page lists repositories for which you are a manager</div></li>\n' +
            '  <li class="list-group-item"><div><i class="icon info circle grey"></i> You can add users as <strong>submitters</strong> to any of the listed repositories</div></li>\n' +
            '  <li class="list-group-item"><div><i class="icon info circle grey"></i> You can also revoke submission rights from users</div></li>\n' +
            '  <li class="list-group-item"><div><i class="icon info circle grey"></i> Use the <strong>tasks menu</strong> attached to each record to access and carry out defined actions</div></li>\n' +
            '</ul></div>'


        message.append(codeList);
        infoPanelElement.prepend(message);
    }

    function load_repositories() {
        var loader = $('<div class="copo-i-loader" style="margin-left: 40%;"></div>');
        $("#cover-spin-bundle").html(loader);

        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'task': 'managed_repositories',
                'component': component
            },
            success: function (data) {
                loader.remove();
                do_display_repositories(data);
            },
            error: function (data) {
                loader.remove();

                var infoPanelElement = trigger_global_notification();
                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-danger")
                    .addClass("page-notifications-node");

                feedback.find(".alert-message").html("Couldn't retrieve repositories. " + data.responseText);
                infoPanelElement.prepend(feedback);
            }
        });
    }


    function dispatch_repositories_events(elem) {
        var repository_id = elem.closest(".repository-panel").attr("data-id");

        var viewPort = elem.closest(".repository-panel").find(".pbody");
        elem.addClass("active");
        var task = elem.data("task");

        if (task == "add_submitters") {
            add_submitters(repository_id);
        } else if (task == "view_statistics") {
            view_statistics(repository_id);
        }
    }


    function view_statistics(repository_id) {
        var parentElem = $('.repository-panel[data-id="' + repository_id + '"]');
        var viewPort = parentElem.find(".pbody");

        var loader = $('<div class="copo-i-loader" style="margin-left: 40%;"></div>');
        viewPort.html(loader);

        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'task': "get_repo_stats",
                'component': componentMeta.component,
                'target_id': repository_id
            },
            success: function (data) {
                loader.remove();

                var instructionMessage = "Full details and statistics for this repository are provided below. " +
                    "Please contact the administrator if you notice any incorrect entry.";
                var messageClass = "";
                var messageTitle = "Repository details";
                var getInstructionsPane = format_feedback_message(instructionMessage, messageClass, messageTitle);

                viewPort.append(getInstructionsPane);

                var view_pane = $('<div/>', {
                    style: "margin-top:30px;",
                });

                viewPort.append(view_pane);

                let result = data.result;

                var tbl = $('<table class="ui compact definition selectable celled table"></table>');
                view_pane.append(tbl);

                var tbody = $('<tbody/>');
                for (let i = 0; i < result.length; ++i) {
                    tbody.append('<tr><td>' + result[i].label + '</td><td>' + result[i].value + '</td></tr>');
                }


                var thead = $('<thead><tr><th></th><th></th></tr></thead>');
                tbl
                    .append(thead)
                    .append(tbody);

            },
            error: function () {
                loader.remove();
                alert("Couldn't retrieve repository details!");
            }
        });
    }


    function add_submitters(repository_id) {
        var parentElem = $('.repository-panel[data-id="' + repository_id + '"]');
        var viewPort = parentElem.find(".pbody");

        var loader = $('<div class="copo-i-loader" style="margin-left: 40%;"></div>');
        viewPort.html(loader);

        $.ajax({
            url: "/copo/get_users_repo_users/",
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'repository_id': repository_id,
                'context': 'submitters'
            },
            success: function (data) {
                loader.remove();

                var filtered_users = data.filtered_users;
                var context_users = data.context_users;


                var instructionMessage = "Select user records from the Users table and click <strong>Add submitter</strong> " +
                    "to add them as submitters to this repository.";
                var messageClass = "";
                var messageTitle = "Manage Repository Submitters";
                var getInstructionsPane = format_feedback_message(instructionMessage, messageClass, messageTitle);

                viewPort.append(getInstructionsPane);

                var view_pane = $('<div/>', {
                    class: "row",
                    style: "margin-top:30px;",
                });

                var allUsersDiv = $('<div/>', {
                    class: "col-sm-6 all-users"
                });

                var assignedUsersDiv = $('<div/>', {
                    class: "col-sm-6 assigned-users"
                });

                view_pane
                    .append(allUsersDiv)
                    .append(assignedUsersDiv);

                viewPort.append(view_pane);

                var allUserstableID = "all_users_tbl_" + repository_id;
                var allUserstable = $('<table/>',
                    {
                        id: allUserstableID,
                        "class": "ui blue celled table hover copo-noborders-table",
                        cellspacing: "0",
                        width: "100%"
                    });

                allUsersDiv.append(allUserstable);

                var allUserstableDT = $('#' + allUserstableID).DataTable({
                    data: filtered_users,
                    searchHighlight: true,
                    dom: 'Bfr<"row"><"row">tip',
                    select: {
                        style: 'multi',
                        selector: 'td:not(.add-submitter)'
                    },
                    buttons: [
                        'selectAll',
                        'selectNone',
                    ],
                    language: {
                        "info": " _START_ to _END_ of _TOTAL_ Users",
                        "search": " ",
                        buttons: {
                            selectAll: "Select all",
                            selectNone: "Clear selection"
                        }
                    },
                    columns: [
                        {
                            "data": null,
                            "title": "Users",
                            "orderable": true,
                            "render": function (rowdata) {
                                return '<div class="webpop-content-div">' +
                                    '<div>' + rowdata.first_name + ' ' + rowdata.last_name + '</div><div>' + rowdata.username + '</div><div>' + rowdata.email + '</div></div>';
                            }
                        },
                        {
                            "data": null,
                            "title": "",
                            className: 'add-submitter',
                            "orderable": false,
                            "width": "2%",
                            "render": function (rowdata) {
                                return '<div class="webpop-content-div">' +
                                    '<span title="Add submitter" style="cursor:pointer;" class="copo-tooltip"><i class="fa fa-user-plus text-primary" aria-hidden="true"></i></span></div>';
                            }
                        },
                        {
                            "data": "id",
                            "title": "",
                            "visible": false
                        },
                    ],
                });

                allUserstableDT
                    .buttons()
                    .nodes()
                    .each(function (value) {
                        $(this)
                            .removeClass("btn btn-default")
                            .addClass('tiny ui button');
                    });

                $('#' + allUserstableID + '_wrapper')
                    .find(".dataTables_filter")
                    .find("input")
                    .removeClass("input-sm")
                    .attr("placeholder", "Search Users")
                    .attr("size", 15);

                //add custom buttons
                var customButtons = $('<span/>', {
                    style: "padding-left: 5px;",
                    class: "copo-table-cbuttons"
                });

                $(allUserstableDT.buttons().container()).append(customButtons);

                //apply to selected rows button
                var assignButton = $('<button/>',
                    {
                        class: "tiny ui basic blue button",
                        type: "button",
                        html: '<i class="fa fa-user-plus" aria-hidden="true" style="padding-right: 5px;"></i>Add submitter',
                        click: function (event) {
                            event.preventDefault();

                            var selectedUserIds = [];
                            var selectedData = allUserstableDT.rows('.selected').data();
                            selectedData.each(function (value, index) {
                                selectedUserIds.push(value.id);
                            });

                            if (selectedUserIds.length > 0) {
                                assign_repo_users(repository_id, selectedUserIds, "submitters");
                            }
                        }
                    });

                customButtons.append(assignButton);

                //handle event for single-row assigning of manager
                $('#' + allUserstableID + ' tbody')
                    .off('click', 'td.add-submitter')
                    .on('click', 'td.add-submitter', function (event) {
                        event.preventDefault();

                        var selectedUserIds = [];
                        selectedUserIds.push(allUserstableDT.row($(this).closest('tr')).data().id);
                        assign_repo_users(repository_id, selectedUserIds, "submitters");
                    });

                refresh_tool_tips();


                //managers table
                var assignedUserstableID = "assigned_users_tbl_" + repository_id;
                var assignedUserstable = $('<table/>',
                    {
                        id: assignedUserstableID,
                        "class": "ui green celled table hover copo-noborders-table",
                        cellspacing: "0",
                        width: "100%"
                    });

                assignedUsersDiv.append(assignedUserstable);

                var assignedUserstableDT = $('#' + assignedUserstableID).DataTable({
                    data: context_users,
                    searchHighlight: true,
                    dom: 'Bfr<"row"><"row">tip',
                    select: {
                        style: 'multi',
                        selector: 'td:not(.remove-submitter)'
                    },
                    buttons: [
                        'selectAll',
                        'selectNone',
                    ],
                    language: {
                        "info": " _START_ to _END_ of _TOTAL_ Submitters",
                        "search": " ",
                        buttons: {
                            selectAll: "Select all",
                            selectNone: "Clear selection"
                        }
                    },
                    columns: [
                        {
                            "data": null,
                            "title": "Submitters",
                            "orderable": true,
                            "render": function (rowdata) {
                                return '<div class="webpop-content-div">' +
                                    '<div>' + rowdata.first_name + ' ' + rowdata.last_name + '</div><div>' + rowdata.username + '</div><div>' + rowdata.email + '</div></div>';
                            }
                        },
                        {
                            "data": null,
                            "title": "",
                            className: 'remove-submitter',
                            "orderable": false,
                            "width": "2%",
                            "render": function (rowdata) {
                                return '<div class="webpop-content-div">' +
                                    '<span title="Remove submitter" style="cursor:pointer;" class="copo-tooltip"><i class="fa fa-trash-o text-danger" aria-hidden="true"></i></span></div>';
                            }
                        },
                        {
                            "data": "id",
                            "title": "",
                            "visible": false
                        },
                    ],
                });

                assignedUserstableDT
                    .buttons()
                    .nodes()
                    .each(function (value) {
                        $(this)
                            .removeClass("btn btn-default")
                            .addClass('tiny ui button');
                    });

                $('#' + assignedUserstableID + '_wrapper')
                    .find(".dataTables_filter")
                    .find("input")
                    .removeClass("input-sm")
                    .attr("placeholder", "Search Submitters")
                    .attr("size", 15);

                //add custom buttons
                var customButtonsManagers = $('<span/>', {
                    style: "padding-left: 5px;",
                    class: "copo-table-cbuttons"
                });

                $(assignedUserstableDT.buttons().container()).append(customButtonsManagers);

                //apply to selected rows button
                var removeButton = $('<button/>',
                    {
                        class: "tiny ui basic red button",
                        type: "button",
                        html: '<i class="fa fa-trash-o" aria-hidden="true" style="padding-right: 5px;"></i>Remove submitter',
                        click: function (event) {
                            event.preventDefault();

                            var selectedUserIds = [];
                            var selectedData = assignedUserstableDT.rows('.selected').data();
                            selectedData.each(function (value, index) {
                                selectedUserIds.push(value.id);
                            });

                            if (selectedUserIds.length > 0) {
                                deassign_repo_users(repository_id, selectedUserIds, "submitters");
                            }
                        }
                    });

                customButtonsManagers.append(removeButton);

                //handle event for single-row assigning of manager
                $('#' + assignedUserstableID + ' tbody')
                    .off('click', 'td.remove-submitter')
                    .on('click', 'td.remove-submitter', function (event) {
                        event.preventDefault();

                        var selectedUserIds = [];
                        selectedUserIds.push(assignedUserstableDT.row($(this).closest('tr')).data().id);
                        deassign_repo_users(repository_id, selectedUserIds, "submitters");
                    });

                refresh_tool_tips();


            },
            error: function () {
                alert("Couldn't retrieve repository details!");
            }
        });
    }


    function assign_repo_users(repository_id, user_ids, user_type) {
        $.ajax({
            url: "/copo/assign_repo_users/",
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'user_type': user_type,
                'repo_id': repository_id,
                'user_ids': JSON.stringify(user_ids),
            },
            success: function (data) {
                add_submitters(repository_id);
            },
            error: function () {
                alert("Couldn't assign repository users!");
            }
        });
    }

    function deassign_repo_users(repository_id, user_ids, user_type) {
        $.ajax({
            url: "/copo/deassign_repo_users/",
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'user_type': user_type,
                'repo_id': repository_id,
                'user_ids': JSON.stringify(user_ids),
            },
            success: function (data) {
                add_submitters(repository_id);
            },
            error: function () {
                alert("Couldn't remove repository users!");
            }
        });
    }

    function handle_repo_type_change(eventObj) {
        var elemId = eventObj.elementId;
        var selectedVal = eventObj.selectedValue;
        var elem = $(document).find("[data-element='" + elemId + "']");

        if (!selectedVal) {
            return true;
        }

        if (!repositorySchemaObject) {
            return true;
        }

        if (!selectizeObjects.hasOwnProperty(elemId)) {
            return true;
        }

        var form_schema = repositorySchemaObject.form.form_schema;
        var valueObject = selectizeObjects[elemId].options[selectedVal];


        // go through and display only relevant fields
        for (var p in form_schema) {
            var specifications = [];

            if (form_schema[p].hasOwnProperty("specifications")) {
                specifications = form_schema[p].specifications;
            }

            var child = document.getElementById(form_schema[p].id);

            if (specifications.length == 0) {
                if (child) {
                    child.closest(".rendered-control").style.display = 'block';
                }

                continue;
            }

            if (specifications.indexOf(selectedVal) > -1) {
                if (child) {
                    child.closest(".rendered-control").style.display = 'block';
                }

                continue;
            }

            child.closest(".rendered-control").style.display = 'none';
        }

        var supported_templates = [];
        var metadata_templates_options = [];


        if (valueObject.hasOwnProperty("supported_templates")) {
            supported_templates = valueObject.supported_templates;
        }

        //get all metadata template options
        for (var p in form_schema) {
            var formElem = form_schema[p];
            var formElemId = formElem.id.split(".").slice(-1)[0];
            if (formElemId == "templates") {
                metadata_templates_options = formElem.option_values;
                break;
            }
        }

        //refresh templates options
        var new_data = [];

        for (var i = 0; i < metadata_templates_options.length; ++i) {
            var data = metadata_templates_options[i];

            if (supported_templates.indexOf(data.value) > -1) {
                new_data.push({
                    id: data.value,
                    text: data.label,
                });
            }
        }


        var templateElem = $('[name="copo.repository.templates"]');
        var currentTemplateValue = templateElem.val();
        templateElem
            .empty()
            .select2({data: new_data});

        if (currentTemplateValue) {
            templateElem
                .val(currentTemplateValue)
                .trigger('change');
        }
    }

    function handle_post_form_load() {
        // var elemId = "copo.repository.type";
        // var elem = $(document).find("[data-element='" + elemId + "']");
        // elem.closest(".rendered-control").siblings().hide();
        return true;
    }


}) //end document ready
