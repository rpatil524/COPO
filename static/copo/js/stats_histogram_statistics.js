async function drawHist() {


    let dimensions = {
        width: $("#graph").innerWidth() * 0.7,
        height: window.innerHeight * 0.7,
        margin: {
            top: 30,
            right: 15,
            bottom: 100,
            left: 100,
        },
    }
    dimensions.boundedWidth = dimensions.width
        - dimensions.margin.left
        - dimensions.margin.right
    dimensions.boundedHeight = dimensions.height
        - dimensions.margin.top
        - dimensions.margin.bottom


    //Draw canvas
    const wrapper = d3.select("#graph")
        .append("svg")
        .attr("width", dimensions.width)
        .attr("height", dimensions.height)

    const bounds = wrapper.append("g")
        .style("transform", `translate(${
            dimensions.margin.left
        }px, ${
            dimensions.margin.top
        }px)`)

    bounds.append("g")
        .attr("class", "x-axis")
        .style("transform", `translateY(${dimensions.boundedHeight}px)`)
        .append("text")
        .attr("class", "x-axis-label")
        .attr("x", dimensions.boundedWidth / 2)
        .attr("y", dimensions.margin.bottom - 10)

    async function update(data_url) {
        console.log(data_url)
        const dataset = await d3.json(data_url)
        // accessors
        console.log(dataset)
    }

    $(document).on("change", "#changeHistMetric", function () {
        var val = $(this).children("option:selected").val()
        //var selectedMetricIndex = parseInt(val)
        const url = `/api/stats/histogram_metric/GET_${val}`
        update(url)
    })
    update(`/api/stats/histogram_metric/GET_${$(this).children("option:selected").val()}`)
}

drawHist()