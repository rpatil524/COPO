$(document).ready(function () {


    var index = getRandomInt(images.length)

    $('body').css("background-image", "url(" + images[index] + ")")


})

function getRandomInt(max) {
    return Math.floor(Math.random() * Math.floor(max));
}