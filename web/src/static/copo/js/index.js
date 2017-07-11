$(document).ready(function () {

    //******************************Event Handlers Block*************************//
    // get table data to display via the DataTables API
    var component = "profile";
    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";
    csrftoken = $.cookie('csrftoken');

    //global_help_call
    do_global_help(component);

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

        var components = get_components_properties();

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
                                cellHTML.find(".profile-details").find(".profile-title")
                                    .html(result[0].data);

                                cellHTML.find(".profile-details").find(".profile-title-link")
                                    .attr("href", $("#view_copo_profile_url").val().replace("999", record_id));
                            }

                            //get description
                            var result = $.grep(data, function (e) {
                                return e.key == "description";
                            });

                            if (result.length) {
                                cellHTML.find(".profile-details")
                                    .attr("id", "profile-" + record_id);

                                cellHTML.find(".profile-details > .profile-description").html(result[0].data);
                            }

                            //get date
                            var result = $.grep(data, function (e) {
                                return e.key == "date_created";
                            });

                            if (result.length) {
                                cellHTML.find(".profile-details > .profile-date").html("[" + result[0].data + "]");
                            }

                            // get components
                            for (var i = 0; i < components.length; ++i) {
                                var componentElem = cellHTML.find(".componentTemplateElements > .componentItemElement").clone();

                                //add color class
                                componentElem.find(".component-item").addClass(components[i].colorClass);

                                // add icon class
                                componentElem.find(".component-item-header").find(".copo-components-icons").addClass(components[i].iconClass);
                                componentElem.find(".component-item-header").find(".copo-components-icons").removeClass(function (index, css) {
                                    return (css.match(/(^|\s)copo-icon-\S+/g) || []).join(' ');
                                });


                                componentElem.find(".component-item-header").find(".copo-components-icons").css("color", "#ffffff");

                                //title
                                componentElem.find(".component-item-header > div > span.icon_text").html(components[i].title);

                                //record count
                                componentElem.find(".component-item-body").find(".component-item-badge").attr("id", record_id + "_" + components[i].countsKey);

                                //action buttons

                                if ($.inArray("add", components[i].actions) > -1) {
                                    //add action
                                    var addElem = cellHTML.find(".componentTemplateElements > .componentAddElement").clone();
                                    addElem.attr("data-component", components[i].component);
                                    addElem.attr("data-profile", record_id);
                                    addElem.find("i").prop("title", components[i].addLabel);

                                    componentElem.find(".component-item-body").find(".action-items").append(addElem);
                                }

                                if ($.inArray("inspect", components[i].actions) > -1) {
                                    //inspect action
                                    var inspectElem = cellHTML.find(".componentTemplateElements > .componentInspectElement").clone();
                                    inspectElem.attr("href", $("#" + components[i].component + "_url").val().replace("999", record_id));
                                    inspectElem.find("i").prop("title", "Inspect " + components[i].title);

                                    componentElem.find(".component-item-body").find(".action-items").append(inspectElem);
                                }


                                cellHTML.find(".components-section").append(componentElem);
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
