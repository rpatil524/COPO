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
    $('.ajax-loading-div').hide()
    $(document).data('url', 'default')
    $(document).on('click', '[id^=view_repo_structure]', check_repo_id)
    $(document).on('click', '[id^=view_repo_structure]', mark_as_active_panel)
    $(document).on('click', '.create_add_dataverse', handle_radio)
    $(document).on('click', '.dataset-checkbox', select_dataset)
    $(document).on('click', '#save_inspection_button', save_inspection_info)

    //check_repo_id()
    do_new_dataverse_fields()
    // here we should call funcs for filling out other repo details

    $(document).on("shown.bs.modal", '#repo_modal', function (e) {
        console.log(e.currentTarget)
        add_delay_keyup(e.currentTarget)
    })


})


// delayed keyup function to delay searching for n miliseconds before firing search off to dataverse
function add_delay_keyup(modal) {

    $(modal).find('#search_dataverse, #search_dspace').delayKeyup(function (e) {
        $(document).data('open_modal', modal)
        var q = e.val()
        var search_type = e.attr('id')
        var box = "";
        var repo_type = $('#repo_modal-body').data('repo')
        $('.ajax-loading-div').fadeIn()

        var url
        var handler
        if (repo_type == "dataverse") {
            url = "/copo/get_dataverse/"
            handler = build_dataverse_modal
        }

        $.ajax({
            url: url,
            data: {
                'q': q,
                'box': $('input[name="dataverse-radio"]:checked').val(),
                'submission_id': $(document).data('submission_id')
            },
            dataType: 'json'
        }).done(handler)
            .error(function () {

                trow = "Error Retieving Data. Are you connected to a network?"
                $(modal).find('.modal-body').append(trow)
            })

    }, 1000)

}


// function to get url for selected repo
function check_repo_id(e) {
    // check for repo_id
    var sub_id = $(e.currentTarget).data('submission_id')
    // get repo info
    $(document).data('current-label', $(e.currentTarget).siblings('.dataset-label').find('.badge'))
    $.getJSON("/copo/get_repo_info/", {'sub_id': sub_id}, function (data) {
        if (data.repo_type == 'dataverse') {
            // load dataverse repo html into modal
            $('#repo_modal-body').html()
            var form_html = $('#template_repo_metadata_form').clone()
            $(form_html).attr('id', 'repo_metadata_form')
            $('#repo_modal-body').html(form_html)
            $('#repo_modal-body').data('repo', data.repo_type)
            add_delay_keyup('#search_dataverse')
        }
        else if (data.repo_type == 'dspace') {
            // load dspace repo html into modal
            $('.ajax-loading-div').show()
            $('#repo_modal-body').html()
            var form_html = $('#template_dspace_form').find('form').clone()
            $(form_html).attr('id', 'dspace_form')
            $('#repo_modal-body').html(form_html)
            $('#repo_modal-body').data('repo', data.repo_type)
            $.getJSON("/copo/get_dspace_communities/", {'submission_id': sub_id}).done(build_dspace_modal
            )
        }
    })
}

function mark_as_active_panel(e) {
    var submission_id = $(e.currentTarget).data('submission_id')
    $(document).data('submission_id', submission_id)
    console.log("Active Sub" + " " + submission_id)
}

// enable / disable inputs depending on which radio has been selected
function handle_radio(el) {
    var checked = $(el.currentTarget).find('input[name=create_repo_radio]:checked').val();
    console.log(checked)
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

    $('.ajax-loading-div').fadeOut()


    var modal = $(document).data('open_modal')
    if (resp == "None") {
        trow = "Repo returned an error. Please try again."
        $(modal).find('.modal-body').append(trow)
        return false
    }

    var t = $('#dataverse-table-template').find('table').clone()
    $(t).attr('id', 'dataverse-table')
    var checked = $('input[name=dataverse-radio]:checked').val();
    var trow
    if (checked == 'dataverse') {
        if (resp.data.items.length > 0) {
            $(resp.data.items).each(function (idx, el) {
                console.log(el)
                trow = "<tr data-alias='" + el.identifier + "' data-type='" + el.type + "' data-entity_id='" + el.entity_id + "'>" +
                    "<td class='summary-details-control' style='text-align:center'></td>" +
                    "<td>" + el.name + "</td>" +
                    "<td>" + el.identifier + "</td>" +
                    "<td>" + el.description + "</td>" +
                    "<td>" + el.published_at + "</td>" +
                    "<td>" + el.type + "</td>"
                "</tr>"
            })
        }
        else {
            trow = "<tr><td colspan='5'>No Data to Show</td></tr>"
        }
        $(t).find('tbody').append(trow)
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
            $(t).find('tbody').append(colCheck).append(trow)
        })
    }

    var dt = $(modal).find('#table-div-dataverse')
    $(dt).empty().append(t)

    ///$('#dataverse-table .summary-details-control').on('click', expand_table)
    $('#dataverse-table').DataTable();

    $('#dataverse-table tbody')
        .off('click', 'td.summary-details-control')
        .on('click', 'td.summary-details-control', expand_table);

}


