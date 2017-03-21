/**
 * felix.shaw@tgac.ac.uk - 20/05/2016.
 *
 * N.B. to change polling update interval, change the value at the bottom of the setInterval method
 */

$(document).ready(function () {
    $('#upload_progress_info').hide()
    var csrftoken = $.cookie('csrftoken');
    $('#current-submissions').DataTable();
    $('.submission_panel').on('click', change_selected);
    $('.file_info').on('click', get_file_info);
    $('.upload_button').on('click', handle_upload);
    $('.delete_button').on('click', handle_delete);
    $(document).on('click', '.publish_button', publish_figshare_article)

    num_pts = 100;
    var ctx = document.getElementById("bandwidth_chart");
    Chart.defaults.global.animation.duration = 0;
    init_data = Array.apply(null, Array(num_pts)).map(Number.prototype.valueOf, 0);
    labels = Array.apply(null, Array(num_pts)).map(Number.prototype.valueOf, 0);
    var myChart = new Chart(ctx, {

            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    borderColor: "rgba(91,192,222, 1)",
                    backgroundColor: "rgba(91,192,222,1)",
                    data: init_data
                }]
            },
            options: {
                scaleShowLabels: false,
                scales: {

                    xAxes: [{
                        display: false,
                        gridLines: {
                            lineWidth: 0,
                            color: "rgba(255,255,255,0)"
                        },
                        ticks: {
                            suggestedMin: 0,
                            suggestedMax: 4,
                        },

                    }],
                    yAxes: [{
                        display: true,
                        gridLines: {
                            lineWidth: 0,
                            color: "rgba(255,255,255,0)"
                        },
                        ticks: {
                            suggestedMin: 0,
                            suggestedMax: 4,

                        },
                        label: 'aha'
                    }]
                }
            }
        }
    );

    var pie_data = {
        labels: [],
        datasets: [
            {
                data: [0, 100],
                backgroundColor: [
                    "rgba(91,192,222, 1)",
                    "rgba(91,192,222, 0.1)",

                ],
            }]
    };
    var cty = document.getElementById("completed_chart");
    var completed_chart = new Chart(cty, {
        type: 'doughnut',
        data: pie_data,
        options: {}
    });


    //$('#bandwidth_chart').height(400).width(400)
    //$('#completed_chart').height(400).width(800)

    setInterval(function () {

        //update chart data
        var id_to_send = $('#displayed_submission').val();
        $.get("/rest/get_upload_information/", {submission_id: id_to_send})
            .done(function (data) {

                data = JSON.parse(data);
                var canvases = $('canvas');
                if (data.found == false) {
                    $('canvas').each(function () {
                        $(this).siblings('h4').hide();
                        $(this).hide()
                    })

                }
                else if (!data.finished) {
                    // update charts with returned upload status data
                    $('#not_running_text').hide()
                    $('#upload_progress_info').show()
                    $('canvas').each(function () {
                        $(this).siblings('h4').show();
                        $(this).show()
                    });


                    myChart.chart.config.data.datasets[0].data = data.speeds;
                    update = [data.complete, 100 - data.complete];
                    completed_chart.config.data.datasets[0].data = update;

                    myChart.update();
                    completed_chart.update()

                }
                else {
                    // hide charts and show accession data
                    $('canvas').each(function () {
                        $(this).siblings('h4').hide();
                        $(this).hide()
                    });
                    $('#not_running_text').hide()
                    if ($('#status-panel').data('accessions_visible') != true) {

                        if (data.repo == 'ena') {
                            $('#status-panel').append('<h3 id="accessions-header">Accessions</h3>');

                            // create accession panels
                            var panel_group = jQuery('<div/>', {
                                class: 'panel-group',
                                id: 'accessions-block'
                            });
                            var c = 1;
                            // for each key, create a collapsable panel
                            for (var key in data.accessions) {

                                var panel = jQuery('<div/>', {
                                    class: 'panel panel-default',
                                });
                                var panel_heading = jQuery('<div/>', {
                                    class: 'panel-heading'
                                });
                                var panel_title = jQuery('<h4/>', {
                                    class: 'panel-title'
                                });

                                a_key = key[0].toUpperCase() + key.slice(1);
                                var title = $.parseHTML('<a data-toggle="collapse" href="#collapse' + c + '">' + a_key + '</a>');

                                $(title).appendTo(panel_title);
                                $(panel_title).appendTo(panel_heading);
                                $(panel_heading).appendTo(panel);

                                var collapse = jQuery('<div/>', {
                                    id: 'collapse' + c,
                                    class: 'panel-collapse collapse'
                                });
                                c = c + 1;

                                var panel_body = jQuery('<div/>', {
                                    class: 'panel-body'
                                });

                                var ul = jQuery('<ul/>');

                                if (key == 'sample') {
                                    $(data.accessions['sample']).each(function (count, smp) {
                                        var li = jQuery('<li/>', {
                                            html: '<span title="Biosample Accession: ' + smp.biosample_accession + '">' + smp.sample_accession + ' - <small>' + smp.sample_alias + '</small></span>'
                                        });
                                        $(li).appendTo(ul)
                                    })
                                }
                                else {

                                    var li = jQuery('<li/>', {
                                        html: data.accessions[key].accession + ' - <small>' + data.accessions[key].alias + '</small>'
                                    });
                                    $(li).appendTo(ul)
                                }
                                $(ul).appendTo(panel_body);
                                $(panel_body).appendTo(collapse);
                                $(collapse).appendTo(panel);

                                $(panel).appendTo(panel_group)

                            }

                            $(panel_group).appendTo('#status-panel');
                            $('#status-panel').data('accessions_visible', true)
                        }
                        else if (data.repo == 'figshare') {
                            $('#status-panel').append('<h3 id="accessions-header">Accessions</h3>');

                            // create accession panels
                            var panel_group = jQuery('<div/>', {
                                class: 'panel-group',
                                id: 'accessions-block'
                            });

                            //ac = data.accessions.split(',')
                            ac = data.article_id.split(',')
                            $(ac).each(function (count, el) {
                                var anc = jQuery('<a/>', {
                                    html: el + ' (Article ID)',
                                    href: el,
                                });
                                $(anc).appendTo(panel_group)
                            })

                            // check status
                            if (data.status == 'not published') {
                                console.log('not published')

                                var button = jQuery('<div/>', {
                                    html: "<a data-sub_id='" + data.sub_id + "' class='publish_button btn btn-primary'>Publish</a>",
                                })

                                panel_group.append('<h4>Not Yet Published</h4>')
                                panel_group.append('This Figshare article has been uploaded but is not yet published and publicly viewable. Click below to publish. Once published, the article can no longer be deleted</br></br>')
                                $(button).appendTo(panel_group)

                            }

                            $(panel_group).appendTo('#status-panel');
                            $('#status-panel').data('accessions_visible', true)
                        }


                    }
                    $(".submission_panel[data-submission-id=" + id_to_send + "]").find('.ctl-buttons').hide()

                }
            });


    }, 1000)

});

