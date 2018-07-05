// FS - 5/07/18

$(document).ready(function () {

    $(document).on('click', '#view_repo_structure', function () {
        // check for repo_id
        var repo_id = $('#custom_repo_id').val()
        $.getJSON("/copo/get_repo_info/", {'repo_id': repo_id}, function (data) {
            if(data.repo_type == 'dataverse'){
                var url = data.repo_url
                build_dataverse_modal(url)
            }
        })
    })
})

function build_dataverse_modal(url){
    alert(url)
}