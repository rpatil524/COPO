//**some re-usable functions across different modules
var AnnotationEventAdded = false;
var selectizeObjects = Object(); //stores reference to selectize objects initialised on the page
var copoVisualsURL = "/copo/copo_visualize/";
var csrftoken = $.cookie('csrftoken');
var quickTourMessages = quick_tour_messages(); //holds quick tour messages
var quickTourArray = []; //holds quick tour elements
var quickTourFlag = true; //flag to decide whether or not to display quick tour

$(document).ready(function () {
    var componentName = $("#nav_component_name").val();

    setup_autocomplete()

    //set up copo-multi-search component lookup
    do_multi_search_lookup();

    //set up global navigation components
    do_page_controls(componentName);

    //global_help_call
    do_global_help(componentName);

    //context help event
    do_context_help_event();

    //input fields help tips event
    set_inputs_help();

    //add event for ontology field change
    ontology_value_change();

});

function setup_autocomplete() {
    var copoFormsURL = "/copo/copo_forms/";
    $(document).on('focus', 'input[id^="annotator-field"]', function (e) {
        t = e.currentTarget
        $('.annotator-listing').find('ul').empty()
        $(t).addClass('ontology-field')

        if (!AnnotationEventAdded) {
            $(t).attr('data-autocomplete', '/copo/ajax_search_ontology/999/')

            auto_complete();
            AnnotationEventAdded = true;
        }
    })
    auto_complete();
}

function ontology_value_change() {
    //handles 'change of mind by user while entering value to clear associated fields'
    $(document).on('keyup', '.ontology-field', function () {
        var elem = $(this);
        elem.closest(".ontology-parent").find(".ontology-field-hidden").each(function () {
            $(this).val('');
        });
    });
}


function do_component_delete_confirmation(params) {
    var targetComponentBody = "Please confirm delete action for the selected records.";
    var targetComponentTitle = "Delete Alert!";

    var doTidyClose = {
        closeIt: function (dialogRef) {
            dialogRef.close();
        }
    };

    var code = BootstrapDialog.show({
        type: BootstrapDialog.TYPE_DANGER,
        title: $('<span>' + targetComponentTitle + '</span>'),
        message: function () {
            var $message = $('<span>' + targetComponentBody + '</span>');
            return $message;
        },
        draggable: true,
        closable: true,
        animate: true,
        onhide: function () {
        },
        buttons: [{
            label: 'Cancel',
            action: function (dialogRef) {
                doTidyClose["closeIt"](dialogRef);
            }
        },
            {
                icon: 'glyphicon glyphicon-trash',
                label: 'Delete',
                cssClass: 'btn-danger',
                action: function (dialogRef) {

                    csrftoken = $.cookie('csrftoken');
                    var target_ids = JSON.stringify(params.target_ids);

                    $.ajax({
                        url: copoFormsURL,
                        type: "POST",
                        headers: {
                            'X-CSRFToken': csrftoken
                        },
                        data: {
                            'task': "delete",
                            'component': params.component,
                            'target_ids': target_ids
                        },
                        success: function (data) {
                            do_render_table(data);
                        },
                        error: function () {
                            alert("Couldn't delete records!");
                        }
                    });

                    doTidyClose["closeIt"](dialogRef);

                }
            }
        ]
    });
}