function change_selected(e) {

    // change colors of table rows
    $('.submission_active').each(function (counter, data) {
        console.log(counter)
        var complete = $(data.closest('.submission_panel')).data('submission-status');
        if (complete == 'True') {
            $(data).removeClass('submission_pending submission_active submission_complete').addClass('submission_complete')
        }
        else {
            $(data).removeClass('submission_pending submission_active submission_complete').addClass('submission_pending')
        }
    });
    $(e.currentTarget).find('.submission_header').removeClass('submission_pending submission_active submission_complete').addClass('submission_active');

    //change displayed_submission
    var current_id = $(e.target).closest('.submission_panel').data('submission-id');
    $('#displayed_submission').val(current_id);
    $('#accessions-block, #accessions-header').remove();
    $('#status-panel').data('accessions_visible', false)

}


function handle_upload(e) {
    $(e.currentTarget).hide();
    BootstrapDialog.show({
        title: 'Upload Submission',
        message: 'Are you sure you want to upload this submission bundle.',
        buttons: [{
            label: 'Yes',
            action: function (dialog) {
                dialog.close();
                var csrftoken = $.cookie('csrftoken');
                $.post("/rest/submit_to_repo/", {
                    'sub_id': $('#displayed_submission').val(),
                    'csrfmiddlewaretoken': csrftoken
                }).done(function (data) {
                    $(e.currentTarget).closest('tr').find('.delete_button', '.upload_button').remove();
                    $(e.currentTarget).closest('tr').removeClass('active').addClass('success')
                })
            }


        }, {
            label: 'No',
            action: function (dialog) {
                dialog.close();
            }

        }]
    });
}

