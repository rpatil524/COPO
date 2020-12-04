$(document).ready(function () {

    $('.ui.dropdown').dropdown();
    var image = getRandomInt(images.length)
    $('body').css("background-image", "url(" + images[image] + ")")

    try {
        var color = getRandomInt(content_classes.length)
        color = 1
        $("#main_banner").addClass(content_classes[color])
    } catch (err) {

    }



})

function getRandomInt(max) {
    return Math.floor(Math.random() * Math.floor(max));
}