$(document).ready(function () {

    //******************************Event Handlers Block*************************//
    // get table data to display via the DataTables API
    var component = "profile";
    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";
    csrftoken = $.cookie('csrftoken');

    load_profiles();


    //trigger refresh of profiles list
    $('body').on('refreshtable', function (event) {
        do_render_profile_table(globalDataBuffer);
    });

    //handle task button event
    $(document).on("click", ".copo-dt", function (event) {
        event.preventDefault();
        do_record_task($(this));
    });

    //details button hover
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view profile details');
    });

    //event handler for resolving doi and pubmed
    $(document).on('click', '.resolver-submit', function () {
        var elem = $(this).closest("li").find(".resolver-data");

        var idHandle = elem.val();

        idHandle = idHandle.replace(/^\s+|\s+$/g, '');

        if (idHandle.length == 0) {
            return false;
        }

        var spinElem = $(this).closest(".nav").find(".doiLoader");

        spinElem.html("<div style='margin: 0 auto;'><i class='fa fa-spinner fa-pulse fa-2x'></i></div>");

        var idType = elem.attr("data-resolver");
        var component = "publication";
        var profile_id = elem.attr("data-profile");

        //reset input field to placeholder
        elem.val("");

        $.ajax({
            url: copoFormsURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'task': 'doi',
                'component': component,
                'profile_id': profile_id,
                'visualize': 'profiles_counts',
                'id_handle': idHandle,
                'id_type': idType
            },
            success: function (data) {
                json2HtmlForm(data);
                spinElem.html("");
            },
            error: function () {
                spinElem.html("");
                alert("Couldn't resolve resource handle!");
            }
        });
    });


    //handle profile record events
    $(document).on("click", ".profile-item-action", function (event) {
        event.preventDefault();
        var task = $(this).attr("data-record-action").toLowerCase();
        var targetId = $(this).attr("data-record-id");

        if (task == "delete") {
            BootstrapDialog.show({
                title: 'Profile Delete Alert!',
                message: "Do you want to delete this profile?",
                type: BootstrapDialog.TYPE_DANGER,
                animate: true,
                closable: true,
                draggable: true,
                buttons: [{
                    label: 'Cancel',
                    action: function (dialogRef) {
                        dialogRef.close();
                    }
                },
                    {
                        label: 'Delete',
                        cssClass: 'btn-danger',
                        action: function (dialogRef) {
                            //$(this).tooltip('destroy');
                            //todo: implement this delete action

                            dialogRef.close();
                        }
                    }
                ]
            });
        }
    });

    //******************************Functions Block******************************//


    function do_render_profile_table(data) {
        var dtd = data.table_data.dataSet;
        var actionsButtons = data.table_data.action_buttons;

        set_empty_component_message(dtd); //display empty profile message for potential first time users

        if (dtd.length == 0) {
            return false;
        }

        var tableID = 'copo_profiles_table';

        var dataSet = [];

        for (var i = 0; i < dtd.length; ++i) {
            var data = dtd[i];

            //get profile id
            var record_id = '';
            var result = $.grep(data, function (e) {
                return e.key == "_id";
            });

            if (result.length) {
                record_id = result[0].data;
            }

            //get title
            var title = '';
            var result = $.grep(data, function (e) {
                return e.key == "title";
            });

            if (result.length) {
                title = result[0].data;
            }

            //get description
            var description = '';
            var result = $.grep(data, function (e) {
                return e.key == "description";
            });

            if (result.length) {
                description = result[0].data;
            }

            //get date
            var profile_date = '';
            var result = $.grep(data, function (e) {
                return e.key == "date_created";
            });

            if (result.length) {
                profile_date = result[0].data;
            }

            if (record_id) {
                var option = {};
                option["title"] = title;
                option["description"] = description;
                option["profile_date"] = profile_date;
                option["record_id"] = record_id;
                dataSet.push(option);
            }
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
                    style: 'multi', //os, multi, api
                    items: 'row' //row, cell, column
                },
                language: {
                    "info": "Showing _START_ to _END_ of _TOTAL_ profiles",
                    "search": "Search:",
                    "lengthMenu": "show _MENU_ records",
                    "emptyTable": "No work profiles available! Use the 'New Profile' button to create work profiles.",
                    buttons: {
                        selectAll: "Select all",
                        selectNone: "Select none",
                    }
                },
                order: [
                    [2, "desc"]
                ],
                columns: [
                    {
                        "className": 'summary-details-control detail-hover-message',
                        "orderable": false,
                        "data": null,
                        "title": "Details",
                        "defaultContent": ''
                    },
                    {
                        "data": "title",
                        "title": "Title",
                        "visible": true
                    },
                    {
                        "data": "profile_date",
                        "title": "Date created",
                        "visible": true
                    },
                    {
                        "data": "description",
                        "visible": false
                    },
                    {
                        "data": "record_id",
                        "visible": false
                    }
                ],
                "columnDefs": [
                    {"width": "15%", "targets": 2},
                    {"width": "5%", "targets": 0}
                ],
                fnDrawCallback: function () {
                    refresh_tool_tips();
                    refresh_sub_table(tableID);
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

            place_task_buttons(actionsButtons, tableID); //this will place custom buttons on the table for executing tasks on records
        }


        if (table) {
            table.on('select', function (e, dt, type, indexes) {
                activity_agent(dt);
            });

            table.on('deselect', function (e, dt, type, indexes) {
                activity_agent(dt);
            });


            table.on('mouseenter', 'tr', function () {
                var row = table.row(this);
                var currentRow = $(this);

                //close other rows
                $('#' + tableID + ' tbody').find('tr').each(function () {
                    $(this).find(".recordbtns-div").css("display", "none");
                });

                if (row.data()) {
                    currentRow.find(".recordbtns-div").css("display", "block");
                }
            });

        }

    } //end of func

    function append_component_buttons(record_id) {
        //components row
        var components = get_profile_components();
        var componentsDIV = $('<div/>', {
            // class: "pull-right"
        });

        components.forEach(function (comp) {
            //skip profile definition
            if (comp.component == "profile") {
                return false;
            }

            var componentBTN = $('<a/>', {
                class: "btn btn-sm " + comp.colorClass,
                style: "background-image: none; border: none; margin-left: 3px; font-size: 10px;",
                href: $("#" + comp.component + "_url").val().replace("999", record_id),
                title: "Navigate to " + comp.title + " page"
            });

            var componentICON = $('<i/>', {
                class: "copo-components-icons " + comp.iconClass,
                style: "color: #fff"
            });

            var componentTXT = $('<span/>', {
                class: "icon_text",
                style: "color: #ffffff; padding-left: 3px;",
                html: comp.title
            });

            componentBTN.append(componentICON).append(componentTXT);
            componentsDIV.append(componentBTN);
        });

        return componentsDIV;
    }


    function refresh_sub_table(tableID) {
        var table = $('#' + tableID).DataTable();
        // handle opening and closing summary details
        $('#' + tableID + ' tbody')
            .off('click', 'td.summary-details-control')
            .on('click', 'td.summary-details-control', function (event) {
                event.preventDefault();

                var tr = $(this).closest('tr');
                var row = table.row(tr);

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


                    //profile components row
                    var descriptionTR = $('<tr/>');
                    var descriptionTD1 = $('<td/>').append('&nbsp;');
                    var descriptionTD2 = $('<td/>').append(append_component_buttons(row.data().record_id));
                    descriptionTR
                        .append(descriptionTD1)
                        .append(descriptionTD2);

                    contentHtml.append(descriptionTR);

                    //description row
                    descriptionTR = $('<tr/>');
                    descriptionTD1 = $('<td/>').append('<span style="font-weight: bold;">Description:</span>');
                    descriptionTD2 = $('<td/>').append(row.data().description);
                    descriptionTR
                        .append(descriptionTD1)
                        .append(descriptionTD2);

                    contentHtml.append(descriptionTR);

                    row.child($('<div></div>').append(contentHtml).html()).show();
                    tr.addClass('shown');
                }
            });
    }

    function do_render_profile_counts(data) {
        if (data.profiles_counts) {
            var stats = data.profiles_counts;

            for (var i = 0; i < stats.length; ++i) {
                var stats_id = stats[i].profile_id + "_";
                if (stats[i].counts) {
                    for (var k in stats[i].counts) {
                        if (stats[i].counts.hasOwnProperty(k)) {
                            var count_id = stats_id + k;
                            $("#" + count_id).html(stats[i].counts[k]);
                        }
                    }
                }
            }
        }
    }

    function update_counts() {
        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'task': 'profiles_counts',
                'component': component
            },
            success: function (data) {
                do_render_profile_counts(data);
            },
            error: function () {
                alert("Couldn't retrieve profiles information!");
            }
        });
    }

    function load_profiles() {
        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'task': 'table_data',
                'component': component
            },
            success: function (data) {
                do_render_profile_table(data);
            },
            error: function () {
                alert("Couldn't retrieve profiles!");
            }
        });
    }

    function do_record_task(elem) {
        var task = elem.attr('data-action').toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var tableID = elem.attr('data-table'); //get target table

        //retrieve target records and execute task
        var table = $('#' + tableID).DataTable();
        var records = []; //
        $.map(table.rows('.selected').data(), function (item) {
            records.push(item);
        });


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
                    alert("Couldn't build profile form!");
                }
            });
        }

        table.rows().deselect(); //deselect all rows

        //handle button actions
        // if (ids.length > 0) {
        //     if (task == "edit") {
        //         $.ajax({
        //             url: copoFormsURL,
        //             type: "POST",
        //             headers: {'X-CSRFToken': csrftoken},
        //             data: {
        //                 'task': 'form',
        //                 'component': component,
        //                 'target_id': ids[0] //only allowing row action for edit, hence first record taken as target
        //             },
        //             success: function (data) {
        //                 json2HtmlForm(data);
        //             },
        //             error: function () {
        //                 alert("Couldn't build publication form!");
        //             }
        //         });
        //     } else if (task == "delete") { //handles delete, allows multiple row delete
        //         var deleteParams = {component: component, target_ids: ids};
        //         do_component_delete_confirmation(deleteParams);
        //     }
        // }
    }


}) //end document ready