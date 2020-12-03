$(document).ready(function () {


    var index = getRandomInt(images.length)

    $('body').css("background-image", "url(" + images[index] + ")")

    try {
        var color = getRandomInt(content_classes.length)
        $("#main_banner").addClass(content_classes[color])
    } catch (err) {

    }
    $('.ui.dropdown')
        .dropdown();

})

function getRandomInt(max) {
    return Math.floor(Math.random() * Math.floor(max));
}