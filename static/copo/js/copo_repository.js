$(document).ready(function () {

    get_repos_data()
    user_lookup()

    $(document).ajaxStart(function () {
        $(".saving_status").show();
    });
    $(document).ajaxStop(function () {
        $(".saving_status").hide();
    });
    $(".saving_status").hide();
    $(document).on("click", ".delete_repo", delete_repo);


    $('#repos_table').on('click', '.clickable-row', function (event) {
        $(this).addClass('active').siblings().removeClass('active');
        $(document).data('selected_row_id', $(this).data('id'))
        $(document).data('selected_row_name', $(this).data('name'))
        $('#selected_row_label').html($(document).data('selected_row_name'))
        $('#users_control').removeClass('hidden')
        get_users_in_repo();
    });

    $('#repoForm').validator().on('submit', function (e) {
        if (e.isDefaultPrevented()) {
            //validation errors
        } else {
            // everything looks good!
            e.preventDefault()
            var type = $("#radio_div input[type='radio']:checked").val()
            var name = $('#name').val()
            var url = $('#url').val()
            var apikey = $('#apikey').val()
            var username = $('#username').val()
            var password = $('#password').val()
            var isCG = $('input[name=isCG]:checked').val();
            $.ajax({
                url: "/copo/create_new_repo/",
                data: {
                    'type': type,
                    'name': name,
                    'url': url,
                    'apikey': apikey,
                    'username': username,
                    'password': password,
                    'isCG': isCG
                },
                headers: {'X-CSRFToken': $.cookie('csrftoken')},
                method: 'POST',
                dataType: 'json'
            }).done(function (item) {
                $('#add_repo_modal').modal('toggle')
                var tr = document.createElement("tr");
                tr.innerHTML = "<td>" + item.name + "</td><td>" + item.type + "</td><td>" + item.url + "</td><td class='delete_repo'>" +
                    "<i class='fa fa-minus-square delete-user-button minus-color'></i>" +
                    "</td>";
                $(tr).data("repo_name", item.repo_name);
                $(tr).data("url", item.url);
                $(tr).data("id", item._id.$oid)
                $(tr).data("name", item.name)
                $(tr).appendTo("#repos_table tbody");
            }).error(function (e) {
                console.log(e)
            })
        }
    })

    //handlers for radio buttons
    $(document).on('click', '.radio', function () {
        var type = $("#radio_div input[type='radio']:checked").val()
        enable_authentication_boxes()
        if (type == 'dspace') {
            disable_apikey_box()
        } else {
            disable_username_password_boxes()
        }
    })

    function disable_username_password_boxes() {
        $('#username').attr('disabled', 'disabled')
        $('#password').attr('disabled', 'disabled')
    }

    function disable_apikey_box() {
        $('#apikey').attr('disabled', 'disabled')
    }

    function delete_repo(e) {
        e.stopPropagation()
        var row = $(e.currentTarget).closest("tr")
        $(document).data("repo_row_for_deletion", row)
        var id = row.data("id")
        var code = BootstrapDialog.show({
            type: BootstrapDialog.TYPE_DANGER,
            title: $('<span>Delete Repository</span>'),
            message: function () {
                return "Are you sure you want to delete this Repo entry?";
            },
            draggable: true,
            closable: true,
            animate: true,
            onhide: function () {
            },
            buttons: [{
                label: 'Cancel',
                action: function (dialogRef) {
                    dialogRef.close();
                }
            },
                {
                    icon: 'glyphicon glyphicon-trash',
                    label: 'Delete',
                    cssClass: 'btn-danger',
                    action: function (dialogRef) {
                        data_dict = {'target_id': id}
                        csrftoken = $.cookie('csrftoken');
                        $.ajax({
                            url: '/copo/delete_repo_entry',
                            type: "GET",
                            dataType: "json",
                            contentType: 'application/json',
                            headers: {
                                'X-CSRFToken': csrftoken
                            },
                            data: data_dict,
                            success: function (d) {
                                // delete row from table
                                $(row).remove()
                            },
                            error: function () {
                                alert("Couldn't delete repo!");

                            }
                        });

                        dialogRef.close();

                    }
                }
            ]
        });
    }

    function enable_authentication_boxes() {
        $('#apikey').val('')
        $('#username').val('')
        $('#password').val('')
        $('#apikey').removeAttr('disabled')
        $('#username').removeAttr('disabled')
        $('#password').removeAttr('disabled')
        $('#repoForm').validator('validate')
    }


})


