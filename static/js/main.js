(function () {
  "use strict";

  var dataEl = document.getElementById("tea-data");
  if (!dataEl) return;

  var D = JSON.parse(dataEl.textContent);
  var cur = D.currency || "$";

  var BLUE = "#1f6feb";
  var GREEN = "#1f9d6b";
  var RED = "#d1493f";
  var AMBER = "#c77f1a";
  var INK = "#1a2230";
  var GRID = "#e3e8ef";

  var FONT = { family: "ui-monospace, SFMono-Regular, Menlo, monospace", color: INK, size: 12 };

  var BASE_LAYOUT = {
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#ffffff",
    font: FONT,
    margin: { t: 44, r: 16, b: 44, l: 64 },
    title: { font: { family: "Inter, system-ui, sans-serif", size: 15, color: INK }, x: 0, xanchor: "left" }
  };

  var CONFIG = { displayModeBar: false, responsive: true };

  function layout(extra) {
    return Object.assign({}, BASE_LAYOUT, extra || {});
  }

  // 1. CAPEX breakdown
  Plotly.newPlot("chart-capex", [{
    type: "pie",
    labels: D.capex_breakdown.labels,
    values: D.capex_breakdown.values,
    hole: 0.5,
    sort: false,
    marker: { colors: [BLUE, "#7fb0f5", AMBER, GREEN] },
    textinfo: "label+percent",
    hovertemplate: "%{label}<br>" + cur + "%{value:,.0f}<extra></extra>"
  }], layout({ title: { text: "CAPEX breakdown" }, showlegend: false }), CONFIG);

  // 2. OPEX breakdown
  Plotly.newPlot("chart-opex", [{
    type: "pie",
    labels: D.opex_breakdown.labels,
    values: D.opex_breakdown.values,
    hole: 0.5,
    sort: false,
    marker: { colors: [RED, GREEN] },
    textinfo: "label+percent",
    hovertemplate: "%{label}<br>" + cur + "%{value:,.0f}<extra></extra>"
  }], layout({ title: { text: "OPEX split" }, showlegend: false }), CONFIG);

  // 3. Net cash flow
  var net = D.cashflow.net;
  var barColors = net.map(function (v) { return v < 0 ? RED : GREEN; });
  Plotly.newPlot("chart-cashflow", [{
    type: "bar",
    x: D.cashflow.years,
    y: net,
    marker: { color: barColors },
    hovertemplate: "Year %{x}<br>" + cur + "%{y:,.0f}<extra></extra>"
  }], layout({
    title: { text: "Net cash flow vs year" },
    xaxis: { title: "Year", gridcolor: GRID, zeroline: false },
    yaxis: { title: cur, gridcolor: GRID, zerolinecolor: INK }
  }), CONFIG);

  // 4. Cumulative cash flow
  Plotly.newPlot("chart-cumulative", [{
    type: "scatter",
    mode: "lines+markers",
    x: D.cashflow.years,
    y: D.cashflow.cumulative,
    line: { color: BLUE, width: 2 },
    marker: { color: BLUE, size: 5 },
    hovertemplate: "Year %{x}<br>" + cur + "%{y:,.0f}<extra></extra>"
  }], layout({
    title: { text: "Cumulative cash flow vs year" },
    xaxis: { title: "Year", gridcolor: GRID, zeroline: false },
    yaxis: { title: cur, gridcolor: GRID, zerolinecolor: INK },
    shapes: [{ type: "line", x0: D.cashflow.years[0], x1: D.cashflow.years[D.cashflow.years.length - 1],
               y0: 0, y1: 0, line: { color: INK, width: 1, dash: "dot" } }]
  }), CONFIG);

  // 5. NPV sensitivity
  var s = D.npv_sensitivity;
  Plotly.newPlot("chart-npv-sens", [
    {
      type: "scatter", mode: "lines+markers", name: "Utility cost",
      x: s.pct_changes, y: s.utility,
      line: { color: GREEN, width: 2 },
      hovertemplate: "%{x:+d}% utility<br>NPV " + cur + "%{y:,.0f}<extra></extra>"
    },
    {
      type: "scatter", mode: "lines+markers", name: "Purchase cost",
      x: s.pct_changes, y: s.purchase,
      line: { color: BLUE, width: 2 },
      hovertemplate: "%{x:+d}% purchase<br>NPV " + cur + "%{y:,.0f}<extra></extra>"
    }
  ], layout({
    title: { text: "NPV sensitivity to drivers" },
    xaxis: { title: "Change in driver (%)", gridcolor: GRID, zeroline: true, zerolinecolor: INK },
    yaxis: { title: "NPV " + cur, gridcolor: GRID, zerolinecolor: INK },
    legend: { orientation: "h", y: -0.25 }
  }), CONFIG);

  // 6. Discount-rate sensitivity
  var d = D.discount_sensitivity;
  var traces = [{
    type: "scatter", mode: "lines",
    x: d.rates, y: d.npv,
    line: { color: AMBER, width: 2 },
    hovertemplate: "%{x:.0f}% rate<br>NPV " + cur + "%{y:,.0f}<extra></extra>",
    name: "NPV"
  }];
  var shapes = [{ type: "line", x0: d.rates[0], x1: d.rates[d.rates.length - 1],
                  y0: 0, y1: 0, line: { color: INK, width: 1, dash: "dot" } }];
  if (D.irr !== null && D.irr !== undefined) {
    shapes.push({ type: "line", x0: D.irr * 100, x1: D.irr * 100,
                  yref: "paper", y0: 0, y1: 1,
                  line: { color: RED, width: 1.5, dash: "dash" } });
  }
  Plotly.newPlot("chart-discount-sens", traces, layout({
    title: { text: "Discount-rate sensitivity" + (D.irr ? "  (IRR " + (D.irr * 100).toFixed(1) + "%)" : "") },
    xaxis: { title: "Discount rate (%)", gridcolor: GRID, zeroline: false },
    yaxis: { title: "NPV " + cur, gridcolor: GRID, zerolinecolor: INK },
    shapes: shapes, showlegend: false
  }), CONFIG);

})();