function do_render_table(data) {
    var table = null;
    var lastRecord = null;
    var filterDivObject = null;
    var lengthDivObject = null;

    if ($.fn.dataTable.isDataTable('#' + data.table_data.table_id)) {
        //if table instance already exists, then this is probably a refresh after an CRUD operation
        table = $('#' + data.table_data.table_id).DataTable();
    }


    if (data.table_data.row_data) {
        //adding single record to table

        if (table) { //this test is probably redundant, but...you never can tell!
            //remove previously highlighted row
            table
                .rows('.row-insert-higlight')
                .nodes()
                .to$()
                .removeClass('row-insert-higlight');

            var rowNode = table
                .row.add(data.table_data.row_data)
                .draw()
                .node();

            //highlight new row
            $(rowNode)
                .addClass('row-insert-higlight')
                .animate({
                    color: 'black'
                });

            lastRecord = data.table_data.row_data;

        }
    } else {
        //probably first time rendering table, or maybe a call to refresh whole table, say after a delete action

        if (table) { //definitely a call to refresh table, as table instance exists!
            table.clear().draw();
            table.rows.add(data.table_data.dataSet); // Add new data
            table.columns.adjust().draw();
            return;
        }


        //get default ordering index;
        //ideally we would want to order by record creation date.
        //if it exists, it should be the last but one item in the columns list
        var orderIndx = 0;
        if (data.table_data.columns.length > 2) {
            orderIndx = data.table_data.columns.length - 2;
        }

        //custom column rendering
        var colDefs = [];

        //button coldefs
        var btnDef = {
            targets: -1,
            data: null,
            searchable: false,
            orderable: false,
            render: function (rdata) {
                var rndHTML = "";
                if (data.table_data.action_buttons.row_btns) {
                    var bTns = data.table_data.action_buttons.row_btns; //row buttons
                    rndHTML = '<span style="white-space: nowrap;">';
                    for (var i = 0; i < bTns.length; ++i) {
                        rndHTML += '<a data-action-target="row" data-record-action="' +
                            bTns[i].btnAction + '" data-record-id="' +
                            rdata[rdata.length - 1] +
                            '" data-toggle="tooltip" data-container="body" style="display: inline-block; white-space: normal;" title="' +
                            bTns[i].text + '" class="' + bTns[i].className + ' btn-xs"><i class="' +
                            bTns[i].iconClass + '"> </i><span></span></a>&nbsp;';
                    }
                    rndHTML += '</span>';
                }
                return rndHTML;
            }
        };

        colDefs.push(btnDef);

        //determine how columns are rendered - cols definition
        var custDef;
        var v = [];
        for (var i = 0; i < data.table_data.columns.length - 1; ++i) {
            v.push(i);
        }

        //exception for datafile table, it treats the first column differently
        if (data.table_data.table_id == 'datafile_table') {
            v.splice(0, 1);
        }

        custDef = {
            targets: v,
            data: data,
            render: function (data, type, row, meta) {
                var rndHTML = "";
                if (Object.prototype.toString.call(data[meta.col]) === '[object String]') {
                    rndHTML = data[meta.col];
                } else if (typeof data[meta.col] === "object") {
                    var collapseLink = data[data.length - 1] + "_" + meta.col;
                    rndHTML = get_data_item_collapse(collapseLink, get_data_list_panel(data[meta.col], collapseLink), data[meta.col].length);
                }

                return rndHTML;
            }
        };

        colDefs.push(custDef);


        //end cols definition

        //column def for datafile table
        if (data.table_data.table_id == 'datafile_table') {
            colDefs.push({
                targets: 0,
                data: null,
                render: function (rdata) {
                    var containerRow = $('<div/>', {
                        class: "row",
                        style: "margin-left:-10px; white-space: nowrap; margin-right: 5px;"
                    });

                    var metadataDiv = $('<div></div>')
                        .attr({
                            "class": "col-sm-1 col-md-1 col-lg-1 itemMetadata-flag",
                            "data-record-id": rdata[rdata.length - 1],
                            "style": "cursor: hand; cursor: pointer; display: inline-block;"
                        });

                    var spanPoor = $('<span/>', {
                        class: "itemMetadata-flag-ind meta-active poor",
                        style: "margin-top: 3px;"
                    });

                    var spanFair = $('<span/>', {
                        class: "itemMetadata-flag-ind fair"
                    });

                    var spanGood = $('<span/>', {
                        class: "itemMetadata-flag-ind good"
                    });

                    metadataDiv.append(spanPoor).append(spanFair).append(spanGood);

                    var dataDiv = $('<div></div>')
                        .attr({
                            "class": "col-sm-11 col-md-11 col-lg-11",
                            "style": "margin-left: -10px; margin-top: 10px; display: inline-block;"
                        });

                    var dataSpan = $('<span/>', {
                        html: rdata[0]
                    });

                    var descFlagSpan = $('<i></i>')
                        .attr({
                            "class": "fa fa-tags inDescription-flag",
                            "data-record-id": rdata[rdata.length - 1],
                            "data-toggle": "tooltip",
                            "style": "padding-left: 5px; display: none;",
                            "title": "Currently being described"
                        });

                    dataDiv.append(dataSpan).append(descFlagSpan);
                    containerRow.append(metadataDiv).append(dataDiv);

                    return $('<div></div>').append(containerRow).html();

                }
            });
        }

        var scrollX = true;

        if (data.table_data.table_id == "datafile_table") {
            //scroll has undesirable effect on this table
            scrollX = false;
        }

        table = $('#' + data.table_data.table_id).DataTable({
            data: data.table_data.dataSet,
            columns: data.table_data.columns,

            paging: true,
            ordering: true,
            scrollX: scrollX,
            lengthChange: true,
            order: [
                [orderIndx, "desc"]
            ],
            select: {
                style: 'multi'
            },
            dom: 'lf<"row button-rw">rtip',
            "fnDrawCallback": function (oSettings) {
                refresh_tool_tips();

                $('.dataTables_filter').each(function () {
                    if ($(this).attr("id") == data.table_data.table_id + "_filter") {
                        filterDivObject = $(this);
                        return false;
                    }
                });

                $('.dataTables_length').each(function () {
                    if ($(this).attr("id") == data.table_data.table_id + "_length") {
                        lengthDivObject = $(this);
                        return false;
                    }
                });

                //trigger metadata refresh for datafiles
                if (data.table_data.table_id == 'datafile_table') {
                    var event = jQuery.Event("refreshmetadataevents");
                    $('body').trigger(event);
                }

            },
            columnDefs: colDefs
        });

        //attach global action buttons
        if (data.table_data.action_buttons.global_btns) {
            var custBtns = data.table_data.action_buttons.global_btns; //global buttons
            var actBtns = ['selectAll', 'selectNone'];
            var bTns = custBtns.concat(actBtns);
            new $.fn.dataTable.Buttons(table, {
                buttons: bTns
            });

            table
                .buttons()
                .nodes()
                .each(function (value) {
                    $(this).addClass(' btn-sm');
                });

            table
                .buttons('.copo-dt')
                .nodes()
                .each(function (value) {
                    var btnImage;
                    for (var i = 0; i < bTns.length; ++i) {
                        if (bTns[i].text == this.text) {
                            btnImage = bTns[i];
                            break;
                        }
                    }

                    $(this).removeClass('btn-default'); //remove default class
                    $(this).addClass(this.className); //attach supplied class
                    $(this).attr('data-record-action', btnImage.btnAction); //data attribute to signal action type
                    $(this).attr('data-action-target', 'rows'); //data attribute to signal batch action
                    $(this).attr('data-copo-tour-id', data.table_data.table_id + "_" + btnImage.btnAction); //quick tour component: table_id + action type
                    //
                    ////attach icon to button
                    try {
                        $('<i class="' + bTns[value].iconClass + '">&nbsp;</i>').prependTo($(this));
                    } catch (err) {
                    }

                });

            $("div.button-rw").append(filterDivObject);
            $("div.button-rw").append(lengthDivObject);
            $("div.button-rw").append($(table.buttons().container()));
            $(lengthDivObject).addClass("pad-it");


        }

        //create a hook for attaching button events in individual table handlers
        if ($.fn.dataTable.isDataTable('#' + data.table_data.table_id)) {
            var tableID = data.table_data.table_id;
            var event = jQuery.Event("addbuttonevents");
            event.tableID = tableID;
            $('body').trigger(event);
        }

    }


    //handle requests for specific tables...
    if (data.table_data.table_id == "datafile_table") {
        table = $('#' + data.table_data.table_id).DataTable();
        if (table && lastRecord) { //trigger event for queuing record
            var event = jQuery.Event("addtoqueue");
            event.recordLabel = lastRecord[0];
            event.recordID = lastRecord[lastRecord.length - 1];
            $('body').trigger(event);
        }
    }

} //end of function


function refresh_tool_tips() {
    $("[data-toggle='tooltip']").tooltip();
    $("[data-toggle='popover']").popover();


    apply_color();
    refresh_selectbox();
    refresh_multiselectbox();
    refresh_multisearch();

    refresh_range_slider();
    auto_complete();

    setup_datepicker();

} //end of func

function setup_datepicker() {
    $('.date-picker').datepicker({
        format: "dd/mm/yyyy"
    })
}

function refresh_validator(formObject) {
    formObject.validator('update');

} //end of func

function refresh_range_slider() {
    $('.range-slider').each(function () {
        var elem = $(this);

        var outputElem = elem.closest(".range-slider-parent").find(".range-slider-output");
        var elemValue = elem.closest(".range-slider-parent").find(".elem-value");

        elem.rangeslider({

            // Feature detection the default is `true`.
            // Set this to `false` if you want to use
            // the polyfill also in Browsers which support
            // the native <input type="range"> element.
            polyfill: false,

            // Default CSS classes
            rangeClass: 'rangeslider',
            disabledClass: 'rangeslider--disabled',
            horizontalClass: 'rangeslider--horizontal',
            verticalClass: 'rangeslider--vertical',
            fillClass: 'rangeslider__fill',
            handleClass: 'rangeslider__handle',

            // Callback function
            onInit: function () {
            },

            // Callback function
            onSlide: function (position, value) {
                outputElem.html(value);
            },

            // Callback function
            onSlideEnd: function (position, value) {
                outputElem.html(value);
                elemValue.val(value);
            }
        });
    });

} //end of function


//refreshes selectboxes to pick up events
function refresh_selectbox() {
    $('.copo-select').each(function () {
        var elem = $(this);

        if (!(/selectize/i.test(elem.attr('class')))) { // if not already instantiated
            var funSelect = elem.selectize({
                delimiter: ',',
                plugins: ['remove_button'],
                persist: false,
                create: function (input) {
                    return {
                        value: input,
                        text: input
                    }
                }
            });
        }
    });

} //end of function

