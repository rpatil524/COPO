/**
 * Created by fshaw on 06/12/2016.
 */
$(document).ready(function () {


    //******************************Setup Annotator Specifics*************************//
    hide_controls()
    show_help()

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
    $(document).on('click', '.fa-minus-square', delete_annotation)
    $(document).on('mouseenter', '#annotations_table tbody tr', mouseenter_annotation)
        .on('mouseleave', '#annotations_table tbody tr', mouseleave_annotation)
    $(document).on('click', '.dropdown-menu li a', function () {
        $('#file_type_dropdown').val($(this).text())
        $('#file_type_dropdown_label').html($(this).text());
    });
    $(document).on('click', '#annotations_table tbody tr', select_from_annotation_list)
    $(document).on('click', '.delete_annotation', delete_annotation)
    $('.ajax_loading_div').css('visibility', 'hidden')

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
                var request = $.ajax({
                    url: annotationURL,
                    type: "POST",
                    headers: {'X-CSRFToken': csrftoken},
                    dataType: 'json',
                    data: {
                        'task': 'form',
                        'component': component,
                        'target_id': ids[0] //only allowing row action for edit, hence first record taken as target
                    }
                })
                request.done(function (e) {
                    $(document).data('mongo_id', e._id.$oid)
                    $('#annotation_table_wrapper').hide();

                    if (e.type == 'Spreadsheet') {
                        $(document).data('annotator_type', 'ss')
                        show_controls()
                        load_ss_data(e)
                    }
                    else {
                        $(document).data('annotator_type', 'txt')

                        load_txt_data(e)
                    }
                    $('#file_picker_modal').modal('hide');
                });
                request.fail(function (jqXHR, textStatus) {
                    alert("Request failed: " + textStatus);
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

    $('#help_tips').show()
}

function show_controls() {
    $('#help_tips').hide()
    $('#annotation_panel').show()
    $('#annotation_list').show()
    auto_complete();
}

function show_annotation_list(){
    $('#help_tips').hide()
    $('#annotation_list').show()
}

function hide_controls() {
    $('#annotation_panel').hide()
    $('#help_tips').hide()
    $('#annotation_list').hide()
}

function remove_ss_controls(){
    $('#annotation_panel').hide()
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
        app.annotations.load();

    });
    // attach data parameter stating that this page is using annotator, therefore what autocomplete should do
    $(this).data('annotator', true)
}


function load_txt_data(e) {
    // load data from pdf
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
    // load data from spreadsheet and initialise handsontable into global variable 'hot'
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
        beforeOnCellMouseDown: _beforeOnCellMouseDown,
        afterSelection: _afterSelection,
    });
    $(document).data('hot', hot)
    $.cookie('document_id', e._id.$oid, {expires: 1, path: '/',});
    // clear annotations table and populate with annotations
    var doc_id = $(document).data('mongo_id')
    $.get('/api/search/', {'document_id': doc_id}, $.noop(), 'json')
        .done(function (d) {
            $(d.rows).each(function (idx, element) {
                add_line_to_annotation_table(element)
            })
        })
}

function _beforeOnCellMouseDown(event, coords, element) {
    // prevent clicks in the leftmost column doing anything
    if (coords.col == 0) {
        event.stopImmediatePropagation();
    }
}


function _afterSelection(row, col, row2, col2) {
    // color column
    $(document).data('selected_col', col)
    cell = hot.getCell(0, col)
    $('.currentColClass').removeClass('currentColClass')
    $('.currentHeaderClass').removeClass('currentHeaderClass')
    $(cell).addClass('currentHeaderClass')
    $('#annotation_content .htCore tr > td:nth-child(' + (parseInt(col) + 1) + ')').addClass('currentColClass')
    cell = hot.getCell(row, col)
    var d = hot.getDataAtCell(0, col)
    $('#selected_column_name').html(d)
}

function select_from_annotation_list(e) {
    var t = e.currentTarget
    var c_h_text = $(t).find('.column_header_cell').html()
    $('#selected_column_name').html(c_h_text)
    cell = $(t).data('attached_cell')
    var coords = hot.getCoords(cell)
    var col = coords[0]
    $(document).data('selected_col', col)
    $('.currentHeaderClass').removeClass('currentHeaderClass')
    $(cell).addClass('currentHeaderClass')
}

