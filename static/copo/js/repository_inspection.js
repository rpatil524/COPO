// FS - 5/07/18


$(document).ready(function () {
    $('.ajax-loading-div').hide()
    $(document).data('url', 'default')
    $(document).on('click', '[id^=view_repo_structure]', mark_as_active_panel)
    $(document).on('click', '[id^=view_repo_structure]', check_repo_id)

    $(document).on('click', '[id^=view_repo_structure]', get_existing_metadata)
    $(document).on('click', '.create_add_dataverse', handle_radio)
    $(document).on('click', '.dataset-checkbox', select_dataset)
    $(document).on('click', '#save_inspection_button', save_inspection_info)
    $(document).on('change', '.create_add_community_radio_div', get_existing_communites)
    $(document).on('click', '.target_repo_option', get_existing_metadata)
    //check_repo_id()
    // do_new_dataverse_fields()
    // here we should call funcs for filling out other repo details


    $(document).on('keyup', '#search_dataverse', function (el) {
        //$(document).data('open_modal', modal
        e = $(el.currentTarget)
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


    })
    //$('#repo_modal').find('input[value="existing"]').attr("checked", "checked")


    // handle dataverse submission context change
    $(document).on('change', '#dataverse_submission_context', function (event) {
        let elem = $(this);

        let parentElem = elem.closest(".submission-panel");
        reload_dv_search(parentElem, elem.val());
    });

    // handle ckan submission context change
    $(document).on('change', '#ckan_submission_context', function (event) {
        let elem = $(this);

        let parentElem = elem.closest(".submission-panel");
        reload_ckan_panel(parentElem, elem.val());
    });

    //handle dspace context change
    $(document).on('change', '#dspace_submission_context', function (event) {
        handle_dspace_context_change($(this).closest(".submission-panel"));
    });

    //handle dataverse/dataset value change
    $(document).on('dv_value_change', function (event) {
        handle_dv_choice(event);
    });

    $(document).on('ds_value_change', function (event) {
        handle_dv_choice(event);
    });

    //ckan dataset search value change
    $(document).on('ckan_value_change', function (event) {
        handle_ckan_choice(event);
    });


}); //end of document ready


// enable / disable inputs depending on which radio has been selected
function handle_radio(el) {
    var checked = $(el.currentTarget).find('input[name=create_repo_radio]:checked').val();
    if (checked == 'new') {
        $('.new-controls').show()
        $('.existing-controls').hide()
        if ($(document).data("selected_repo_type") == "ckan") {
            $('#repo_modal').find('#table-div-dataverse').hide()
        }
        $('#repo_modal').find('#existing_metadata_table_div').show()
        get_existing_metadata()
    } else {
        $('#repo_modal').find('#table-div-dataverse').show()
        //$('.new-controls').hide()
        //$('.existing-controls').show()
        $('#repo_modal').find('#existing_metadata_table_div').hide()
    }
}


function get_existing_metadata(e) {
    if (e) {
        var sub_id = $(e.currentTarget).attr('data-submission_id')
    } else {
        var sub_id = $(document).data('submission_id')
    }
    $.ajax({
        url: '/copo/get_existing_metadata/',
        data: {'sub_id': $(document).data('submission_id')},
        dataType: 'json',
    }).done(function (data) {
        if (!$.isEmptyObject(data)) {
            var table = $("<table/>", {id: "existing_metadata_table"})
            var hr = $("<tr/>")
            $(hr).append($("<th/>", {text: "Fieldname"}), $("<th/>", {text: "Value"}))
            $(table).append(hr)
            for (el in data.meta) {
                var row = $("<tr/>")
                item = data.meta[el]
                $(row).append($("<td/>", {text: item.dc}), $("<td/>", {text: item.vals}))
                $(table).append(row)
            }
            $('#repo_modal').find('#existing_metadata_table_div').empty()
            $('#repo_modal').find("#existing_metadata_table_div").append($("<h5/>", {text: "Submitting with the following metadata."}))
            $('#repo_modal').find("#existing_metadata_table_div").append(table)
            $('#repo_modal').find('#existing_metadata_table_div').show()
            $(table).DataTable()
        }
    })
}

function get_existing_communites() {

    $('.ajax-loading-div').show()
    // retrieve community details for community

    $('.existing_community_table').show()
    $.ajax({
        url: '/copo/get_dspace_communities/',
        dataType: 'json',
        data: {
            'submission_id': $(document).data('submission_id')
        }
    }).done(function (data) {
        // destroy existing datatable and pass data for refresh
        var table = $("#repo_modal").find("#dspace-table").DataTable()
        table.destroy()
        build_dspace_modal(data)
    })
}

// delayed keyup function to delay searching for n miliseconds before firing search off to dataverse


// function to get url for selected repo
function check_repo_id(e) {
    // check for repo_id
    var sub_id = $(e.currentTarget).data('submission_id')
    // get repo info
    $(document).data('current-label', $(e.currentTarget).siblings('.dataset-label'))
    $.getJSON("/copo/get_repo_info/", {'sub_id': sub_id}, function (data) {
        $(document).data("selected_repo_type", data.repo_type)
        if (data.repo_type == 'dataverse') {
            // load dataverse repo html into modal
            $('#repo_modal-body').html()
            var form_html = $('#template_repo_metadata_form').clone()
            $(form_html).attr('id', 'repo_metadata_form')
            $('#repo_modal-body').html(form_html)
            $('#repo_modal-body').data('repo', data.repo_type)
            //add_delay_keyup('#search_dataverse')
        } else if (data.repo_type == 'dspace') {
            // load dspace repo html into modal
            $('.ajax-loading-div').show()
            $('#repo_modal-body').html()
            var form_html = $('#template_dspace_form').find('.form_content').clone()
            $(form_html).attr('id', 'dspace_form')
            $('#repo_modal-body').html(form_html)
            $('#repo_modal-body').data('repo', data.repo_type)
            $.getJSON("/copo/get_dspace_communities/", {'submission_id': sub_id}).done(build_dspace_modal
            )
        } else if (data.repo_type == 'ckan') {
            $('.ajax-loading-div').show()
            $('#repo_modal-body').html()
            var form_html = $('#template_dspace_form').find('.form_content').clone()
            $(form_html).attr('id', 'dspace_form')
            $('#repo_modal-body').html(form_html)
            $('#repo_modal-body').data('repo', data.repo_type)
            $.getJSON("/copo/get_ckan_items/", {'submission_id': sub_id})
                .done(build_ckan_modal)
        }
    })
    //get_existing_metadata(sub_id)
}

function mark_as_active_panel(e) {
    $(document).data('current-label', $(e.currentTarget).siblings('.dataset-label'))
    var submission_id = $(e.currentTarget).data('submission_id')
    $(document).data('submission_id', submission_id)
}

