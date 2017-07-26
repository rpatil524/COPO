/**
 * felix.shaw@tgac.ac.uk - 20/05/2016.
 *
 * N.B. to change polling update interval, change the value at the bottom of the setInterval method
 */

$(document).ready(function () {
    var component = "submission";

    //global_help_call
    do_global_help(component);


    build_submission_table()
    get_dataset_data()
    //$('#submission_table').DataTable()

    $('#upload_progress_info').hide()
    var csrftoken = $.cookie('csrftoken');
    $('#current-submissions').DataTable();
    $('.submission_panel').on('click', change_selected);
    $('.file_info').on('click', get_file_info);
    $(document).on('click', '.upload_button', handle_upload);
    $('.delete_button').on('click', handle_delete);
    $(document).on('click', '.publish_button', publish_figshare_article)
    $(document).on('click', '.submission_row', get_accession_info)

    setInterval(function () {

        //get table row ids
        var ids = new Array
        $('.submission_row').each(function (idx, row) {
            ids.push($(row).data('submission_id'))
        })
        ids = JSON.stringify(ids)
        $.ajax({
            url: "/rest/get_upload_information/",
            data: {'ids': ids},
            dataType: 'json',
            method: 'GET'
        }).done(function (data) {
            $(data.return).each(function (idx, element) {
                var s_id = element.id;
                var tr = $(".submission_row[data-submission_id='" + s_id + "']")
                var pct_complete = 0
                try {
                    var pct_complete = (Number((element.complete).toFixed(2)))
                }
                catch (TypeError) {
                    pct_complete = 100
                }
                $(tr).find('.progress-bar').css('width', pct_complete + '%')
                $(tr).find('.progress-bar').html(pct_complete + ' %')
                var mean_speed = 0
                try {
                    // try to calculate mean speed
                    element.speeds.forEach(function (entry) {
                        mean_speed += entry
                    })
                    mean_speed /= element.speeds.length
                    // convert to MB
                    mean_speed = mean_speed / 8
                    mean_speed = (Number((mean_speed).toFixed(2)))
                }
                catch (TypeError) {
                    mean_speed = 0
                }
                $(tr).find('.upload_speed').html(mean_speed)
            })
        })


    }, 5000)

});

function get_dataset_data() {
    $.getJSON('/rest/call_get_dataset_details', {'profile_id': $('#profile_id').val()}, function (data) {
        if (data != 'null') {
            var output = 'Please select a Dataset to add to.<br/><br/>'
            output = output + '<div id="dataset_selector">'
            $(data).each(function(idx, it){
                output = output + '<div style="margin-top: 10px"><label class="radio-inline"><input type="radio" name="optradio">' + it.title + '</label></div>'
            })
            output = output + '<div style="margin-top: 10px"><label class="radio-inline"><input type="radio" name="optradio">New Dataset</label></div>'
            output = output + '</div>'
            $(document).data('message', output)
        }
        else {
            $(document).data('message', 'Are you sure you want to upload this submission bundle.')
        }
    })
}


