/**
 * Created by fshaw on 06/12/2016.
 */
$(document).ready(function () {

    //******************************Setup Annotator Specifics*************************//

    $.cookie('document_id', 'undefined', {expires: 1, path: '/',});

    $(document).data('annotator_type', 'txt')

    $(document).ajaxStart(function () {
        $('.processing_div').show()
    });
    $(document).ajaxStop(function () {
        $('.processing_div').hide()
    });

    $('#handson').on('click', load_ss_data);

    $(document).on('click', '#tips_button', show_help)
    $(document).on('click', '#annotate_button', show_controls)
    $(document).on('click', '.fa-minus-square', delete_from_annotations_table)
    $(document).on('mouseenter', '#annotations_table tbody tr', mouseenter_annotation)
        .on('mouseleave', '#annotations_table tbody tr', mouseleave_annotation)
    $(document).on('click', '.dropdown-menu li a', function () {
        $('#file_type_dropdown').val($(this).text())
        $('#file_type_dropdown_label').html($(this).text());
    });
    $(document).on('click', '#save_ss_annotation', function () {
        save_annotation()
    })


    //******************************Event Handlers Block*************************//
    // get table data to display via the DataTables API
    var tableID = null; //rendered table handle
    var component = "annotation";
    var copoFormsURL = "/copo/copo_forms/";
    var copoVisualsURL = "/copo/copo_visualize/";
    var annotationURL = "/copo/get_annotation/";

    csrftoken = $.cookie('csrftoken');

    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {'X-CSRFToken': csrftoken},
        data: {
            'task': 'table_data',
            'component': component
        },
        success: function (data) {
            do_render_table(data);
        },
        error: function () {
            alert("Couldn't retrieve annotation data!");
        }
    });


    //event handler for resolving doi and pubmed
    $('.resolver-submit').on('click', function (event) {
        var elem = $($(event.target)).parent().parent().find(".resolver-data");

        var idHandle = elem.val();

        idHandle = idHandle.replace(/^\s+|\s+$/g, '');

        if (idHandle.length == 0) {
            return false;
        }

        $("#doiLoader").html("<div style='text-align: center'><i class='fa fa-spinner fa-pulse fa-2x'></i></div>");

        var idType = elem.attr("data-resolver");

        //reset input field to placeholder
        elem.val("");

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
                $("#doiLoader").html("");
            },
            error: function () {
                $("#doiLoader").html("");
                alert("Couldn't resolve resource handle!");
            }
        });
    });

    // handle/attach events to table buttons
    $('body').on('addbuttonevents', function (event) {
        tableID = event.tableID;

        $(document).on("click", ".copo-dt", function (event) {
            do_record_task($(this));
        });

    });

    //instantiate/refresh tooltips
    refresh_tool_tips();

    //******************************Functions Block******************************//

    function do_record_task(elem) {
        var task = elem.attr('data-record-action').toLowerCase(); //action to be performed e.g., 'Edit', 'Delete'
        var taskTarget = elem.attr('data-action-target'); //is the task targeting a single 'row' or group of 'rows'?

        var ids = [];

        if (taskTarget == 'row') {
            ids = [elem.attr('data-record-id')];
            console.log(elem.target)
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
                    url: annotationURL,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    dataType: 'json',
                    data: {
                        'task': 'form',
                        'component': component,
                        'target_id': ids[0] //only allowing row action for edit, hence first record taken as target
                    },
                    success: function (e) {
                        $('#annotation_table_wrapper').hide();

                        if (e.type == 'Spreadsheet') {
                            $(document).data('annotator_type', 'ss')
                            load_ss_data(e)
                        }
                        else {
                            $(document).data('annotator_type', 'txt')
                            load_txt_data(e)
                        }
                        $('#file_picker_modal').modal('hide');
                    },
                    error: function () {
                        alert("Error loading table data");
                    }
                });
            } else if (task == "delete") { //handles delete, allows multiple row delete
                var deleteParams = {component: component, target_ids: ids};
                do_component_delete_confirmation(deleteParams);
            }
        }
    }

})// end document ready

// global variable for selected cell
cell;

function show_help() {
    $('#annotation_panel').hide()
    $('#help_tips').show()
}

function show_controls() {
    $('#help_tips').hide()
    $('#annotation_panel').show()
}

function setup_annotator(element) {

    // setup csrf token and annotator plugins
    var csrftoken = $.cookie('csrftoken');
    var app = new annotator.App();

    app.include(annotator.ui.main);
    app.include(annotator.storage.http, {
        prefix: 'http://127.0.0.1:8000/api',
        headers: {
            'X-CSRFToken': csrftoken,
        },
    });

    app.start().then(function () {
        //app.annotations.load();

    });

    // attach data parameter stating that this page is using annotator, therefore what autocomplete should do
    $(this).data('annotator', true)
}