function refresh_multiselectbox() {
    $('.copo-multi-select').each(function () {
        var elem = $(this);
        var valueElem = elem.closest('.copo-form-group').find('.copo-multi-values');
        var maxTems = 'null'; //maximum selectable items


        if (valueElem.is("[data-maxItems]")) {
            maxTems = valueElem.attr("data-maxItems");
        }

        if (!(/selectize/i.test(elem.attr('class')))) { // if not already instantiated
            var $funSelect = elem.selectize({
                onChange: function (value) {
                    if (value) {
                        valueElem.val(value)
                            .trigger('change');
                    } else {
                        valueElem.val("");
                    }
                },
                //dropdownParent: 'body',
                maxItems: maxTems,
                plugins: ['remove_button']
            });

            //set default values
            var control = $funSelect[0].selectize;
            control.setValue(valueElem.val().split(",")); //set default value
        }
    });
}


function refresh_multisearch() {
    $('.copo-multi-search').each(function () {
        var elem = $(this);

        if (!(/selectize/i.test(elem.attr('class')))) { // if not already instantiated
            var valueElem = elem.closest('.copo-form-group').find('.copo-multi-values');
            var elemSpecs = JSON.parse(elem.closest('.copo-form-group').find('.elem-json').val());
            var maxTems = 'null'; //maximum selectable items

            if (valueElem.is("[data-maxItems]")) {
                maxTems = valueElem.attr("data-maxItems");
            }

            var $funSelect = elem.selectize({
                onChange: function (value) {
                    if (value) {
                        valueElem.val(value)
                            .trigger('change');
                    } else {
                        valueElem.val("");
                    }
                },
                // dropdownParent: 'body',
                maxItems: maxTems,
                persist: true,
                create: false,
                plugins: ['remove_button'],
                valueField: elemSpecs.value_field,
                labelField: elemSpecs.label_field,
                searchField: elemSpecs.search_field,
                options: elemSpecs.options,
                render: {
                    item: function (item, escape) {
                        return '<div>' +
                            (item[elemSpecs.label_field] ? '<span>' +
                                escape(item[elemSpecs.label_field]) + '</span>' : '') +
                            '</div>';
                    },
                    option: function (item, escape) {
                        var label = ''; // item[elemSpecs.label_field];
                        var caption = '<div>';
                        for (var i = 0; i < elemSpecs.secondary_label_field.length; ++i) {
                            caption += '<div class="text-primary">' + item[elemSpecs.secondary_label_field[i]] + '</div>';
                        }
                        caption += "</div>";

                        return '<div>' +
                            '<span class="caption">' + escape(label) + '</span>' +
                            (caption ? '<div class="caption">' + caption + '</div>' : '') +
                            '</div>';
                    }
                }
            });


            var control = $funSelect[0].selectize;
            control.setValue(valueElem.val().split(",")); //set default value

            //retain reference to control for any future reference
            selectizeObjects[valueElem.attr("id")] = control;
        }

    });
}


var auto_complete = function () {

    // remove all previous autocomplete divs
    $('.autocomplete').remove()
    AutoComplete({
        EmptyMessage: "No Annotations Found",
        Url: $("#elastic_search_ajax").val(),
        _Select: do_select,
        _Render: do_post,
        _Position: do_position,
        _Pre: do_pre,
    }, '.ontology-field')

    function do_pre(){
        // make loading spinner visible before request to OLS
        $(this.Input).siblings(".input-group-addon").css("visibility", "visible")
        // we can also make changes to the value sent OLS here if needs be
        return this.Input.value;
    }

    function do_select(item) {
        if ($(document).data('annotator_type') == 'txt') {
            $('#annotator-field-0').val($(item).data('annotation_value') + ' :-: ' + $(item).data('term_accession'));
        } else if ($(document).data('annotator_type') == 'ss') {
            // this function defined in copo_annotations.js
            append_to_annotation_list(item)
        } else {
            $(this.Input).val($(item).data('annotation_value'));
            $(this.Input).closest(".ontology-parent").find("[id*='termSource']").val($(item).data('term_source'));
            $(this.Input).closest(".ontology-parent").find("[id*='termAccession']").val($(item).data('term_accession'));
        }

    }

    function do_position(a, b, c) {

    }


    function do_post(response) {
        response = JSON.parse(response);

        console.log("num_found " + response.response.numFound);
        var properties = Object.getOwnPropertyNames(response);
        //Try parse like JSON data

        var empty,
            length = response.length,
            li = document.createElement("li"),
            ul = document.createElement("ul");


        for (var item in response.response.docs) {

            doc = response.response.docs[item];


            try {
                //
                //console.log(response.highlighting[doc.id])
                //console.log(doc)
                var s;
                s = response.highlighting[doc.id].label_autosuggest[0];
                if (s == undefined) {
                    s = response.highlighting[doc.id].synonym
                }
                var short_form;
                var desc = doc.description
                if (desc == undefined) {
                    desc = "Description Not Available"
                }
                if (doc.ontology_prefix == undefined) {
                    short_form = "Origin Unknown"
                } else {
                    short_form = doc.ontology_prefix
                }
                li.innerHTML = '<span title="' + doc.iri + " - " + desc + '" class="ontology-label label label-info"><span class="ontology-label-text"><img src="/static/copo/img/ontology.png"/>' + doc.ontology_prefix + ' : ' + s + ' ' + '</span>' + ' - ' + '<span class="ontology-description">' + desc + '</span></span>';


                $(li).attr('data-id', doc.id);
                var styles = {
                    margin: "2px",
                    marginTop: '4px',
                    fontSize: "large",

                };
                $(li).css(styles);
                $(li).attr('data-term_accession', doc.iri);

                $(li).attr('data-annotation_value', doc.label);

                $(li).attr('data-term_source', short_form);
                //$(li).attr("data-autocomplete-value", response.highlighting[item].label_autosuggest[0].replace('<b>', '').replace('</b>', '') + ' - ' + item);

                //console.log($(li).data('label'))

                ul.appendChild(li);
                li = document.createElement("li");
            } catch (err) {
                console.log(err);
                li = document.createElement("li");
            }
        }
        $(this.DOMResults).empty()
        this.DOMResults.append(ul)
        $(this.Input).siblings(".input-group-addon").css("visibility", "hidden")
    }

} //end of function

function isInArray(value, array) {
    //checks if a value is in array
    return array.indexOf(value) > -1;
}

function get_attributes_outer_div() {
    //used in rendering table information

    var ctrlsDiv = $('<div/>', {
        class: "copo-component-attributes-outer"
    });

    return ctrlsDiv.clone();
}


function get_attributes_inner_div() {
    //used in rendering table information

    var ctrlSpan = $('<span/>', {
        class: "copo-component-attributes-inner"
    });

    return ctrlSpan.clone();
}

function get_attributes_inner_div_1() {
    //used in rendering table information

    var ctrlSpan = $('<span/>', {
        class: "copo-component-attributes-inner-0"
    });

    return ctrlSpan.clone();
}