function append_to_annotation_list(item) {
    // this function is called from generic_handlers.js and is fired when an annotation from OLS is selected
    var selected_column_text = $('#selected_column_name').html()
    if (selected_column_text == 'None Selected') {
        return false
    }
    // check if there is already a label with selectedColumnText
    $('#annotations_table tbody tr').each(function (idx, element) {
        var column_header = $(element).data('column_header')
        if (selected_column_text == column_header) {
            // in this case there is already an annotation so delete and then readd
            delete_annotation($(element), true)
        }
    })
    $('.ajax_loading_div').css('visibility', 'visible')
    $('#annotator-field-0').val($(item).data('annotation_value') + ' :-: ' + $(item).data('term_accession'))
    // we are dealing with a spreadsheet so need to add ref to cell data item
    var annotation_value = $(item).data('annotation_value');
    var term_source = $(item).data('term_source');
    var term_accession = $(item).data('term_accession');
    var column_header = $('#selected_column_name').html()
    // add colouring to column to show it has been labelled
    var col = $(document).data('selected_col')
    $('.currentColClass').removeClass('currentColClass')
    $('.currentHeaderClass').removeClass('currentHeaderClass')
    var count = "" + (parseInt(col) + 1)
    $('#annotation_content .htCore tr > td:nth-child(' + count + ')').addClass('labelledColumnClass');
    // send request to backend to save annotation
    var csrftoken = $.cookie('csrftoken');
    var document_id = $(document).data('mongo_id')
    line_data = {
        'document_id': document_id,
        'column_header': column_header,
        'annotation_value': annotation_value,
        'term_source': term_source,
        'term_accession': term_accession,
        'id': {}
    }
    $.ajax({
        url: '/rest/save_ss_annotation',
        type: 'post',
        headers: {
            'X-CSRFToken': csrftoken,
        },
        data: line_data
    }).done(function (d) {
        // add div to panel showing annotation
        line_data.id.$oid = d
        add_line_to_annotation_table(line_data)
    })
}

function add_line_to_annotation_table(line_data) {
    // this function updates the list of annotation on the page
    var tr = $("<tr>");
    var t_header_name = $("<td>");
    t_header_name.append(line_data.column_header).addClass('column_header_cell');
    var t_annotation_value = $("<td>");
    t_annotation_value.append(line_data.annotation_value);
    var t_source = $("<td>");
    t_source.append(line_data.term_source);
    var t_reference = $("<td>");
    t_reference.append(line_data.term_accession);
    var t_delete = $("<td>", {
        "class": "delete_annotation"
    })
    t_delete.append('<i class="fa fa-minus-square" aria-hidden="true"></i>')
    $(tr).append(t_header_name).append(t_annotation_value).append(t_source).append(t_reference).append(t_delete)
    if (typeof cell !== 'undefined') {
        var coords = hot.getCoords(cell)
        cell = hot.getCell(0, coords.col)
        $(tr).data('attached_cell', cell)
    }
    else {
        //iterate through table columns to find correct cell to mouseover matching colors to column
        var c;
        for (var i = 0; i < hot.countCols(); i++) {
            c = hot.getDataAtCell(0, i);
            if (c == line_data.column_header) {
                $(tr).data('attached_cell', hot.getCell(0, i))
                $('#annotation_content .htCore tr > td:nth-child(' + (i + 1) + ')').addClass('labelledColumnClass');
            }
        }
    }
    $(tr).data('annotation_id', line_data.id.$oid)
    $(tr).data('column_header', line_data.column_header)
    $('#annotations_table tbody').append(tr)
    $('.ajax_loading_div').css('visibility', 'hidden')
}


function delete_annotation(e, replacement) {
    // function called when delete button is clicked on annotation list
    var tr;
    if ('currentTarget' in e){
        tr = $(e.currentTarget).closest('tr')
    }
    else{
        tr = e;
    }

    var cell = $(tr).data('attached_cell')
    var hot = $(document).data('hot')
    var col = parseInt(hot.getCoords(cell).col + 1)
    var doc_id = $(document).data('mongo_id')
    var annotation_id = $(tr).data('annotation_id')
    $.ajax({
        url: '/rest/delete_ss_annotation/',
        data: {
            'document_id': doc_id,
            'annotation_id': annotation_id
        },
        type: 'post',
        dataType: 'json',
        headers: {'X-CSRFToken': csrftoken}
    }).done(function (d) {
        if (d.deleted = true) {
            if (typeof replacement == 'undefined') {
                // if the annotation was simply deleted then change the column highlighting back to default state

                $('#annotation_content .htCore tr > td:nth-child(' + col + ')').removeClass('highlightedColumnClass').removeClass('labelledColumnClass');
                $(cell).removeClass('table-header-labeled')
                $(cell).css({'background-color': '', 'color': ''})
            }

            // if the deleteion was a delete and replace, leave colouring the same, just delete the row from the annotation list
            tr.remove()
        }
        else {
            alert('There was a problem deleting the annotation')
        }
    })
}

//these two functions deal with hover colour matching so the user knows which column an annotation refers to
function mouseenter_annotation(e) {
    // get attached cell
    var cell = $(e.currentTarget).data('attached_cell')
    var col_idx = hot.getCoords(cell).col
    $('#annotation_content .htCore tr > td:nth-child(' + (col_idx + 1) + ')').addClass('highlightedColumnClass');
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
    var col_idx = hot.getCoords(cell).col
    $('#annotation_content .htCore tr > td:nth-child(' + (col_idx + 1) + ')').removeClass('highlightedColumnClass');
    try {
        $(cell).css({'background-color': '', 'color': ''})
    }
    catch (err) {
        console.log('cannot remove mouseover class from cell')
    }
    $(e.currentTarget).removeClass('annotation_mouseover')
}


