$(document).ready(function () {
    // attach array to document which will be used to hold spreadsheet data
    $(document).data('ss_data', new Array())
    refresh_display()
    $(document).on("shown.bs.tab", ".hot_tab", function () {
        var id = this.innerText
        var hot = $(document).data("table_" + id)
        hot.render()
    })
    $("#search_term_text_box").val("")
    $("#ss_data").droppable({
        drop:startDrop
    })
})

$(document).ajaxStart(function () {

})

function startDrag(ev){
    console.log("drag")
}
function startDrop(ev, ui){
    console.log("drop")
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
            }).draggable({
                helper: "clone",
                containment: 'window',
                start:startDrag,
                
            })
            $(result).append($("<span/>", {
                html: v,
                class: "highlight"
            }))
            $(result).append($("<span/>", {
                html: entry["ontology_prefix"],
                class:"pull-right"
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

    console.log(val)
}))

function allowDrop(ev) {
  ev.preventDefault();
}

function refresh_display() {
    var file_id = $("#file_id").attr("val")
    $.ajax({
        url: "/copo/refresh_annotation_display/",
        data: {"file_id": file_id},
        type: "GET",

    }).done(function (data) {
        data = JSON.parse(data)
        $("#ss_data").empty()
        $("#ss_sheets").empty()
        $(data.data).each(function (idx, d) {
            if (idx == 0) {
                var active = "in active"
            } else {
                var active = ""
            }
            var id = data.names[idx]
            var li = '<li class="hot_tab ' + active + '"><a data-toggle="tab" href="#' + id + '">' + id + '</a></li>'

            $('#ss_sheets').append(li)

            var h = $('<div class="tab-pane fade ' + active + '" id="' + id + '"></div>')

            $("#ss_data").append(h)

            var t = document.getElementById(id)
            //d = JSON.parse(d)

            var hot = new Handsontable(t, {
                data: d,
                rowHeaders: false,
                colHeaders: false,
                filters: false,
                dropdownMenu: true,
                licenseKey: 'non-commercial-and-evaluation',
                autoColumnSize: {useHeaders: true},
            });
            hot.render()
            $(document).data('table_' + id, hot)


        })

    }).error(function (data) {
        console.error(data)
    })
}