function get_data_list_panel(itemData, link) {
    if (!itemData) {
        return "";
    }

    var containerFuild = $('<div/>', {
        class: "container-fluid",
    });

    var containerRow = $('<div/>', {
        class: "row",
        style: "padding:1px;"
    });

    var containerColumn = $('<div/>', {
        class: "col-sm-12 col-md-12 col-lg-12",
        style: "padding:1px;"
    });

    var mainMenuDiv = $('<div/>', {
        id: "mainMenu_" + link,
    });

    var listGroupPanel = $('<div/>', {
        class: "list-group panel",
        style: "margin-bottom: 0px; border: 0 solid transparent;"
    });

    var topLevelLink = $('<a></a>')
        .attr({
            "href": "#demo3",
            "class": "list-group-item",
            "data-toggle": "collapse",
            "data-parent": "#MainMenu",
            "style": "background: #ebf0fa;"
        });


    var topLevelDiv = $('<div/>', {
        class: "collapse"
    });


    var subMenuLink = $('<a/>', {
        href: "#",
        class: "list-group-item",
        click: function (event) {
            event.preventDefault();
            return false;
        }
    });


    if (Object.prototype.toString.call(itemData) === '[object Array]') {
        $.each(itemData, function (key, val) {
            if (Object.prototype.toString.call(val) === '[object String]') {
                var ctrlElem = subMenuLink.clone();
                ctrlElem.html(val);
                listGroupPanel.append(ctrlElem);
            } else if (Object.prototype.toString.call(val) === '[object Array]') {
                var ctrlElemLink = topLevelLink.clone();
                ctrlElemLink.attr("href", "#rec_" + link + "_" + key);
                ctrlElemLink.html('<span>Item ' + (key + 1) + '</span><i class="fa fa-caret-down pull-right"></i>');

                listGroupPanel.append(ctrlElemLink);

                var ctrlElemDiv = topLevelDiv.clone();
                ctrlElemDiv.attr("id", "rec_" + link + "_" + key);
                ctrlElemDiv.attr("class", "collapse");

                $.each(val, function (key2, val2) {
                    var spl = [];
                    var displayedValue = "";
                    var ctrlElemSubLink = subMenuLink.clone();
                    if (Object.prototype.toString.call(val2) === '[object String]') {
                        displayedValue = val2;
                    } else if (Object.prototype.toString.call(val2) === '[object Array]') {
                        $.each(val2, function (key22, val22) {
                            spl.push(val22);
                        });
                        displayedValue = spl.join("<br/>");

                        if (key2 == 0) {
                            ctrlElemLink.find("span").html(displayedValue);
                            displayedValue = "";
                        }
                    } else if (Object.prototype.toString.call(val2) === '[object Object]') {
                        Object.keys(val2).forEach(function (k2) {
                            spl.push(k2 + ": " + val2[k2]);
                        });

                        displayedValue = spl.join("<br/>");

                        if (key2 == 0) {
                            ctrlElemLink.find("span").html(displayedValue);
                            displayedValue = "";
                        }
                    }

                    if (displayedValue) {
                        ctrlElemSubLink.html(displayedValue);
                        ctrlElemDiv.append(ctrlElemSubLink);
                    }

                });


                listGroupPanel.append(ctrlElemDiv);

            } else if (Object.prototype.toString.call(val) === '[object Object]') {
            }
        });

    } else if (Object.prototype.toString.call(itemData) === '[object Object]') {
        //not an array-type object
        $.each(itemData, function (key, val) {
            var ctrlElem = subMenuLink.clone();
            ctrlElem.html(key + ": " + val);

            listGroupPanel.append(ctrlElem);
        });
    }


    containerColumn.append(mainMenuDiv.append(listGroupPanel));
    containerRow.append(containerColumn);
    containerFuild.append(containerRow);


    return $('<div/>').append(containerFuild).html();
}


function deconvulate_column_data(itemData, link) {
    if (!itemData) {
        return "";
    }

    if (Object.prototype.toString.call(itemData) === '[object String]') {
        return itemData;
    }

    var resolvedDiv = $('<table/>');

    var itemData = [itemData];

    itemData.forEach(function (entry) {
        var iRow = $('<tr/>').css("background-color", "transparent");

        resolvedDiv.append(iRow);

        var labelCol = $('<td/>');

        var valueCol = $('<td/>');

        iRow.append('');
        iRow.append(valueCol);

        // labelCol.append(entry.title);

        var valueNode = [];
        if (Object.prototype.toString.call(entry) === '[object String]') {
            valueNode.push(entry);
        } else if (Object.prototype.toString.call(entry) === '[object Array]') {
            entry.forEach(function (item) {
                if (Object.prototype.toString.call(item) === '[object String]') {
                    valueNode.push(item);
                } else {
                    var valueNode_sub = [];
                    item.forEach(function (item_sub) {
                        if (Object.prototype.toString.call(item_sub) === '[object String]') {
                            valueNode.push(item_sub);
                        } else if (Object.prototype.toString.call(item_sub) === '[object Object]') {
                            $.each(item_sub, function (key, val) {
                                valueNode_sub.push(format_camel_case(key) + ":  " + val);
                            });
                        }
                    });

                    if (valueNode_sub.length > 0) {
                        valueNode.push(valueNode_sub.join("<br/>"));
                    }
                }

            });
        }

        var breakr = $('<div/>', {
            style: "border-top: 1px solid rgba(34, 36, 38, 0.1);"
        });

        if (valueNode.length > 1) {
            valueCol.append(valueNode[0]);
            for (var i = 1; i < valueNode.length; ++i) {
                valueCol.append(breakr.clone().append(valueNode[i]));
            }
        } else {
            valueCol.append(valueNode.join("<br/>"));
        }
    });

    return resolvedDiv;
}

function get_data_item_collapse(link, itemData, itemCount) {
    // create badge
    var badgeSpan = $('<span/>', {
        class: "badge",
        style: "background: #fff;  border-radius: 5px; margin-left: 2px; margin-bottom: 1px;",
        html: itemCount
    });

    //create button
    var itemsLanguage = "items";
    if (itemCount == 1) {
        itemsLanguage = "item";
    }
    var collapseBtn = $('<a></a>')
        .attr({
            "class": "btn btn-xs btn-info",
            "data-toggle": "collapse",
            "data-target": "#" + link,
            "style": "margin-left:1px; margin-bottom:0px; border-radius:0; background-image:none; border-color:transparent; ",
            "type": "button",
        })
        .html($('<div/>').append(badgeSpan).html() + '<span style="margin-left: 2px; margin-bottom:0px;"> ' + itemsLanguage + '</span>');

    var collapseDiv = $('<div>', {
        id: link,
        class: "collapse",
        html: itemData
    });

    var ctrlDiv = $('<div/>')
        .append(collapseBtn)
        .append(collapseDiv);


    return ctrlDiv.html();
}

function format_camel_case(xter) {
    var a = xter
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, function (str) {
            return str.toUpperCase();
        });


    var refinedXter = a.trim().split(/\s+/g);

    for (var i = 1; i < refinedXter.length; ++i) {
        var str = refinedXter[i];
        str = str.toLowerCase().replace(/\b[a-z]/g, function (letter) {
            return letter.toLowerCase();
        });

        refinedXter[i] = str;
    }

    return refinedXter.join(' ');

}

