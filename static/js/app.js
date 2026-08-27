const API = {
  async get(url) {
    const response = await fetch(url);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Could not load data");
    return data;
  },
  async post(url, body) {
    const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Could not save your changes");
    return data;
  },
};

const SECTION_COLORS = { QA: "#6FA8FF", DILR: "#C792EA", VARC: "#35C2C1" };

function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function localDate() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now - offset).toISOString().slice(0, 10);
}

async function save(action) {
  try { return await action(); }
  catch (error) { toast(error.message || "Something went wrong. Try again."); return null; }
}

// ---------------------------------------------------------------------
// Tab routing
// ---------------------------------------------------------------------
const screens = {
  home: renderHome,
  week: renderWeek,
  syllabus: renderSyllabus,
  mocks: renderMocks,
  errors: renderErrors,
  predictor: renderPredictor,
  analytics: renderAnalytics,
  settings: renderSettings,
};

document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

document.addEventListener("keydown", event => {
  if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  const names = ["home", "week", "syllabus", "mocks", "errors", "predictor", "analytics", "settings"];
  const target = names[Number(event.key) - 1];
  const tab = target && document.querySelector(`.tab[data-tab="${target}"]`);
  if (tab) { event.preventDefault(); tab.click(); tab.focus(); }
});

window.addEventListener("unhandledrejection", event => {
  event.preventDefault();
  toast(event.reason?.message || "Something went wrong. Try again.");
});

function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => {
    const active = t.dataset.tab === name;
    t.classList.toggle("active", active);
    t.toggleAttribute("aria-current", active);
  });
  document.querySelectorAll(".screen").forEach(s => s.classList.toggle("active", s.id === "screen-" + name));
  screens[name]();
}

// ---------------------------------------------------------------------
// HOME
// ---------------------------------------------------------------------
async function renderHome() {
  const s = document.getElementById("screen-home");
  s.innerHTML = '<div class="empty-state">Loading\u2026</div>';
  const data = await API.get("/api/summary");

  const daysStr = String(Math.max(0, data.days_left));
  const digits = daysStr.padStart(3, "0").split("");

  s.innerHTML = `
    <div class="panel hero">
      <div>
        <div class="flap-row">
          ${digits.map(d => `<div class="flap">${d}</div>`).join("")}
        </div>
        <div class="days-label">days to CAT 2026</div>
      </div>
      <div class="hero-right">
        <div class="eyebrow">Exam day &middot; ${escapeHTML(new Date(`${data.exam_date}T00:00:00`).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" }))}</div>
        <h1>${greeting()}</h1>
        <div class="subtle">Week ${data.current_week} of ${data.total_weeks} &middot; overall plan completion ${data.overall_plan_completion_pct}%</div>
        <div class="hero-meta">
          <div class="hero-stat"><div class="val">${data.streak}</div><div class="lbl">day streak</div></div>
          <div class="hero-stat"><div class="val">${data.overall_plan_completion_pct}%</div><div class="lbl">plan logged</div></div>
          <div class="hero-stat"><div class="val">${data.current_week}/${data.total_weeks}</div><div class="lbl">week</div></div>
        </div>
        ${data.persona_lines.map(l => `<div class="persona-line">${escapeHTML(l)}</div>`).join("")}
      </div>
    </div>

    <div class="grid grid-2">
      <div class="panel">
        <h3>Today's focus</h3>
        ${data.focus_topic ? `
          <div class="flex-between mb">
            <div>
              <div style="font-size:16px;">${escapeHTML(data.focus_topic.topic_name)}</div>
              <span class="badge ${data.focus_topic.section.toLowerCase()}">${data.focus_topic.section}</span>
              ${data.focus_topic.volatile_flag ? '<span class="badge volatile">volatile</span>' : ''}
            </div>
            <div class="num" style="font-size:22px;color:var(--accent-gold)">${data.focus_topic.historical_weight}</div>
          </div>
          <div class="subtle mb">Highest gap between historical exam weightage and how much you've logged so far.</div>
          <div class="pbar-row">
            <div class="pbar-track"><div class="pbar-fill gold" style="width:${data.focus_topic.completion_pct}%"></div></div>
            <div class="pbar-pct">${data.focus_topic.completion_pct}%</div>
          </div>
        ` : '<div class="empty-state">Nothing flagged \u2014 you\'re tracking evenly.</div>'}
      </div>

      <div class="panel">
        <h3>Quick log</h3>
        <div id="quick-log-form"></div>
      </div>
    </div>
  `;

  renderQuickLogForm();
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Morning check-in";
  if (h < 17) return "Midday check-in";
  return "Evening check-in";
}

