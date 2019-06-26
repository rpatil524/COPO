$(document).ready(function () {
    // attach array to document which will be used to hold spreadsheet data
    $(document).data('ss_data', new Array())
    refresh_display()
    //refresh_annotations()
    $(document).on("shown.bs.tab", ".hot_tab", function () {
        var id = this.innerText
        var hot = $(document).data("table_" + id)
        hot.render()
        make_dropabble()
        refresh_annotations()
    })
    $("#search_term_text_box").val("")

    $(document).on("click", "#filters a", do_my_annotations)

})

$(document).ajaxStart(function () {

})

function startDrag(ev) {

}

function stopDrag(ev) {
    $(".selectedColumn").removeClass("selectedColumn")
}

function dropHandler(ev, ui) {
    var data = new Object();
    var iri = $(ui.draggable.context).data("iri")
    data.label = $(ui.draggable.context).data("label")
    data.id = $(ui.draggable.context).data("id")
    data.obo_id = $(ui.draggable.context).data("obo_id")
    data.ontology_name = $(ui.draggable.context).data("ontology_name")
    data.ontology_prefix = $(ui.draggable.context).data("ontology_prefix")
    data.short_form = $(ui.draggable.context).data("short_form")
    data.type = $(ui.draggable.context).data("type")
    data.description = $(ui.draggable.context).data("description")

    // call backend to save term
    var col = $(ev.target).index();
    var name = $(ev.target).closest("div[name^='table']").attr("name")
    var hot = $(document).data(name)
    name = name.split("table_")[1]
    var col_header = hot.getDataAtCell(0, col)

    data.col_idx = col;
    data.sheet_name = name;
    data.col_header = col_header;
    data.iri = iri;
    data.file_id = $("#file_id").val()
    data.file_name = $("#file_name").val()
    csrftoken = $.cookie('csrftoken');
    $.ajax({
        url: "/copo/send_file_annotation/",
        type: "POST",
        data: data,
        headers: {
            'X-CSRFToken': csrftoken
        },
    }).done(function (d) {
        d = JSON.parse(d)
        refresh_display()
    }).error(function (d) {
        console.error("error: " + d)
    })
}

// this handler is called to indicate when a user has moused over a column
function overHandler(ev, ui) {

    var pt = ui.offset
    el = document.elementFromPoint(pt.left, pt.top)
    var name = $(ev.target).closest("div[name^='table']").attr("name")
    var hot = $(document).data(name)
    var col = $(ev.target).index();
    var row = $(ev.target).closest('tr').index();

    $(".selectedColumn").removeClass("selectedColumn")
    for (var i = 0; i < hot.countRows(); i++) {
        var cell = hot.getCell(i, col)

        $(cell).addClass("selectedColumn");
    }

}


function delay(fn, ms) {
    let timer = 0
    return function (...args) {
        clearTimeout(timer)
        timer = setTimeout(fn.bind(this, ...args), ms || 1000)
    }
}

var lastValue = '';
// this is the handler which is called 1 second after the user stops typing in the search box
$(document).on("input propertychange", "#search_term_text_box", delay(function (e) {
    var val = $(e.currentTarget).val()
    $.ajax({
        url: "/copo/ajax_search_ontology/999",
        data: {"q": val}
    }).done(function (data) {
        var d = JSON.parse(data)
        $("#search_results").empty()
        d.response.docs.forEach(function (entry, idx) {
            if (idx == 0) {
            }
            var p = build_result_panel(d, idx, entry)
            $("#search_results").append(p)
        })


    })


}))

