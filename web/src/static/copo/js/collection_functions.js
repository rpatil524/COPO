function do_add_study_type() {
    var clonableTarget = $("#study_types_lists_div").children(":last").clone();

    //update id of cloned div
    var targetId = clonableTarget.attr("id");
    var splitIndex = targetId.lastIndexOf("_");
    var literalPart = targetId.substr(0, splitIndex + 1);
    var indexPart = targetId.substr(splitIndex + 1);

    clonableTarget.attr("id", literalPart + (parseInt(indexPart) + 1));


    // update the id, name of the study type select element
    var targetChild = clonableTarget.children(":nth-child(1)").children(":first");
    update_id_name_indx(targetChild);

    // update id, name of the cloned study type id text field
    targetChild = clonableTarget.children(":nth-child(2)").children(":first");
    targetChild.val("");
    update_id_name_indx(targetChild);

    // update id of anchor element
    targetChild = clonableTarget.children(":nth-child(3)").children(":first");
    update_id_name_indx(targetChild);

    //show the delete button for the cloned node
    clonableTarget.children(":nth-child(3)").children(":first").show();
    $("#study_types_lists_div").append(clonableTarget);
}

function do_add_sample_attribute() {
    var clonableTarget = $("#sample_attribute_div_0").clone();

    var indexPart = "";
    //sort index for this clone
    var largestIndex = 0;
    $("div[id^='sample_attribute_div']").each(function () {
        indexPart = parseInt(this.id.substr(this.id.lastIndexOf("_") + 1));
        if (!isNaN(indexPart)) {
            if (indexPart > largestIndex) {
                largestIndex = indexPart;
            }
        }
    });

    //this caters for sequential incremental of indexPart
    indexPart = largestIndex;
    indexPart = parseInt(indexPart) + 1;


    var literalPart = "sample_attribute_div_";


    clonableTarget.attr("id", literalPart + indexPart);


    // update the id, name of category term
    var targetChild = clonableTarget.children(":nth-child(1)").children(":first");
    targetChild.val("");
    update_child_by_indx(targetChild, indexPart);

    // update id, name of characteristics
    targetChild = clonableTarget.children(":nth-child(2)").children(":first");
    targetChild.val("");
    update_child_by_indx(targetChild, indexPart);

    // update id, name of unit
    targetChild = clonableTarget.children(":nth-child(3)").children(":first");
    targetChild.val("");
    update_child_by_indx(targetChild, indexPart);

    // update id, name of termAccessionNumber
    targetChild = clonableTarget.children(":nth-child(4)");
    targetChild.val("");
    update_child_by_indx(targetChild, indexPart);

    // update id, name of termSourceREF
    targetChild = clonableTarget.children(":nth-child(5)");
    targetChild.val("");
    update_child_by_indx(targetChild, indexPart);

    // update id of message element
    targetChild = clonableTarget.children(":nth-child(6)").children(":first");
    update_child_by_indx(targetChild, indexPart);

    // update id of anchor element
    targetChild = clonableTarget.children(":nth-child(7)").children(":first");
    update_child_by_indx(targetChild, indexPart);

    //show the delete button for the cloned node
    clonableTarget.children(":nth-child(7)").children(":first").show();
    $("#sample_attributes_div").append(clonableTarget.show());

    return clonableTarget.attr("id");
}

function update_child_by_indx(targetChild, indexPart) {
    var targetId = targetChild.attr("id");
    var literalPart = targetId.substr(0, targetId.lastIndexOf("_") + 1);
    targetChild.attr("id", literalPart + indexPart);
    targetChild.attr("name", literalPart + indexPart);
}

function update_id_name_indx(targetChild) {
    var targetId = targetChild.attr("id");
    var splitIndex = targetId.lastIndexOf("_");
    var literalPart = targetId.substr(0, splitIndex + 1);
    var indexPart = targetId.substr(splitIndex + 1);
    targetChild.attr("id", literalPart + (parseInt(indexPart) + 1));
    targetChild.attr("name", literalPart + (parseInt(indexPart) + 1));
}

function update_id_name_byref(targetChild, ref) {
    var targetId = targetChild.attr("id");
    var splitIndex = targetId.lastIndexOf("_");
    var literalPart = targetId.substr(0, splitIndex + 1);
    targetChild.attr("id", literalPart + ref);
}

function do_remove_study_type(event) {
    var targetId = $($(event.target)).attr("id");
    if (typeof targetId !== "undefined") {
        var splitIndex = targetId.lastIndexOf("_");
        var indexPart = targetId.substr(splitIndex + 1);

        //remove the parent
        $("#study_type_select_divs_" + indexPart).remove();
    }
}

function do_remove_sample_attribute(event) {
    var targetId = $($(event.target)).attr("id");

    var literalPart = "sample_attribute_remove";

    if (typeof targetId !== "undefined") {
        if (targetId.slice(0, (parseInt(literalPart.length))) == literalPart) {
            var indexPart = targetId.substr(parseInt(literalPart.length + 1));
            //remove the parent
            $("#sample_attribute_div_" + indexPart).remove();
        }
    }
}

function toggle_collection_type(collection_type) {
    if (collection_type.toLocaleLowerCase() == "ena submission") {
        $("#study_type_div").show();
    } else {
        $("#study_type_div").hide();
    }
}


//function to refresh tooltips and popup after automatic component redisplay
function refresh_tool_tips() {
    $("[data-toggle='tooltip']").tooltip();
    $('[data-toggle="popover"]').popover();

    //implements custom popover by extending Bootstrap's
    $('.popinfo').each(function () {
        var elem = $(this);
        var title = elem.attr('data-popinfo-title');
        var trigger = elem.attr('data-popinfo-trigger');

        var $popover1 = elem.popover({
            trigger: trigger,
            toggle: 'popover',
            placement: 'left',
            //title: title, //not picking up this assignment, found its place in template below
            html: true,
            content: elem.find('.popinfo-content').html(),
            template: '<div class="popover1" role="tooltip"><div class="arrow"></div>' +
            '<div class="popover1-title">' + title + '</div><div class="popover-content"></div></div>'
        });

    });
    $(".autocomplete").removeAttr('style');
}




