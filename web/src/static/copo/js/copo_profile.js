/**
 * felix.shaw@tgac.ac.uk - 22/10/15.
 */
$(document).ready(function () {
    csrftoken = $.cookie('csrftoken');

    //form call
    $(document).on('click', '.index-form-call', function (e) {
        e.preventDefault();

        var component = $(this).attr("data-component");
        var profile_id = $("#profile_id").val();

        $.ajax({
            url: copoFormsURL,
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            data: {
                'task': 'form',
                'component': component,
                'profile_id': profile_id,
                'visualize': 'get_profile_count'
            },
            success: function (data) {
                json2HtmlForm(data);
            },
            error: function () {
                alert("Couldn't build " + component + " form!");
            }
        });
    });

    $('body').on('getprofilecount', function (event) {
        update_counts();
    });


    update_counts()


    $('#publication_link').click(function (e) {
        e.stopImmediatePropagation()
        var url = $('#publications_url').val()
        window.location.href = url
    })
    $('#data_link').click(function (e) {
        e.stopImmediatePropagation()
        var url = $('#data_url').val()
        window.location.href = url
    })
    $('#sample_link').click(function (e) {
        e.stopImmediatePropagation()
        var url = $('#samples_url').val()
        window.location.href = url
    })
    $('#submission_link').click(function (e) {
        e.stopImmediatePropagation()
        var url = $('#submissions_url').val()
        window.location.href = url
    })
    $('#people_link').click(function (e) {
        e.stopImmediatePropagation()
        var url = $('#people_url').val()
        window.location.href = url
    })


    $('.block > .features').hide()

    $('.block').click(function (e) {
        var duration = 150
        var the_others = $('.features')
        var features = $(this).find('.features')
        if (features.is(":visible")) {
            features.slideUp(duration)
        }
        else {
            the_others.slideUp(duration)
            features.slideDown(duration)
        }
    })

})

function update_counts() {
    var url = $(update_counts_url).val()
    $.getJSON(url)
        .done(function (data) {
            $('.data .price span').html(data.num_data)
            $('.samples .price span').html(data.num_sample)
            $('.submissions .price span').html(data.num_submission)
            $('.publication .price span').html(data.num_pub)
            $('.people .price span').html(data.num_person)
        })

} //end of func