async function renderQuickLogForm() {
  const wk = await API.get("/api/weeks");
  const current = wk.weeks.find(w => w.week_num === wk.current_week);
  const box = document.getElementById("quick-log-form");
  if (!current || current.topics.length === 0) {
    box.innerHTML = '<div class="empty-state">No plan topics found</div>';
    return;
  }
  const opts = current.topics.map(t => `<option value="${t.id}" data-unit="${t.unit}">${t.section} \u2014 ${t.topic_name}</option>`).join("");
  box.innerHTML = `
    <div class="field mb">
      <label>Topic (this week)</label>
      <select id="ql-topic">${opts}</select>
    </div>
    <div class="grid" style="grid-template-columns: 1fr 1fr; gap:10px;">
      <div class="field">
        <label>Count done</label>
        <input type="number" id="ql-count" min="0" placeholder="0">
      </div>
      <div class="field">
        <label>Notes (optional)</label>
        <input type="text" id="ql-notes" placeholder="\u2014">
      </div>
    </div>
    <button class="btn mt" id="ql-submit">Log it</button>
  `;
  document.getElementById("ql-submit").addEventListener("click", async () => {
    const topicSel = document.getElementById("ql-topic");
    const count = document.getElementById("ql-count").value;
    if (!count) { toast("Enter a count first"); return; }
    const unit = topicSel.selectedOptions[0].dataset.unit;
    const result = await save(() => API.post("/api/log", {
      plan_topic_id: parseInt(topicSel.value),
      count_done: parseInt(count),
      unit,
      notes: document.getElementById("ql-notes").value || null,
    }));
    if (!result) return;
    toast("Logged \u2713");
    renderHome();
  });
}

// ---------------------------------------------------------------------
// THIS WEEK
// ---------------------------------------------------------------------
let selectedWeek = null;

async function renderWeek() {
  const s = document.getElementById("screen-week");
  s.innerHTML = '<div class="empty-state">Loading\u2026</div>';
  const data = await API.get("/api/weeks");
  if (selectedWeek === null) selectedWeek = data.current_week;

  const rail = data.weeks.map(w => `
    <div class="week-tick ${w.week_num === data.current_week ? 'current' : ''} ${w.week_num === selectedWeek ? 'selected' : ''}" data-week="${w.week_num}">W${w.week_num}</div>
  `).join("");

  s.innerHTML = `
    <div class="eyebrow">9-week plan</div>
    <h1 class="mb">This Week</h1>
    <div class="week-rail">${rail}</div>
    <div id="week-detail"></div>
  `;

  s.querySelectorAll(".week-tick").forEach(tick => {
    tick.addEventListener("click", () => {
      selectedWeek = parseInt(tick.dataset.week);
      renderWeek();
    });
  });

  renderWeekDetail(data.weeks.find(w => w.week_num === selectedWeek));
}

