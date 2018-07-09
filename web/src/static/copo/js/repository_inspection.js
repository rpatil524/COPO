// FS - 5/07/18

$(document).ready(function () {

    $(document).data('url', 'default')
    $(document).on('click', '#view_repo_structure', check_repo_id)
    $(document).on('click', '.create_add_dataverse', handle_radio)
    $(document).on('keyup', '#search_dataverse, #search_dataverse_id', search_dataverse)

    $('#create_new_dataverse').attr('disabled', 'disabled')
    $('#search_dataverse').attr('disabled', 'disabled')
    $('#search_dataverse_id').attr('disabled', 'disabled')
})


function check_repo_id(e) {
    // check for repo_id
    var repo_id = $('#custom_repo_id').val()
    // get repo info
    $.getJSON("/copo/get_repo_info/", {'repo_id': repo_id}, function (data) {
        if (data.repo_type == 'dataverse') {
            var url = data.repo_url
            $(document).data('url', url)
        }
    })
}


function handle_radio() {
    var checked = $('input[name=create_dataverse_radio]:checked').val();
    if (checked == 'new') {
        $('#create_new_dataverse').removeAttr('disabled')
        $('#search_dataverse').attr('disabled', 'disabled')
        $('#search_dataverse_id').attr('disabled', 'disabled')
    }
    else {
        $('#search_dataverse').removeAttr('disabled')
        $('#search_dataverse_id').removeAttr('disabled')
        $('#create_new_dataverse').attr('disabled', 'disabled')
    }
}


function search_dataverse(e) {
    var typed = $(e.currentTarget).val()
    var box;
    if (e.target.id == "search_dataverse_id") {
        $('#search_dataverse').val("")
        box = 'id'
    }
    else if (e.target.id == "search_dataverse") {
        $('#search_dataverse_id').val("")
        box = 'term'
    }
    $.getJSON("/copo/get_dataverse/", {'q': typed, 'box': box, 'url': $(document).data('url')}, function (data) {
            console.log(data)
        }
    )
}


function build_dataverse_modal(url) {
    alert(url)
}