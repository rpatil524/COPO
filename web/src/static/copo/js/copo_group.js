/**
 * Created by etuka on 06/11/15.
 */

$(document).ready(function () {

    $(document).on('click', ".dropdown-menu li a", function (e) {
        $(this).parents(".btn-group").find('.selection').text($(this).text() + ' ');
        alert(el)
    })

    $(document).on('click', '#submit_group', validate_group_form)


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
            })
                .done(function (data) {
                    console.log(data)
                })
        }
    })


});