function build_dspace_modal(data) {
    var dt = $('#repo_modal').find('#table-div-dataverse')
    if (data.hasOwnProperty('error')) {
        $(dt).empty().append(data.error)
        return false
    }

    var t = $('#dspace-table-template').find('table').clone()
    $(t).attr('id', 'dspace-table')

    $(data).each(function (idx, el) {
        trow = "<tr  data-dspace_type='" + el.type + "' data-type='dspace' data-alias='" + el.id + "'>" +
            "<td class='summary-details-control' style='text-align:center'></td>" +
            "<td>" + el.name + "</td>" +
            "<td>" + el.handle + "</td>" +
            "<td>" + el.type + "</td></tr>"
        $(t).find('tbody').append(trow)
    })
    var dt = $('.modal').find('#table-div-dataverse')
    $(dt).empty().append(t)
    $('#dspace-table').DataTable()
    $('.ajax-loading-div').fadeOut()
    $('#dspace-table tbody')
        .off('click', 'td.summary-details-control')
        .on('click', 'td.summary-details-control', expand_dspace_table);
}

/*
function build_dataverse_header_click(e) {
    var doid = $(e.currentTarget).data('doid')
}
*/


function expand_dspace_table(event) {
    console.log("EXPAND TABLE")
    event.preventDefault();
    var dv_alias = $(event.currentTarget).closest('tr').data('alias')
    $(document).data('dv_alias', dv_alias)
    var table = $(event.currentTarget).closest('table')


    var tid = $(table).attr('id')

    var table = $("#" + tid).DataTable({

        "bRetrieve": true
    });

    //table = table.DataTable()
    var tr = $(event.currentTarget).closest('tr')
    var row = table.row(tr);

    var type = $(tr).data('type')
    var entity_id = $(tr).data('alias')
    var dspace_type = $(tr).data('dspace_type')
    if (row.child.isShown()) {
        // This row is already open - close it
        row.child('');
        row.child.hide();
        tr.removeClass('shown');
    } else {
        // expand row
        if (type == 'dspace') {
            // get dspace type i.e. collection or item

            if (dspace_type == 'community') {
                $.get("/copo/get_collection/", {
                    'collection_id': entity_id,
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
                    if (data.hasOwnProperty("no_datasets")) {
                        row.child($('<div></div>').append("<h5>" + data.no_datasets + "</h5>")).show();
                        tr.addClass('shown');
                        return
                    }
                    if (data.hasOwnProperty('error')) {
                        row.child($('<div></div>').append("<h5>" + data.error + "</h5>")).show();
                        tr.addClass('shown');
                        return
                    }
                    if (data.length == 0) {
                        row.child($('<div></div>').append("<h5>No Datasets to Show</h5>")).show();
                        return
                    }
                    var headerHtml = $("<h5>Collections in Community</h5>")
                    var contentHtml = ($('<table/>', {
                        // cellpadding: "5",
                        id: "table_" + data.id,
                        cellspacing: "0",
                        border: "0",
                        style: "width: 100% !important"
                    }))
                    var tr_header = $("<tr/>", {
                        "data-id": data.id
                    })

                    var name = $("<th/>", {
                        html: "Name"
                    })

                    var handle = $("<th/>", {
                        html: "Handle"
                    })

                    var type = $("<th/>", {
                        html: "Type"
                    })

                    var thead = document.createElement("thead")
                    $(thead).append($(tr_header).append("<td/>").append(name).append(handle).append(type))
                    $(contentHtml).append(thead)

                    $(data).each(function (idx, el) {
                        var colTR = $('<tr/>', {
                            "data-alias": el.id,
                            "data-type": 'dspace',
                            "data-dspace_type": el.type,
                        })
                        $(colTR).attr('data-id', el.id)

                        var col1 = $('<td/>').append(el.name);
                        var col11 = $('<td/>').append(el.handle);
                        var col111 = $('<td>').append(el.type)

                        var plus = "<td class='summary-details-control' style='vertical-align: top; text-align:center'></td>"
                        colTR.append(plus).append(col1).append(col11).append(col11).append(col111)
                        contentHtml.append(colTR);

                    })

                    $('.shown').removeClass('shown')
                    var del = $(document).data('shown_tr')
                    $(del).remove()

                    contentHtml.find("tbody > tr, thead > tr").css("background-color", "#ececec");
                    contentHtml.find(".row").addClass("no-15-left-margin")
                    //$(contentHtml)
                    //    .off('click', 'td.summary-details-control')
                    //    .on('click', 'td.summary-details-control', expand_dspace_table);
                    var td_temp = $("<td/>", {
                        "colspan": 5
                    })

                    var tdata = $(headerHtml).append(contentHtml)
                    //$(td).append(tdata)
                    td_temp.append(tdata)
                    var tr_temp = $("<tr/>").append(td_temp)
                    //$(tr).parent().append(tr_temp).show();
                    $(tr_temp).insertAfter(tr)
                    $(document).data('shown_tr', tr_temp)
                    $(tr).addClass('shown');
                })
            }
            else if (dspace_type == "collection") {
                $.get("/copo/get_dspace_items/",
                    {
                        'collection_id': entity_id,
                        'submission_id': $(document).data('submission_id')
                    },
                    function (data) {
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
                        if (data.hasOwnProperty("no_datasets")) {
                            row.child($('<div></div>').append("<h5>" + data.no_datasets + "</h5>")).show();
                            tr.addClass('shown');
                            return
                        }
                        if (data.hasOwnProperty('error')) {
                            row.child($('<div></div>').append("<h5>" + data.error + "</h5>")).show();
                            tr.addClass('shown');
                            return
                        }
                        if (data.length == 0) {
                            row.child($('<div></div>').append("<h5>No Datasets to Show</h5>")).show();
                            return
                        }
                        var headerHtml = $("<h5>Items in Collection</h5>")
                        var contentHtml = ($('<table/>', {
                            // cellpadding: "5",
                            cellspacing: "0",
                            border: "0",
                            style: "width: 100% !important"
                        }))
                        var tr_header = $("<tr/>")

                        var name = $("<th/>", {
                            html: "Name"
                        })

                        var handle = $("<th/>", {
                            html: "Handle"
                        })

                        var type = $("<th/>", {
                            html: "Type"
                        })

                        var thead = document.createElement("thead")
                        $(thead).append($(tr_header).append("<td/>").append(name).append(handle).append(type))
                        $(contentHtml).append(thead)

                        $(data).each(function (idx, el) {
                            var colTR = $('<tr/>', {
                                "data-alias": el.id,
                                "data-type": 'dspace',
                                "data-dspace_type": el.type,
                            })
                            $(colTR).attr('data-id', el.id)

                            var col1 = $('<td/>', {
                                class: "name"
                            }).append(el.name);
                            var col11 = $('<td/>', {
                                class: "handle"
                            }).append(el.handle);
                            var col111 = $('<td>', {
                                class: "type"
                            }).append(el.type)

                            var colCheck = $('<td>/').append("<div class='pretty p-default' style='font-size: 26px'>" +
                                "<input type='checkbox' class='dataset-checkbox'/>" +
                                "<div class='state  p-success'>" +
                                "<label></label>" +
                                "</div>" +
                                "</div>")


                            colTR.append(colCheck).append(col1).append(col11).append(col11).append(col111)
                            contentHtml.append(colTR);

                        })
                        contentHtml.find("tbody > tr, thead > tr").css("background-color", "#dceeff");
                        var td_temp = $("<td/>", {
                            "colspan": 5
                        })
                        var tdata = $(headerHtml).append(contentHtml)
                        //$(td).append(tdata)
                        td_temp.append(tdata)
                        var tr_temp = $("<tr/>").append(td_temp)
                        $(tr_temp).insertAfter(tr)
                        $(tr).addClass('shown');
                    }
                )
            }
        }
    }
}