function renderWeekDetail(week) {
  const box = document.getElementById("week-detail");
  if (!week) { box.innerHTML = '<div class="empty-state">No such week</div>'; return; }

  const bySection = { QA: [], DILR: [], VARC: [] };
  week.topics.forEach(t => bySection[t.section].push(t));

  const sectionsHtml = Object.keys(bySection).map(sec => {
    const topics = bySection[sec];
    if (topics.length === 0) return "";
    return `
      <div class="panel mb">
        <div class="section-title-row">
          <h2><span class="section-color-${sec.toLowerCase()}">${sec}</span></h2>
          <span class="subtle">${topics.reduce((a, t) => a + t.target_count, 0)} target</span>
        </div>
        ${topics.map(t => `
          <div class="topic-row" data-topic-id="${t.id}">
            <div class="topic-name">${escapeHTML(t.topic_name)}</div>
            <div class="topic-target">${t.done}/${t.target_count} ${t.unit}</div>
            <div class="pbar-row">
              <div class="pbar-track"><div class="pbar-fill" style="width:${t.completion_pct}%; background:${SECTION_COLORS[sec]}"></div></div>
              <div class="pbar-pct">${t.completion_pct}%</div>
            </div>
            <div style="display:flex; gap:4px;">
              <input type="number" class="log-input" min="0" placeholder="+n" id="add-${t.id}">
              <button class="log-btn" data-add="${t.id}" data-unit="${t.unit}">Add</button>
            </div>
          </div>
        `).join("")}
      </div>
    `;
  }).join("");

  box.innerHTML = `
    <div class="week-header">
      <h2>Week ${week.week_num} ${week.is_current ? '<span class="badge" style="border-color:var(--accent-signal);color:var(--accent-signal)">current</span>' : ''}</h2>
      <span class="week-dates">${week.start_date} \u2192 ${week.end_date}</span>
    </div>
    ${sectionsHtml || '<div class="empty-state">No topics this week</div>'}
  `;

  box.querySelectorAll("[data-add]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.add;
      const unit = btn.dataset.unit;
      const input = document.getElementById(`add-${id}`);
      const val = input.value;
      if (!val) { toast("Enter a number first"); return; }
      const result = await save(() => API.post("/api/log", { plan_topic_id: parseInt(id), count_done: parseInt(val), unit }));
      if (!result) return;
      toast("Logged \u2713");
      renderWeek();
    });
  });
}

// ---------------------------------------------------------------------
// SYLLABUS MASTER
// ---------------------------------------------------------------------
let syllabusSort = { key: "historical_weight", dir: -1 };

async function renderSyllabus() {
  const s = document.getElementById("screen-syllabus");
  s.innerHTML = '<div class="empty-state">Loading\u2026</div>';
  const data = await API.get("/api/syllabus");
  window.__syllabusData = data;
  drawSyllabus();
}

function drawSyllabus() {
  const s = document.getElementById("screen-syllabus");
  const data = window.__syllabusData;
  const secStats = data.section_completion_pct;

  let topics = [...data.topics];
  topics.sort((a, b) => (a[syllabusSort.key] > b[syllabusSort.key] ? 1 : -1) * syllabusSort.dir);

  s.innerHTML = `
    <div class="eyebrow">Full syllabus &middot; 2021\u20132025 question frequency</div>
    <h1 class="mb">Syllabus Master</h1>

    <div class="grid grid-3 mb">
      ${["QA", "DILR", "VARC"].map(sec => `
        <div class="panel panel-tight">
          <div class="flex-between">
            <span class="section-color-${sec.toLowerCase()}" style="font-family:var(--font-mono);font-size:13px;">${sec}</span>
            <span class="num">${secStats[sec]}%</span>
          </div>
          <div class="pbar-track mt" style="height:6px;"><div class="pbar-fill" style="width:${secStats[sec]}%; background:${SECTION_COLORS[sec]}"></div></div>
        </div>
      `).join("")}
    </div>

    <div class="panel">
      <table class="data-table">
        <thead>
          <tr>
            <th data-sort="section">Section</th>
            <th data-sort="topic_name">Topic</th>
            <th data-sort="historical_weight">Weight (5yr)</th>
            <th data-sort="completion_pct">Completion</th>
          </tr>
        </thead>
        <tbody>
          ${topics.map(t => `
            <tr>
              <td><span class="badge ${t.section.toLowerCase()}">${t.section}</span></td>
              <td>${escapeHTML(t.topic_name)} ${t.volatile_flag ? '<span class="badge volatile">volatile</span>' : ''}</td>
              <td class="num">${t.historical_weight}</td>
              <td>
                <div class="pbar-row" style="max-width:180px;">
                  <div class="pbar-track"><div class="pbar-fill" style="width:${t.completion_pct}%; background:${SECTION_COLORS[t.section]}"></div></div>
                  <div class="pbar-pct">${t.completion_pct}%</div>
                </div>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;

  s.querySelectorAll("th[data-sort]").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      syllabusSort.dir = (syllabusSort.key === key) ? -syllabusSort.dir : -1;
      syllabusSort.key = key;
      drawSyllabus();
    });
  });
}

