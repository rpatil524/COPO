$(document).ready(function () {
    update_display()
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
        $(data).each(function (idx, el) {
            rows = rows + "<tr data-repo-id='" + el.id + "'><td>" + el.name + "</td><td>dataverse</td><td>" + el.url + "</td><td><button style=\"margin-left:20px\" class=\"ui red icon button\">\n" +
                "  <i class=\"cloud icon\"></i>\n" +
                "</button></td>"
        })
        console.log(rows)
        $("#repos_table").find("tbody").html(rows)
    }).error(function(data){
        console.error("error" + data)
    })
}


/*
function get_repos_data() {
    var u_type = $('#user_type').val()
    $.ajax({
        url: "/copo/get_repos_data/",
        method: "GET",
        dataType: "json",
        data: {"u_type": $('#user_type').val()}
    }).done(function (data) {
        $("#repos_table tbody").empty();
        $(data).each(function (idx, item) {

            var tr = document.createElement("tr");
            if (u_type == "managers") {
                tr.innerHTML = "<td>" + item.name + "</td><td>" + item.type + "</td><td>" + item.url + "</td><td class='delete_repo'>" +
                    "<i class='fa fa-minus-square delete-repo-button minus-color'></i>" +
                    "</td>";
            } else if (u_type == "submitters") {
                tr.innerHTML = "<td>" + item.name + "</td><td>" + item.type + "</td><td>" + item.url + "</td>";
            }

            $(tr).data("id", item._id.$oid)
            $(tr).data("repo_name", item.repo_name);
            $(tr).data("url", item.url);
            $(tr).data("name", item.name)
            $(tr).addClass("clickable-row")
            $(tr).appendTo("#repos_table tbody");
        });
    });
}
*/