// when dataverse is expanded, fire off request to dataverse to get information on datasets contained within
function expand_table(event) {
    console.log("EXPAND TABLE")
    event.preventDefault();
    var dv_alias = $(event.currentTarget).closest('tr').data('alias')
    $(document).data('dv_alias', dv_alias)
    var table = $(event.currentTarget).closest('table')


    var tid = $(table).attr('id')

    var table = $("#" + tid).DataTable();
    //table = table.DataTable()

    var tr = $(event.currentTarget).closest('tr')
    var type = $(tr).data('type')
    var entity_id = $(tr).data('alias')
    var dspace_type = $(tr).data('dspace_type')
    /*
    if (dspace_type == "community") {
        table = $(table).DataTable({"sorting": false})
    }
    else if (dspace_type == "collection") {
        table = $(table).DataTable({
            "paging": false,
            "sorting": false,
            "searching": false,
            "info": false
        })
    }
    */

    var row = table.row(tr);
    row.deselect(); // remove selection on row
    if (row.child.isShown()) {
        // This row is already open - close it
        row.child('');
        row.child.hide();
        tr.removeClass('shown');
    } else {
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
            if (data.hasOwnProperty("no_datasets")) {
                row.child($('<div></div>').append("<h5>" + data.no_datasets + "</h5>")).show();
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

            var identifier = $("<th/>", {
                html: "Identifier"
            })
            var publisher = $("<th/>", {
                html: "Publisher"
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
            var type = $("<th/>", {
                html: "Type"
            })

            var thead = document.createElement("thead")
            $(thead).append($(tr_header).append("<th/>").append(identifier).append(publisher).append(publication_date).append(type))
            $(contentHtml).append(thead)

            $(data).each(function (idx, el) {
                var colTR = $('<tr/>')
                $(colTR).attr('data-id', el.id)
                $(colTR).attr('data-identifier', el.identifier)
                $(colTR).attr('data-persistent', el.persistentUrl)
                var col1 = $('<td/>').append(el.identifier);
                var col11 = $('<td/>').append(el.publisher);
                //var col2 = $('<td/>').append(el.dsDescription[0].dsDescriptionValue.value);
                var col3 = $('<td/>').append(el.publicationDate)
                var col4 = $('<td/>').append('dataset')

                var colCheck = $('<td>/').append("<div class='pretty p-default' style='font-size: 26px'>" +
                    "<input type='checkbox' class='dataset-checkbox'/>" +
                    "<div class='state  p-success'>" +
                    "<label></label>" +
                    "</div>" +
                    "</div>")
                colTR.append(colCheck).append(col1).append(col11).append(col3).append(col4);
                contentHtml.append(colTR);
            })
            contentHtml.find("tbody > tr").css("background-color", "rgba(229, 239, 255, 0.3)");
            row.child($('<div></div>').append(headerHtml).append(contentHtml).html()).show();
            tr.addClass('shown');
        })
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
            var label = $(document).data('current-label')
            $(label).html("New Dataverse: " + $('#dvName').val())
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
    if ($(row).data('type') == 'dspace') {
        var identifier = $(row).data('alias')
        var name = $(row).find('.name').html()
        var handle = $(row).find('.name').html()
        var label = $(document).data('current-label')
        $(label).html(identifier + " - " + name)
        data = {
            'submission_id': sub_id,
            'task': 'change_meta',
            'meta': JSON.stringify({
                'identifier': identifier,
                'dspace_item_name': name
            })
        }
    }
    else {
        var dataset_id = $(row).data('id')
        var persistent = $(row).data('persistent')
        var identifier = $(row).data('identifier')
        var entity_id = $(row).data('id')
        $('#dataset_id').val(dataset_id)
        var label = $(document).data('current-label')
        $(label).html(identifier + " - " + persistent)
        data = {
            'submission_id': sub_id,
            'task': 'change_meta',
            'meta': JSON.stringify({
                'doi': persistent,
                'dataset_id': dataset_id,
                'identifier': identifier,
                'dataverse_alias': $(document).data('dv_alias'),
                'dataverse_id': $(document).data('entity_id')
            })
        }
    }

    $.ajax({
        url: "/copo/update_submission_repo_data/",
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: data,
        success:
            function (data) {
                $('#repo_modal').modal('hide')
            },
        error: function () {
        }
    })
    ;


}