function build_description_display(data) {
    //this is a specialised counterpart to the function 'build_attributes_display()',
    // but handles datafile description metadata

    var resolvedTable = $('<table/>');

    for (var j = 0; j < data.description.length; ++j) {
        var Ddata = data.description[j];

        var i = 0; //need to change this to reflect stage index...actually suppressing that on purpose for now

        var iRow = $('<tr/>');

        var labelCol = $('<td/>').attr('colspan', 2).append(Ddata.title);
        iRow.append(labelCol);

        var valueCol = $('<div/>');
        labelCol.append(valueCol);

        for (var k = 0; k < Ddata.data.length; ++k) {
            var Mdata = Ddata.data[k];

            var mDataDiv = $('<tr/>', {
                //class: "row"
            });

            var mDataDivLabel = $('<td/>', {
                //class: "col-sm-5 col-md-5 col-lg-5",
                html: Mdata.label
            });

            var mDataDivData = $('<td/>', {
                //class: "col-sm-7 col-md-7 col-lg-7",
            });

            mDataDiv.append(mDataDivLabel).append(mDataDivData);

            var displayedValue = "";

            if (Object.prototype.toString.call(Mdata.data) === '[object Array]') {
                Mdata.data.forEach(function (vv) {
                    displayedValue += "<div>" + vv + "</div>";
                });
            } else if (Object.prototype.toString.call(Mdata.data) === '[object String]') {
                displayedValue = String(Mdata.data);
            }

            mDataDivData.append(displayedValue);

            valueCol.append(mDataDiv);
        }

        resolvedTable.append(iRow);
    }

    return resolvedTable;
}

function build_attributes_display(data) {
    var resolvedTable = $('<table/>');

    data.component_attributes.forEach(function (entry) {
        var iRow = $('<tr/>');

        resolvedTable.append(iRow);

        var labelCol = $('<td/>');

        var valueCol = $('<td/>');

        iRow.append(labelCol);
        iRow.append(valueCol);

        labelCol.append(entry.title);

        var valueNode = [];
        if (Object.prototype.toString.call(entry.data) === '[object String]') {
            valueNode.push(entry.data);
        } else if (Object.prototype.toString.call(entry.data) === '[object Array]') {
            entry.data.forEach(function (item) {
                var valueNode_sub = [];
                item.forEach(function (item_sub) {
                    if (Object.prototype.toString.call(item_sub) === '[object String]') {
                        valueNode.push(item_sub);
                    } else if (Object.prototype.toString.call(item_sub) === '[object Object]') {
                        $.each(item_sub, function (key, val) {
                            valueNode_sub.push(format_camel_case(key) + ":  " + val);
                        });
                    }
                });

                if (valueNode_sub.length > 0) {
                    valueNode.push(valueNode_sub.join("<br/>"));
                }
            });
        }


        var breakr = $('<div/>', {
            style: "border-top: 1px solid rgba(34, 36, 38, 0.1);"
        });

        if (valueNode.length > 1) {
            valueCol.append(valueNode[0]);
            for (var i = 1; i < valueNode.length; ++i) {
                valueCol.append(breakr.clone().append(valueNode[i]));
            }
        } else {
            valueCol.append(valueNode.join("<br/>"));
        }
    });

    return resolvedTable;
}

function get_collapsible_panel(panelType) {
    if (!panelType) {
        panelType = 'default'
    }

    var panelGroup = $('<div/>', {
        class: "panel-group",
    });

    var panelClass = "panel panel-" + panelType;
    var panel = $('<div/>', {
        class: panelClass,
    });

    var panelHeading = $('<div/>', {
        class: "panel-heading",
    });

    var panelTitle = $('<div/>', {
        class: "panel-title"
    });

    var panelTitleAnchor = $('<a/>', {
        "data-toggle": "collapse"
    });

    panelTitle.append(panelTitleAnchor);
    panelHeading.append(panelTitle);

    panel.append(panelHeading);

    var panelCollapse = $('<div/>', {
        class: "panel-collapse collapse",
    });


    var panelBody = $('<div/>', {
        class: "panel-body"
    });

    panelCollapse.append(panelBody);

    panel.append(panelCollapse);

    panelGroup.append(panel);

    return $('<div/>').append(panelGroup).clone();
}

function get_panel(panelType) {
    if (!panelType) {
        panelType = 'default'
    }

    var panelClass = "panel panel-" + panelType;
    var panel = $('<div/>', {
        class: panelClass,
    });

    var panelHeading = $('<div/>', {
        class: "panel-heading",
        style: "background-image: none;"
    });

    panel.append(panelHeading);


    var panelBody = $('<div/>', {
        class: "panel-body"
    });

    panel.append(panelBody);

    return $('<div/>').append(panel).clone();
}

// Set COPO frontpage properties in this dictionary
function get_component_meta(component) {
    var componentMeta = null;
    var components = get_profile_components();

    components.forEach(function (comp) {
        if (comp.component == component) {
            componentMeta = comp;
            return false;
        }
    });

    return componentMeta
}

function get_profile_components() {
    var componentProperties = [
        {
            component: 'profile',
            title: 'Work Profiles',
            buttons: ["quick-tour-template", "new-component-template"],
            sidebarPanels: ["copo-sidebar-info", "copo-sidebar-help"],
            tableID: 'copo_profiles_table',
            secondaryTableID: 'copo_shared_profiles_table',
            visibleColumns: 3,
            recordActions: ["add_record_all", "edit_record_single"] //specifies action buttons for records manipulation
        },
        {
            component: 'sample',
            title: 'Samples',
            iconClass: "fa fa-filter",
            semanticIcon: "filter", //semantic UI equivalence of fontawesome icon
            countsKey: "num_sample",
            buttons: ["quick-tour-template", "new-samples-template"],
            sidebarPanels: ["copo-sidebar-info", "copo-sidebar-help"],
            colorClass: "samples_color",
            color: "olive",
            tableID: 'sample_table',
            recordActions: ["describe_record_all", "edit_record_single"],
            visibleColumns: 3 //no of columns to be displayed, if tabular data is required. remaining columns will be displayed in a sub-table
        },
        {
            component: 'datafile',
            title: 'Datafiles',
            iconClass: "fa fa-database",
            semanticIcon: "database",
            countsKey: "num_data",
            colorClass: "data_color",
            color: "black",
            buttons: ["quick-tour-template"],
            sidebarPanels: ["copo-sidebar-info", "copo-sidebar-help"],
            tableID: 'datafile_table',
            recordActions: ["describe_record_multi", "undescribe_record_multi"],
            visibleColumns: 3
        },
        {
            component: 'submission',
            title: 'Submissions',
            iconClass: "fa fa-envelope",
            semanticIcon: "mail outline",
            countsKey: "num_submission",
            buttons: ["quick-tour-template"],
            sidebarPanels: ["copo-sidebar-info", "copo-sidebar-help"],
            colorClass: "submissions_color",
            color: "green",
            tableID: 'submission_table',
            recordActions: [],
            visibleColumns: 3
        },
        {
            component: 'publication',
            title: 'Publications',
            iconClass: "fa fa-paperclip",
            semanticIcon: "attach",
            countsKey: "num_pub",
            buttons: ["quick-tour-template", "new-component-template"],
            sidebarPanels: ["copo-sidebar-info", "copo-sidebar-help"],
            colorClass: "pubs_color",
            color: "orange",
            tableID: 'publication_table',
            recordActions: ["add_record_all", "edit_record_single", "delete_record_multi"],
            visibleColumns: 4
        },
        {
            component: 'person',
            title: 'People',
            iconClass: "fa fa-users",
            semanticIcon: "users",
            countsKey: "num_person",
            buttons: ["quick-tour-template", "new-component-template"],
            sidebarPanels: ["copo-sidebar-info", "copo-sidebar-help"],
            colorClass: "people_color",
            color: "red",
            tableID: 'person_table',
            recordActions: ["add_record_all", "edit_record_single", "delete_record_multi"],
            visibleColumns: 5
        },
        {
            component: 'annotation',
            title: 'Generic Annotations',
            iconClass: "fa fa-pencil",
            semanticIcon: "write",
            countsKey: "num_annotation",
            buttons: ["quick-tour-template", "new-component-template"],
            sidebarPanels: ["copo-sidebar-info", "copo-sidebar-help", "copo-sidebar-annotate"],
            colorClass: "annotations_color",
            color: "violet",
            tableID: 'annotation_table',
            recordActions: ["delete_record_multi"],
            visibleColumns: 10000
        }
    ];

    return componentProperties
}


