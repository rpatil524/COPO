// FS - 5/07/18

$.fn.delayKeyup = function (callback, ms) {
    var timer = 0;
    var el = $(this);
    $(this).keyup(function () {
        clearTimeout(timer);
        timer = setTimeout(function () {
            callback(el)
        }, ms);
    });
    return $(this);
};

$(document).ready(function () {

    $(document).data('url', 'default')
    $(document).on('click', '#view_repo_structure', check_repo_id)
    $(document).on('click', '.create_add_dataverse', handle_radio)
    $(document).on('click', '.panel-heading', build_dataverse_header_click)
    $(document).on('click', '.dataset-checkbox', select_dataverse)


    $('#create_new_dataverse').attr('disabled', 'disabled')
    $('#search_dataverse').attr('disabled', 'disabled')
    $('#search_dataverse_id').attr('disabled', 'disabled')

    $('#search_dataverse, #search_dataverse_id').delayKeyup(function (e) {
        var typed = e.val()
        var box;
        if (e.attr('id') == "search_dataverse_id") {
            $('#search_dataverse').val("")
            box = 'id'
        }
        else if (e.attr('id') == "search_dataverse") {
            $('#search_dataverse_id').val("")
            box = 'term'
        }
        $('#ajax-loading-div').fadeIn()
        var box = $('input[name="dataverse-radio"]:checked').val()
        $.getJSON("/copo/get_dataverse/", {
            'q': typed,
            'box': box,
            'url': $(document).data('url')
        }, build_dataverse_modal)
    }, 1000)
})


function check_repo_id(e) {
    // check for repo_id
    var repo_id = $('#custom_repo_id').val()
    // get repo info
    $(document).data('current-label', $(e.currentTarget).siblings('.dataset-label').find('.badge'))
    $.getJSON("/copo/get_repo_info/", {'repo_id': repo_id}, function (data) {
        if (data.repo_type == 'dataverse') {
            var url = data.repo_url
            $(document).data('url', url)
        }
    })
}


function handle_radio() {
    var checked = $('input[name=create_dataverse_radio]:checked').val();
    if (checked == 'new') {
        $('#create_new_dataverse').removeAttr('disabled')
        $('#search_dataverse').attr('disabled', 'disabled')
        $('#search_dataverse_id').attr('disabled', 'disabled')
    }
    else {
        $('#search_dataverse').removeAttr('disabled')
        $('#search_dataverse_id').removeAttr('disabled')
        $('#create_new_dataverse').attr('disabled', 'disabled')
    }
}


function build_dataverse_modal(resp) {
    $('#ajax-loading-div').fadeOut()
    var t = $('#dataverse-table-template').clone()
    $(t).attr('id', 'dataverse-table')

    // here we can build dataset table
    var checked = $('input[name=dataverse-radio]:checked').val();
    if (checked == 'dataverse') {
        $(resp.data.items).each(function (idx, el) {
            var trow = "<tr data-type='" + el.type + "' data-entity_id='" + el.entity_id + "'>" +
                "<td class='summary-details-control' style='min-width: 50px; text-align:center'></td>" +
                "<td>" + el.name + "</td>" +
                "<td>" + el.description + "</td>" +
                "<td>" + el.published_at + "</td>" +
                "<td>" + el.type + "</td>"
            "</tr>"
            t.find('tbody').append(trow)
        })
    }
    else if (checked == 'dataset') {
        var trow
        var colCheck
        $(resp.data.items).each(function (idx, el) {

            colCheck = "<td style='text-align: center'><div class='dataset-checkbox pretty p-default' style='font-size: 26px'>" +
                "<input type='checkbox'/>" +
                "<div class='state  p-success'>" +
                "<label></label>" +
                "</div>" +
                "</div></td>"
            trow = "<tr data-type='" + el.type + "' data-id='" + el.entity_id + "' data-identifier='" + el.name + "' data-persistent='" + el.url + "'>" +
                colCheck +
                "<td>" + el.name + "</td>" +
                "<td>" + el.description + "</td>" +
                "<td>" + el.published_at + "</td>" +
                "<td>" + el.type + "</td></tr>"
            t.find('tbody').append(colCheck).append(trow)


        })

    }

    $('#table-div-dataverse').empty()
    $('#table-div-dataverse').append(t)
    ///$('#dataverse-table .summary-details-control').on('click', expand_table)
    $('#dataverse-table').DataTable();

    $('#dataverse-table tbody')
        .off('click', 'td.summary-details-control')
        .on('click', 'td.summary-details-control', expand_table);

}

