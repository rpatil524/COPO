//**some re-usable functions across different modules

$(document).ready(function () {
    ;
});

function set_empty_component_message(dataRows) {
    //decides, based on presence of record, to display table or getting started info

    if (dataRows.length == 0) {
        $(".table-parent-div").hide();
        $(".page-welcome-message").show();

    } else {
        $(".table-parent-div").show();
        $(".page-welcome-message").hide();
    }
}


function activity_agent(dt) {
    //highlights tasks to be fulfilled based on record selection
    var selectedRows = dt.rows({selected: true}).count(); //number of rows selected


    $(dt.buttons().container()).find(".copo-table-cbuttons").find(".copo-dt").each(function () {
        var btnType = "single";
        $(this).addClass("disabled");

        try {
            btnType = $(this).attr("data-btntype");
        } catch (err) {
            ;
        }

        if (selectedRows == 1) {
            $(this).removeClass("disabled");
        } else if (selectedRows > 1 && btnType == "multi") {
            $(this).removeClass("disabled");
        }
    });
}

function place_task_buttons(actionButtons, tableID) {
    //place custom buttons on table
    var table = $('#' + tableID).DataTable();

    var customButtons = $('<span/>', {
        style: "padding-left: 15px;",
        class: "copo-table-cbuttons"
    });

    $(table.buttons().container()).append(customButtons);

    actionButtons.forEach(function (item) {
        var actionBTN = $('<a/>', {
            class: "btn btn-sm dtables-dbuttons copo-dt disabled",
            style: "background:" + item.btnColor + " none; border: none; margin-top: 2px;",
            "data-action": item.btnAction,
            "data-btntype": item.btnType,
            "data-table": tableID,
            title: item.btnMessage
        });

        var actionICON = $('<i/>', {
            class: "copo-components-icons " + item.iconClass,
            style: "color: #fff"
        });

        var actionTXT = $('<span/>', {
            class: "icon_text",
            style: "color: #fff; padding-left: 3px;",
            html: item.text
        });

        actionBTN.append(actionICON).append(actionTXT);
        customButtons.append(actionBTN);
    });
}