//builds component-page navbar
function do_page_controls(componentName) {
    var component = null;
    var components = get_profile_components();

    components.forEach(function (comp) {
        if (comp.component == componentName) {
            component = comp;
            return false;
        }
    });

    if (component == null) {
        return false;
    }


    var pageHeaders = $(".copo-page-headers"); //page header/icons
    var pageIcons = $(".copo-page-icons"); //profile component icons
    var sideBar = $(".copo-sidebar"); //sidebar panels

    var PageTitle = $('<span/>', {
        class: "page-title-custom",
        style: "margin-right:10px;",
        html: component.title
    });

    pageHeaders.append(PageTitle);


    //create panels
    if (component.sidebarPanels) {
        var sidebarPanels = $(".copo-sidebar-templates").clone();
        var sidebarPanels2 = sidebarPanels.clone();
        sidebarPanels.find(".nav-tabs").html('');
        sidebarPanels.find(".tab-content").html('');
        $(".copo-sidebar-templates").remove();


        component.sidebarPanels.forEach(function (item) {
            sidebarPanels.find(".nav-tabs").append(sidebarPanels2.find(".nav-tabs").find("." + item));
            sidebarPanels.find(".tab-content").append(sidebarPanels2.find(".tab-content").find("." + item));
        });

        sideBar
            .append(sidebarPanels.find(".nav-tabs"))
            .append(sidebarPanels.find(".tab-content"));


    }

    //create buttons
    component.buttons.forEach(function (item) {
        if (component.buttons) {
            component.buttons.forEach(function (item) {
                pageHeaders.append($("." + item)).append("<span>&nbsp;</span>");
            });
        }
    });

    //...and profile component buttons
    if (componentName != "profile") {
        var pcomponentHTML = $(".pcomponents-icons-templates").clone().removeClass("pcomponents-icons-templates");
        var pcomponentAnchor = pcomponentHTML.find(".pcomponents-anchor").clone().removeClass("pcomponents-anchor");
        pcomponentHTML.find(".pcomponents-anchor").remove();

        pageIcons.append(pcomponentHTML);

        for (var i = 1; i < components.length; ++i) {
            var comp = components[i];
            if ((comp.component == componentName) || (comp.component == "profile")) {
                continue;
            }

            var newAnchor = pcomponentAnchor.clone();
            pcomponentHTML.append(newAnchor);

            newAnchor.attr("title", "Navigate to " + comp.title);
            newAnchor.attr("href", $("#" + comp.component + "_url").val());
            newAnchor.find("i")
                .addClass(comp.color)
                .addClass(comp.semanticIcon);
        }
    }

    //refresh components...
    quick_tour_event();
    refresh_tool_tips();

} //end of func

function refresh_webpop(elem, title, content, exrta_meta) {
    var config = {
        title: title,
        content: '<div class="webpop-content-div">' + content + '</div>',
        closeable: true,
        cache: false,
        width: 300,
        trigger: 'hover',
        arrow: false,
        animation: 'fade',
        placement: 'right',
        dismissible: false,
        onHide: function ($element) {
            WebuiPopovers.updateContent(elem, '<div class="webpop-content-div">' + content + '</div>');
            elem.removeClass("copo-form-control-focus");
        },
        onShow: function ($element) {
            elem.addClass("copo-form-control-focus");
        }
    };

    //refresh config with extra configurations
    $.each(exrta_meta, function (key, val) {
        config[key] = val;
    });

    elem.webuiPopover(config);
}

function toggle_display_help_tips(state, parentElement) {
    if (!state) {
        parentElement.find(".copo-form-group").webuiPopover('destroy');
        parentElement.find(".copo-form-group").attr("data-helptip", "no");
    } else {
        parentElement.find(".copo-form-group").attr("data-helptip", "yes");
    }
}

function do_multi_search_lookup() {
    //handle hover info for copo-select control types

    $(document).on("mouseenter", ".selectize-dropdown-content .active", function (event) {
        if ($(this).closest(".copo-multi-search").length) {
            var recordId = $(this).attr("data-value"); // the id of the hovered-on option
            var associatedComponent = ""; //the form control with which the event is associated

            //get the associated component
            var clss = $($(event.target)).closest(".input-copo").attr("class").split(" ");
            $.each(clss, function (key, val) {
                var cssSplit = val.split("copo-component-control-");
                if (cssSplit.length > 1) {
                    associatedComponent = cssSplit.slice(-1)[0];

                    resolve_element_view(recordId, associatedComponent, $($(event.target)).closest(".copo-form-group"));
                    return false;
                }
            });

        }
    });
}


function resolve_element_view(recordId, associatedComponent, eventTarget) {
    //maps form element by id to component type e.g source, sample

    if (associatedComponent == "") {
        return false;
    }

    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'task': "attributes_display",
            'component': associatedComponent,
            'target_id': recordId
        },
        success: function (data) {
            var gAttrib = Object();
            if (associatedComponent == "datafile") { //datafile component rendered differently
                gAttrib = build_description_display(data);
            } else {
                gAttrib = build_attributes_display(data);
            }
            var attribDiv = $('<div/>', {
                style: "max-height:300px; overflow-y: scroll;"
            });
            attribDiv.append(gAttrib);
            WebuiPopovers.updateContent(eventTarget, '<div class="webpop-content-div">' + $('<div/>').append(attribDiv).html() + '</div>');
        },
        error: function () {
            var message = "Couldn't retrieve attributes!";
            WebuiPopovers.updateContent(eventTarget, '<div class="webpop-content-div">' + message + '</div>');
        }
    });
}


