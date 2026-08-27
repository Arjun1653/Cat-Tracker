// Minimal, dependency-free SVG chart helpers. No CDN, works fully offline.
const Charts = (() => {

  function svgEl(tag, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const k in attrs) el.setAttribute(k, attrs[k]);
    return el;
  }

  function niceMax(v) {
    if (v <= 0) return 1;
    const mag = Math.pow(10, Math.floor(Math.log10(v)));
    const norm = v / mag;
    let f;
    if (norm <= 1) f = 1; else if (norm <= 2) f = 2; else if (norm <= 5) f = 5; else f = 10;
    return f * mag;
  }

  // Simple multi-series line chart. series = [{name, color, points:[{x label,y}]}]
  function lineChart(container, series, opts = {}) {
    container.innerHTML = "";
    const w = opts.width || container.clientWidth || 600;
    const h = opts.height || 220;
    const padL = 40, padR = 16, padT = 16, padB = 28;
    const plotW = w - padL - padR, plotH = h - padT - padB;

    const allY = series.flatMap(s => s.points.map(p => p.y)).filter(v => v !== null && v !== undefined);
    if (allY.length === 0) {
      container.innerHTML = '<div class="empty-state">No data logged yet</div>';
      return;
    }
    const maxY = niceMax(Math.max(...allY) * 1.15);
    const minY = Math.min(0, Math.min(...allY));
    const n = Math.max(...series.map(s => s.points.length));

    const svg = svgEl("svg", { viewBox: `0 0 ${w} ${h}`, width: "100%", height: h });

    // gridlines
    const gridSteps = 4;
    for (let i = 0; i <= gridSteps; i++) {
      const y = padT + plotH - (plotH * i / gridSteps);
      const val = minY + (maxY - minY) * i / gridSteps;
      svg.appendChild(svgEl("line", { x1: padL, x2: w - padR, y1: y, y2: y, stroke: "#21252E", "stroke-width": 1 }));
      const t = svgEl("text", { x: padL - 8, y: y + 4, "text-anchor": "end", fill: "#565D6B", "font-size": 10, "font-family": "ui-monospace,monospace" });
      t.textContent = Math.round(val);
      svg.appendChild(t);
    }

    series.forEach(s => {
      const pts = s.points;
      if (pts.length === 0) return;
      const stepX = n > 1 ? plotW / (n - 1) : 0;
      const coords = pts.map((p, i) => {
        const x = padL + (n > 1 ? i * stepX : plotW / 2);
        const y = padT + plotH - ((p.y - minY) / (maxY - minY || 1)) * plotH;
        return [x, y];
      });
      const d = coords.map((c, i) => (i === 0 ? "M" : "L") + c[0].toFixed(1) + "," + c[1].toFixed(1)).join(" ");
      svg.appendChild(svgEl("path", { d, fill: "none", stroke: s.color, "stroke-width": 2 }));
      coords.forEach((c, i) => {
        if (pts[i].y === null || pts[i].y === undefined) return;
        svg.appendChild(svgEl("circle", { cx: c[0], cy: c[1], r: 3, fill: s.color }));
      });
    });

    // x labels (first, mid, last)
    const labelIdxs = n <= 6 ? [...Array(n).keys()] : [0, Math.floor(n / 2), n - 1];
    const refPoints = series.find(s => s.points.length === n)?.points || series[0].points;
    labelIdxs.forEach(i => {
      if (!refPoints[i]) return;
      const stepX = n > 1 ? plotW / (n - 1) : 0;
      const x = padL + (n > 1 ? i * stepX : plotW / 2);
      const t = svgEl("text", { x, y: h - 8, "text-anchor": "middle", fill: "#565D6B", "font-size": 10, "font-family": "ui-monospace,monospace" });
      t.textContent = refPoints[i].x;
      svg.appendChild(t);
    });

    container.appendChild(svg);

    if (series.length > 1) {
      const legend = document.createElement("div");
      legend.style.cssText = "display:flex;gap:14px;margin-top:6px;flex-wrap:wrap;";
      series.forEach(s => {
        const item = document.createElement("span");
        item.style.cssText = "font-family:ui-monospace,monospace;font-size:11px;color:#8B92A0;display:flex;align-items:center;gap:5px;";
        item.innerHTML = `<span style="width:8px;height:8px;border-radius:50%;background:${s.color};display:inline-block;"></span>${s.name}`;
        legend.appendChild(item);
      });
      container.appendChild(legend);
    }
  }

  // Horizontal bar chart. data = [{label, value, color}]
  function hBarChart(container, data, opts = {}) {
    container.innerHTML = "";
    if (!data.length) { container.innerHTML = '<div class="empty-state">No data yet</div>'; return; }
    const w = opts.width || container.clientWidth || 600;
    const rowH = opts.rowHeight || 26;
    const h = data.length * rowH + 10;
    const labelW = opts.labelWidth || 160;
    const maxVal = niceMax(Math.max(...data.map(d => d.value), 1));
    const plotW = w - labelW - 60;

    const svg = svgEl("svg", { viewBox: `0 0 ${w} ${h}`, width: "100%", height: h });
    data.forEach((d, i) => {
      const y = i * rowH + 6;
      const barW = Math.max(2, (d.value / maxVal) * plotW);
      const label = svgEl("text", { x: labelW - 10, y: y + rowH * 0.42, "text-anchor": "end", fill: "#E9E7E0", "font-size": 12, "font-family": "-apple-system,sans-serif" });
      label.textContent = d.label.length > 26 ? d.label.slice(0, 25) + "\u2026" : d.label;
      svg.appendChild(label);

      svg.appendChild(svgEl("rect", { x: labelW, y: y, width: plotW, height: rowH - 10, fill: "#171A20", rx: 2 }));
      svg.appendChild(svgEl("rect", { x: labelW, y: y, width: barW, height: rowH - 10, fill: d.color || "#35C2C1", rx: 2 }));

      const val = svgEl("text", { x: labelW + barW + 8, y: y + rowH * 0.42, fill: "#8B92A0", "font-size": 11, "font-family": "ui-monospace,monospace" });
      val.textContent = d.value;
      svg.appendChild(val);
    });
    container.appendChild(svg);
  }

  // Vertical bar chart. data=[{label, value, color}]
  function vBarChart(container, data, opts = {}) {
    container.innerHTML = "";
    if (!data.length) { container.innerHTML = '<div class="empty-state">No data yet</div>'; return; }
    const w = opts.width || container.clientWidth || 600;
    const h = opts.height || 200;
    const padL = 36, padR = 10, padT = 10, padB = 34;
    const plotW = w - padL - padR, plotH = h - padT - padB;
    const maxVal = niceMax(Math.max(...data.map(d => d.value), 1));
    const gap = 6;
    const barW = (plotW - gap * (data.length - 1)) / data.length;

    const svg = svgEl("svg", { viewBox: `0 0 ${w} ${h}`, width: "100%", height: h });
    for (let i = 0; i <= 3; i++) {
      const y = padT + plotH - (plotH * i / 3);
      svg.appendChild(svgEl("line", { x1: padL, x2: w - padR, y1: y, y2: y, stroke: "#21252E" }));
    }
    data.forEach((d, i) => {
      const x = padL + i * (barW + gap);
      const bh = (d.value / maxVal) * plotH;
      const y = padT + plotH - bh;
      svg.appendChild(svgEl("rect", { x, y, width: barW, height: Math.max(1, bh), fill: d.color || "#6FA8FF", rx: 2 }));
      const t = svgEl("text", { x: x + barW / 2, y: h - 14, "text-anchor": "middle", fill: "#565D6B", "font-size": 10, "font-family": "ui-monospace,monospace" });
      t.textContent = d.label;
      svg.appendChild(t);
      const vt = svgEl("text", { x: x + barW / 2, y: y - 5, "text-anchor": "middle", fill: "#8B92A0", "font-size": 10, "font-family": "ui-monospace,monospace" });
      vt.textContent = d.value;
      svg.appendChild(vt);
    });
    container.appendChild(svg);
  }

  // Calendar heatmap. entries = [{date:'YYYY-MM-DD', count}]
  function heatmap(container, entries, opts = {}) {
    container.innerHTML = "";
    const map = {};
    entries.forEach(e => map[e.date] = e.count);
    const days = opts.days || 98; // 14 weeks
    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - (days - 1));
    // align start to Sunday
    start.setDate(start.getDate() - start.getDay());

    const maxCount = Math.max(1, ...Object.values(map));
    const cell = 13, gap = 3;
    const weeks = Math.ceil((days + start.getDay()) / 7) + 1;
    const w = weeks * (cell + gap) + 30;
    const h = 7 * (cell + gap) + 20;

    const svg = svgEl("svg", { viewBox: `0 0 ${w} ${h}`, width: "100%", height: h });
    let cur = new Date(start);
    let col = 0;
    const dayLabels = ["", "Mon", "", "Wed", "", "Fri", ""];
    dayLabels.forEach((lbl, i) => {
      if (!lbl) return;
      const t = svgEl("text", { x: 0, y: 14 + i * (cell + gap) + 9, fill: "#565D6B", "font-size": 9, "font-family": "ui-monospace,monospace" });
      t.textContent = lbl;
      svg.appendChild(t);
    });

    while (cur <= today) {
      const dow = cur.getDay();
      const key = cur.toISOString().slice(0, 10);
      const count = map[key] || 0;
      let fill = "#171A20";
      if (count > 0) {
        const ratio = Math.min(1, count / maxCount);
        fill = ratio > 0.66 ? "#FF5A36" : ratio > 0.33 ? "#c9633f" : "#7A3324";
      }
      const x = 26 + col * (cell + gap);
      const y = 6 + dow * (cell + gap);
      const rect = svgEl("rect", { x, y, width: cell, height: cell, fill, rx: 2 });
      const titleEl = svgEl("title", {});
      titleEl.textContent = `${key}: ${count} logged`;
      rect.appendChild(titleEl);
      svg.appendChild(rect);
      if (dow === 6) col++;
      cur.setDate(cur.getDate() + 1);
    }
    container.appendChild(svg);
  }

  return { lineChart, hBarChart, vBarChart, heatmap };
})();