// ---------------------------------------------------------------------
// MOCKS
// ---------------------------------------------------------------------
async function renderMocks() {
  const s = document.getElementById("screen-mocks");
  s.innerHTML = '<div class="empty-state">Loading\u2026</div>';
  const data = await API.get("/api/mocks");

  s.innerHTML = `
    <div class="eyebrow">Full-length tests</div>
    <h1 class="mb">Mocks</h1>

    <div class="panel mb">
      <h3>Score trend</h3>
      <div class="chart-box" id="mock-trend-chart"></div>
    </div>

    <div class="panel mb">
      <h3>Log a mock</h3>
      <div id="mock-form"></div>
    </div>

    <div class="panel">
      <h3>History</h3>
      <div id="mock-list"></div>
    </div>
  `;

  Charts.lineChart(document.getElementById("mock-trend-chart"), [
    { name: "Overall score", color: "#FF5A36", points: data.mocks.slice().reverse().map(m => ({ x: m.date.slice(5), y: m.overall_score })) }
  ]);

  renderMockForm();
  renderMockList(data.mocks);
}

function renderMockForm() {
  const box = document.getElementById("mock-form");
  box.innerHTML = `
    <div class="form-grid mb">
      <div class="field"><label>Date *</label><input type="date" id="m-date" value="${localDate()}"></div>
      <div class="field"><label>Series (free text)</label><input type="text" id="m-series" placeholder="e.g. IMS SimCAT 4"></div>
      <div class="field"><label>Overall score *</label><input type="number" id="m-overall" step="0.01"></div>
      <div class="field"><label>Overall percentile</label><input type="number" id="m-overall-pct" step="0.01"></div>
    </div>
    <div class="grid grid-3">
      ${["QA", "DILR", "VARC"].map(sec => `
        <div class="panel panel-raised panel-tight">
          <div class="section-color-${sec.toLowerCase()}" style="font-family:var(--font-mono);font-size:12px;margin-bottom:8px;">${sec}</div>
          <div class="field mb"><label>Attempts</label><input type="number" id="m-${sec}-att"></div>
          <div class="field mb"><label>Correct</label><input type="number" id="m-${sec}-cor"></div>
          <div class="field mb"><label>Wrong</label><input type="number" id="m-${sec}-wro"></div>
          <div class="field mb"><label>Score</label><input type="number" step="0.01" id="m-${sec}-sco"></div>
          <div class="field mb"><label>Percentile</label><input type="number" step="0.01" id="m-${sec}-pct"></div>
          <div class="field"><label>Time (min)</label><input type="number" step="0.1" id="m-${sec}-time"></div>
        </div>
      `).join("")}
    </div>
    <div class="field mt mb"><label>Notes</label><textarea id="m-notes"></textarea></div>
    <button class="btn" id="m-submit">Save mock</button>
  `;

  document.getElementById("m-submit").addEventListener("click", async () => {
    const dateV = document.getElementById("m-date").value;
    const overall = document.getElementById("m-overall").value;
    if (!dateV || !overall) { toast("Date and overall score are required"); return; }

    const sections = ["QA", "DILR", "VARC"].map(sec => {
      const v = (id) => { const el = document.getElementById(id); return el.value === "" ? null : parseFloat(el.value); };
      const att = v(`m-${sec}-att`), cor = v(`m-${sec}-cor`), wro = v(`m-${sec}-wro`), sco = v(`m-${sec}-sco`), pct = v(`m-${sec}-pct`), time = v(`m-${sec}-time`);
      if ([att, cor, wro, sco, pct, time].every(x => x === null)) return null;
      return { section: sec, attempts: att, correct: cor, wrong: wro, score: sco, percentile: pct, time_taken_min: time };
    }).filter(Boolean);

    const result = await save(() => API.post("/api/mocks", {
      date: dateV,
      series_name: document.getElementById("m-series").value || null,
      overall_score: parseFloat(overall),
      overall_percentile: document.getElementById("m-overall-pct").value ? parseFloat(document.getElementById("m-overall-pct").value) : null,
      notes: document.getElementById("m-notes").value || null,
      sections,
    }));
    if (!result) return;
    toast("Mock saved \u2713");
    renderMocks();
  });
}