function get_spinner_image() {
    var loaderObject = $('<div>', {
        style: 'text-align: center',
        html: "<span class='fa fa-spinner fa-pulse fa-3x'></span>"
    });

    return loaderObject.clone();
}

function sanitise_help_list(contextHelpList) {
    var dataSet = [];

    if (contextHelpList.properties) {
        var dtd = contextHelpList.properties;

        for (var i = 0; i < dtd.length; ++i) {
            var option = {};
            option["id"] = i + 1;
            option["title"] = dtd[i].title;
            option["content"] = dtd[i].content;
            option["context"] = dtd[i].context;
            var helpID = Math.random() + Math.random() + Math.random();
            helpID = helpID.toString();
            option["help_id"] = "context_help_" + i + "_" + helpID.replace(".", "_");
            dataSet.push(option);
        }
    }

    return dataSet;
}

function do_context_help(data) {
    //does current page request context help?
    var tableID = 'page-context-help';
    var helpComponent = $("#" + tableID);

    //if true then page requests context help control to be added
    if (!helpComponent.length) {
        return false;
    }


    var dtd = sanitise_help_list(data);

    //set data
    var table = null;


    if ($.fn.dataTable.isDataTable('#' + tableID)) {
        //if table instance already exists, then do refresh
        table = $('#' + tableID).DataTable();
    }

    if (table) {
        //clear old, set new data
        table
            .clear()
            .draw();
        table
            .rows
            .add(dtd);
        table
            .columns
            .adjust()
            .draw();
        table
            .search('')
            .columns()
            .search('')
            .draw();
    } else {
        table = $('#' + tableID).DataTable({
            data: dtd,
            searchHighlight: true,
            "lengthChange": false,
            order: [
                [0, "asc"]
            ],
            pageLength: 5,
            language: {
                "info": " _START_ to _END_ of _TOTAL_ topics",
                "lengthMenu": "_MENU_ tips",
                "search": " ",
            },
            columns: [
                {
                    "data": "id",
                    "visible": false
                },
                {
                    "orderable": false,
                    "width": "2%",
                    "data": null,
                    "render": function (data, type, row, meta) {
                        var iconSpan = '<span data-target="' + data.help_id + '" class="side-help-trigger" aria-hidden="true" title="View help content"></span>';

                        var parentDiv = $('<div></div>');
                        parentDiv.append(iconSpan);

                        return $('<div></div>').append(parentDiv).html();
                    }
                },
                {
                    "data": null,
                    "title": "Help Topics",
                    "render": function (data, type, row, meta) {
                        var helpTopicID = data.help_id;

                        var helpTitleDiv = $('<div></div>')
                            .attr("id", "title_" + helpTopicID)
                            .html('<div>' + data.title + '</div>');

                        var helpContentDiv = $('<div></div>')
                            .attr("id", helpTopicID)
                            .attr("class", "collapse context-help-collapse")
                            .css("margin-top", "10px")
                            .html('<div>' + data.content + '</div>');


                        return $('<div></div>').append(helpTitleDiv).append(helpContentDiv).html();
                    }
                },
                {
                    "data": "content",
                    "visible": false
                }
            ],
            dom: 'lft<"row">rip',
            "columnDefs": [{
                "orderData": 0,
            }]
        });
    }


    $('#' + tableID + '_wrapper')
        .find(".dataTables_filter")
        .find("input")
        .removeClass("input-sm")
        .attr("placeholder", "Search Help")
        .attr("size", 30);
}

function do_global_help(component) {
    //global help

    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'task': 'help_messages',
            'component': component
        },
        success: function (data) {

            //set quick tour message and trigger display event
            try {
                do_context_help(data.context_help);
                quickTourFlag = data.quick_tour_flag;

                if (quickTourFlag && data.user_has_email) {
                    $(".takeatour").trigger("click");
                }

            } catch (err) {
            }
        },
        error: function () {
            alert("Couldn't retrieve page help!");
        }
    });
}

function do_context_help_event() {
    //handles collapsing of help topics

    $(document).on('click', '.side-help-trigger', function (e) {
        var dataTargetID = $(this).attr('data-target');

        if ($(this).parent().hasClass("shown")) {
            $(this).parent().removeClass("shown");
            $("#" + dataTargetID).collapse("hide");
        } else {
            $(this).parent().addClass("shown");
            $("#" + dataTargetID).collapse("show");
        }
    });
}

function set_inputs_help() {
    $(document).on("focus", ".copo-form-group", function (event) {
        var elem = $(this);

        if (elem.attr("data-helptip") == "no") { //help turned off
            return false;
        }

        if (!(elem.find(".form-input-help").length)) {
            return false;
        }

        var title = elem.find("label").html();
        var content = elem.find(".form-input-help").html();

        elem.webuiPopover('destroy');

        elem.webuiPopover({
            title: title,
            content: '<div class="webpop-content-div">' + content + '</div>',
            trigger: 'sticky',
            width: 300,
            arrow: true,
            closeable: true,
            animation: 'fade',
            placement: 'right',
        });

    });

    $(document).on("blur", ".copo-form-group", function (event) {
        $(this).webuiPopover('destroy');
    });
}


function dialog_display(dialog, dTitle, dMessage, dType) {
    var dTypeObject = {
        "warning": '<div class="circular ui large basic red icon button"><i class="large icon remove"></i></div>',
        "danger": '<div class=" ui  basic red icon button"><i class=" icon remove"></i></div>',
        "info": "fa fa-exclamation-circle copo-icon-info"
    };

    var dTypeClass = "fa fa-exclamation-circle copo-icon-default";

    if (dTypeObject.hasOwnProperty(dType)) {
        dTypeClass = dTypeObject[dType];
    }

    var iconElement = $(dTypeClass);


    var messageDiv = $('<div/>', {
        html: dMessage
    });


    var $dialogContent = $('<div></div>');
    $dialogContent.append($('<div/>').append(iconElement));
    $dialogContent.append('<div class="copo-custom-modal-message">' + messageDiv.html() + '</div>');
    dialog.realize();
    dialog.setClosable(false);
    dialog.setSize(BootstrapDialog.SIZE_SMALL);
    dialog.getModalHeader().hide();
    dialog.setTitle(dTitle);
    dialog.setMessage($dialogContent);
    dialog.getModalBody().prepend('<div class="copo-custom-modal-title">' + dialog.getTitle() + '</div>');
    dialog.getModalBody().addClass('copo-custom-modal-body');
    //dialog.getModalContent().css('border', '4px solid rgba(255, 255, 255, 0.3)');
    dialog.open();
}

function update_quick_tour_flag() {
    WebuiPopovers.hideAll(); //hide all shown popovers

    $.ajax({
        url: copoVisualsURL,
        type: "POST",
        headers: {
            'X-CSRFToken': csrftoken
        },
        data: {
            'task': 'update_quick_tour_flag',
            'quick_tour_flag': false
        },
        success: function (data) {
            //set quick tour flag
            try {
                quickTourFlag = data.quick_tour_flag;
            } catch (err) {
            }
        },
        error: function () {
            alert("Couldn't update settings!");
        }
    });
}

