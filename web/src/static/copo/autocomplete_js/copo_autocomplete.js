AutoComplete({
    post: do_post
});


function do_post(result, response, custParams) {
    response = JSON.parse(response);
    var properties = Object.getOwnPropertyNames(response);
    //Try parse like JSON data

    var empty,
        length = response.length,
        li = domCreate("li"),
        ul = domCreate("ul");
    //Reverse result if limit parameter is custom
    if (custParams.limit < 0) {
        properties.reverse();
    }


    for (var item in response.highlighting) {
        try {
            li.innerHTML = response.highlighting[item].label_autosuggest[0];

            $(li).attr("data-autocomplete-value", response.highlighting[item].label_autosuggest[0].replace('<b>', '').replace('</b>', '') + ' - ' + item);

            ul.appendChild(li);
            li = domCreate("li");
        }
        catch (err) {
            console.log(err)
        }
    }
    if (result.hasChildNodes()) {
        result.childNodes[0].remove();
    }

    result.appendChild(ul);
}