function renderMockList(mocks) {
  const box = document.getElementById("mock-list");
  if (!mocks.length) { box.innerHTML = '<div class="empty-state">No mocks logged yet</div>'; return; }
  box.innerHTML = mocks.map(m => `
    <div class="panel panel-raised panel-tight mb">
      <div class="flex-between">
        <div>
          <strong>${escapeHTML(m.series_name || "Mock")}</strong>
          <span class="subtle"> &middot; ${escapeHTML(m.date)}</span>
        </div>
        <div class="num" style="font-size:18px;">${m.overall_score}${m.overall_percentile ? ` <span class="subtle">(${m.overall_percentile}%ile)</span>` : ""}</div>
      </div>
      ${m.sections.length ? `
        <div class="grid grid-3 mt">
          ${m.sections.map(sec => `
            <div class="small">
              <span class="section-color-${sec.section.toLowerCase()}">${sec.section}</span>
              <span class="subtle"> &middot; ${sec.attempts ?? "?"} att / ${sec.accuracy_pct !== null ? sec.accuracy_pct + "% acc" : "?"} ${sec.score !== null ? "&middot; score " + sec.score : ""}</span>
            </div>
          `).join("")}
        </div>
      ` : ""}
      ${m.notes ? `<div class="subtle mt">${escapeHTML(m.notes)}</div>` : ""}
    </div>
  `).join("");
}

// ---------------------------------------------------------------------
// ERROR LOG
// ---------------------------------------------------------------------
async function renderErrors() {
  const s = document.getElementById("screen-errors");
  s.innerHTML = '<div class="empty-state">Loading\u2026</div>';
  const [data, syllabus, mocks] = await Promise.all([
    API.get("/api/errors"), API.get("/api/syllabus"), API.get("/api/mocks")
  ]);

  s.innerHTML = `
    <div class="eyebrow">Track every mistake</div>
    <h1 class="mb">Error Log</h1>

    <div class="grid grid-2 mb">
      <div class="panel">
        <h3>By reason</h3>
        <div id="err-reason-chart"></div>
      </div>
      <div class="panel">
        <h3>By section</h3>
        <div id="err-section-chart"></div>
      </div>
    </div>

    <div class="panel mb">
      <h3>Log a mistake</h3>
      <div id="error-form"></div>
    </div>

    <div class="panel">
      <h3>Recent entries</h3>
      <div id="error-list"></div>
    </div>
  `;

  Charts.hBarChart(document.getElementById("err-reason-chart"),
    data.breakdown_by_reason.map(r => ({ label: r.reason, value: r.count, color: "#E8B94A" })));
  Charts.hBarChart(document.getElementById("err-section-chart"),
    data.breakdown_by_section.map(r => ({ label: r.section, value: r.count, color: SECTION_COLORS[r.section] })));

  const form = document.getElementById("error-form");
  const topicOpts = syllabus.topics.map(t => `<option value="${t.id}" data-section="${t.section}">${t.section} \u2014 ${t.topic_name}</option>`).join("");
  const mockOpts = mocks.mocks.map(m => `<option value="${m.id}">${m.date} \u2014 ${m.series_name || "mock"}</option>`).join("");
  form.innerHTML = `
    <div class="form-grid">
      <div class="field"><label>Date *</label><input type="date" id="e-date" value="${localDate()}"></div>
      <div class="field"><label>Topic</label><select id="e-topic"><option value="">\u2014</option>${topicOpts}</select></div>
      <div class="field"><label>Linked mock</label><select id="e-mock"><option value="">\u2014</option>${mockOpts}</select></div>
      <div class="field"><label>Reason</label>
        <select id="e-reason"><option value="">\u2014</option>${data.reason_tags.map(r => `<option value="${r}">${r}</option>`).join("")}</select>
      </div>
      <div class="field" style="grid-column: span 2;"><label>Notes</label><input type="text" id="e-notes"></div>
    </div>
    <button class="btn mt" id="e-submit">Add entry</button>
  `;

  document.getElementById("e-topic").addEventListener("change", (ev) => {
    const opt = ev.target.selectedOptions[0];
    // no-op, section auto derived server-side isn't required; we send section from data attr
  });

  document.getElementById("e-submit").addEventListener("click", async () => {
    const dateV = document.getElementById("e-date").value;
    if (!dateV) { toast("Date is required"); return; }
    const topicSel = document.getElementById("e-topic");
    const section = topicSel.value ? topicSel.selectedOptions[0].dataset.section : null;
    const result = await save(() => API.post("/api/errors", {
      date: dateV,
      topic_id: topicSel.value ? parseInt(topicSel.value) : null,
      mock_id_nullable: document.getElementById("e-mock").value ? parseInt(document.getElementById("e-mock").value) : null,
      section,
      reason_tag: document.getElementById("e-reason").value || null,
      notes: document.getElementById("e-notes").value || null,
    }));
    if (!result) return;
    toast("Logged \u2713");
    renderErrors();
  });

  renderErrorList(data.entries);
}