function quick_tour_event() {
    $('.takeatour').on('click', function (e) {
        var dismissTour = '<a class="dismisstouralert pull-right" href="#" role="button" ' +
            'style="text-decoration: none; color:  #c93c00;" aria-haspopup="true" aria-expanded="false">' +
            '<i class="fa fa-times-circle " aria-hidden="true">' +
            '</i>&nbsp; Dismiss Tour</a>';

        var takeTour = '<a class="takeatouryes" href="#" role="button" ' +
            'style="text-decoration: none;" aria-haspopup="true" aria-expanded="false">' +
            '<i class="fa fa-lightbulb-o " style="color: #35637e;" aria-hidden="true">' +
            '</i>&nbsp; Take Tour</a>';


        var messageContent = 'Do you want to take a quick tour of the page? <br/><br/><span style="color: #35637e;">Please note that your screen will be dimmed, and regular page elements inaccessible in the quick tour mode.</span>' + '<hr/>' + takeTour + dismissTour;

        $(this).webuiPopover('destroy');

        $(this).webuiPopover({
            title: "Quick Tour",
            content: '<div class="webpop-content-div">' + messageContent + '</div>',
            trigger: 'sticky',
            width: 300,
            arrow: true,
            closeable: true,
            placement: 'bottom-right'
        });
    });

    $(document).on("click", ".takeatouryes", function (e) {
        quickTourArray = [];
        WebuiPopovers.hideAll(); //hide all shown popovers

        //retain quick tour elements with defined messages
        $('[data-copo-tour-id]').each(function () {
            if (quickTourMessages.hasOwnProperty($(this).attr("data-copo-tour-id"))) {
                if ($(this).is(":visible")) { //only consider elements that are visible on the DOM
                    quickTourArray.push($(this));
                }
            }
        });

        if (quickTourArray.length > 0) {
            quick_tour_select();
        }

    });

    $(document).on("click", ".quicktournext", function () {
        if (quickTourArray.length > 0) {
            quick_tour_select();
        }
    });

    $(document).on("click", ".endcopotour", function () {
        quickTourArray = [];
        WebuiPopovers.hideAll(); //hide all shown popovers
    });

    $(document).on("click", ".dismisstouralert", function () {
        update_quick_tour_flag();
    });
}

function quick_tour_select() {
    // display tour elements

    var item = quickTourArray[0];
    var itemMessage = quickTourMessages[item.attr("data-copo-tour-id")];

    var endTour = '<a class="endcopotour pull-right" href="#" role="button" ' +
        'style="text-decoration: none; color:  #c93c00;" aria-haspopup="true" aria-expanded="false">' +
        '<i class="fa fa-times-circle " aria-hidden="true">' +
        '</i>&nbsp; End Tour</a>';

    var nextTip = endTour;


    if (quickTourArray.length > 1) {
        nextTip = '<a class="quicktournext" href="#" role="button" ' +
            'style="text-decoration: none;" aria-haspopup="true" aria-expanded="false">' +
            '<i class="fa fa-lightbulb-o " style="color: #35637e;" aria-hidden="true">' +
            '</i>&nbsp; Next Tip</a>';

        nextTip += endTour;
    }

    var messageContent = itemMessage.content + '<hr/>' + nextTip;

    item.webuiPopover('destroy');
    item.webuiPopover({
        title: itemMessage.title,
        content: '<div class="webpop-content-div">' + messageContent + '</div>',
        trigger: 'sticky',
        width: 300,
        arrow: true,
        closeable: true,
        placement: 'auto-bottom',
        backdrop: true,
    });

    for (var i = 0; i < quickTourArray.length; i++) {
        if (quickTourArray[i].attr("data-copo-tour-id") === item.attr("data-copo-tour-id")) {
            quickTourArray.splice(i, 1);
            break;
        }
    }
} //end of func

function quick_tour_messages() {
    var qt = {
        "description": "Provides messages for creating quick tour of system components/elements:",
        "properties": {
            "new_profile_button": {
                "title": "Create New Profile",
                "content": "Click here to create a new Profile. A COPO Profile is a collection of 'research objects' or components that form part of a research project or study."
            },
            "documentation_button": {
                "title": "Documentation",
                "content": "Click here to access COPO's documentation."
            },
            "global_notification_button": {
                "title": "Notification Component",
                "content": "Click this button to view system notifications."
            },
            "global_user_authenticated_button": {
                "title": "Authenticated User",
                "content": "Click here to access the following tasks: <ul><li>View your ORCiD profile</li><li>View obtained tokens</li><li>Logout of the system</li></ul>"
            },
            "profile_links_button_group": {
                "title": "Profile Links",
                "content": "Shortcut buttons for accessing profile components."
            },
            "copo_data_upload_tab": {
                "title": "File Upload Tab",
                "content": "Select this tab to access the file upload view. <br/>For more information about this control, including a demonstration of its usage, please use the help component."
            },
            "copo_data_inspect_tab": {
                "title": "File Inspect Tab",
                "content": "Select this tab to view files uploaded to COPO. <br/>For more information about this control, including a demonstration of its usage, please use the help component."
            },
            "copo_data_describe_tab": {
                "title": "File Describe Tab",
                "content": "Select this tab to view the file description wizard and files currently being described. <br/>For more information about this control, including a demonstration of its usage, please use the help component."
            },
            "copo_data_upload_file_button": {
                "title": "Upload File Button",
                "content": "Click this button to upload files to COPO. Multiple files can be selected and uploaded at once. <p>Uploaded files are displayed in the <strong>Inspect</strong> pane. "
            },
            "datafile_table_describe": {
                "title": "Describe Button",
                "content": "Use this button to activate the datafile description wizard. Please note that one or more files must be selected before clicking the describe button. Once clicked, the view will change to display the wizard, where the target datafiles may be described."
            },
            "profile_details_panel": {
                "title": "Profile Details",
                "content": "View a profile details here having selected a profile record."
            },
            "page_context_help_panel": {
                "title": "Help",
                "content": "Interact with the help pane to find help topics relevant to the page and/or current task."
            },
            "profile_table": {
                "title": "Profile Records",
                "content": "Profile records list.<ol><li>Click on any component (e.g., Samples) within a profile to access any particular component's page</li><li>Use the action buttons (e.g., Select all, Add) to interact with profile records</li><li>Use the profile search control to display a filtered listing of records, based on matched terms</li></ol>"
            },
            "new_publication_button": {
                "title": "Create New Publication",
                "content": "Click here to create a new Publication. You will be provided with the following options: <ol><li>Manually enter a new publication record using the publication form</li><li>Resolve a Digital Object Identifier (DOI) to retrieve a target publication record from an external service</li><li>Resolve a PubMed ID to retrieve a target publication record from an external service</li></ol>"
            },
            "page_activity_panel": {
                "title": "Task",
                "content": "Interact with the task pane to perform available tasks on selected records. <ol><li>Select one or more records by clicking on target rows</li><li>Select the required task from available tasks to perform</li></ol>"
            }
        }
    }

    return qt.properties;
}