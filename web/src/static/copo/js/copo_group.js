/**
 * Created by etuka on 06/11/15.
 */

$(document).ready(function () {

    $(document).on('click', ".dropdown-menu li a", function (e) {
        $(this).parents(".btn-group").find('.selection').text($(this).text() + ' ');
        $('#selected_group').html($(this).text())
        $('#selected_group').data('selected_group_id', $(this).data('group-id'))
        $('#delete_group_button').css('visibility', 'visible')
        $('.in,.open').removeClass('in open');
    })
    //toggle_profile_in_group
    $(document).on('click', '#submit_group', validate_group_form)
    $(document).on('click', '#delete_group_button', show_delete_dialog)
    $('#profiles_in_group').multiSelect({
        selectableHeader: "<div class='custom-header'>Your Profiles</div>",
        selectionHeader: "<div class='custom-header'>Added to Group</div>",
        dblClick: true,
        afterSelect: profile_in_group_handler
    })

    //******************************Event Handlers Block*************************//
    var component = "group";
    var copoFormsURL = "/copo/copo_forms/";
    var csrftoken = $.cookie('csrftoken');

    //get component metadata
    var componentMeta = {
        component: 'annotation',
        title: 'Generic Annotations',
        iconClass: "fa fa-pencil",
        semanticIcon: "write",
        countsKey: "num_annotation",
        buttons: ["quick-tour-template", "new-component-template"],
        sidebarPanels: ["copo-sidebar-info", "copo-sidebar-help", "copo-sidebar-annotate"],
        colorClass: "annotations_color",
        color: "violet",
        tableID: 'annotation_table',
        recordActions: ["delete_record_multi"],
        visibleColumns: 10000
    }

    do_global_help(component)

    //load records
    //load_records(componentMeta);

    //instantiate/refresh tooltips
    refresh_tool_tips();

    //trigger refresh of profiles list
    // $('body').on('refreshtable', function (event) {
    //     do_render_component_table(globalDataBuffer, componentMeta);
    // });

    //handle task button event
    $('body').on('addbuttonevents', function (event) {
        do_record_task(event);
    });

    //add new component button
    $(document).on("click", ".new-component-template", function (event) {
        initiate_form_call(component);
    });

    //details button hover
    $(document).on("mouseover", ".detail-hover-message", function (event) {
        $(this).prop('title', 'Click to view ' + component + ' details');
    });


    //******************************Functions Block******************************//

    function do_record_task(event) {
        var task = event.task.toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var tableID = event.tableID; //get target table

        //retrieve target records and execute task
        var table = $('#' + tableID).DataTable();
        var records = []; //
        $.map(table.rows('.selected').data(), function (item) {
            records.push(item);
        });

        //add task
        if (task == "add") {
            initiate_form_call(component);
            return false;
        }

        //edit task
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
                    alert("Couldn't build person form!");
                }
            });
        }

        //table.rows().deselect(); //deselect all rows

    }


    function validate_group_form(e) {
        $('#group_form').validator('validate')
    }

    $('#group_form').validator().on('submit', function (e) {
        if (e.isDefaultPrevented()) {

        } else {
            // submit form to create new group
            var group_name = $('#groupName').val()
            var description = $('#groupDescription').val()
            $.ajax({
                url: "/copo/create_group/",
                data: {
                    "group_name": group_name,
                    "description": description
                },
                dataType: "json"
            }).done(function (data) {
                var li = $("<li>").html("<a href='#' data-group-id='" + data.id + "'>" + data.name + "</a>")
                $('#group_dropdown_ul').append(li)
                $('#group_name_button').text(data.name + ' ');
                $('#selected_group').html(data.name)
                $('#selected_group').data('selected_group_id', data.id)
                $('#add_group_modal').modal('hide')
                $('#delete_group_button').css('visibility', 'visible')
            })
        }
    })

    function show_delete_dialog(e) {
        BootstrapDialog.show({
            title: "Delete Group",
            message: "Do you really want to delete this group?",
            cssClass: 'copo-modal1',
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
                label: '<i class="copo-components-icons fa fa-trash"></i> Delete',
                cssClass: 'tiny ui basic orange button',
                action: function (dialogRef) {
                    $.ajax({
                        url: "/copo/delete_group/",
                        data: {
                            "group_id": $('#selected_group').data('selected_group_id')
                        },
                        dataType: "json"
                    }).done(function (data) {
                        var el = $("a[data-group-id='" + $('#selected_group').data('selected_group_id') + "']")
                        el.remove()
                        $('#group_name_button').text("Select Group" + ' ');
                        $('#selected_group').html("Select Group")
                        $('#selected_group').data('selected_group_id', undefined)
                        $('#delete_group_button').css('visibility', 'hidden')
                    })
                    dialogRef.close();
                }
            }]
        });
    }

    function profile_in_group_handler(values) {
        console.log(values)
    }

});