// build panel to show ckan datasets
function build_ckan_modal(resp) {
    $('.ajax-loading-div').hide()
    if (!resp) {
        trow = "Repo returned an error. Please try again."
        $(modal).find('.modal-body').append(trow)
        return false
    }
    var t = $('#ckan-table-template').find('table').clone()
    $(t).attr('id', 'ckan-table')
    if (resp.status == 1) {
        trow = "<tr><td colspan='5'>" + resp.message + "</td></tr>"
    } else if (resp.result.length > 0) {
        var trow = ""
        $(resp.result).each(function (idx, el) {
            var colCheck = "<tr data-type='ckan' data-alias='" + el + "'><td><div class='pretty p-default' style='font-size: 26px'>" +
                "<input type='checkbox'  class='dataset-checkbox'/>" +
                "<div class='state  p-success'>" +
                "<label></label>" +
                "</div>" +
                "</div>" +
                "</td>" +
                "<td>" + el + "</td>"
            trow = trow + colCheck
        })
        $('#repo_modal').find('#ckan-table').DataTable()
    } else {
        trow = "<tr><td colspan='5'>No Data to Show</td></tr>"
    }
    $(t).find('tbody').append(trow)
    $('#repo_modal').find('#table-div-dataverse').append(t)

    $('#repo_modal').find('input[value="existing"]').trigger("click")
    $('#repo_modal').data("type", "ckan")
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
    var new_or_existing = $('#repo_modal').find('input[name=create_repo_radio]:checked').val()
    console.log(new_or_existing)
    var t = $('#dataverse-table-template').find('table').clone()
    $(t).attr('id', 'dataverse-table')
    var checked = $('input[name=dataverse-radio]:checked').val();
    var trow
    if (checked == 'dataverse') {
        if (resp.data.items.length > 0) {
            if (new_or_existing == "new") {
                colCheck = "<td style='text-align: center'><div class='dataset-checkbox pretty p-default' style='font-size: 26px'>" +
                    "<input type='checkbox'/>" +
                    "<div class='state  p-success'>" +
                    "<label></label>" +
                    "</div>" +
                    "</div></td>"
                $(resp.data.items).each(function (idx, el) {
                    trow = "<tr data-alias='" + el.identifier + "' data-type='" + el.type + "' data-entity_id='" + el.entity_id + "'>" +
                        colCheck +
                        "<td>" + el.name + "</td>" +
                        "<td>" + el.identifier + "</td>" +
                        "<td>" + el.description + "</td>" +
                        "<td>" + el.published_at + "</td>" +
                        "<td>" + el.type + "</td>"
                    "</tr>"

                })
            } else {
                $(resp.data.items).each(function (idx, el) {
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
        } else {
            trow = "<tr><td colspan='5'>No Data to Show</td></tr>"
        }
        $(t).find('tbody').append(trow)
    } else if (checked == 'dataset') {
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

    var dt = $("#repo_modal").find('#table-div-dataverse')
    $(dt).empty().append(t)

    ///$('#dataverse-table .summary-details-control').on('click', expand_table)
    $('#dataverse-table').DataTable();

    $('#dataverse-table tbody')
        .off('click', 'td.summary-details-control')
        .on('click', 'td.summary-details-control', expand_table);

    //$('#repo_modal').find('input[value="existing"]').trigger("click")
    $('#repo_modal').data("type", "dataverse")
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

    $('#repo_modal').find('input[value="existing"]').trigger("click")
    $('#repo_modal').data("type", "dspace")
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
                    } catch (e) {
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
                            "data-name": el.name
                        })
                        $(colTR).attr('data-id', el.id)

                        var col1 = $('<td/>').append(el.name);
                        var col11 = $('<td/>').append(el.handle);
                        var col111 = $('<td>').append(el.type)
                        var new_or_existing = $('#repo_modal').find('input[name=create_repo_radio]:checked').val()
                        if (new_or_existing == "new") {
                            var colCheck = $('<td>/').append("<div class='pretty p-default' style='font-size: 26px'>" +
                                "<input type='checkbox' class='dataset-checkbox'/>" +
                                "<div class='state  p-success'>" +
                                "<label></label>" +
                                "</div>" +
                                "</div>")
                            colTR.append(colCheck).append(col1).append(col11).append(col11).append(col111)
                        } else if (new_or_existing == "existing") {
                            var plus = "<td class='summary-details-control' style='vertical-align: top; text-align:center'></td>"
                            colTR.append(plus).append(col1).append(col11).append(col11).append(col111)

                        }
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
            } else if (dspace_type == "collection") {

                $.get("/copo/get_dspace_items/",
                    {
                        'collection_id': entity_id,
                        'submission_id': $(document).data('submission_id')
                    },
                    function (data) {
                        try {
                            var data = JSON.parse(data)
                        } catch (e) {
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
                                "data-name": el.name
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
    event.preventDefault();
    var dv_alias = $(event.currentTarget).closest('tr').data('alias')
    $(document).data('dv_alias', dv_alias)
    var table = $(event.currentTarget).closest('table')
    var new_or_existing = $('#repo_modal').find('input[name=create_repo_radio]:checked').val()

    var tid = $(table).attr('id')

    var table = $("#" + tid).DataTable();
    //table = table.DataTable()

    var tr = $(event.currentTarget).closest('tr')
    var type = $(tr).data('type')
    var entity_id = $(tr).data('alias')
    var dspace_type = $(tr).data('dspace_type')


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
            } catch (e) {
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
                html: "Name"
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
                $(colTR).attr('data-publisher', el.publisher)
                $(colTR).attr('data-type', "dataverse")
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
    var jsondata = $('#repo_modal').find('form').serializeFormJSON()
    jsondata.new_or_existing = $('#repo_modal').find('input[name=create_repo_radio]:checked').val()

    jsondata_s = JSON.stringify(jsondata)
    $.ajax({
        url: "/copo/update_submission_repo_data/",
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'submission_id': sub_id,
            'task': 'change_meta',
            'meta': jsondata_s,
            'type': $('#repo_modal').data("type")
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
    var type = $(row).data('type')
    var new_or_existing = $('#repo_modal').find('input[name=create_repo_radio]:checked').val()
    if (type == 'dspace' || type == 'ckan') {
        var identifier = $(row).data('alias')
        var name = $(row).data('name')
        var handle = $(row).data('name')

        if (type == 'dspace') {
            data = {
                'type': type,
                'submission_id': sub_id,
                'task': 'change_meta',
                'meta': JSON.stringify({
                    'identifier': identifier,
                    'dspace_item_name': name,
                    'new_or_existing': new_or_existing
                })
            }
        } else if (type == 'ckan') {
            data = {
                'type': type,
                'submission_id': sub_id,
                'task': 'change_meta',
                'meta': JSON.stringify({
                    'identifier': identifier,
                    'new_or_existing': new_or_existing
                })
            }
        }
        // if we are dealing with a dspace submission, decide whether or not to append form data containing new item data

        if (new_or_existing == "new") {
            var formdata = JSON.stringify($('#repo_modal').find('#new_dspace_form').serializeFormJSON())
            data.new_or_existing = "new"
            data.form_data = formdata
            var label = $(document).data('current-label')
            $(label).html(identifier + " - " + name)
        } else {
            data.new_or_existing = "existing"
            var label = $(document).data('current-label')
            if (type == "dspace")
                $(label).html(identifier + " - " + name)
            else {
                $(label).html(identifier)
            }
        }
    } else {
        if (new_or_existing == "existing") {
            var dataset_id = $(row).data('id')
            var persistent = $(row).data('persistent')
            var identifier = $(row).data('identifier')
            var entity_id = $(row).data('id')
            var publisher = $(row).data('publisher')
            $('#dataset_id').val(dataset_id)
            var label = $(document).data('current-label')
            if (type == "ckan") {
                $(label).html("Submitting to: <span class='badge'>" + identifier + "</span>")
            } else {
                $(label).html("Submitting to: <span class='badge'>" + identifier + " - " + persistent + "</span>")
            }
            data = {
                'type': type,
                'submission_id': sub_id,
                'task': 'change_meta',
                'meta': JSON.stringify({
                    "new_or_existing": new_or_existing,
                    'doi': persistent,
                    'dataset_id': dataset_id,
                    'identifier': identifier,
                    'dataverse_alias': $(document).data('dv_alias'),
                    'dataverse_id': $(document).data('entity_id'),
                    'publisher': publisher
                })
            }
        } else {
            var alias = $(row).data('alias')
            var entity_id = $(row).data('entity_id')
            $(document).data('current-label').html(alias)
            data = {
                'type': type,
                'submission_id': sub_id,
                'task': 'change_meta',
                'meta': JSON.stringify({
                    "new_or_existing": new_or_existing,
                    'alias': alias,
                    'entity_id': entity_id
                })
            }
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
    });
}

function get_dataset_api_schema() {
    return [
        {'id': 'name', 'label': 'Name', 'show_in_table': true},
        {'id': 'description', 'label': 'Description', 'show_in_table': true},
        {'id': 'name_of_dataverse', 'label': 'Name_Of_Dataverse', 'show_in_table': false},
        {'id': 'identifier_of_dataverse', 'label': 'Identifier_Of_Dataverse', 'show_in_table': false},
        {'id': 'identifier', 'label': 'Identifier', 'show_in_table': true},
        {'id': 'url', 'label': 'URL', 'show_in_table': true},
        {'id': 'authors', 'label': 'Authors', 'show_in_table': true},
        {'id': 'published_at', 'label': 'Published', 'show_in_table': true},
        {'id': 'citation', 'label': 'Citation', 'show_in_table': true},
        {'id': 'type', 'label': 'Type', 'show_in_table': false},
        {'id': 'global_id', 'label': 'Global Id', 'show_in_table': false},
        {'id': 'citationHtml', 'label': 'Citationhtml', 'show_in_table': false},
        {'id': 'entity_id', 'label': 'Entity_Id', 'show_in_table': false}
    ]
}

function reload_dv_search(parentElem, dv_type) {

    let params = {
        'submission_id': parentElem.attr("data-id"),
        "submission_context": dv_type
    };

    get_dataverse_display(parentElem.find(".submission-proceed-section"), params);
    return true

}


function get_dataverse_display(displayPanel, params) {
    //build ui components and place on panel

    displayPanel.find(".dv-local-panel").remove();
    var localPanel = $('<div/>', {class: "dv-local-panel"});

    displayPanel.append(localPanel);

    // add displayable sections
    var dvTypeDiv = $('<div class="dv-type-div"></div>');
    var searchDiv = $('<div class="search-ctrl-div"></div>');
    var dsListDiv = $('<div class="ds-list-div copo-form-group"></div>');
    var dvSummaryDiv = $('<div class="dv-summary-div copo-form-group"></div>');


    localPanel.append(dvTypeDiv);
    localPanel.append(searchDiv);
    localPanel.append(dsListDiv);
    localPanel.append(dvSummaryDiv);

    //schema will be used to format API returned fields
    params.api_schema = get_dataset_api_schema();

    var search_context = params.submission_context;

    if (search_context == "dataset") {
        search_context = "dataverse,dataset"; //to search across dataverses and datasets
        params.label = "Dataset/Dataverse search";
    }

    params.call_parameters = {'context': search_context, 'submission_id': params.submission_id};

    dvTypeDiv.append(get_submission_context(params));
    searchDiv.append(get_dv_search(params));

    refresh_tool_tips();

    return true;
}

function get_submission_context(params) {
    var panel = $('<div/>');

    var formElem = {
        "ref": "dataverse_submission_context",
        "id": "dataverse_submission_context",
        "label": "Submission context ",
        "help_tip": "Please specify where you want to place this submission.",
        "control": "copo-button-list",
        "type": "string",
        "required": true,
        "control_meta": {},
        "default_value": params.submission_context,
        "option_values": [
            {
                "value": "dataverse",
                "label": "Create a new dataset",
                "description": "Submission will be made to a new dataset. Use the search box below to locate a target dataverse."
            },
            {
                "value": "dataset",
                "label": "Add to an existing dataset",
                "description": "Submission will be made to an existing dataset. Use the search box below to locate a target dataset."
            }
        ]
    };

    var elemValue = formElem.default_value;
    panel.append(dispatchFormControl[controlsMapping[formElem.control.toLowerCase()]](formElem, elemValue));
    panel.find(".constraint-label").remove();

    return panel;
}

function get_dv_search(params) {
    var panel = $('<div/>');

    //place search box
    var label = "Dataverse search";

    if (params.hasOwnProperty("label")) {
        label = params.label;
    }

    var formElem = {
        "ref": "",
        "id": "dataverse_search",
        "label": label,
        "help_tip": "Start typing to search. You can search by author, keyword, name, etc.",
        "required": "true",
        "type": "string",
        "control": "copo-general-onto",
        "value_change_event": "dv_value_change",
        "default_value": "",
        "placeholder": "Enter author, keyword, etc.",
        "control_meta": {},
        "deprecated": false,
        "hidden": "false",
        "data_url": "/copo/get_dataverse_vf/",
        "api_schema": params.api_schema,
        "call_parameters": params.call_parameters
    }

    var elemValue = formElem.default_value;
    panel.append(dispatchFormControl[controlsMapping[formElem.control.toLowerCase()]](formElem, elemValue));
    panel.find(".constraint-label").remove();

    return panel;
}

function format_summary_message(message) {
    let feedback = '<div class="ui info message">\n' +
        '  <i class="close icon"></i>\n' +
        '  <div class="header">\n' +
        '    Summary\n' +
        '  </div>\n' +
        '  <p>' + message + '</p>\n' +
        '</div>'

    return feedback;

}

function handle_dv_choice(eventObj) {
    var elemId = eventObj.elementId;
    var selectedVal = eventObj.selectedValue;
    var elem = $(document).find("[data-element='" + elemId + "']");
    var parentElem = elem.closest(".submission-panel");
    var submission_id = parentElem.attr("data-id");
    var dsListPanel = parentElem.find(".ds-list-div");
    var dvSummaryPanel = parentElem.find(".dv-summary-div");
    var context = parentElem.find("#dataverse_submission_context").val().toLowerCase(); //dataverse, dataset


    if (!selectedVal) {
        dvSummaryPanel.html("");

        if (context == "dataset" && eventObj.type == "dv_value_change") {
            dsListPanel.html("");
        }

        return true;
    }

    var valueObject = null;


    try {
        valueObject = selectizeObjects[elemId].options[selectedVal];
    } catch (e) {
        let feedback = get_alert_control();
        feedback
            .removeClass("alert-success")
            .addClass("alert-danger");

        feedback.find(".alert-message").html("Couldn't retrieve selected value. Please try searching again.");
        dsListPanel.append(feedback);

        return true;
    }

    if (!valueObject) {
        let feedback = get_alert_control();
        feedback
            .removeClass("alert-success")
            .addClass("alert-danger");

        feedback.find(".alert-message").html("Couldn't retrieve selected value. Please try searching again.");
        dsListPanel.append(feedback);

        return true;
    }

    var apiSchema = get_dataset_api_schema();

    //dataset list engaged - user has selected a dataset to submit to
    if (eventObj.type == "ds_value_change") {
        let message = "Your submission will be made to " +
            " <label>" + valueObject.copo_labelblank + "</label> dataset. " +
            "Your existing metadata is not required for this submission." +
            "<div>Click the submit button when you are ready to proceed.</div>";

        //get user selection
        var form_values = {};

        //obtain fields based on schema used
        for (var i = 0; i < apiSchema.length; ++i) {
            var schemaNode = apiSchema[i];
            form_values[schemaNode.id] = valueObject[schemaNode.id];
        }

        $.ajax({
            url: "/copo/update_submission_meta/",
            type: "POST",
            dataType: "json",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'submission_id': submission_id,
                'form_values': JSON.stringify(form_values),
            },
            success: function (data) {
                dvSummaryPanel.html(format_summary_message(message));
                $('html, body').animate({
                    scrollTop: dvSummaryPanel.offset().top - 60
                }, 'slow');

                dvSummaryPanel.append(submit_submission_record(submission_id));
                refresh_tool_tips();
            },
            error: function () {
                dvSummaryPanel.html('');

                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-danger")
                    .addClass("page-notifications-node");

                feedback.find(".alert-message").html("Encountered an error. Please check that you are connected to a network and try again.");
                dvSummaryPanel.append(feedback);
            }
        });

        return true;
    }

    //dataverse list engaged -
    if (context == "dataverse" && eventObj.type == "dv_value_change") {
        let message = "<div>Your submission will be made to a new dataset within " +
            " <label>" + valueObject.copo_labelblank + "</label> dataverse. " +
            "Your existing metadata will be used for the submission. " +
            " <a class='ui green tag label show-sub-meta' data-submission-id='" + submission_id + "'> show metadata</a></div>" +
            "<div style='margin-top: 10px;'>Click the submit button when you are ready to proceed.</div>";

        //get user selection

        var form_values = {};

        //obtain fields based on schema
        for (var i = 0; i < apiSchema.length; ++i) {
            var schemaNode = apiSchema[i];
            form_values[schemaNode.id] = valueObject[schemaNode.id];
        }

        $.ajax({
            url: "/copo/update_submission_meta/",
            type: "POST",
            dataType: "json",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'submission_id': submission_id,
                'form_values': JSON.stringify(form_values),
            },
            success: function (data) {
                dvSummaryPanel.html(format_summary_message(message));
                $('html, body').animate({
                    scrollTop: dvSummaryPanel.offset().top - 60
                }, 'slow');

                dvSummaryPanel.append(submit_submission_record(submission_id));
                refresh_tool_tips();
            },
            error: function () {
                dvSummaryPanel.html('');

                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-danger")
                    .addClass("page-notifications-node");

                feedback.find(".alert-message").html("Encountered an error. Please check that you are connected to a network and try again.");
                dvSummaryPanel.append(feedback);
            }
        });

        return true;
    }

    //dataverse list engaged and selected value has type - dataset - user has specified a dataset to submit to
    if (context == "dataset" && eventObj.type == "dv_value_change" && valueObject.hasOwnProperty("type") && valueObject.type == "dataset") {
        let message = "Your submission will be made to " +
            " <label>" + valueObject.copo_labelblank + "</label> dataset. " +
            "Your existing metadata is not required for this submission." +
            "<div>Click the submit button when you are ready to proceed.</div>";

        //get user selection

        var form_values = {};

        //obtain fields based on schema
        var dsapischema = get_dataset_api_schema();
        for (var i = 0; i < dsapischema.length; ++i) {
            var schemaNode = dsapischema[i];
            form_values[schemaNode.id] = valueObject[schemaNode.id];
        }

        $.ajax({
            url: "/copo/update_submission_meta/",
            type: "POST",
            dataType: "json",
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'submission_id': submission_id,
                'form_values': JSON.stringify(form_values),
            },
            success: function (data) {
                dvSummaryPanel.html(format_summary_message(message));
                $('html, body').animate({
                    scrollTop: dvSummaryPanel.offset().top - 60
                }, 'slow');

                dvSummaryPanel.append(submit_submission_record(submission_id));
                refresh_tool_tips();
            },
            error: function () {
                dvSummaryPanel.html('');

                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-danger")
                    .addClass("page-notifications-node");

                feedback.find(".alert-message").html("Encountered an error. Please check that you are connected to a network and try again.");
                dvSummaryPanel.append(feedback);
            }
        });

        return true;
    }


    //come this far, we want to display datasets under selected dataverse

    var searchPane = $('' +
        '               <div class="row">\n' +
        '                   <div class="col-sm-1"><span class="input-group">\n' +
        '                    <img style="height: 24px; margin-left:5px;" src="/static/copo/img/loading.gif"></span></div>\n' +
        '                   <div class="col-sm-11"><span class="webpop-content-div">Searching for datasets under ' + valueObject.copo_labelblank + '</span></div>\n' +
        '               </div>'
    );

    dsListPanel.html(searchPane);

    var api_schema = get_dataset_api_schema();

    $.ajax({
        url: "/copo/get_dataverse_content_vf/",
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            "dataverse_record": JSON.stringify(valueObject),
            "submission_id": submission_id,
            "api_schema": JSON.stringify(api_schema),
        },
        success: function (data) {

            if (data.hasOwnProperty('message') && data.hasOwnProperty('status') && data.status == "error") {
                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-danger");

                feedback.find(".alert-message").html(data.message);
                dsListPanel.html(feedback);

                return true;
            }

            if (data.hasOwnProperty('status') && data.status == 'success' && data.items.length == 0) {
                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-info");

                feedback.find(".alert-message").html(data.message);
                dsListPanel.html(feedback);

                return true;
            }

            var ontologies = data.items;


            var panel = $('<div/>');

            //place search box
            var label = "Dataset select";

            var formElem = {
                "ref": "",
                "id": "dataset_select",
                "label": label,
                "help_tip": "Please select a dataset from the list",
                "required": "true",
                "type": "string",
                "control": "copo-general-ontoselect",
                "value_change_event": "ds_value_change",
                "default_value": "",
                "placeholder": "Select a dataset...",
                "control_meta": {},
                "deprecated": false,
                "hidden": "false",
                "api_schema": api_schema,
                "option_values": ontologies,
            }

            var elemValue = formElem.default_value;
            panel.append(dispatchFormControl[controlsMapping[formElem.control.toLowerCase()]](formElem, elemValue));
            panel.find(".constraint-label").remove();

            // retain info about parent dataverse
            dsListPanel.html(panel);
            dsListPanel.append($('<input/>',
                {
                    type: "hidden",
                    id: "ds-dv-parent-values" + submission_id,
                    value: JSON.stringify(valueObject)
                }));

            refresh_tool_tips();

            if (selectizeObjects.hasOwnProperty(formElem.id)) {
                var selectizeControl = selectizeObjects[formElem.id];
                selectizeControl.focus();
            }
        },
        error: function () {

        }
    });
}

function build_dspace_display(params) {
    //build ui components and place on panel
    var panel = $('<div/>');

    panel.append("Watch this space for dspace");

    return panel;
}

function reload_ckan_panel(parentElem, dv_type) {

    let params = {
        'submission_id': parentElem.attr("data-id"),
        "submission_context": dv_type
    };

    get_ckan_display(parentElem.find(".submission-proceed-section"), params);
    return true
}

function get_ckan_display(displayPanel, params) {
    //build ui components and place on panel

    displayPanel.find(".dv-local-panel").remove();
    var localPanel = $('<div/>', {class: "dv-local-panel"});

    displayPanel.append(localPanel);

    // add displayable sections
    var dvTypeDiv = $('<div class="dv-type-div"></div>');
    var searchDiv = $('<div class="search-ctrl-div"></div>');
    var dsListDiv = $('<div class="ds-list-div copo-form-group"></div>');
    var dvSummaryDiv = $('<div class="dv-summary-div copo-form-group"></div>');


    localPanel.append(dvTypeDiv);
    localPanel.append(searchDiv);
    localPanel.append(dsListDiv);
    localPanel.append(dvSummaryDiv);

    var submission_context = params.submission_context;
    var submission_id = params.submission_id;
    dvTypeDiv.append(get_ckan_submission_context(params));

    if (submission_context == "existing") {
        //schema will be used to format API returned fields
        params.api_schema = get_ckan_api_schema();
        params.call_parameters = {'submission_id': params.submission_id};

        searchDiv.append(get_ckan_search(params));
    } else if (submission_context == "new") {
        let summary_message = "<div>Your submission will be made to a new dataset together with your existing metadata." +
            " <a class='ui green tag label show-sub-meta' data-submission-id='" + submission_id + "'> show metadata</a></div>" +
            "<div style='margin-top: 10px;'>Click the submit button when you are ready to proceed.</div>";

        params.summary_message = summary_message;
        get_ckan_summary(params);
    }

    refresh_tool_tips();
    return true;
}

function get_ckan_summary(params) {
    var context = params.submission_context;
    var submission_id = params.submission_id;
    var parentElem = get_viewport(submission_id);
    var dvSummaryPanel = parentElem.find(".dv-summary-div");

    var form_values = {};
    form_values['type'] = context;

    if (context == "existing") {
        form_values = params.form_values;
        form_values['type'] = context;
    }

    $.ajax({
        url: "/copo/update_submission_meta/",
        type: "POST",
        dataType: "json",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'submission_id': submission_id,
            'form_values': JSON.stringify(form_values),
        },
        success: function (data) {
            dvSummaryPanel.html(format_summary_message(params.summary_message));
            $('html, body').animate({
                scrollTop: dvSummaryPanel.offset().top - 250
            }, 'slow');

            dvSummaryPanel.append(submit_submission_record(submission_id));
            refresh_tool_tips();
        },
        error: function () {
            dvSummaryPanel.html('');

            let feedback = get_alert_control();
            feedback
                .removeClass("alert-success")
                .addClass("alert-danger")
                .addClass("page-notifications-node");

            feedback.find(".alert-message").html("Encountered an error. Please check that you are connected to a network and try again.");
            dvSummaryPanel.append(feedback);
        }
    });

    return true;
}

function get_ckan_submission_context(params) {
    var panel = $('<div/>');

    var formElem = {
        "ref": "ckan_submission_context",
        "id": "ckan_submission_context",
        "label": "Submission context ",
        "help_tip": "Please specify where you want to place this submission.",
        "control": "copo-button-list",
        "type": "string",
        "required": true,
        "control_meta": {},
        "default_value": params.submission_context,
        "option_values": [
            {
                "value": "new",
                "label": "Create a new dataset",
                "description": "A new dataset will be created for this submission."
            },
            {
                "value": "existing",
                "label": "Add to an existing dataset",
                "description": "Submission will be made to an existing dataset. Use the search box below to locate a target dataset."
            }
        ]
    };

    var elemValue = formElem.default_value;
    panel.append(dispatchFormControl[controlsMapping[formElem.control.toLowerCase()]](formElem, elemValue));
    panel.find(".constraint-label").remove();

    return panel;
}


function get_ckan_search(params) {
    var panel = $('<div/>');

    //place search box

    var formElem = {
        "ref": "",
        "id": "ckan_dataset_search",
        "label": "Dataset search",
        "help_tip": "Start typing to search. You can search by author, keyword, name, etc.",
        "required": "true",
        "type": "string",
        "control": "copo-general-onto",
        "value_change_event": "ckan_value_change",
        "default_value": "",
        "placeholder": "Enter author, keyword, etc.",
        "control_meta": {},
        "deprecated": false,
        "hidden": "false",
        "data_url": "/copo/ckan_package_search/",
        "api_schema": params.api_schema,
        "call_parameters": params.call_parameters
    }

    var elemValue = formElem.default_value;
    panel.append(dispatchFormControl[controlsMapping[formElem.control.toLowerCase()]](formElem, elemValue));
    panel.find(".constraint-label").remove();

    return panel;
}

function get_ckan_api_schema() {
    return [
        {'id': 'title', 'label': 'Title', 'show_in_table': true},
        {'id': 'name', 'label': 'Name', 'show_in_table': true},
        {'id': 'author', 'label': 'Author', 'show_in_table': true},
        {'id': 'author_email', 'label': 'Author Email', 'show_in_table': true},
        {'id': 'id', 'label': 'Identifier', 'show_in_table': true}
    ]
}

function handle_ckan_choice(eventObj) {
    var elemId = eventObj.elementId;
    var selectedVal = eventObj.selectedValue;
    var elem = $(document).find("[data-element='" + elemId + "']");
    var parentElem = elem.closest(".submission-panel");
    var submission_id = parentElem.attr("data-id");
    var dsListPanel = parentElem.find(".ds-list-div");
    var dvSummaryPanel = parentElem.find(".dv-summary-div");

    dvSummaryPanel.html("");
    dsListPanel.html("");

    if (!selectedVal) {
        return true;
    }

    var valueObject = null;

    try {
        valueObject = selectizeObjects[elemId].options[selectedVal];
    } catch (e) {
        let feedback = get_alert_control();
        feedback
            .removeClass("alert-success")
            .addClass("alert-danger");

        feedback.find(".alert-message").html("Couldn't retrieve selected value. Please try searching again.");
        dsListPanel.append(feedback);

        return true;
    }

    if (!valueObject) {
        let feedback = get_alert_control();
        feedback
            .removeClass("alert-success")
            .addClass("alert-danger");

        feedback.find(".alert-message").html("Couldn't retrieve selected value. Please try searching again.");
        dsListPanel.append(feedback);

        return true;
    }

    // summary message
    let summary_message = "Your submission will be made to " +
        " <label>" + valueObject.copo_labelblank + "</label> dataset. " +
        "Your existing metadata is not required for this submission." +
        "<div>Click the submit button when you are ready to proceed.</div>";

    let params = {
        'submission_id': submission_id,
        "submission_context": "existing",
        "summary_message": summary_message

    };

    var apiSchema = get_ckan_api_schema();

    //obtain fields based on schema used
    var form_values = {}
    for (var i = 0; i < apiSchema.length; ++i) {
        var schemaNode = apiSchema[i];
        form_values[schemaNode.id] = valueObject[schemaNode.id];
    }

    params.form_values = form_values;

    get_ckan_summary(params);

    return true;
}


function get_dspace_display(displayPanel, params) {
    //build ui components and place on panel

    displayPanel.find(".dv-local-panel").remove();
    var localPanel = $('<div/>', {class: "dv-local-panel"});

    displayPanel.append(localPanel);

    // add displayable sections
    var dvTypeDiv = $('<div class="dv-type-div"></div>');
    var ObjectsDiv = $('<div class="objects-display row" style="margin-bottom: 30px;"></div>');
    var communitiesDiv = $('<div class="communities-display col-sm-4 col-md-4 col-lg-4"></div>');
    var collectionsDiv = $('<div class="collections-display col-sm-4 col-md-4 col-lg-4"></div>');
    var itemsDiv = $('<div class="items-display col-sm-4 col-md-4 col-lg-4"></div>');
    var dsListDiv = $('<div class="ds-list-div copo-form-group"></div>');
    var dvSummaryDiv = $('<div class="dv-summary-div copo-form-group"></div>');

    ObjectsDiv
        .append(communitiesDiv)
        .append(collectionsDiv)
        .append(itemsDiv)


    localPanel.append(dvTypeDiv);
    localPanel.append(ObjectsDiv);
    localPanel.append(dsListDiv);
    localPanel.append(dvSummaryDiv);

    dvTypeDiv.append(get_dspace_submission_context(params));
    params.communitiesDiv = communitiesDiv;
    params.collectionsDiv = collectionsDiv;
    params.itemsDiv = itemsDiv;
    display_dspace_communities(params);

    refresh_tool_tips();
    return true;
}

function get_dspace_submission_context(params) {
    var panel = $('<div/>');

    var formElem = {
        "ref": "dspace_submission_context",
        "id": "dspace_submission_context",
        "label": "Submission context ",
        "help_tip": "Please specify where you want to place this submission.",
        "control": "copo-button-list",
        "type": "string",
        "required": true,
        "control_meta": {},
        "default_value": params.submission_context,
        "option_values": [
            {
                "value": "new",
                "label": "Create a new DSpace item",
                "description": "A new item will be created for your submission. Please locate the community/collection of interest below."
            },
            {
                "value": "existing",
                "label": "Add to an existing DSpace item",
                "description": "Submission will be made to an existing item. Please locate the community/collection/item of interest below."
            }
        ]
    };

    var elemValue = formElem.default_value;
    panel.append(dispatchFormControl[controlsMapping[formElem.control.toLowerCase()]](formElem, elemValue));
    panel.find(".constraint-label").remove();

    return panel;
}

function display_dspace_communities(params) {
    var displayPanel = params.communitiesDiv;
    var submission_id = params.submission_id;

    var tableID = 'communities_view_tbl' + submission_id;
    var table = null;
    var tbl = $('<table/>',
        {
            id: tableID,
            "class": "ui blue celled table hover copo-noborders-table",
            cellspacing: "0",
            width: "100%"
        });


    var table_div = $('<div/>').append(tbl);
    var filter_message = $('<div style="margin-bottom: 20px;"><div class="text-info filter-message" style="margin-bottom: 5px; padding: 5px;">Loading DSpace communities...</div></div>');
    var spinner_div = $('<div/>', {style: "margin-left: 40%; padding-top: 15px; padding-bottom: 15px;"}).append($('<div class="copo-i-loader-50"></div>'));

    var panelTitleDiv = $('<div class="webpop-content-div"></div>');
    var recordDetailDiv = $('<div class="webpop-content-div rdetail-view"></div>');
    var codeList = '<div style="margin-top: 10px;"><ul class="list-group">\n' +
        '  <li class="list-group-item active" style="background: #31708f; text-shadow: none; border-color: #d9edf7; color: #fff;">Communities</li>\n' +
        '</ul></div>'


    panelTitleDiv.append(codeList);

    displayPanel
        .html('')
        .append(panelTitleDiv)
        .append(filter_message)
        .append(recordDetailDiv)
        .append(spinner_div)
        .append(table_div);

    var api_schema = get_dspace_communities_schema();

    $.ajax({
        url: '/copo/retrieve_dspace_objects/',
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'submission_id': submission_id,
            'object_type': 'communities',
            'api_schema': JSON.stringify(api_schema)
        },
        success: function (data) {
            spinner_div.remove();

            if (data.hasOwnProperty('status') && data.status == "error") {

                filter_message.find(".filter-message").html("No records returned");

                var errorMessage = "Encountered an error! No specific details provided.";
                if (data.hasOwnProperty('message') && data.message != "") {
                    errorMessage = data.message;
                }

                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-danger");

                feedback.find(".alert-message").html(errorMessage);
                displayPanel.append(feedback);

                return true;
            }

            var dtd = data.items;
            var cols = [
                {title: "", className: 'select-checkbox', data: null, orderable: false, "defaultContent": ''}
            ];

            filter_message.find(".filter-message").html('');

            if (dtd.length > 0) {
                filter_message.find(".filter-message").html("Select a community to view corresponding collections.");
            }

            var visible = false;
            for (var i = 0; i < api_schema.length; ++i) {
                var entry = api_schema[i];
                var option = {};

                //display only the first displayable item
                option["visible"] = false;
                if (!visible) {
                    visible = entry.show_in_table;
                    option["visible"] = visible;
                }

                option["title"] = entry.label;
                option["data"] = entry.id;
                cols.push(option);
            }

            table = $('#' + tableID).DataTable({
                data: dtd,
                searchHighlight: true,
                "lengthChange": false,
                order: [
                    [1, "asc"]
                ],
                scrollY: "300px",
                scrollX: true,
                scrollCollapse: true,
                paging: false,
                language: {
                    "info": " _START_ to _END_ of _TOTAL_ communities",
                    "search": " "
                },
                select: {
                    style: 'single',
                    // selector: 'td:first-child'
                },
                columns: cols,
                dom: 'fr<"row"><"row info-rw" i>tlp'
            });

            $('#' + tableID + '_wrapper')
                .find(".dataTables_filter")
                .find("input")
                .removeClass("input-sm")
                .attr("placeholder", "Search communities");

            table
                .on('select', function (e, dt, type, indexes) {
                    var selectedData = dt.row({selected: true}).data();
                    //todo: uncomment this for row details
                    //
                    // var subTable = $('<table cellpadding="5" cellspacing="0" border="0"></table>');
                    // recordDetailDiv.html(subTable);
                    //
                    // for (var i = 0; i < api_schema.length; ++i) {
                    //     var entry = api_schema[i];
                    //     if(entry.show_in_table) {
                    //         subTable.append('<tr><td>'+entry.label+':</td>' +'<td>' + selectedData[entry.id] + '</td></tr>');
                    //     }
                    // }
                    params.community_record = selectedData;
                    display_dspace_collections(params);
                });

            table
                .on('deselect', function (e, dt, type, indexes) {
                    params.itemsDiv.html('');
                    params.collectionsDiv.html('');
                    recordDetailDiv.html('');
                });

        },
        error: function () {
            spinner_div.remove();

            let feedback = get_alert_control();
            feedback
                .removeClass("alert-success")
                .addClass("alert-danger")
                .addClass("page-notifications-node");

            feedback.find(".alert-message").html("Encountered an error. Please check that you are connected to a network and try again.");
            displayPanel.append(feedback);
        }
    });

}

function display_dspace_collections(params) {
    var displayPanel = params.collectionsDiv;
    var submission_id = params.submission_id;
    var community_record = params.community_record;

    displayPanel.html('');

    var tableID = 'collections_view_tbl' + submission_id;
    var table = null;
    var tbl = $('<table/>',
        {
            id: tableID,
            "class": "ui blue celled table hover copo-noborders-table",
            cellspacing: "0",
            width: "100%"
        });


    var table_div = $('<div/>').append(tbl);
    var filter_message = $('<div style="margin-bottom: 20px;"><div class="text-info filter-message" style="margin-bottom: 5px; padding: 5px;">Loading collections...</div></div>');
    var spinner_div = $('<div/>', {style: "margin-left: 40%; padding-top: 15px; padding-bottom: 15px;"}).append($('<div class="copo-i-loader-50"></div>'));

    var panelTitleDiv = $('<div class="webpop-content-div"></div>');
    var recordDetailDiv = $('<div class="webpop-content-div rdetail-view"></div>');
    var codeList = '<div style="margin-top: 10px;"><ul class="list-group">\n' +
        '  <li class="list-group-item active" style="background: #31708f; text-shadow: none; border-color: #d9edf7; color: #fff;">Collections</li>\n' +
        '</ul></div>'


    panelTitleDiv.append(codeList);

    displayPanel
        .html('')
        .append(panelTitleDiv)
        .append(filter_message)
        .append(recordDetailDiv)
        .append(spinner_div)
        .append(table_div);

    var api_schema = get_dspace_communities_schema();


    $.ajax({
        url: '/copo/retrieve_dspace_objects/',
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'submission_id': submission_id,
            'community_id': community_record.id,
            'object_type': 'collections',
            'api_schema': JSON.stringify(api_schema)
        },
        success: function (data) {
            spinner_div.remove();

            if (data.hasOwnProperty('status') && data.status == "error") {

                filter_message.find(".filter-message").html("No records returned");

                var errorMessage = "Encountered an error! No specific details provided.";
                if (data.hasOwnProperty('message') && data.message != "") {
                    errorMessage = data.message;
                }

                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-danger");

                feedback.find(".alert-message").html(errorMessage);
                displayPanel.append(feedback);

                return true;
            }

            var dtd = data.items;
            var cols = [
                {title: "", className: 'select-checkbox', data: null, orderable: false, "defaultContent": ''}
            ];

            filter_message.find(".filter-message").html('');

            if (dtd.length > 0) {
                var filterMessage = "Select a collection to view corresponding items.";
                var submission_context = displayPanel.closest(".submission-panel").find("#dspace_submission_context").val();
                if (submission_context == "new") {
                    filterMessage = "Select a collection to place your new item.";
                }
                filter_message.find(".filter-message").html(filterMessage);
            }

            var visible = false;
            for (var i = 0; i < api_schema.length; ++i) {
                var entry = api_schema[i];
                var option = {};

                //display only the first displayable item
                option["visible"] = false;
                if (!visible) {
                    visible = entry.show_in_table;
                    option["visible"] = visible;
                }

                option["title"] = entry.label;
                option["data"] = entry.id;
                cols.push(option);
            }

            table = $('#' + tableID).DataTable({
                data: dtd,
                searchHighlight: true,
                "lengthChange": false,
                order: [
                    [1, "asc"]
                ],
                scrollY: "300px",
                scrollX: true,
                scrollCollapse: true,
                paging: false,
                language: {
                    "info": " _START_ to _END_ of _TOTAL_ collections",
                    "search": " "
                },
                select: {
                    style: 'single',
                    // selector: 'td:first-child'
                },
                columns: cols,
                dom: 'fr<"row"><"row info-rw" i>tlp'
            });

            $('#' + tableID + '_wrapper')
                .find(".dataTables_filter")
                .find("input")
                .removeClass("input-sm")
                .attr("placeholder", "Search collections");

            table
                .on('select', function (e, dt, type, indexes) {
                    var selectedData = dt.row({selected: true}).data();
                    var submission_context = displayPanel.closest(".submission-panel").find("#dspace_submission_context").val();
                    if (submission_context == "existing") {
                        //load items
                        params.collection_record = selectedData;
                        display_dspace_items(params);
                    } else {
                        //save user choice and display summary
                        var form_values = {};
                        form_values['type'] = submission_context;
                        form_values['identifier'] = selectedData.id;
                        params.form_values = form_values;


                        let summary_message = "<div>Your submission will be made to a new collection together with your existing metadata." +
                            " <a class='ui green tag label show-sub-meta' data-submission-id='" + submission_id + "'> show metadata</a></div>" +
                            "<div style='margin-top: 10px;'>Click the submit button when you are ready to proceed.</div>";

                        params.summary_message = summary_message;
                        get_dspace_summary(params);
                    }
                });

            table
                .on('deselect', function (e, dt, type, indexes) {
                    params.itemsDiv.html('');
                    recordDetailDiv.html('');
                    get_viewport(submission_id).find(".dv-summary-div").html('');
                });

        },
        error: function () {
            spinner_div.remove();

            let feedback = get_alert_control();
            feedback
                .removeClass("alert-success")
                .addClass("alert-danger")
                .addClass("page-notifications-node");

            feedback.find(".alert-message").html("Encountered an error. Please check that you are connected to a network and try again.");
            displayPanel.append(feedback);
        }
    });

}

