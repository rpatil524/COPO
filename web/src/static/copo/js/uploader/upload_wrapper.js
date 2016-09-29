//this function is called on when the file upload changes, and sets some option in the
//jquery file upload plugin. If the file is larger than chunk_threshold, it should be chunked
var upload_size = 0;
var chunk_size = 0;
var chunk_threshold = 200000000; // size of chunks in bytes

function get_chunk_size(event) {
    upload_size = event.currentTarget.files[0].size;
    if (upload_size < chunk_threshold) {
        chunk_size = 0;
        $(event.currentTarget).parent().parent().fileupload(
            'option',
            {
                maxChunkSize: 0,
                url: '/rest/receive_data_file/'
            }
        );
    }
    else {
        chunk_size = chunk_threshold;
        $(event.currentTarget).parent().parent().fileupload(
            'option',
            {
                maxChunkSize: chunk_threshold,
                url: '/rest/receive_data_file_chunked/'
            }
        );
    }
}


$(document).ready(function () {

    var u_id = undefined;
    var token = $.cookie('csrftoken');
    var f = $('#file_upload');
    $('input[name=upload_id]').val('');
    //this is the zip image being hidden
    $('.zip_image').hide();
    //hide the hashing image
    $('.hash_image').hide();
    //$('#input_md5_checksum').val('To Be Calculated...')
    //this is how many upload panels are on the screen
    $('#upload_info_count').val('0');

    $('#add_upload_group_button').hide();
    $('#select_file_type').change(function () {
        $('#file_type_guess').animate({opacity: "0"}, "fast")
    });

    $(function () {
        'use strict';
        //file upload plugin
        var s;
        $(document).on('click', 'form[id^=upload]', function () {

            $(this).fileupload({
                dataType: 'json',
                headers: {'X-CSRFToken': token},
                progressInterval: '300',
                bitrateInterval: '300',
                maxChunkSize: chunk_size,
                singleFileUploads: true,
                sequentialUploads: true,
                fail: function (e, data) {
                    alert('FAIL!!!')
                },
                done: function (e, data) {
                    var final = data.result.upload_id;
                    $(this).find('input[name=upload_id]').val('');
                    finalise_upload(e, data, final, this)
                },
                error: function (e, data) {
                    console.log($.makeArray(arguments));
                },
                start: function (e, data) {
                    $(this).parents().eq(2).find('.progress').show()
                },
                add: function (e, data) {
                    for (var k = 0; k < data.files.length; k++) {
                        var insert_node = $(this).parents().eq(2).find('.file_status_label');
                        var size = parseFloat(data.files[k].size);
                        size = size / 1000000.0;
                        size = size.toFixed(2) + ' MB';
                        var file_name = data.files[k].name.substr(0, data.files[k].name.indexOf('.'));
                        $('#upload_files_button').attr('disabled', 'disabled');
                        $('<div/>').addClass('alert alert-warning file_info').attr('id', 'id_' + file_name).html("<strong>" + file_name + "</strong>").appendTo(insert_node);

                        var html = '<div id="progress_info_' + file_name + '" class="progress_info">' +
                            '<input type="hidden" id="upload_id_' + file_name + '" value="" />' +
                            '<span id="progress_label"></span>' +
                            '<span id="total_label"> of ' + size + '</span>' +
                            '<span id="bitrate"></span>' +
                            '</div>' +
                            '<div id="progress_' + file_name + '" class="progress">' +
                            '<div style="width: 0%;height: 20px;background: green" class="bar"></div>' +
                            '<div class="progress-bar progress-bar-success"></div>' +
                            '</div>';

                        $(html).appendTo(insert_node);
                    }
                    data.submit();
                },
                progress: function (e, data) {
                    //get name of the file for which the progress update is for
                    var file_name = data.files[0].name;
                    file_name = file_name.substr(0, file_name.indexOf('.'));
                    //increment progress bar
                    var progress = parseInt(data.loaded / data.total * 100, 10);
                    var selector = '#progress_' + file_name;
                    $(selector + ' .bar').css(
                        'width',
                        progress + '%'
                    );
                    //display uploaded bytes
                    var uploaded = parseFloat(data.loaded) / 1000000.0;
                    s = uploaded.toFixed(2) + " MB of";
                    $('#progress_info_' + file_name).children('#progress_label').html(s);
                    //display upload bitrate
                    var bit = " @ " + (data.bitrate / 1000.0 / 1000.0 / 8).toFixed(2) + " MB/sec";
                    $('#progress_info_' + file_name).children('#bitrate').html(bit)
                }
            }).on('fileuploadchunkdone', function (e, data) {
                var file_name = data.files[0].name.substr(0, data.files[0].name.indexOf('.'));
                //console.log(data)
                $(this).find('input[name=upload_id]').val(data.result.upload_id);
                console.log($(this).fileupload('active'))

            }).bind('fileuploadchange', function (e, data) {


            })
        })
    });


    //function called to finalised chunked upload
    function finalise_upload(e, data, final, tform) {
        //serialise form
        form = $(tform).serializeFormJSON();
        panel_id = $(tform).attr('id');
        panel_id = panel_id.split('_')[1];
        token = $.cookie('csrftoken');
        var output;
        if (chunk_size > 0) {
            //if we have a chunked upload, call the complete view method in web
            $.ajax({
                headers: {'X-CSRFToken': token},
                url: "/rest/complete_upload/",
                type: "POST",
                data: {'upload_id': final, 'panel_id': panel_id},
                success: function (data) {
                    update_html(data, tform)
                },
                error: function () {
                    alert('error');
                    console.log($.makeArray(arguments));
                },
                dataType: 'json'
            })
        }
        else {
            //if we have a non chunked upload, just call the update_html method
            update_html(data, tform)
        }

    }

    //update the html based on the results of the upload process
    function update_html(data, tform) {
        var x;
        if (chunk_size > 0) {
            x = $(data.files)
        }
        else {
            x = $(data.result.files)
        }

        var zipping_img = $('#zipping_image').val();
        var hashing_img = $('#hashing_image').val();
        for (var i = 0; i < x.size(); i++) {
            var file_name = x[i].name;
            file_name = file_name.substr(0, file_name.indexOf('.'));
            $('#progress_' + file_name).remove();
            $('#progress_info_' + file_name).remove();
            $('#id_' + file_name).remove();
            div = $('<div/>');
            var html = "<a href='#' class='close' data-dismiss='alert' aria-label='close'>&times;</a>";
            html += "<div class='row'><div class='col-sm-9 col-md-9 col-lg-9'>"
                + "<input name='file_id' type='hidden' value='" + x[i].id + "'/> <ul class='list-inline'><li><strong>" + x[i].name + "</strong></li><li class='file_size'>" + x[i].size.toFixed(1) + " MB</li></ul>"
                + "</div><div class='col-sm-3 col-md-3 col-lg-3'>"
                + '<span class="text-right zip-image"><img src="' + zipping_img + '" height="20px" class="pull-right"/>'
                + '<h4 style="margin-right:30px">Zipping</h4></span>'
                + '<span class="text-right hash-image"><img src="' + hashing_img + '" height="20px" class="pull-right"/>'
                + '<h4 style="margin-right:30px">Hashing</h4></span></div></div>';
            insert_node = $(tform).parents().eq(2).find('.file_status_label');
            div.addClass('alert alert-success file_info').html(html).insertBefore(insert_node).fadeIn();
            div.find('.zip-image').hide();
            div.find('.hash-image').hide()
        }

        if ($.active < 2) {

            $('#upload_files_button').removeAttr('disabled')
        }

        //now call function to inspect files
        inspect_uploaded_files(x[0].id, tform)
    }


    function inspect_uploaded_files(file_id, tform) {
        //this function calls the server to ask it to inspect the files just uploaded and provide
        //the front end with any information to autocomplete the input form

        //var finished = $('.alert-success')
        //var file_id = $(finished[finished.length-1]).children('input').val()
        type_warning = $('input[value=' + file_id + ']').parents().eq(5).find('.file_type_warning');
        file_type = $('input[value=' + file_id + ']').parents().eq(5).find('select[name=select_file_type]');

        //etuka start
        var ena_collection_id = $("#ena_collection_id").val();
        var studyId = $("#study_id").val();
        //etuka stop


        $.ajax({
            url: '/rest/inspect_file/',
            type: 'GET',
            dataType: 'json',
            data: {
                'file_id': file_id,
                'ena_collection_id': ena_collection_id,
                'study_id': studyId
            }
        }).done(function (data) {
            /*etuka begin*/
            // Add an exception to NOT do gzip and hash as this takes up user's time; should be done in the background
            $("#study_data_table_div").html(data.data_file_html);
            $('#uploaded_file_id').val(file_id).trigger('change');

            return false;
            /*etuka end*/

            //now search through list of filetypes in dropdown
            //and make correct type selected
            $(file_type).children().removeAttr('selected').each(function (index, val) {
                if ($(val).val() == data.file_type) {
                    $(val).prop('selected', 'selected')
                }
            });
            if (data.file_type != 'unknown' && type_warning.children().length == 0) {
                var warning_label = "<h4><small> We think your file is a </small>" +
                    data.file_type + "<small> file. If this is incorrect please change accordingly.</small></h4><br/>";

                $(type_warning).append(warning_label).fadeIn('fast')
            }

            //check if the file was gzipped, and if not send request to server to gzip
            if (data.file_type == 'fastq' && data.gzip == false) {
                $("input[value='" + file_id + "']").parent().next().children('.zip-image').fadeIn('4000');
                $.ajax({
                    url: '/rest/zip_file/',
                    type: 'GET',
                    dataType: 'json',
                    data: {'file_id': file_id},
                    success: function (data) {
                        $("input[value='" + file_id + "']").parent().next().children('.zip-image').fadeOut('4000');
                        //now change the file name and file size in the alert div
                        var new_name = data.file_name;
                        var new_size = data.file_size;
                        var node = $('input[value=' + file_id + ']');
                        $(node).next().find('strong').html(new_name);
                        $(node).next().find('.file_size').html(new_size + ' MB');
                        get_hash(file_id, tform)
                    },
                    error: function (data) {
                        console.log(data)
                    }
                })
            }
            else {
                get_hash(file_id, tform)
            }
        })
    }

});

