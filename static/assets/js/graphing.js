$(document).ready(function () {
    var d = JSON.parse($("#stats").val())
    console.log(d.samples)


    fetch("/static/assets/js/stats_samples.csv")
        .then(response => response.text())
        .then(text => {
            console.log(text)
            var chart = JSC.chart('chartDiv', {
                debug: true,
                type: 'line',
                title_label_text:
                    'COPO Samples over time',
                data: text,
                legend_visible: false,

                options: {
                    scales: {
                        xAxes: [{
                            type: 'time'
                        }]
                    }
                }
            });
        });


})