function build_result_panel(d, idx, entry) {

    var v
    var desc
    var used = d.hasOwnProperty("highlighting") == false
    if (!used) {
        v = d.highlighting[entry["id"]]["label_autosuggest"][0]
        desc = entry["description"][0]
    } else {
        v = entry.label
        desc = entry.description
    }
    var result = $("<div/>", {
        class: "annotation_term panel panel-default",
        "data-iri": entry.iri,
        "data-label": entry.label,
        "data-id": entry.id,
        "data-obo_id": entry.obo_id,
        "data-ontology_name": entry.ontology_name,
        "data-ontology_prefix": entry.ontology_prefix,
        "data-short_form": entry.short_form,
        "data-type": entry.type,
        "data-is_search_result": true
    }).draggable({
        helper: "clone",
        containment: 'window',
        opacity: 0.6,
        start: startDrag,
        stop: stopDrag
    })
    $(result).append($("<span/>", {
        html: v,
        class: "highlight"
    }))
    $(result).append($("<span/>", {
        html: " - <strong>" + entry["ontology_prefix"] + "</strong>",
        class: ""
    }))
    if (used) {
        $(result.append($("<span/>", {
            html: "used: " + entry["count"],
            class: "pull-right"
        })))
    }
    if (entry.hasOwnProperty("description")) {
        t = desc
    } else {
        t = "Description Unavailable"
    }
    $(result).data("description", t)
    $(result).append($("<div/>", {html: t}))
    return result
}

function refresh_display() {
    var file_id = $("#file_id").val()
    $.ajax({
        url: "/copo/refresh_annotation_display/",
        data: {"file_id": file_id},
        type: "GET",

    }).done(function (data) {
        data = JSON.parse(data)
        $("#ss_data").empty()
        $("#ss_sheets").empty()
        $(data.data).each(function (idx, d) {
            // refresh spreadsheet section
            if (idx == 0) {
                var active = "in active"
            } else {
                var active = ""
            }
            var tag_text = data.names[idx]
            var id = "table_" + data.names[idx]
            var li = '<li class="hot_tab ' + active + '"><a data-toggle="tab" href="#' + id + '">' + tag_text + '</a></li>'

            $('#ss_sheets').append(li)

            var h = $('<div name=' + id + ' class="tab-pane fade ' + active + '" id="' + id + '"></div>')

            $("#ss_data").append(h)

            var t = document.getElementById(id)


            var hot = new Handsontable(t, {
                data: d,
                rowHeaders: false,
                colHeaders: false,
                filters: false,
                dropdownMenu: true,
                licenseKey: 'non-commercial-and-evaluation',
                autoColumnSize: {useHeaders: true},
                beforeOnCellMouseOver: function (evt, coords, td) {
                    evt.preventDefault()
                }
            });
            hot.render()
            $(document).data(id, hot)
            make_dropabble()
            refresh_annotations()
        })

    }).error(function (data) {
        console.error(data)
    })


}

function refresh_annotations() {
    // refresh current annotations
    var sheet_name = $("div[name^='table']:visible").attr("name").split("table_")[1]
    var file_id = $("#file_id").val()
    $.ajax({
        url: "/copo/refresh_annotations/",
        data: {"file_id": file_id, "sheet_name": sheet_name},
        type: "GET"
    }).done(function (data) {
        data = JSON.parse(data)
        $("#existing_annotations").empty()
        for (var d in data.annotations) {
            var result = make_annotation_panel(data.annotations, d)

            $("#existing_annotations").append(result)
            var sheet_name = $("div[name^='table']:visible").attr("name")
            var hot = $(document).data(sheet_name)
            for (var i = 0; i < hot.countRows(); i++) {
                var cell = hot.getCell(i, data.annotations[d].file_level_annotation.column_idx)
                $(cell).addClass("annotatedColumn");
            }
        }
    })
    do_my_annotations()

}

var annotation_fiter = ""