function get_hash(id, tform) {
    $("input[value='" + id + "']").parent().next().children('.hash-image').show();
    $.ajax({
        url: "/rest/hash_upload/",
        type: "GET",
        data: {file_id: id},
        dataType: 'text'
    }).done(function (data) {
        //now find the correct div and append the hash to it
        var obj = jQuery.parseJSON(data);
        $d = $("input[value='" + obj.file_id + "']").parent();
        html = '<h5><span class="hash_span label label-success">' + obj.output_hash + '</span></h5>';
        $d.children('ul').append(html);
        $("input[value='" + id + "']").parent().next().children('.hash-image').hide();
        //now finalise group update box heading and close panel if necessary
        finalise_group(id, tform)
    })

}

function finalise_group(file_id, tform) {
    //if this is the last upload
    if ($(tform).fileupload('active') < 1) {
        var total = 0;
        var file_type = '';
        var ext = '';
        //get all the input success alerts
        $('input[value=' + file_id + ']').parents().eq(3).children('.alert-success').each(function (i, value) {
            //iterate over them counting the sizes of their files
            var f_name = $(value).parent().find('strong').html();
            if (i == 0) {
                file_type = f_name.split('.').pop()
            }
            else {
                f_ext = f_name.split('.').pop();
                if (file_type != f_ext) {
                    file_type = 'Mixed'
                }
            }
            total = total + parseFloat($(value).find('li[class=file_size]').text().replace(' MB', ''));
            //console.log(parseFloat($(value).find('li[class=file_size]').text().replace(' MB', '')))

        });
        //$('input[value=' + file_id + ']').parents().eq(6).find('.panel-title').html(file_type + ' Files Group - ' + total + ' MB')
        //$('input[value=' + file_id + ']').parents().eq(5).css('display', 'none')
    }
}
/*
 get_upload_box_html()

 this code is to calculate an md5 checksum on the client side, but is very slow
 document.getElementById("file_upload").addEventListener("change", function() {
 var blobSlice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice,
 file = this.files[0],
 chunkSize = 2097152,                               // read in chunks of 2MB
 chunks = Math.ceil(file.size / chunkSize),
 currentChunk = 0,
 spark = new SparkMD5.ArrayBuffer(),
 frOnload = function(e) {
 console.log("read chunk nr", currentChunk + 1, "of", chunks);
 spark.append(e.target.result);                 // append array buffer
 currentChunk++;

 if (currentChunk < chunks) {
 loadNext();
 }
 else {
 console.log("finished loading");
 console.info("computed hash", spark.end()); // compute hash
 $('#md5').val(spark.end())
 }
 },
 frOnerror = function () {
 console.warn("oops, something went wrong.");
 };

 function loadNext() {
 var fileReader = new FileReader();
 fileReader.onload = frOnload;
 fileReader.onerror = frOnerror;

 var start = currentChunk * chunkSize,
 end = ((start + chunkSize) >= file.size) ? file.size : start + chunkSize;

 fileReader.readAsArrayBuffer(blobSlice.call(file, start, end));
 };

 loadNext();
 })
 */

