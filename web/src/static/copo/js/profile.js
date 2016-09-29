/**
 * Created by fshaw on 16/02/15.
 */

$(document).ready(function () {

    $('.spinner').hide();
    $('.coolHandLuke li').on('click', function (e) {
        if ($(e.target).prev().hasClass('red')) {
            // find type of submission
            var collection_id = $(e.target).closest('tr').attr('data-collection_id');
            var type = delegate_handler(e, collection_id)
        }
        else {
            view_in_figshare(e)
        }

    });

    //handle modal hide event
    $('.modal').on('hidden.bs.modal', function () {
        $('.modal-backdrop').remove();

        try {
            $(this).find('form')[0].reset();
        } catch (err) {
        }

        if (this.id == "newCollectionModal") {
            do_disengage_study_modal();
        }

    });

    //hide delete button for first element in the study type group
    $("#study_type_remove_0").hide();

    //handle change event for collection types drop-down
    toggle_collection_type($("#collection_type option:selected").val());

    $("#collection_type").change(function () {
        toggle_collection_type($("#collection_type option:selected").val());
    });

    //handle event for add study type
    $(".study-type-add").click(function (event) {
        do_add_study_type();
    });

    //handle click event for delete study type
    $("#study_types_lists_div").on('click', 'a.study-type-remove', function (event) {
        do_remove_study_type(event);
    });


    function submit_to_figshare(e) {


        var spinner = $(e.target).closest('td').find('.spinner');
        var color_span = $(e.target).prev();
        $(spinner).show();

        // ajax call checks if figshare creds are valid
        $.ajax({
            type: "GET",
            url: "/rest/check_figshare_credentials",
            dataType: "json"
        }).done(function (data) {
            // if creds invalid, prompt user
            if (data.exists == false) {
                url = data.url;
                window.open(url, "_blank", "toolbar=no, scrollbars=yes, resizable=no, top=500, left=20, width=800, height=600");
            }
            // if creds valid call submit_to_figshare backend handler
            else {
                var article_id = $(e.target).closest('tr').attr('data-collection_id');
                $.ajax({
                    type: "GET",
                    url: "/api/submit_to_figshare/" + article_id,
                    dataType: "json"
                }).done(function (data, textStatus, xhr) {

                    if (data.success == true) {

                        BootstrapDialog.show({
                            title: 'Success',
                            message: 'Figshare Object Deposited'
                        });
                        $(color_span).removeClass('red').addClass('green');
                        $(e.target).text('Inspect')
                    }
                    $(spinner).hide()
                })
            }
        })
    }

    function do_disengage_study_modal() {

        //remove all redundant fields
        $('.study-type-remove').each(function () {
            var targetId = this.id;
            var splitIndex = targetId.lastIndexOf("_");
            var indexPart = targetId.substr(splitIndex + 1);

            if (parseInt(indexPart) > 0) {
                //remove study type element
                $("#study_type_select_divs_" + indexPart).remove();
            }

        });

    }


    function delegate_handler(e, collection_id) {
        e.preventDefault();
        var csrftoken = $.cookie('csrftoken');
        $.get("/api/get_collection_type/", {'collection_id': collection_id})
            .done(function (data) {
                if (data == 'Figshare') {
                    submit_to_figshare(e)
                }
                else if (data == 'ENA Submission') {
                    $.post('/api/refactor_collection_schema/',
                        {
                            'collection_head_id': collection_id,
                            'collection_type': 'ENA Submission',
                            'csrfmiddlewaretoken': csrftoken
                        }
                    ).done(function (data) {
                            console.log(data.status);
                            if (data.status == "success") {
                                return false; //todo: need to remove this line later in order to access sra conversion...
                                $.post('/api/convert_to_sra/', {
                                    'collection_id': collection_id,
                                    'csrfmiddlewaretoken': csrftoken
                                }).done(function (data) {
                                    console.log(data)
                                });
                            }

                        });
                }
            });
    }
});