function display_dspace_items(params) {
    var displayPanel = params.itemsDiv;
    var submission_id = params.submission_id;
    var community_record = params.community_record;
    var collection_record = params.collection_record;

    displayPanel.html('');

    var tableID = 'items_view_tbl' + submission_id;
    var table = null;
    var tbl = $('<table/>',
        {
            id: tableID,
            "class": "ui blue celled table hover copo-noborders-table",
            cellspacing: "0",
            width: "100%"
        });


    var table_div = $('<div/>').append(tbl);
    var filter_message = $('<div style="margin-bottom: 20px;"><div class="text-info filter-message" style="margin-bottom: 5px; padding: 5px;">Loading items...</div></div>');
    var spinner_div = $('<div/>', {style: "margin-left: 40%; padding-top: 15px; padding-bottom: 15px;"}).append($('<div class="copo-i-loader-50"></div>'));

    var panelTitleDiv = $('<div class="webpop-content-div"></div>');
    var recordDetailDiv = $('<div class="webpop-content-div rdetail-view"></div>');
    var codeList = '<div style="margin-top: 10px;"><ul class="list-group">\n' +
        '  <li class="list-group-item active" style="background: #31708f; text-shadow: none; border-color: #d9edf7; color: #fff;">Items</li>\n' +
        '</ul></div>'


    panelTitleDiv.append(codeList);

    displayPanel
        .html('')
        .append(panelTitleDiv)
        .append(filter_message)
        .append(recordDetailDiv)
        .append(spinner_div)
        .append(table_div);

    var api_schema = get_dspace_communities_schema();


    $.ajax({
        url: '/copo/retrieve_dspace_objects/',
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'submission_id': submission_id,
            'collection_id': collection_record.id,
            'object_type': 'items',
            'api_schema': JSON.stringify(api_schema)
        },
        success: function (data) {
            spinner_div.remove();

            if (data.hasOwnProperty('status') && data.status == "error") {

                filter_message.find(".filter-message").html("No records returned");

                var errorMessage = "Encountered an error! No specific details provided.";
                if (data.hasOwnProperty('message') && data.message != "") {
                    errorMessage = data.message;
                }

                let feedback = get_alert_control();
                feedback
                    .removeClass("alert-success")
                    .addClass("alert-danger");

                feedback.find(".alert-message").html(errorMessage);
                displayPanel.append(feedback);

                return true;
            }

            var dtd = data.items;
            var cols = [
                {title: "", className: 'select-checkbox', data: null, orderable: false, "defaultContent": ''}
            ];

            filter_message.find(".filter-message").html('');

            if (dtd.length > 0) {
                filter_message.find(".filter-message").html("Select an item to submit to.");
            }

            var visible = false;
            for (var i = 0; i < api_schema.length; ++i) {
                var entry = api_schema[i];
                var option = {};

                //display only the first displayable item
                option["visible"] = false;
                if (!visible) {
                    visible = entry.show_in_table;
                    option["visible"] = visible;
                }

                option["title"] = entry.label;
                option["data"] = entry.id;
                cols.push(option);
            }

            table = $('#' + tableID).DataTable({
                data: dtd,
                searchHighlight: true,
                "lengthChange": false,
                order: [
                    [1, "asc"]
                ],
                scrollY: "300px",
                scrollX: true,
                scrollCollapse: true,
                paging: false,
                language: {
                    "info": " _START_ to _END_ of _TOTAL_ items",
                    "search": " "
                },
                select: {
                    style: 'single',
                    // selector: 'td:first-child'
                },
                columns: cols,
                dom: 'fr<"row"><"row info-rw" i>tlp'
            });

            $('#' + tableID + '_wrapper')
                .find(".dataTables_filter")
                .find("input")
                .removeClass("input-sm")
                .attr("placeholder", "Search items");

            table
                .on('select', function (e, dt, type, indexes) {
                    var selectedData = dt.row({selected: true}).data();
                    var submission_context = displayPanel.closest(".submission-panel").find("#dspace_submission_context").val();

                    //save user choice and display summary
                    var form_values = {};
                    form_values['type'] = submission_context;
                    form_values['identifier'] = selectedData.id;
                    params.form_values = form_values;

                    let summary_message = "Your submission will be made to the selected item. " +
                        "Your existing metadata is not required for this submission." +
                        "<div>Click the submit button when you are ready to proceed.</div>";

                    params.summary_message = summary_message;
                    get_dspace_summary(params);
                });

            table
                .on('deselect', function (e, dt, type, indexes) {
                    recordDetailDiv.html('');
                    get_viewport(submission_id).find(".dv-summary-div").html('');
                });

        },
        error: function () {
            spinner_div.remove();

            let feedback = get_alert_control();
            feedback
                .removeClass("alert-success")
                .addClass("alert-danger")
                .addClass("page-notifications-node");

            feedback.find(".alert-message").html("Encountered an error. Please check that you are connected to a network and try again.");
            displayPanel.append(feedback);
        }
    });

}

