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
                            ;
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
                'countsKey': 'num_data',
                'actions': ["inspect"]
            },
            {
                'text': 'Samples',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-filter copo-icon-success',
                'btnAction': 'sample',
                'countsKey': 'num_sample',
                'actions': ["inspect", "add"]
            },
            {
                'text': 'Submissions',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-envelope copo-icon-warning',
                'btnAction': 'submission',
                'countsKey': 'num_submission',
                'actions': ["inspect"]
            },
            {
                'text': 'Publications',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-paperclip copo-icon-primary',
                'btnAction': 'publication',
                'countsKey': 'num_pub',
                'actions': ["inspect", "add"]
            },
            {
                'text': 'People',
                'className': 'profile-item-url',
                'iconClass': 'fa fa-users copo-icon-default',
                'btnAction': 'person',
                'countsKey': 'num_person',
                'actions': ["inspect", "add"]
            },
            // {
            //     'text': 'Delete profile',
            //     'className': 'profile-item-action',
            //     'iconClass': 'fa fa-trash copo-icon-danger space-left',
            //     'btnAction': 'delete'
            // }
        ];

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
                    "emptyTable": "No work profiles available! Use the 'New Profile' button to create work profiles."
                },
                order: [[1, "desc"]],
                columns: [
                    {
                        "data": null,
                        "orderable": false,
                        "render": function (data) {
                            //grab template from DOM
                            var cellHTML = $(".profile-components-copy").clone().css("display", "block");

                            //get profile id
                            var record_id = null;
                            var result = $.grep(data, function (e) {
                                return e.key == "_id";
                            });

                            if (result.length) {
                                record_id = result[0].data;
                            }

                            //get title
                            var result = $.grep(data, function (e) {
                                return e.key == "title";
                            });

                            if (result.length) {
                                cellHTML.find(".profile-header").find(".profile-title-link")
                                    .html(result[0].data)
                                    .attr("href", $("#view_copo_profile_url").val().replace("999", record_id));
                            }

                            //get description
                            var result = $.grep(data, function (e) {
                                return e.key == "description";
                            });

                            if (result.length) {
                                cellHTML.find(".profile-description")
                                    .html(result[0].data);
                            }

                            //get date
                            var result = $.grep(data, function (e) {
                                return e.key == "date_created";
                            });

                            if (result.length) {
                                cellHTML.find(".profile-column")
                                    .html("[" + result[0].data + "]");
                            }

                            var componentsSection = cellHTML.find(".profile-components-section");
                            for (var i = 0; i < buttons.length; ++i) {
                                var cloneLi = componentsSection.find(".clonable-li").clone().css("display", "block");
                                cloneLi.removeClass("clonable-li");

                                //icon
                                cloneLi.find(".copo-components-icons").addClass(buttons[i].iconClass);

                                //label
                                cloneLi.find(".component-label").html(buttons[i].text);

                                //record count element
                                cloneLi.find(".badge").attr("id", record_id + "_" + buttons[i].countsKey);

                                //inspect element
                                cloneLi.find(".inspect-element").attr("href", $("#" + buttons[i].btnAction + "_url").val().replace("999", record_id));


                                //add action
                                if ($.inArray("add", buttons[i].actions) > -1) {
                                    //form-call element
                                    cloneLi.find(".index-form-call")
                                        .attr("data-profile", record_id)
                                        .attr("data-component", buttons[i].btnAction);
                                } else {
                                    cloneLi.find(".add-li").html("");
                                }

                                componentsSection.append(cloneLi);
                            }


                            return cellHTML.html();
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
