$(document).ready(function () {
    update_display()
    $(document).on("click", ".delete", handle_delete)
    $("#repoForm").validator().on("submit", function (e) {
        if (e.isDefaultPrevented()) {
            // handle the invalid form...
        } else {
            e.preventDefault()
            var name = $('#repoForm').find("#name").val()
            var url = $('#repoForm').find("#url").val()
            var apikey = $('#repoForm').find("#apikey").val()
            var data = {"name": name, "url": url, "apikey": apikey}
            csrftoken = $.cookie('csrftoken');
            $.ajax({
                url: "/copo/add_personal_dataverse/",
                method: "POST",
                data: data,
                headers: {
                    'X-CSRFToken': csrftoken
                },

            }).done(function () {
                $("#add_repo_modal").modal("toggle")
                update_display()
            })
        }
    })
})

function update_display() {
    $.ajax({
        url: "/copo/get_personal_dataverses/",
        method: "GET"
    }).done(function (data) {
        var rows
        data = JSON.parse(data)
        if (data.length == 0) {
            rows = rows + "<tr><td colspan='4'>No Repositories Entered</td>"
            $("#repos_table").find("tbody").html(rows)
        } else {
            $(data).each(function (idx, el) {
                rows = rows + "<tr data-repo-id='" + el.id + "'><td>" + el.name + "</td><td>dataverse</td><td>" + el.url + "</td><td><button style=\"margin-left:20px\" class=\"ui delete red icon button\">\n" +
                    "  <i class=\"trash icon\"></i>\n" +
                    "</button></td>"
            })
            $("#repos_table").find("tbody").html(rows)
        }
    })
}

function handle_delete(e) {
    var id = $(e.currentTarget).closest("tr").data("repo-id")
    csrftoken = $.cookie('csrftoken');
    $.ajax({
        url: "/copo/delete_personal_dataverse/",
        method: "POST",
        data: {"repo_id": id},
        headers: {
            'X-CSRFToken': csrftoken
        },

    }).done(function () {
        update_display()
    })
}
