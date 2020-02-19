$(document).ready(function () {

    $(document).on("keyup", "#taxonid", delay(function (e) {
            var taxonid = $("#taxonid").val()
            $.ajax(
                {
                    url: "/copo/resolve_taxon_id",
                    method: "GET",
                    data: {"taxonid": taxonid}
                }
            ).done(function (data) {
                alert(data)
            }).error(function (error) {
                console.log(error)
                BootstrapDialog.alert('Taxon IDs must be numeric');
            })
        })
    )
})

function delay(fn, ms) {
    let timer = 0
    return function (...args) {
        clearTimeout(timer)
        timer = setTimeout(fn.bind(this, ...args), ms || 1000)
    }
}