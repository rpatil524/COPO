$(document).ready(function () {
    refresh_display()
})

function refresh_display() {
    var file_id = $("#file_id").attr("val")
    $.ajax({
        url: "/copo/refresh_annotation_display/",
        data: {"file_id": file_id},
        type: "GET",
    }).done(function (data) {
        $("#ss_data").html(data)
    }).error(function (data) {
        console.error(data)
    })
}