function build_dataverse_header_click(e) {
    var doid = $(e.currentTarget).data('doid')
}

function select_dataverse(e) {

    var row = $(e.currentTarget).closest('tr')
    var dataset_id = $(row).data('id')
    var persistent = $(row).data('persistent')
    var identifier = $(row).data('identifier')
    var entity_id = $(row).data('id')
    $('#dataset_id').val(dataset_id)
    var label = $(document).data('current-label')
    $(label).html(identifier + " - " + persistent)
    $('#repo_modal').modal('hide')

}

function expand_table(event) {
    event.preventDefault();

    var table = $('#dataverse-table').DataTable()

    var tr = $(this).closest('tr');
    var type = $(tr).data('type')
    var entity_id = $(tr).data('entity_id')
    var row = table.row(tr);
    row.deselect(); // remove selection on row

    //close other rows
    // $('#' + tableID + ' tbody').find('tr').each(function () {
    //
    //     var row_all = table.row($(this));
    //
    //     if (row_all.child.isShown()) {
    //         // This row is already open - close it
    //         if (row_all.data().record_id != row.data().record_id) {
    //             row_all.child('');
    //             row_all.child.hide();
    //             $(this).removeClass('shown');
    //         }
    //     }
    // });

    if (row.child.isShown()) {
        // This row is already open - close it
        row.child('');
        row.child.hide();
        tr.removeClass('shown');
    } else {
        // expand row
        if (type == 'dataverse') {
            $.get("/copo/get_dataverse_content/", {
                'id': entity_id,
                'url': $(document).data('url')
            }, function (data) {

                try {
                    var data = JSON.parse(data)
                }
                catch (e) {
                    row.child($('<div></div>').append("<h5>JSON ERROR</h5>")).show();
                    return
                }
                if (data.status == "ERROR") {
                    row.child($('<div></div>').append("<h5>" + data.message + "</h5>")).show();
                    return
                }
                if (data.length == 0) {
                    row.child($('<div></div>').append("<h5>No Datasets to Show</h5>")).show();
                    return
                }

                var headerHtml = $("<h5>Datasets in Dataverse</h5>")
                var contentHtml = ($('<table/>', {
                    // cellpadding: "5",
                    cellspacing: "0",
                    border: "0",
                    // style: "padding-left:50px;"
                }))
                var tr_header = $("<tr/>")

                var title = $("<th/>", {
                    html: "Title"
                })
                var doi = $("<th/>", {
                    html: "DOI"
                })

                var description = $("<th/>", {
                    html: "Description"
                })
                var publication_date = $("<th/>", {
                    html: "Publication Date"
                })
                var czech = $("<th/>", {
                    html: "Select"
                })

                var thead = document.createElement("thead")
                $(thead).append($(tr_header).append(title).append(doi).append(description).append(publication_date).append(czech))
                $(contentHtml).append(thead)

                $(data).each(function (idx, el) {
                    var colTR = $('<tr/>')
                    $(colTR).attr('data-id', el.id)
                    $(colTR).attr('data-identifier', el.title)
                    $(colTR).attr('data-persistent', el.persistentUrl)
                    var col1 = $('<td/>').append(el.title);
                    var col2 = $('<td/>').append(el.dsDescription[0].dsDescriptionValue.value);
                    var col3 = $('<td/>').append(el.dateOfDeposit)
                    var col4 = $('<td/>').append('dataset')

                    var colCheck = $('<td>/').append("<div class='pretty p-default' style='font-size: 26px'>" +
                        "<input type='checkbox' class='dataset-checkbox'/>" +
                        "<div class='state  p-success'>" +
                        "<label></label>" +
                        "</div>" +
                        "</div>")
                    colTR.append(colCheck).append(col1).append(col2).append(col3).append(col4);
                    contentHtml.append(colTR);
                })


                contentHtml.find("tbody > tr").css("background-color", "rgba(229, 239, 255, 0.3)");

                row.child($('<div></div>').append(headerHtml).append(contentHtml).html()).show();
                tr.addClass('shown');
            })
        }


    }
}
