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



})

$(document).ajaxStart(function () {

})

function startDrag(ev) {

}

function stopDrag(ev) {
    $(".selectedColumn").removeClass("selectedColumn")
}

function dropHandler(ev, ui) {
    var iri = $(ui.draggable.context).data("iri")
    // call backend to save term
    var col = $(ev.target).index();
    var name = $(ev.target).closest("div[name^='table']").attr("name")
    var hot = $(document).data(name)
    name = name.split("table_")[1]
    var col_header = hot.getDataAtCell(0, col)
    var data = new Object();
    data.col_idx = col;
    data.sheet_name = name;
    data.col_header = col_header;
    data.iri = iri;
    data.file_id = $("#file_id").val()
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
        console.log(d)
    }).error(function (d) {
        console.error("error: " + d)
    })
}

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
                console.log(entry)
            }
            //console.log(d.highlighting[entry["id"]])
            var v = d.highlighting[entry["id"]]["label_autosuggest"][0]
            var result = $("<div/>", {
                class: "annotation_term panel panel-default",
                "data-iri": entry.iri
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
                html: entry["ontology_prefix"],
                class: "pull-right"
            }))
            if (entry.hasOwnProperty("description")) {
                t = entry["description"][0]
            } else {
                t = "Description Unavailable"
            }
            $(result).append($("<div/>", {html: t}))
            $("#search_results").append(result)

        })


    })


}))

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
                    //console.log($(td).html())
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
        data: {"file_id": file_id,"sheet_name": sheet_name},
        type: "GET"
    }).done(function(data){
        data = JSON.parse(data)
        for(var d in data.annotations){
            var result = $("<div/>", {
                class: "panel panel-default",
                "data-iri": data.annotations[d].file_level_annotation.iri,
                text: data.annotations[d].file_level_annotation.iri
            })
            $("#existing_annotations").append(result)
        }
    })

}


function make_dropabble() {
    $("#ss_data tr td").droppable({
        activeClass: "dropActive",
        tolerance: "pointer",
        drop: dropHandler,
        over: overHandler

    })
}