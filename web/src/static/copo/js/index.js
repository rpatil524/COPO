$(document).ready(function () {

    //******************************Event Handlers Block*************************//
    // get table data to display via the DataTables API
    var component = "profile";
    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";
    csrftoken = $.cookie('csrftoken');

    load_profiles();

    //trigger refresh of profiles list
    $('body').on('refreshprofiles', function (event) {
        do_render_profile_table(globalDataBuffer);
    });

    $('body').on('refreshprofilescounts', function (event) {
        do_render_profile_counts(globalDataBuffer);
    });

    $(document).on('click', '.component-li', function (event) {
        //hide_component_panels();
    });

    $(document).on("click", ".modules-panel", function (event) {
        var targetID = $(this).attr("data-target-id");

        $('.modules-panel').each(function () {
            if ($(this).attr('data-target-id') != targetID) {
                $(this).closest(".panel-group").find(".collapse").collapse('hide');
            }
        });
    });

    //handle expansion of description
    $(document).on('click', 'span.summary-details-control', function () {
        var div = $(this).closest(".profile-column");
        var trg = div.find(".full-description");
        var shrtrg = div.find(".short-description");

        if (trg.is(":visible")) {
            // already open - close it
            trg.hide(400);
            shrtrg.show();
            div.removeClass("shown");
        }
        else {
            trg.show(400);
            shrtrg.hide();
            div.addClass("shown");
        }
    });

    //form call
    $(document).on('click', '.index-form-call', function (e) {
        e.preventDefault();

        var component = $(this).attr("data-component");
        var profile_id = $(this).attr("data-profile");

        $.ajax({
            url: copoFormsURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'task': 'form',
                'component': component,
                'profile_id': profile_id,
                'visualize': 'profiles_counts'
            },
            success: function (data) {
                json2HtmlForm(data);
            },
            error: function () {
                alert("Couldn't build " + component + " form!");
            }
        });
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
            headers: {'X-CSRFToken': csrftoken},
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
                buttons: [
                    {
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

    function isInArray(value, array) {
        return array.indexOf(value) > -1;
    }

    function do_render_profile_table(data) {
        var dtd = data.table_data;

        var buttons = [
            {
                'text': 'Datafiles',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-database copo-icon-info',
                'btnAction': 'datafile',
                'countsKey': 'num_data'
            },
            {
                'text': 'Samples',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-filter copo-icon-success pad-left',
                'btnAction': 'sample',
                'countsKey': 'num_sample'
            },
            {
                'text': 'Submissions',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-envelope copo-icon-warning pad-left',
                'btnAction': 'submission',
                'countsKey': 'num_submission'
            },
            {
                'text': 'Publications',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-paperclip copo-icon-primary pad-left',
                'btnAction': 'publication',
                'countsKey': 'num_pub'
            },
            {
                'text': 'People',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-users copo-icon-default pad-left',
                'btnAction': 'person',
                'countsKey': 'num_person'
            },
            {
                'text': 'Delete profile',
                'className': 'profile-item-action',
                'iconClass': 'fa fa-trash copo-icon-danger space-left',
                'btnAction': 'delete'
            }];

        var table = null;

        if ($.fn.dataTable.isDataTable('#copo_profiles_table')) {
            //if table instance already exists, then do refresh
            table = $('#copo_profiles_table').DataTable();
        }

        if (table) {
            //clear old, set new data
            table.clear().draw();
            table.rows.add(dtd);
            table.columns.adjust().draw();
        } else {
            var table = $('#copo_profiles_table').DataTable({
                data: dtd,
                ordering: true,
                lengthChange: false,
                language: {
                    "info": "Showing _START_ to _END_ of _TOTAL_ work profiles",
                    "search": "Search work profiles:",
                    "emptyTable": "No work profiles available! Use the 'New Profile' button in menu to create work profiles."
                },
                order: [[1, "desc"]],
                columns: [
                    {
                        "data": null,
                        "orderable": false,
                        "render": function (data) {
                            var cellHTML = '<div class="row" style="margin-bottom: 10px;">';

                            //data div
                            var leftColHTML = '<div class="col-sm-5 col-md-5 col-lg-5">';
                            var record_id = data[0].data; //first item is record (profile) id
                            var locus = $("#view_copo_profile_url").val().replace("999", record_id);

                            for (var i = 1; i < data.length; ++i) {
                                if (data[i].key == "title") {
                                    leftColHTML += '<div class="profile-header" style="margin-top: -20px;">';
                                    leftColHTML += '<a href="' + locus + '">' + data[i].data + '</a>';
                                    leftColHTML += '</div>';
                                } else if (data[i].key == "description") {
                                    var toggle_id = record_id + "_description";
                                    leftColHTML += '<div class="profile-column">';
                                    leftColHTML += '<span style="padding-right: 5px;" class="short-description profile-column-data">' + data[i].data.slice(0, 60) + '</span>';
                                    leftColHTML += '<span style="padding-right:5px; display: none;" class="full-description profile-column-data">' + data[i].data + '</span>';
                                    leftColHTML += '<span class="summary-details-control"></span>';
                                    leftColHTML += '</div>';
                                } else {
                                    leftColHTML += '<div class="profile-column">';
                                    leftColHTML += '<span class="profile-column-title">' + data[i].header + ':</span>';
                                    leftColHTML += '<span class="profile-column-data">' + data[i].data + '</span>';
                                    leftColHTML += '</div>';
                                }
                            }
                            leftColHTML += '</div>';

                            //icons div
                            var rightColHTML = '<div class="col-sm-7 col-md-7 col-lg-7">';
                            var bTns = buttons;
                            rightColHTML += '<div>';
                            for (var i = 0; i < bTns.length; ++i) {
                                if (bTns[i].className.indexOf("profile-item-url") > -1) {
                                    var locus = $("#" + bTns[i].btnAction + "_url").val().replace("999", record_id); //matches url hidden in landing_page.html
                                    rightColHTML += '<div class="col-sm-2 col-md-2 col-lg-2" style="text-align: center; padding-right: 0px !important; padding-left: 5px !important;">';

                                    rightColHTML += '<div class="panel-group">';
                                    rightColHTML += '<div class="panel panel-default" style="border-top: 1px solid rgba(245, 245, 240, 0.95); border-color: rgba(245, 245, 240, 0.95);">';
                                    rightColHTML += '<div class="panel-heading" style="background: rgba(245, 245, 240, 0.95);">';
                                    rightColHTML += '<h4 class="panel-title">';
                                    var panel_id = record_id + bTns[i].btnAction;
                                    rightColHTML += '<a class="modules-panel" data-target-id="' + panel_id + '" data-toggle="collapse" href="#' + panel_id + '"><i style="margin-bottom: 5px; font-size: 16px;" class="' + bTns[i].iconClass + '"> </i>';
                                    rightColHTML += '<div style="font-size: 11px; text-align: center;">' + bTns[i].text + '</div>';
                                    var counts_id = record_id + "_" + bTns[i].countsKey;
                                    rightColHTML += '<div style="font-size: 11px; margin-left: -10px; margin-top: 5px;"><span style="background: #595959; border-radius: 4px;" class="badge" id="' + counts_id + '"></span></div>';
                                    rightColHTML += '</a>';
                                    rightColHTML += '</h4>';
                                    rightColHTML += '</div>';
                                    rightColHTML += '<div id="' + panel_id + '" class="panel-collapse collapse">';
                                    rightColHTML += '<div class="panel-body" style="border-top: 1px solid rgba(245, 245, 240, 0.95); overflow: auto;">';

                                    rightColHTML += '<ul class="nav">';
                                    rightColHTML += '<li class="component-li" style="font-size: 11px; white-space: nowrap;"><a href="' + locus + '"><i class="fa fa-eye" aria-hidden="true"></i> Inspect</a></li>';
                                    if (["datafile", "submission"].indexOf(bTns[i].btnAction) < 0) {
                                        rightColHTML += '<li class="component-li" style="font-size: 11px; white-space: nowrap;"><a href="#" class="index-form-call" data-profile="' + record_id + '" data-component="' + bTns[i].btnAction + '"><i class="fa fa-plus-circle" aria-hidden="true"></i> New</a></li>';
                                    }

                                    if (bTns[i].btnAction == "publication") {
                                        rightColHTML += '<li class="component-li"><div style="margin: 0 auto;" class="doiLoader"></div></li>';

                                        rightColHTML += '<li class="component-li" style="font-size: 11px; white-space: nowrap;">';
                                        rightColHTML += '<div class="fuelux">';
                                        rightColHTML += '<div data-initialize="placard" class="placard" style="margin: 0 auto;">';
                                        rightColHTML += '<div class="placard-popup" style="bottom: -34px;"></div>';
                                        rightColHTML += '<input style="font-size: 10px; margin: 0 auto;" size="11" type="text" placeholder="Resolve DOI"  data-profile="' + record_id + '" class="form-control placard-field glass resolver-data" data-resolver="doi">';
                                        rightColHTML += '<div class="placard-footer" style="margin: 0 auto;">';
                                        rightColHTML += '<button type="button" class="btn btn-primary btn-xs placard-cancel resolver-submit">Resolve</button>';
                                        rightColHTML += '</div></div></div>';
                                        rightColHTML += '</li>';

                                        rightColHTML += '<li class="component-li" style="font-size: 11px; white-space: nowrap;">';
                                        rightColHTML += '<div class="fuelux">';
                                        rightColHTML += '<div data-initialize="placard" class="placard" style="margin: 0 auto;">';
                                        rightColHTML += '<div class="placard-popup" style="bottom: -34px;"></div>';
                                        rightColHTML += '<input style="font-size: 10px; margin: 0 auto;" size="11" type="text" placeholder="Resolve PMID"  data-profile="' + record_id + '" class="form-control placard-field glass resolver-data" data-resolver="pmid">';
                                        rightColHTML += '<div class="placard-footer" style="margin: 0 auto;">';
                                        rightColHTML += '<button type="button" class="btn btn-primary btn-xs placard-cancel resolver-submit">Resolve</button>';
                                        rightColHTML += '</div></div></div>';
                                        rightColHTML += '</li>';
                                    }

                                    rightColHTML += '</ul>';

                                    rightColHTML += '</div>';
                                    rightColHTML += '</div>';
                                    rightColHTML += '</div>';
                                    rightColHTML += '</div>';

                                    rightColHTML += '</div>';
                                } else {
                                }

                            }
                            rightColHTML += '</div>';
                            rightColHTML += '</div>';

                            cellHTML += leftColHTML;
                            cellHTML += rightColHTML;

                            cellHTML += '</div>';
                            return cellHTML;
                        }
                    },
                    {
                        "data": dtd,
                        "visible": false,
                        "render": function (data) {
                            return "";
                        }
                    }
                ],
                fnDrawCallback: function () {
                    $("#copo_profiles_table thead").remove();
                    refresh_tool_tips();
                    update_counts();
                }
            });
        }

    }//end of func

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
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'task': 'profiles_counts',
                'component': component
            },
            success: function (data) {
                do_render_profile_counts(data);
                hide_component_panels();
            },
            error: function () {
                alert("Couldn't retrieve profiles information!");
            }
        });
    }

    function hide_component_panels() {
        $('.modules-panel').each(function () {
            $(this).closest(".panel-group").find(".collapse").collapse('hide');
        });
    }

    function load_profiles() {
        $.ajax({
            url: copoVisualsURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
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


})//end document ready