function do_my_annotations(event) {

    if (event == undefined) {
        annotation_fiter = "all"

    } else {
        $(".label-primary").removeClass("label-primary")
        $(event.currentTarget).addClass("label-primary")
        annotation_fiter = $(event.currentTarget).data("filter")
    }

    var file_id = $("#file_id").val()
    var sheet_name = $("div[name^='table']:visible").attr("name").split("table_")[1]
    $.ajax({
        url: "/copo/refresh_annotations_for_user/",
        data: {"file_id": file_id, "sheet_name": sheet_name, "filter": annotation_fiter},
        type: "GET",
        dataType: "json"
    }).done(function (d) {

        $("#your_annotations").empty()
        if (annotation_fiter != "by_dataset") {
            $(d.annotations).each(function (idx, entry) {
                var result = build_result_panel(d=d, idx=idx, entry=entry)
                $('#your_annotations').append(result)
            })
        }
        else {
            var accordion = $('<div class="panel-group" id="by_dataset_accordion" role="tablist" aria-multiselectable="true"></div>')
            $(d.annotations).each(function (idx, entry) {
                var p1 = $('<div class="panel panel-default">')
                var p_heading = $('<div class="panel-heading" role="tab" id="accordion_heading_' + idx + '">')
                $(p_heading).append('<h4 class="panel-title">')
                $(p_heading).append('<a role="button" class="collapsed" data-toggle="collapse" data-parent="#by_dataset_accordion" href="#collapse_' + idx + '" aria-expanded="true"' +
                    'aria-controls="collapse_' + idx + '">' + entry.annotations[0].file_name + '</a>')
                $(p1).append(p_heading)

                var accordion_panel = $('<div id="collapse_' + idx + '" class="panel-collapse collapse" role="tabpanel" aria-labelledby="accordion_heading_' + idx + '"><div class="panel-body">')

                for (data in entry.annotations) {
                    s = entry.annotations[data]
                    var panel = build_result_panel(0, 0, s)
                    $(accordion_panel).append(panel)
                }
                $(p1).append(accordion_panel)
                $(accordion).append(p1)
            })
            $("#your_annotations").append(accordion)
        }

    })

}

function make_annotation_panel(data, d) {
    var obj
    var do_delete = false
    if (data[d].hasOwnProperty("file_level_annotation")) {
        obj = data[d].file_level_annotation
        do_delete = true
    } else {
        obj = data[d]
    }
    var result = $("<div/>", {
        class: "panel panel-default annotation_term",
        "data-iri": obj.iri,
        "data-col_idx": obj.column_idx,
        "data-is_search_result": false,
    })
    var content = $("<div></div>")
    if (do_delete) {
        $(content).append('<button type="button" ' +
            'data-col_idx="' + obj.column_idx + '" ' +
            'data-sheet_name="' + obj.sheet_name + '"' +
            'class="btn pull-right btn-danger btn-sm delete_annotation" style="padding:5px" aria-label="Left Align"><span style="margin: 0" class="glyphicon glyphicon-trash" aria-hidden="true"></span></button>')
    }
    $(content).append("<u style='" + "font-size: larger" + "'>" + obj.label + "</u><br/>")
    $(content).append("<strong>" + obj.ontology_name + "</strong><br>")
    $(content).append(obj.description)
    $(result).append(content)
    return result
}

$(document).on("mouseover", ".annotation_term", function (data) {
    if ($(data.currentTarget).data("is_search_result") == false) {
        var sheet_name = $("div[name^='table']:visible").attr("name")
        var hot = $(document).data(sheet_name)
        var col = $(data.currentTarget).data("col_idx")
        $(".selectedAnnotation").removeClass("selectedAnnotation")
        $(data.currentTarget).addClass("selectedAnnotation")
        $(".selectedColumn").removeClass("selectedColumn")
        for (var i = 0; i < hot.countRows(); i++) {
            var cell = hot.getCell(i, col)
            $(cell).addClass("selectedColumn");
        }
    }
})
$(document).on("mouseout", ".annotation_term", function (data) {
    $(".selectedAnnotation").removeClass("selectedAnnotation")
    $(".selectedColumn").removeClass("selectedColumn")
})
$(document).on("click", ".delete_annotation", function (ev) {
    var col_idx = $(ev.currentTarget).data("col_idx")
    var sheet_name = $(ev.currentTarget).data("sheet_name")
    var file_id = $("#file_id").val()
    var label = $(ev.currentTarget).closest(".annotation_term").data("iri")
    $.ajax({
        url: "/copo/delete_annotation",
        type: "GET",
        data: {"col_idx": col_idx, "sheet_name": sheet_name, "file_id": file_id, "iri": label}
    }).done(function (data) {
        refresh_display()
    }).error(function (data) {
        console.error(data)
    })
})

function make_dropabble() {
    $("#ss_data tr td").droppable({
        activeClass: "dropActive",
        tolerance: "pointer",
        drop: dropHandler,
        over: overHandler

    })
}