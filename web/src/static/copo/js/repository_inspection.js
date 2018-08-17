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
    $(document).on('click', '#view_repo_structure', mark_as_active_panel)
    $(document).on('click', '.create_add_dataverse', handle_radio)
    $(document).on('click', '.dataset-checkbox', select_dataset)
    $(document).on('click', '#save_inspection_button', save_inspection_info)

    do_new_dataverse_fields()


    // delayed keyup function to delay searching for n miliseconds before firing search off to dataverse
    $('#search_dataverse').delayKeyup(function (e) {
        var typed = e.val()
        var search_type = e.attr('id')
        var box;

        $('#ajax-loading-div').fadeIn()
        var box = $('input[name="dataverse-radio"]:checked').val()
        $.getJSON("/copo/get_dataverse/", {
            'q': typed,
            'box': box,
            'submission_id': $(document).data('submission_id')
        }, build_dataverse_modal)
    }, 1000)


})


// function to get url for selected repo
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

function mark_as_active_panel(e) {
    var submission_id = $(e.currentTarget).data('submission_id')
    $(document).data('submission_id', submission_id)
    console.log("Active Sub" + " " + submission_id)
}

// enable / disable inputs depending on which radio has been selected
function handle_radio() {
    var checked = $('input[name=create_dataverse_radio]:checked').val();
    if (checked == 'new') {
        $('.new-controls').show()
        $('.existing-controls').hide()
    }
    else {
        $('.new-controls').hide()
        $('.existing-controls').show()
    }
}

// build table showing either dataverses or datasets based on returns from search
function build_dataverse_modal(resp) {

    $('#ajax-loading-div').fadeOut()
    var t = $('#dataverse-table-template').clone()
    $(t).attr('id', 'dataverse-table')
    var checked = $('input[name=dataverse-radio]:checked').val();
    if (checked == 'dataverse') {
        $(resp.data.items).each(function (idx, el) {
            var trow = "<tr data-alias='" + el.identifier + "' data-type='" + el.type + "' data-entity_id='" + el.entity_id + "'>" +
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

/*
function build_dataverse_header_click(e) {
    var doid = $(e.currentTarget).data('doid')
}
*/


// when dataverse is expanded, fire off request to dataverse to get information on datasets contained within
function expand_table(event) {

    event.preventDefault();
    var dv_alias = $(event.currentTarget).closest('tr').data('alias')
    $(document).data('dv_alias', dv_alias)
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
                'submission_id': $(document).data('submission_id')
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
                $(thead).append($(tr_header).append("<td/>").append(title).append(doi).append(description).append(publication_date).append(czech))
                $(contentHtml).append(thead)

                $(data).each(function (idx, el) {
                    var colTR = $('<tr/>')
                    $(colTR).attr('data-id', el.id)
                    $(colTR).attr('data-identifier', el.title)
                    $(colTR).attr('data-persistent', el.persistentUrl)
                    var col1 = $('<td/>').append(el.title);
                    var col11 = $('<td/>').append(el.persistentUrl);
                    var col2 = $('<td/>').append(el.dsDescription[0].dsDescriptionValue.value);
                    var col3 = $('<td/>').append(el.dateOfDeposit)
                    var col4 = $('<td/>').append('dataset')

                    var colCheck = $('<td>/').append("<div class='pretty p-default' style='font-size: 26px'>" +
                        "<input type='checkbox' class='dataset-checkbox'/>" +
                        "<div class='state  p-success'>" +
                        "<label></label>" +
                        "</div>" +
                        "</div>")
                    colTR.append(colCheck).append(col1).append(col11).append(col2).append(col3).append(col4);
                    contentHtml.append(colTR);
                })


                contentHtml.find("tbody > tr").css("background-color", "rgba(229, 239, 255, 0.3)");

                row.child($('<div></div>').append(headerHtml).append(contentHtml).html()).show();
                tr.addClass('shown');
            })
        }


    }
}

function do_new_dataverse_fields() {
    $.getJSON("/copo/get_info_for_new_dataverse/", function (data) {

        $('#dvName').val(data.dvName)
        $('#dvAlias').val(data.dvAlias)
        $('#dvContactFirstname').val(data.dvPerson[0].firstName)
        $('#dvContactLastname').val(data.dvPerson[0].lastName)
        $('#dsTitle').val(data.dsTitle)
        $('#dsDescription').val(data.dsDescriptionValue)
        $('#dsAuthorFirstname').val(data.dvPerson[0].firstName)
        $('#dsAuthorLastname').val(data.dvPerson[0].lastName)
        $('#dsAffiliation').val(data.dsAffiliation)
        $('#dsContactFirstname').val(data.dvPerson[0].firstName)
        $('#dsContactLastname').val(data.dvPerson[0].lastName)
        $('#dsContactEmail').val(data.dvPerson[0].email)
    })
}

function save_inspection_info(e) {
    //e.preventDefault()
    var sub_id = $(document).data('submission_id')
    var jsondata = JSON.stringify($('#repo_metadata_form').serializeFormJSON())
    $.ajax({
        url: "/copo/update_submission_repo_data/",
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'submission_id': sub_id,
            'task': 'change_meta',
            'meta': jsondata,
        },
        success: function (data) {
            $('#repo_modal').modal('toggle')
        },
        error: function () {
        }
    });
}

// when a dataset checkbox is clicked store dataset details and update label info
function select_dataset(e) {
    var sub_id = $(document).data('submission_id')
    var row = $(e.currentTarget).closest('tr')
    var dataset_id = $(row).data('id')
    var persistent = $(row).data('persistent')
    var identifier = $(row).data('identifier')
    var entity_id = $(row).data('id')
    $('#dataset_id').val(dataset_id)
    var label = $(document).data('current-label')
    $(label).html(identifier + " - " + persistent)
    $.ajax({
        url: "/copo/update_submission_repo_data/",
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'submission_id': sub_id,
            'task': 'change_meta',
            'meta': JSON.stringify({
                'doi': persistent,
                'dataset_id': dataset_id,
                'identifier': identifier,
                'dataverse_alias': $(document).data('dv_alias'),
                'dataverse_id': $(document).data('entity_id')
            })
        },
        success: function (data) {
            $('#repo_modal').modal('hide')
        },
        error: function () {
        }
    });


}