function renderErrorList(entries) {
  const box = document.getElementById("error-list");
  if (!entries.length) { box.innerHTML = '<div class="empty-state">No mistakes logged yet</div>'; return; }
  box.innerHTML = entries.slice(0, 30).map(e => `
    <div class="topic-row" style="grid-template-columns: 90px 1fr 140px 1fr;">
      <div class="mono small subtle">${e.date}</div>
      <div>${e.topic_name || "\u2014"} ${e.topic_section ? `<span class="badge ${e.topic_section.toLowerCase()}">${e.topic_section}</span>` : ""}</div>
      <div>${e.reason_tag ? `<span class="badge" style="border-color:var(--accent-gold);color:var(--accent-gold)">${e.reason_tag}</span>` : ""}</div>
      <div class="subtle small">${escapeHTML(e.notes || "")}</div>
    </div>
  `).join("");
}

// ---------------------------------------------------------------------
// PREDICTOR
// ---------------------------------------------------------------------
async function renderPredictor() {
  const s = document.getElementById("screen-predictor");
  s.innerHTML = '<div class="empty-state">Loading\u2026</div>';
  const data = await API.get("/api/predictor");

  const mock = data.mock_based;
  const prep = data.prep_based;

  s.innerHTML = `
    <div class="eyebrow">Where you might land</div>
    <h1 class="mb">Predictor</h1>

    <div class="grid grid-2">
      <div class="panel">
        <h3>Mock-based estimate</h3>
        ${mock ? `
          <div class="predictor-range">${mock.overall_percentile_range ? mock.overall_percentile_range[0] : "\u2014"}<span class="sep">\u2013</span>${mock.overall_percentile_range ? mock.overall_percentile_range[1] : ""}<span style="font-size:16px;">%ile</span></div>
          <div class="predictor-sub">based on your last ${mock.basis_mocks} mock${mock.basis_mocks > 1 ? "s" : ""}, avg overall score ${mock.avg_overall_score}</div>
          <div class="grid grid-3 mt">
            ${["varc", "dilr", "qa"].map(k => `
              <div class="panel-raised panel-tight" style="border-radius:6px;">
                <div class="small section-color-${k === 'varc' ? 'varc' : k}" style="font-family:var(--font-mono)">${k.toUpperCase()}</div>
                <div class="num" style="font-size:15px;">${mock.section_percentile_ranges[k] ? mock.section_percentile_ranges[k].join("\u2013") + "%ile" : "\u2014"}</div>
              </div>
            `).join("")}
          </div>
          <div class="predictor-note">${mock.note}</div>
        ` : `<div class="empty-state">Log a mock to see this estimate</div>`}
      </div>

      <div class="panel">
        <h3>Prep-based rough estimate</h3>
        <div class="predictor-range" style="color:var(--accent-gold)">${prep.estimated_percentile_range[0]}<span class="sep">\u2013</span>${prep.estimated_percentile_range[1]}<span style="font-size:16px;">%ile</span></div>
        <div class="predictor-sub">weighted syllabus completion ${prep.weighted_completion_pct}% &middot; ${prep.weeks_remaining} weeks left</div>
        <div class="predictor-note">${prep.note}</div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------
// ANALYTICS
// ---------------------------------------------------------------------
async function renderAnalytics() {
  const s = document.getElementById("screen-analytics");
  s.innerHTML = '<div class="empty-state">Loading\u2026</div>';
  const data = await API.get("/api/analytics");

  s.innerHTML = `
    <div class="eyebrow">The full picture</div>
    <h1 class="mb">Analytics</h1>

    <div class="panel mb">
      <h3>Daily activity</h3>
      <div class="chart-box" id="an-heatmap"></div>
    </div>

    <div class="grid grid-2 mb">
      <div class="panel">
        <h3>This week vs last week</h3>
        <div id="an-week-compare"></div>
      </div>
      <div class="panel">
        <h3>Mock score trend</h3>
        <div class="chart-box" id="an-mock-trend"></div>
      </div>
    </div>

    <div class="panel mb">
      <h3>Weightage vs completion gap (top 15)</h3>
      <div class="subtle mb">Highest-weight topics with the least coverage \u2014 biggest opportunity first.</div>
      <div class="chart-box" id="an-gap-chart"></div>
    </div>

    <div class="grid grid-2">
      <div class="panel">
        <h3>Questions logged over time, by section</h3>
        <div class="chart-box" id="an-section-series"></div>
      </div>
      <div class="panel">
        <h3>Mistake reasons</h3>
        <div class="chart-box" id="an-reason-chart"></div>
      </div>
    </div>
  `;

  Charts.heatmap(document.getElementById("an-heatmap"), data.heatmap);

  const wc = document.getElementById("an-week-compare");
  const maxWC = Math.max(data.this_week_total, data.last_week_total, 1);
  wc.innerHTML = `
    <div class="mb">
      <div class="flex-between small subtle"><span>This week (W${data.current_week})</span><span class="num">${data.this_week_total}</span></div>
      <div class="pbar-track"><div class="pbar-fill signal" style="width:${data.this_week_total/maxWC*100}%"></div></div>
    </div>
    <div>
      <div class="flex-between small subtle"><span>Last week</span><span class="num">${data.last_week_total}</span></div>
      <div class="pbar-track"><div class="pbar-fill" style="width:${data.last_week_total/maxWC*100}%"></div></div>
    </div>
  `;

  Charts.lineChart(document.getElementById("an-mock-trend"), [
    { name: "Overall", color: "#FF5A36", points: data.mock_trend.map(m => ({ x: m.date.slice(5), y: m.overall_score })) }
  ]);

  Charts.hBarChart(document.getElementById("an-gap-chart"),
    data.gap_data.map(g => ({ label: `${g.topic_name}`, value: g.gap, color: SECTION_COLORS[g.section] })),
    { labelWidth: 200 });

  const secSeries = Object.keys(data.section_series).map(sec => ({
    name: sec, color: SECTION_COLORS[sec],
    points: data.section_series[sec].map(p => ({ x: p.date.slice(5), y: p.count }))
  })).filter(s => s.points.length > 0);
  if (secSeries.length) {
    Charts.lineChart(document.getElementById("an-section-series"), secSeries);
  } else {
    document.getElementById("an-section-series").innerHTML = '<div class="empty-state">No logs yet</div>';
  }

  Charts.hBarChart(document.getElementById("an-reason-chart"),
    data.reason_breakdown.map(r => ({ label: r.reason, value: r.count, color: "#E8B94A" })));
}

// ---------------------------------------------------------------------
// SETTINGS
// ---------------------------------------------------------------------
async function renderSettings() {
  const s = document.getElementById("screen-settings");
  s.innerHTML = '<div class="empty-state">Loading\u2026</div>';
  const [settings, weeks] = await Promise.all([API.get("/api/settings"), API.get("/api/weeks")]);

  s.innerHTML = `
    <div class="eyebrow">Configure the tracker</div>
    <h1 class="mb">Settings</h1>

    <div class="grid grid-2 mb">
      <div class="panel">
        <h3>Persona commentary</h3>
        <div class="field mb">
          <label>Frequency</label>
          <select id="st-persona">
            <option value="once_per_day" ${settings.persona_frequency === "once_per_day" ? "selected" : ""}>Once per app-open, per day</option>
            <option value="always" ${settings.persona_frequency === "always" ? "selected" : ""}>Every time Home loads</option>
            <option value="off" ${settings.persona_frequency === "off" ? "selected" : ""}>Off</option>
          </select>
        </div>
        <h3>Schedule adherence mode</h3>
        <div class="field">
          <select id="st-adherence">
            <option value="flexible" ${settings.schedule_adherence_mode === "flexible" ? "selected" : ""}>Flexible \u2014 browse any week freely</option>
            <option value="strict" ${settings.schedule_adherence_mode === "strict" ? "selected" : ""}>Strict \u2014 emphasize current week only</option>
          </select>
        </div>
        <button class="btn mt" id="st-save">Save settings</button>
      </div>

      <div class="panel">
        <h3>Backup & export</h3>
        <div class="subtle mb">Your data lives entirely in <span class="mono">cat_tracker.db</span>, next to the app. Copy that file anywhere to back it up, or export a JSON snapshot below.</div>
        <button class="btn secondary" id="st-export">Download JSON snapshot</button>
      </div>
    </div>

    <div class="panel">
      <h3>Edit the pre-loaded plan</h3>
      <div class="subtle mb">Adjust weekly targets if your schedule shifts.</div>
      <div id="st-plan-editor"></div>
    </div>
  `;

  document.getElementById("st-save").addEventListener("click", async () => {
    const result = await save(() => API.post("/api/settings", {
      persona_frequency: document.getElementById("st-persona").value,
      schedule_adherence_mode: document.getElementById("st-adherence").value,
    }));
    if (!result) return;
    toast("Settings saved \u2713");
  });

  document.getElementById("st-export").addEventListener("click", async () => {
    const dump = await API.get("/api/export/json");
    const blob = new Blob([JSON.stringify(dump, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `cat_tracker_backup_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast("Snapshot downloaded \u2713");
  });

  const editor = document.getElementById("st-plan-editor");
  editor.innerHTML = weeks.weeks.map(w => `
    <div class="mb">
      <div class="mono small subtle mb">Week ${w.week_num} &middot; ${w.start_date} \u2192 ${w.end_date}</div>
      ${w.topics.map(t => `
        <div class="topic-row" style="grid-template-columns: 1fr 60px 90px 70px;">
          <div>${t.section} \u2014 ${escapeHTML(t.topic_name)}</div>
          <input type="number" class="log-input" value="${t.target_count}" id="pt-${t.id}" style="width:64px;">
          <span class="subtle small">${t.unit}</span>
          <button class="log-btn" data-plan-topic="${t.id}">Update</button>
        </div>
      `).join("")}
    </div>
  `).join("");

  editor.querySelectorAll("[data-plan-topic]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.planTopic;
      const val = document.getElementById(`pt-${id}`).value;
      const result = await save(() => API.post(`/api/settings/plan_topic/${id}`, { target_count: parseInt(val) }));
      if (!result) return;
      toast("Target updated \u2713");
    });
  });
}

// ---------------------------------------------------------------------
// boot
// ---------------------------------------------------------------------
renderHome();