function handle_delete(e) {
    $(e.currentTarget).hide();
    BootstrapDialog.show({
        title: 'Delete Submission',
        message: 'Are you sure you want to delete this submission bundle.',
        buttons: [{
            label: 'Yes',
            action: function (dialog) {
                dialog.close();
                $(e.currentTarget).data('submission_id');
                $.post("/rest/delete_submission/", {
                    'sub_id': $(e.currentTarget).data('submission_id'),
                    'csrfmiddlewaretoken': csrftoken
                }).done(function (data) {
                    $(e.currentTarget).closest('tr').remove()
                })
            }


        }, {
            label: 'No',
            action: function (dialog) {
                dialog.close();
            }

        }]
    });
}


function publish_figshare_article(e) {
    var csrftoken = $.cookie('csrftoken');
    var sub_id = $(e.currentTarget).data('sub_id')
    var d = {'submission_id': sub_id}

    $.ajax({
            url: '/copo/publish_figshare/',
            data: {'submission_id': sub_id},
            type: "POST",
            headers: {'X-CSRFToken': csrftoken},
            dataType: 'json'
        })
        .done(function (e) {
            if(e.status_code == 201 || e.status_code == 200){
                $('#status-panel').empty()
                $('#status-panel').data('accessions_visible', false)
            }
        })
}


function get_file_info(e) {
    e.preventDefault;
    var file_id = $(e.currentTarget).data('file_id');
    var copoVisualsURL = "/copo/copo_visualize/";
    var csrftoken = $.cookie('csrftoken');
    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {'X-CSRFToken': csrftoken},
        data: {
            'task': 'description_summary',
            'component': "datafile",
            'target_id': file_id
        },
        success: function (data) {
            var descriptionDiv = $('<div></div>');

            for (var j = 0; j < data.description.length; ++j) {
                var Ddata = data.description[j];

                var i = 0; //need to change this to reflect stage index...

                var level1Div = $('<div/>', {
                    style: 'padding: 5px; border: 1px solid #ddd; border-radius:2px; margin-bottom:3px;'
                });

                var level2Anchor = $('<a/>', {
                    class: "review-to-stage",
                    "data-stage-indx": i,
                    "data-sel-target": file_id,
                    style: "cursor: pointer; cursor: hand;",
                    html: Ddata.title
                });

                var level2Div = $('<div/>', {
                    style: 'padding-bottom: 5px;'
                }).append($('<span></span>').append(level2Anchor));

                level1Div.append(level2Div);

                for (var k = 0; k < Ddata.data.length; ++k) {
                    var Mdata = Ddata.data[k];

                    var mDataDiv = $('<div/>', {
                        style: 'padding-bottom: 5px;'
                    });

                    var mDataLabelSpan = $('<span/>', {
                        style: 'margin-right: 10px;',
                        html: Mdata.label + ":"
                    });

                    var displayedValue = "";

                    if (Object.prototype.toString.call(Mdata.data) === '[object Array]') {
                        Mdata.data.forEach(function (vv) {
                            displayedValue += "<div style='padding-left: 25px; padding-top: 3px;'>" + vv + "</div>";
                        });
                    } else if (Object.prototype.toString.call(Mdata.data) === '[object String]') {
                        displayedValue = String(Mdata.data);
                    }

                    var mDataDataSpan = $('<span/>', {
                        html: displayedValue
                    });

                    mDataDiv.append(mDataLabelSpan).append(mDataDataSpan);
                    level1Div.append(mDataDiv)
                }

                descriptionDiv.append(level1Div);
            }

            var descriptionHtml = "No description!";

            if (data.description.length) {
                descriptionHtml = descriptionDiv.html();
            }

            var descriptionInfoPanel = $('<div/>', {
                class: "panel panel-default",
                style: 'margin-top:1px;'
            });

            var descriptionInfoPanelPanelHeading = $('<div/>', {
                class: "panel-heading",
                style: "background-image: none;",
                html: "Description Metadata"
            });

            var descriptionInfoPanelPanelBody = $('<div/>', {
                class: "panel-body",
                style: "overflow:scroll",
                html: descriptionHtml
            });

            descriptionInfoPanel.append(descriptionInfoPanelPanelHeading).append(descriptionInfoPanelPanelBody);

            //row.child($('<div></div>').append(descriptionInfoPanel).html()).show();
            $('#file_info_modal').find('.modal-body').empty();
            $('#file_info_modal').find('.modal-body').append(descriptionInfoPanel);
            $('#file_info_modal').modal('show')
        },
        error: function () {
            alert("Couldn't retrieve description attributes!");
            return '';
        }
    })
}