function get_dspace_summary(params) {
    var submission_id = params.submission_id;
    var parentElem = get_viewport(submission_id);
    var dvSummaryPanel = parentElem.find(".dv-summary-div");
    var summary_message = params.summary_message;
    var form_values = params.form_values;


    $.ajax({
        url: "/copo/update_submission_meta/",
        type: "POST",
        dataType: "json",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'submission_id': submission_id,
            'form_values': JSON.stringify(form_values),
        },
        success: function (data) {
            dvSummaryPanel.html(format_summary_message(summary_message));
            $('html, body').animate({
                scrollTop: dvSummaryPanel.offset().top - 250
            }, 'slow');

            dvSummaryPanel.append(submit_submission_record(submission_id));
            refresh_tool_tips();
        },
        error: function () {
            dvSummaryPanel.html('');

            let feedback = get_alert_control();
            feedback
                .removeClass("alert-success")
                .addClass("alert-danger")
                .addClass("page-notifications-node");

            feedback.find(".alert-message").html("Encountered an error. Please check that you are connected to a network and try again.");
            dvSummaryPanel.append(feedback);
        }
    });

    return true;
}


function handle_dspace_context_change(parentElem) {
    parentElem.find(".dv-summary-div").html('');
    parentElem.find(".ds-list-div").html('');
    parentElem.find(".items-display").html('');
    parentElem.find(".collections-display").html('');

    var submission_id = parentElem.attr("data-id");
    var tableID = 'communities_view_tbl' + submission_id;

    var table = $('#' + tableID).DataTable();
    table.rows().deselect();
}

function get_dspace_communities_schema() {
    return [
        {'id': 'name', 'label': 'Name', 'show_in_table': true},
        {'id': 'id', 'label': 'Id', 'show_in_table': true},
        {'id': 'handle', 'label': 'Handle', 'show_in_table': true},
    ]
}


