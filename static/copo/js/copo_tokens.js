/**
 * Created by fshaw on 07/11/2016.
 */
$(document).ready(function () {
    refresh_token_display()
    $(this).on('click', '.delete_token_btn', delete_token_handler)
})

function refresh_token_display() {
    $.ajax({
        url: '/copo/get_tokens_for_user/',
        type: 'GET',
        dataType: 'json'
    }).done(function (data) {
        $('#figshare_div').empty()
        $(data.figshare_tokens).each(function (count, d) {
            var out = jQuery('<div/>', {
                class: 'token_div',
                html: 'Figshare Token &nbsp' + '...' + d.token.substring(d.token.length - 20, d.token.length),
            })
            var del_button = jQuery('<span/>', {
                html: "<a class='btn btn-primary delete_token_btn' data-token_id='" + d._id.$oid + "'>Remove Token</a>",
            })
            $(out).appendTo('#figshare_div')
            $(del_button).appendTo(out)
        })
    })
}

function delete_token_handler(e) {
    var tok_id = $(e.currentTarget).data('token_id')
    var csrftoken = $.cookie('csrftoken');
    $.ajax({
        url: '/copo/delete_token/',
        type: 'POST',
        dataType: 'json',
        headers: {'X-CSRFToken': csrftoken},
        data: {'token_id': tok_id}
    }).done(function (d) {
        refresh_token_display()
        BootstrapDialog.show({
            message: 'If you have been having problems uploading to a repository and have just deleted a token, please ' +
            'go back to the file description. You may need to enter your credentials for the repository again.',
            buttons: [{
                label: 'Close',
                action: function (dialogItself) {
                    dialogItself.close();
                }
            }]
        });
    })
}