function load_txt_data(e) {
    $('#annotation_content').show();
    var initAnnotator = false;
    if (!$.trim($("#annotation_content").html())) {
        // if #annotation_content is empty
        initAnnotator = true
    }
    $('#annotation_content').html(e.raw);
    if (initAnnotator) {
        setup_annotator();
        setup_autocomplete();
    }
    $.cookie('document_id', e._id.$oid, {expires: 1, path: '/',});
}

function load_ss_data(e) {


    var data = JSON.parse(e.raw)
    $('#annotation_content').empty()
    $('#annotation_content').removeAttr("style");

    $('#file_picker_modal').modal('hide');

    $('#annotation_table_wrapper').hide();

    var element = document.getElementById('annotation_content');

    hot = new Handsontable(element, {
        data: data,
        readOnly: true,
        rowHeaders: false,
        colHeaders: false,
        dropdownMenu: true,
        //afterInit: _afterInit,
        beforeOnCellMouseDown: _beforeOnCellMouseDown,
        afterOnCellMouseDown: _columnHeaderClickHandler,
        //currentColClassName: 'currentColClass',
        afterSelection: _afterSelection,

    });
    $(document).data('hot', hot)
    $.cookie('document_id', e._id.$oid, {expires: 1, path: '/',});
}


function _beforeOnCellMouseDown(event, coords, element) {
    if (coords.col == 0) {
        event.stopImmediatePropagation();
    }
}

function _columnHeaderClickHandler(changes, sources) {
    show_controls()
    var hot = $(document).data('hot')
    var d = hot.getDataAtCell(0, sources.col)
    $('#selected_column_name').html(d)
}

function _afterSelection(row, col, row2, col2) {
    // color column
    $(document).data('selected_col', col)
    cell = hot.getCell(0, col)
    $('.currentColClass').removeClass('currentColClass')
    $(cell).addClass('currentHeaderClass')
    $('#annotation_content .htCore tr > td:nth-child(' + (parseInt(col) + 1) + ')').addClass('currentColClass')

    cell = hot.getCell(row, col)
}

function append_to_annotation_list(item) {
    $('#annotator-field-0').val($(item).data('annotation_value') + ' :-: ' + $(item).data('term_accession'))
    // we are dealing with a spreadsheet so need to add ref to cell data item
    var annotation_value = $(item).data('annotation_value');
    var term_source = $(item).data('term_source');
    var term_accession = $(item).data('term_accession');
    $(cell).data('annotation_value', annotation_value);
    $(cell).data('termSource', term_source);
    $(cell).data('termAccession', term_accession);

    // add colouring to column to show it has been labelled
    var col = $(document).data('selected_col')
    $('.ht_core tr:nth-child(col) > td').css('background-color', 'red')
    $(cell).addClass('table-header-labeled');

    // add div to panel showing annotation
    var tr = $("<tr>");

    var t_value = $("<td>");
    t_value.append(annotation_value);
    var t_source = $("<td>");
    t_source.append(term_source);
    var t_accession = $("<td>");
    t_accession.append(term_accession);
    var t_delete = $("<td>")
    t_delete.append('<i class="fa fa-minus-square" aria-hidden="true"></i>')
    $(tr).append(t_value).append(t_source).append(t_accession).append(t_delete)
    $(tr).data('attached_cell', cell)
    $('#annotations_table tbody').append(tr)
}


function save_annotation() {
    console.log($(cell).data('annotation_value'))
    console.log($(cell).data('termSource'))
    console.log($(cell).data('termAccession'))

}


function delete_from_annotations_table(e) {
    var tr = $(e.currentTarget).closest('tr')
    var cell = $(tr).data('attached_cell')
    $(cell).removeClass('table-header-labeled')
    $(cell).css({'background-color': '', 'color': ''})
    tr.remove()
}

function mouseenter_annotation(e) {
    // get attached cell
    var cell = $(e.currentTarget).data('attached_cell')
    try {
        $(cell).css({'background-color': 'rgba(123, 187, 232, 1)', 'color': 'white'})
    }
    catch (err) {
        console.log('cannot add mouseover class to cell')
    }
    $(e.currentTarget).addClass('annotation_mouseover')
}

function mouseleave_annotation(e) {
    var cell = $(e.currentTarget).data('attached_cell')
    try {
        $(cell).css({'background-color': '', 'color': ''})
    }
    catch (err) {
        console.log('cannot remove mouseover class from cell')
    }
    $(e.currentTarget).removeClass('annotation_mouseover')
}