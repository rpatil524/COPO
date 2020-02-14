$(document).ready(function(){

    $(document).on("change", "#taxonid", function(evt){
        var taxonid = $(evt.currentTarget).val()
        $.ajax(
            {
                url: "/copo/resolve_taxon_id",
                method: "GET",
                data: {"taxonid": taxonid}
            }
        ).done(function(data){
            alert(data)
        })
    })


})