function build_submission_table() {
    var profile_id = $('#profile_id').val()
    $.ajax({
        url: '/rest/copo_get_submission_table_data/',
        method: 'POST',
        headers: {'X-CSRFToken': $.cookie('csrftoken')},
        dataType: 'json',
        data: {'profile_id': profile_id}
    }).done(function (data) {

        // for each element, create a row in the submissions table
        $(data).each(function (idx, element) {

            if (element.complete == "true" || element.complete == true) {
                var percent_complete = '100';
                var progress_bar_style = 'progress-bar-success'
                var striped = ''
                var active_button = 'disabled'
            }
            else {
                var striped = 'progress-bar-striped'
                var progress_bar_style = 'progress-bar-info'
                var percent_complete = '0'
                var active_button = 'active'
            }


            var send_cell = '<td><button type="button" class="btn btn-default upload_button ' + active_button + '">'
                + '<span style="margin:0" class="glyphicon glyphicon-cloud-upload"></span></button>' +
                '<span class="ajax_span" style="visibility: hidden"><img src="/static/copo/img/ajax.gif" style="margin-left: 20px; height: 32px"></span>' +
                '</td>'


            var row = $('<tr class="submission_row" data-submission_id="' + element._id.$oid + '"></tr>')
            $(row).append('<td class="repo_cell"">' + element.repository + '</td>')
            $(row).append('<td style="cursor: pointer"><a data-toggle="modal" data-target="#accessionModal">Files / Accessions <span style="vertical-align: middle" class="fa fa-info-circle fa-2x"></span></a></td>')
            $(row).append('<td>' + element.date_created + '</td>')
            $(row).append('<td class="status">' + element.status + '</td>')
            $(row).append('<div style="margin-top: 20px" class="progress">'
                + '<div class="progress-bar ' + progress_bar_style + ' ' + striped + ' active" role = "progressbar"'
                + 'aria-valuenow="' + percent_complete + '" aria-valuemin="0" aria-valuemax="100" style="width:' + percent_complete + '%">' + percent_complete + '%</div></div>')
            $(row).append('<td><span class="upload_speed">0</span>MB/sec</td>')
            $(row).append(send_cell)
            $('#submission_table tbody').append(row)
        })
        $('#submission_table').DataTable()
    })
}


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

    var btn = $(e.currentTarget)
    if (btn.hasClass('disabled')) {
        return false;
    }

    btn.addClass('disabled');
    var tr = btn.closest('tr')
    var submission_id = $(tr).data('submission_id')

    var message = $(document).data('message')
    if ($(tr).find('.repo_cell').html() != 'dcterms'){
        message = 'Are you sure you want to upload this submission bundle.'
    }

    BootstrapDialog.show({
        title: 'Upload Submission',
        message: message,
        buttons: [{
            label: 'Yes',
            action: function (dialog) {
                $(tr).find('.ajax_span').css('visibility', 'visible')
                dialog.close();
                var csrftoken = $.cookie('csrftoken');
                $('#dataset_selector')
                $.ajax({
                    url: "/rest/submit_to_repo/",
                    data: {'sub_id': submission_id},
                    headers: {'X-CSRFToken': $.cookie('csrftoken')},
                    method: 'POST',
                    dataType: 'json'
                }).done(function (data) {
                    get_dataset_data()
                    if (data.status == 1) {
                        // we have uploaded the file, so change table row
                        $(tr).find('.progress-bar').css('width', '100%')
                        $(tr).find('.progress-bar').removeClass('progress-bar-striped').removeClass('progress-bar-info').addClass('progress-bar-success')
                        $(tr).find('.progress-bar').html('100%')
                        $(tr).find('.status').html('Submitted')
                        var remove_button = true
                    }
                    else {
                        BootstrapDialog.show({
                            title: 'Error In Upload',
                            message: '<p>Please see below and fix</p>' + data.status,
                            buttons: [
                                {
                                    label: 'Continue',
                                    action: function (dialog) {
                                        dialog.close()
                                    }
                                }
                            ]
                        })
                    }
                }).fail(function (data) {
                    console.log(data)
                }).always(function (data) {
                    $(tr).find('.ajax_span').css('visibility', 'hidden')
                    if (remove_button == true) {

                    }
                    else {
                        btn.removeClass('disabled');
                    }
                    get_dataset_data()
                })
            }
        }, {
            label: 'No',
            action: function (dialog) {
                dialog.close();
                get_dataset_data()
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
            if (e.status_code == 201 || e.status_code == 200) {
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


function get_accession_info(e) {

    // get table row
    var sub_id = $(e.currentTarget).data('submission_id')
    $.ajax({
        url: '/rest/get_accession_data',
        data: {'sub_id': sub_id},
        method: 'GET',
        dataType: 'json'
    }).done(function (data) {

        $('#file_accession_panel').empty()

        // create accession panels
        var panel_group = jQuery('<div/>', {
            class: 'panel-group',
            id: 'files-block'
        });
        var c = 1;

        var h = $('<h4></h4>', {
            html: 'Submission Files'
        })
        $(h).appendTo(panel_group);

        var panel = jQuery('<div/>', {
            class: 'panel panel-default',
        });
        var panel_heading = jQuery('<div/>', {
            class: 'panel-heading'
        });
        var panel_title = jQuery('<h4/>', {
            class: 'panel-title'
        });

        var title = $.parseHTML('<a data-toggle="collapse" href="#collapse' + c + '">Files</a>');

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
        var li;
        $(data.sub.filenames).each(function (count, smp) {
            li = jQuery('<li/>', {
                class: 'filelist_li',
                html: smp
            });
            $(li).appendTo(ul)
        })

        $(ul).appendTo(panel_body);
        $(panel_body).appendTo(collapse);
        $(collapse).appendTo(panel);

        $(panel).appendTo(panel_group)
        $(panel_group).appendTo('#file_accession_panel');


        panel_group = jQuery('<div/>', {
            class: 'panel-group',
            id: 'accessions-block'
        });

        var h4 = $('<h4></h4>', {
            html: 'Submission Accessions'
        })
        $(h4).appendTo(panel_group);

        if (Object.keys(data.sub.accessions).length == 0) {
            var message = $('<span></span>', {
                html: 'Accessions not available yet'
            })
            $(panel_group).appendTo('#file_accession_panel');
            $(message).appendTo('#file_accession_panel');
        }
        else {

            if (data.sub.repo == 'figshare') {

                // create accession panels
                var panel_group = jQuery('<div/>', {
                    class: 'panel-group',
                    id: 'acc-block'
                });
                var c = 2;

                var h = $('<h4></h4>', {
                    html: 'Accessions'
                })
                $(h).appendTo(panel_group);

                var panel = jQuery('<div/>', {
                    class: 'panel panel-default',
                });
                var panel_heading = jQuery('<div/>', {
                    class: 'panel-heading'
                });
                var panel_title = jQuery('<h4/>', {
                    class: 'panel-title'
                });

                var title = $.parseHTML('<a data-toggle="collapse" href="#collapse' + c + '">Accessions</a>');

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
                var li;
                $(data.sub.accessions).each(function (count, smp) {
                    li = jQuery('<li/>', {
                        class: 'filelist_li',
                        html: '<a href="https://figshare.com/account/articles/' + smp + '">' + 'Figshare Accession: ' + smp + '</a>'
                    });
                    $(li).appendTo(ul)
                })

                $(ul).appendTo(panel_body);
                $(panel_body).appendTo(collapse);
                $(collapse).appendTo(panel);

                $(panel).appendTo(panel_group)
                $(panel_group).appendTo('#file_accession_panel');
            }
            else {
                for (var key in data.sub.accessions.accessions) {
            if (data.sub.accessions.accessions instanceof Array) {
                panel = jQuery('<div/>', {
                    class: 'panel panel-default',
                });
                panel_heading = jQuery('<div/>', {
                    class: 'panel-heading'
                });
                panel_title = jQuery('<h4/>', {
                    class: 'panel-title'
                });

                //var a_key = key[0].toUpperCase() + key.slice(1);
                title = $.parseHTML('<a data-toggle="collapse" href="#collapse' + c + '">Accessions</a>');

                $(title).appendTo(panel_title);
                $(panel_title).appendTo(panel_heading);
                $(panel_heading).appendTo(panel);

                collapse = jQuery('<div/>', {
                    id: 'collapse' + c,
                    class: 'panel-collapse collapse'
                });
                c = c + 1;

                panel_body = jQuery('<div/>', {
                    class: 'panel-body'
                });

                ul = jQuery('<ul/>');
                var ul = jQuery('<ul/>');
                d = data.sub.accessions.accessions[0]
                var allowed_keys = ['filesize', 'id', 'dataverse_title', 'dataset_doi']

                for (var key in d) {
                    if ($.inArray(key, allowed_keys) > -1) {
                        li2 = jQuery('<li/>', {
                            html: '<span>' + key + ' - <small>' + d[key] + '</small></span>'
                        });
                        $(li2).appendTo(ul)
                    }
                }
                $(ul).appendTo(panel_body);
                $(panel_body).appendTo(collapse);
                $(collapse).appendTo(panel);
                $(panel).appendTo(panel_group)
            }
            else {
                for (var key in data.sub.accessions.accessions) {

                    panel = jQuery('<div/>', {
                        class: 'panel panel-default',
                    });
                    panel_heading = jQuery('<div/>', {
                        class: 'panel-heading'
                    });
                    panel_title = jQuery('<h4/>', {
                        class: 'panel-title'
                    });

                    var a_key = key[0].toUpperCase() + key.slice(1);
                    title = $.parseHTML('<a data-toggle="collapse" href="#collapse' + c + '">' + a_key + '</a>');

                    $(title).appendTo(panel_title);
                    $(panel_title).appendTo(panel_heading);
                    $(panel_heading).appendTo(panel);

                    collapse = jQuery('<div/>', {
                        id: 'collapse' + c,
                        class: 'panel-collapse collapse'
                    });
                    c = c + 1;

                    panel_body = jQuery('<div/>', {
                        class: 'panel-body'
                    });

                    ul = jQuery('<ul/>');

                    var li2
                    if (key == 'sample') {
                        $(data.sub.accessions.accessions['sample']).each(function (count, smp) {
                            li2 = jQuery('<li/>', {
                                html: '<span title="Biosample Accession: ' + smp.biosample_accession + '">' + smp.sample_accession + ' - <small>' + smp.sample_alias + '</small></span>'
                            });
                            $(li2).appendTo(ul)
                        })
                    }
                    else {

                        li2 = jQuery('<li/>', {
                            html: data.sub.accessions.accessions[key].accession + ' - <small>' + data.sub.accessions.accessions[key].alias + '</small>'
                        });
                        $(li2).appendTo(ul)
                    }
                    $(ul).appendTo(panel_body);
                    $(panel_body).appendTo(collapse);
                    $(collapse).appendTo(panel);
                    $(panel).appendTo(panel_group)
                }
            }

            $(panel_group).appendTo('#file_accession_panel');
        }


        $('#status-panel').data('accessions_visible', true)
    })


}