var user_lookup = function () {
    // remove all previous autocomplete divs
    $(".autocomplete").remove();
    AutoComplete({
        EmptyMessage: "No Users Found",
        Url: "/rest/get_users/",
        _Select: do_user_select,
        _Render: do_user_post,
        _Position: do_user_position,
    }, ".user_search_field");

    function do_user_select(item) {
        add_user_to_repo(item)
    }

    function do_user_position(a, b, c) {
        console.log(a, b, c)
    }


    function do_user_post(response) {
        if (response == "") {
            response = "[]";
        }
        response = JSON.parse(response);


        var empty,
            length = response.length,
            li = document.createElement("li"),
            ul = document.createElement("ul");


        for (var item in response) {

            try {

                li.innerHTML = "<div class='h5'>" + response[item][1] + " " + response[item][2] + "</div><span class='h6'>" + response[item][3] + "</span>";
                $(li).data("id", response[item][0]);
                $(li).data("first_name", response[item][1]);
                $(li).data("last_name", response[item][2]);
                $(li).data("email", response[item][3]);
                $(li).data("username", response[item][4]);


                //$(li).attr("data-id", doc.id);
                var styles = {
                    margin: "2px",
                    marginTop: "4px",
                    fontSize: "large",
                };
                $(li).css(styles);

                ul.appendChild(li);
                li = document.createElement("li");
            } catch (err) {
                console.log(err);
                li = document.createElement("li");
            }
        }
        $(this.DOMResults).empty();
        this.DOMResults.append(ul);
    }
}

function add_user_to_table(item) {

}

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


function add_user_to_repo(row) {

    var user_details = get_user_details_from_row(row);
    var repo_id = $(document).data('selected_row_id')
    $.ajax({
        url: "/copo/add_user_to_repo/",
        method: 'GET',
        data: {
            "repo_id": repo_id,
            "user_id": user_details.id,
            "email": user_details.email,
            "username": user_details.username,
            "first_name": user_details.first_name,
            "last_name": user_details.last_name,
            "u_type": $('#user_type').val()
        },
        dataType: "json"
    }).error(function (data) {
        console.log(data)
    }).success(function (data) {
        if (data.out == '0') {
            var tr = document.createElement("tr");
            tr.innerHTML = "<td>" + data.first_name + " " + data.last_name + "</td><td class='delete_cell'>" +
                "<i class='fa fa-minus-square delete-user-button minus-color'></i>" +
                "</td>";
            $(tr).data("first_name", data.first_name);
            $(tr).data("last_name", data.last_name);
            $(tr).data("username", data.username);
            $(tr).data("email", data.email);
            $(tr).data("id", data.id);
            $(tr).appendTo("#users_table tbody");
        }
    })
}

function get_user_details_from_row(row) {
    var user_details = new Object();
    user_details.id = $(row).data("id");
    user_details.first_name = $(row).data("first_name");
    user_details.last_name = $(row).data("last_name");
    user_details.username = $(row).data("username");
    user_details.email = $(row).data("email");
    return user_details
}

function get_users_in_repo() {
    var repo_id = $(document).data('selected_row_id')
    var u_type = $('#user_type').val()
    $.ajax({
        url: "/copo/get_users_in_repo/",
        method: 'GET',
        data: {
            "user_type": u_type,
            "repo_id": repo_id
        },
        dataType: "json"
    }).error(function (data) {
        console.log(data)
    }).success(function (data) {
        $('#users_table tbody').empty()
        $(data).each(function (idx, d) {

            var tr = document.createElement("tr");
            $(tr).data("id", d.uid)
            $(tr).data("first_name", d.first_name);
            $(tr).data("last_name", d.last_name);
            $(tr).append("<td>" + d.first_name + "</td>");
            $(tr).append("<td>" + d.last_name + "</td>")
            $(tr).append("<td class='delete_cell_user text-center'><i class=\"fa fa-minus-square delete-user-button minus-color\"></i>")
            $('#users_table tbody').append(tr)
        })
    })
}


function delete_user_row(e) {
    var row = $(e.currentTarget).parents("tr");
    remove_user_from_repo(row);
    row.remove();
}

function remove_user_from_repo(row) {
    u_type = $('#user_type').val()
    var user_details = get_user_details_from_row(row);
    var repo_id = $(document).data('selected_row_id')

    $.ajax({
        url: "/copo/remove_user_from_repo/",
        data: {
            "repo_id": repo_id,
            "uid": user_details.id
        },
        dataType: "json"
    });
}