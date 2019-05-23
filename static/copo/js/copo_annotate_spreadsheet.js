$(document).ready(function () {
    // attach array to document which will be used to hold spreadsheet data
    $(document).data('ss_data', new Array())
    refresh_display()
})

function refresh_display() {
    var file_id = $("#file_id").attr("val")
    $.ajax({
        url: "/copo/refresh_annotation_display/",
        data: {"file_id": file_id},
        type: "GET",

    }).done(function (data) {
        data = JSON.parse(data)
        $("#ss_data").empty()
        //$("#ss_sheets").empty()
        $(data.data).each(function (idx, d) {
            if (idx == 0) {
                var active = "in active"
            } else {
                var active = ""
            }
            var li = '<li class="' + active + '"><a data-toggle="tab" href="#' + data.names[idx] + '">' + data.names[idx] + '</a></li>'
            $('#ss_sheets').append(li)

            var h = $('<div class="tab-pane fade ' + active + '" id="' + data.names[idx] + '"></div>')

            $("#ss_data").append(h)

            var cells = document.getElementById(data.names[idx])
            //d = JSON.parse(d)

            new Handsontable(cells, {
                data: d,
                rowHeaders: true,
                colHeaders: true,
                filters: true,
                dropdownMenu: true,
                licenseKey: 'non-commercial-and-evaluation'
            });


        })

    }).error(function (data) {
        console.error(data)
    })
}