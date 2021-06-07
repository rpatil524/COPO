async function draw_line_graph() {

    const data = await d3.json("/api/stats/sample_stats_csv")
    // accessors

    const xAccessor = d => d.date
    const yAccessor = d => d.samples
}

draw_line_graph()
