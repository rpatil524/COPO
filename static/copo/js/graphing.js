async function draw_line_graph() {

    const dataset = await d3.json("/api/stats/combined_stats_json")
    // accessors
    console.log(dataset)
    const yAccessor = d => d.users
    const dateParser = d3.timeParse("%Y-%m-%d")
    const xAccessor = d => dateParser(d.date)

    let dimensions = {
        width: window.innerWidth * 0.3,
        height: window.innerHeight * 0.45,
        margin: {
            top: 15,
            right: 15,
            bottom: 40,
            left: 60,
        },
    }
    dimensions.boundedWidth = dimensions.width
        - dimensions.margin.left
        - dimensions.margin.right
    dimensions.boundedHeight = dimensions.height
        - dimensions.margin.top
        - dimensions.margin.bottom


    const draw_line = metric => {
        const yAccessor = d => d[metric]
        const dateParser = d3.timeParse("%Y-%m-%d")
        const xAccessor = d => dateParser(d.date)

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

        // scales
        const yScale = d3.scaleLinear()
            .domain(d3.extent(dataset, yAccessor))
            .range([dimensions.boundedHeight, 0])
        const xScale = d3.scaleTime()
            .domain(d3.extent(dataset, xAccessor))
            .range([0, dimensions.boundedWidth])

        //draw
        const lineGenerator = d3.line()
            .x(d => xScale(xAccessor(d)))
            .y(d => yScale(yAccessor(d)))

        const line = bounds.append("path")
            .attr("d", lineGenerator(dataset))
            .attr("fill", "none")
            .attr("stroke", "cornflowerblue")
            .attr("stroke-width", 3)

        let dots = bounds.selectAll("circle")
            .data(dataset)
            .enter()
            .append("circle")
            .attr("cx", d => xScale(xAccessor(d)))
            .attr("cy", d => yScale(yAccessor(d)))
            .attr("r", 3)
            .attr("fill", "steelblue")

        // Draw peripherals

        const yAxisGenerator = d3.axisLeft()
            .scale(yScale)

        const yAxis = bounds.append("g")
            .call(yAxisGenerator)

        const xAxisGenerator = d3.axisBottom()
            .scale(xScale)

        const xAxis = bounds.append("g")
            .call(xAxisGenerator)
            .style("transform", `translateY(${
                dimensions.boundedHeight
            }px)`)

        const yAxisLabel = yAxis.append("text")
            .attr("x", -dimensions.boundedHeight / 2)
            .attr("y", -dimensions.margin.left + 10)
            .attr("fill", "black")
            .attr("font-size", "1.4em")
            .text("number of " + metric)
            .style("transform", "rotate(-90deg)")
            .style("text-anchor", "middle")
    }

    const metrics = [
        "samples",
        "datafiles",
        "users",
        "profiles"
    ]

    metrics.forEach(draw_line)
}

draw_line_graph()
