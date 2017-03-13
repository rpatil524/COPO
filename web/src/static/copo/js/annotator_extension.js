/**
 * Created by fshaw on 22/12/2016.
 */
function helloWorld() {
    return {
        start: function (app) {
            var a = app.adder.Adder()
            app.notify(a)
        }
    };
}