$(document).ready(function () {

    //******************************Event Handlers Block*************************//
    // get table data to display via the DataTables API
    var tableID = null; //rendered table handle
    var component = "publication";
    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";

    csrftoken = $.cookie('csrftoken');

    load_records(); // call to load component records

    register_resolvers_event(); //register event for publication resolvers

    //instantiate/refresh tooltips
    refresh_tool_tips();

    //trigger refresh of table
    $('body').on('refreshtable', function (event) {
        do_render_component_table(globalDataBuffer);
    });

    //handle task button event
    $(document).on("click", ".copo-dt", function (event) {
        event.preventDefault();
        alert($(this).attr("data-action"));
    });

    //details button hover
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view ' + component + ' details');
    });

    //******************************Functions Block******************************//

    function do_record_task(elem) {
        var task = elem.attr('data-record-action').toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var taskTarget = elem.attr('data-action-target'); //is the task targeting a single 'row' or group of 'rows'?

        var ids = [];

        if (taskTarget == 'row') {
            ids = [elem.attr('data-record-id')];
        } else if (taskTarget == 'rows') {
            //get reference to table, and retrieve selected rows
            if ($.fn.dataTable.isDataTable('#' + tableID)) {
                var table = $('#' + tableID).DataTable();

                ids = $.map(table.rows('.selected').data(), function (item) {
                    return item[item.length - 1];
                });
            }
        }

        //handle button actions
        if (ids.length > 0) {
            if (task == "edit") {
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
                        alert("Couldn't build publication form!");
                    }
                });
            } else if (task == "delete") { //handles delete, allows multiple row delete
                var deleteParams = {component: component, target_ids: ids};
                do_component_delete_confirmation(deleteParams);
            }
        }
    }


    function do_render_component_table(data) {
        var tableID = 'publication_table';
        var dataSet = data.table_data.dataSet;
        var cols = data.table_data.columns;
        var actionsButtons = data.table_data.action_buttons;

        set_empty_component_message(dataSet); //display empty profile message for potential first time users
        if (dataSet.length == 0) {
            return false;
        }

        // treat columns
        var columns = [
            {
                "className": 'summary-details-control detail-hover-message',
                "orderable": false,
                "data": null,
                "title": "Details",
                "defaultContent": ''
            }
        ];

        var sortIndex = 1; //column by which records may be sorted

        for (var i = 0; i < cols.length; ++i) {
            var col = cols[i];
            col["visible"] = false;

            // use date_modified as sort column
            if (col.data == "date_modified") {
                sortIndex = i + 1;
            }

            //only display the first column and date_modifed fields, all others go in sub table
            if ((i < 2) || col.data == "date_modified") {
                col["visible"] = true;
            }

            columns.push(col);
        }


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
                lengthChange: true,
                buttons: [
                    'selectAll',
                    'selectNone'
                ],
                select: {
                    style: 'multi',
                },
                language: {
                    "info": "Showing _START_ to _END_ of _TOTAL_ records",
                    "search": "Search:",
                    "lengthMenu": "show _MENU_ records",
                    select: {
                        rows: {
                            _: "%d records selected",
                            0: "<span style='font-weight:600;'>Click the <span class='fa-stack' style='color:green; font-size:10px;'><i class='fa fa-circle fa-stack-2x'></i><i class='fa fa-plus fa-stack-1x fa-inverse'></i></span> button beside a record to view record details.</span>",
                            1: ""
                        }
                    },
                    buttons: {
                        selectAll: "Select all",
                        selectNone: "Select none"
                    }
                },
                order: [
                    [sortIndex, "desc"]
                ],
                columns: columns,
                "columnDefs": [
                    {"width": "5%", "targets": 0}
                ],
                fnDrawCallback: function () {
                    refresh_tool_tips();
                    refresh_sub_table(tableID, columns);
                },
                dom: 'Bfrtlip',
            });

            table
                .buttons()
                .nodes()
                .each(function (value) {
                    $(this)
                        .removeClass("btn-default")
                        .addClass(' btn-sm dtables-dbuttons');
                });
        }

        if (table) {
            table.on('select', function (e, dt, type, indexes) {
                activity_agent(dt);
            });

            table.on('deselect', function (e, dt, type, indexes) {
                activity_agent(dt);
            });
        }

    } //end of func


    function refresh_sub_table(tableID, columns) {
        var table = $('#' + tableID).DataTable();
        // handle opening and closing summary details
        $('#' + tableID + ' tbody')
            .off('click', 'td.summary-details-control')
            .on('click', 'td.summary-details-control', function (event) {
                event.preventDefault();

                var tr = $(this).closest('tr');
                var row = table.row(tr);

                console.log(columns);

                //close other rows
                $('#' + tableID + ' tbody').find('tr').each(function () {

                    var row_all = table.row($(this));

                    if (row_all.child.isShown()) {
                        // This row is already open - close it
                        if (row_all.data().record_id != row.data().record_id) {
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

                    var contentHtml = $('<table/>', {
                        // cellpadding: "5",
                        cellspacing: "0",
                        border: "0",
                        // style: "padding-left:50px;"
                    });

                    //description row
                    var descriptionTR = $('<tr/>');
                    var descriptionTD1 = $('<td/>').append('<span style="font-weight: bold;">Description:</span>');
                    var descriptionTD2 = $('<td/>').append(row.data().description);
                    descriptionTR
                        .append(descriptionTD1)
                        .append(descriptionTD2);

                    contentHtml.append(descriptionTR);

                    //components row
                    var components = get_profile_components();

                    var componentsTR = $('<tr/>');
                    contentHtml.append(componentsTR);

                    var componentsDIV = $('<div/>');

                    var componentsTD1 = $('<td/>').append('&nbsp;');
                    var componentsTD2 = $('<td/>').append(componentsDIV);
                    componentsTR
                        .append(componentsTD1)
                        .append(componentsTD2);


                    components.forEach(function (item) {
                        var componentBTN = $('<a/>', {
                            class: "btn btn-xs copo-btn-grps " + item.colorClass,
                            style: "margin-right: 5px;",
                            href: $("#" + item.component + "_url").val().replace("999", row.data().record_id),
                            title: "Navigate to " + item.title + " page"
                        });

                        var componentICON = $('<i/>', {
                            class: "copo-components-icons " + item.iconClass,
                            style: "color: rgb(255, 255, 255);",
                        });

                        var componentTXT = $('<span/>', {
                            class: "icon_text",
                            style: "color: #ffffff; padding-left: 3px;",
                            html: item.title
                        });

                        componentBTN.append(componentICON).append(componentTXT);
                        componentsDIV.append(componentBTN);

                    });

                    row.child($('<div></div>').append(contentHtml).html()).show();
                    tr.addClass('shown');
                }
            });
    }

    function register_resolvers_event() {
        //event handler for resolving doi and pubmed
        $('.resolver-submit').on('click', function (event) {
            var triggerElem = $(this);
            $(this).html("<div style='text-align: center'><i class='fa fa-spinner fa-pulse'></i></div>");

            var elem = $(this).closest(".input-group").find(".resolver-data");
            var idHandle = elem.val();

            //reset input field to placeholder
            elem.val("");

            idHandle = idHandle.replace(/^\s+|\s+$/g, '');

            if (idHandle.length == 0) {
                triggerElem.html("Resolve");
                return false;
            }

            var idType = elem.attr("data-resolver");

            $.ajax({
                url: copoFormsURL,
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                data: {
                    'task': 'doi',
                    'component': component,
                    'id_handle': idHandle,
                    'id_type': idType
                },
                success: function (data) {
                    json2HtmlForm(data);
                    triggerElem.html("Resolve");
                    $("#pub_options").collapse("hide");
                },
                error: function () {
                    triggerElem.html("Resolve");
                    $("#pub_options").collapse("hide");
                    alert("Couldn't resolve resource!");
                }
            });
        });
    }

    function load_records() {
        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'task': 'table_data',
                'component': component
            },
            success: function (data) {
                do_render_component_table(data);
            },
            error: function () {
                alert("Couldn't retrieve publication data!");
            }
        });
    }

})//end document ready

