import json
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, request, render_template

import db
import persona
import predictor
from seed_data import EXAM_DATE

app = Flask(__name__)

SECTIONS = ["QA", "DILR", "VARC"]
REASON_TAGS = ["silly error", "concept gap", "misread", "time pressure", "guessed wrong"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def today_str():
    return date.today().isoformat()


def parse_iso_date(value, field="date"):
    """Validate an ISO date supplied by the browser and return its value."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a date in YYYY-MM-DD format")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field} must be a date in YYYY-MM-DD format") from exc
    return value


def json_error(message, status=400):
    return jsonify({"error": message}), status


def get_settings(conn):
    return dict(conn.execute("SELECT * FROM settings WHERE id=1").fetchone())


def compute_streak(conn):
    row = conn.execute("SELECT * FROM streak_state WHERE id=1").fetchone()
    return row["current_streak"], row["last_log_date"]


def bump_streak(conn, log_date_str):
    row = conn.execute("SELECT * FROM streak_state WHERE id=1").fetchone()
    cur, last = row["current_streak"], row["last_log_date"]
    log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date()

    if last is None:
        new_streak = 1
    else:
        last_date = datetime.strptime(last, "%Y-%m-%d").date()
        delta = (log_date - last_date).days
        if delta == 0:
            new_streak = cur
        elif delta == 1:
            new_streak = cur + 1
        elif delta > 1:
            new_streak = 1
        else:
            # backdated log earlier than last_date - don't disturb streak/last_log_date
            return
    conn.execute(
        "UPDATE streak_state SET current_streak=?, last_log_date=? WHERE id=1",
        (new_streak, log_date_str),
    )
    conn.commit()


def syllabus_with_completion(conn):
    rows = conn.execute("SELECT * FROM syllabus_master ORDER BY section, historical_weight DESC").fetchall()
    out = []
    for r in rows:
        weight = r["historical_weight"]
        done = r["total_done"]
        # completion target heuristic: treat 2x historical_weight as "full mastery" volume
        # so completion isn't capped oddly for low-weight topics with any real practice.
        target = max(weight * 2, 10)
        pct = min(100.0, round((done / target) * 100, 1)) if target else 0.0
        out.append({
            "id": r["id"],
            "section": r["section"],
            "topic_name": r["topic_name"],
            "historical_weight": weight,
            "volatile_flag": bool(r["volatile_flag"]),
            "total_done": done,
            "completion_pct": pct,
        })
    return out


def plan_progress(conn):
    """Returns plan_topics rows joined with sum(daily_logs.count_done) for that plan_topic."""
    rows = conn.execute("""
        SELECT pt.id, pt.week_num, pt.section, pt.topic_name, pt.target_count, pt.unit,
               COALESCE(SUM(dl.count_done), 0) as done
        FROM plan_topics pt
        LEFT JOIN daily_logs dl ON dl.plan_topic_id = pt.id
        GROUP BY pt.id
        ORDER BY pt.week_num, pt.section, pt.id
    """).fetchall()
    out = []
    for r in rows:
        pct = min(100.0, round((r["done"] / r["target_count"]) * 100, 1)) if r["target_count"] else 0.0
        out.append({
            "id": r["id"], "week_num": r["week_num"], "section": r["section"],
            "topic_name": r["topic_name"], "target_count": r["target_count"],
            "unit": r["unit"], "done": r["done"], "completion_pct": pct,
        })
    return out


def current_week_num(conn):
    weeks = conn.execute("SELECT * FROM weeks ORDER BY week_num").fetchall()
    t = date.today()
    for w in weeks:
        s = datetime.strptime(w["start_date"], "%Y-%m-%d").date()
        e = datetime.strptime(w["end_date"], "%Y-%m-%d").date()
        if s <= t <= e:
            return w["week_num"]
    if weeks and t < datetime.strptime(weeks[0]["start_date"], "%Y-%m-%d").date():
        return weeks[0]["week_num"]
    if weeks:
        return weeks[-1]["week_num"]
    return 1


def build_persona_context(conn):
    ctx = {}

    # days since last log per section
    sections_gap = {}
    for sec in SECTIONS:
        row = conn.execute("""
            SELECT MAX(dl.date) as last_date FROM daily_logs dl
            JOIN syllabus_master sm ON sm.id = dl.topic_id
            WHERE sm.section = ?
        """, (sec,)).fetchone()
        if row and row["last_date"]:
            last = datetime.strptime(row["last_date"], "%Y-%m-%d").date()
            sections_gap[sec] = (date.today() - last).days
        else:
            sections_gap[sec] = None
    ctx["section_days_since_log"] = sections_gap

    # last two mocks, per-section attempts/accuracy
    mocks = conn.execute("SELECT * FROM mocks ORDER BY date DESC, id DESC LIMIT 2").fetchall()
    pairs = {sec: (None, None) for sec in SECTIONS}
    if len(mocks) >= 1:
        curr = mocks[0]
        prev = mocks[1] if len(mocks) > 1 else None
        for sec in SECTIONS:
            curr_row = conn.execute(
                "SELECT * FROM mock_sections WHERE mock_id=? AND section=?", (curr["id"], sec)
            ).fetchone()
            prev_row = None
            if prev:
                prev_row = conn.execute(
                    "SELECT * FROM mock_sections WHERE mock_id=? AND section=?", (prev["id"], sec)
                ).fetchone()

            def to_dict(row):
                if not row or row["attempts"] in (None, 0) or row["correct"] is None:
                    return None
                acc = (row["correct"] / row["attempts"]) * 100 if row["attempts"] else None
                return {"attempts": row["attempts"], "accuracy": acc}

            pairs[sec] = (to_dict(prev_row), to_dict(curr_row))
    ctx["mock_pairs_by_section"] = pairs

    ctx["syllabus_topics"] = syllabus_with_completion(conn)

    recent_mocks = conn.execute(
        "SELECT * FROM mocks ORDER BY date ASC, id ASC"
    ).fetchall()
    ctx["recent_overall_scores"] = [m["overall_score"] for m in recent_mocks[-3:]]

    streak, _ = compute_streak(conn)
    ctx["current_streak"] = streak

    return ctx


# ---------------------------------------------------------------------------
# page shell
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API: home / summary
# ---------------------------------------------------------------------------

@app.route("/api/summary")
def api_summary():
    conn = db.get_conn()
    settings = get_settings(conn)
    exam = datetime.strptime(settings["exam_date"], "%Y-%m-%d").date()
    days_left = (exam - date.today()).days

    streak, last_log = compute_streak(conn)

    topics = syllabus_with_completion(conn)
    focus_topic = None
    if topics:
        gaps = [(t, t["historical_weight"] - (t["historical_weight"] * t["completion_pct"] / 100)) for t in topics]
        gaps.sort(key=lambda x: x[1], reverse=True)
        focus_topic = gaps[0][0] if gaps and gaps[0][1] > 0 else None

    weeks = conn.execute("SELECT COUNT(*) c FROM weeks").fetchone()["c"]
    cur_week = current_week_num(conn)

    persona_lines = []
    show_persona = True
    if settings["persona_frequency"] == "once_per_day" and settings["last_persona_shown_date"] == today_str():
        show_persona = False
    if settings["persona_frequency"] == "off":
        show_persona = False

    if show_persona:
        ctx = build_persona_context(conn)
        persona_lines = persona.generate_persona_lines(ctx, max_lines=2)
        conn.execute("UPDATE settings SET last_persona_shown_date=? WHERE id=1", (today_str(),))
        conn.commit()

    total_target = conn.execute("SELECT SUM(target_count) t FROM plan_topics").fetchone()["t"] or 0
    total_done = conn.execute("SELECT COALESCE(SUM(count_done),0) d FROM daily_logs").fetchone()["d"] or 0
    overall_plan_pct = round((total_done / total_target) * 100, 1) if total_target else 0.0

    conn.close()
    return jsonify({
        "days_left": days_left,
        "exam_date": settings["exam_date"],
        "streak": streak,
        "last_log_date": last_log,
        "current_week": cur_week,
        "total_weeks": weeks,
        "focus_topic": focus_topic,
        "persona_lines": persona_lines,
        "overall_plan_completion_pct": overall_plan_pct,
    })


# ---------------------------------------------------------------------------
# API: weeks / plan
# ---------------------------------------------------------------------------

@app.route("/api/weeks")
def api_weeks():
    conn = db.get_conn()
    weeks = conn.execute("SELECT * FROM weeks ORDER BY week_num").fetchall()
    progress = plan_progress(conn)
    cur = current_week_num(conn)
    conn.close()

    by_week = {}
    for w in weeks:
        by_week[w["week_num"]] = {
            "week_num": w["week_num"], "start_date": w["start_date"], "end_date": w["end_date"],
            "is_current": w["week_num"] == cur, "topics": [],
        }
    for p in progress:
        by_week[p["week_num"]]["topics"].append(p)

    return jsonify({"weeks": list(by_week.values()), "current_week": cur})


@app.route("/api/log", methods=["POST"])
def api_log():
    data = request.get_json(silent=True) or {}
    try:
        log_date = parse_iso_date(data.get("date") or today_str())
        count_done = int(data.get("count_done"))
    except (TypeError, ValueError):
        return json_error("count_done must be a whole number and date must use YYYY-MM-DD")
    plan_topic_id = data.get("plan_topic_id")
    topic_id = data.get("topic_id")  # syllabus_master id, optional
    unit = data.get("unit")
    notes = data.get("notes")

    if count_done <= 0:
        return json_error("count_done must be greater than zero")

    conn = db.get_conn()

    pt = None
    # auto-resolve syllabus_master topic from plan_topic name/section if not given
    if plan_topic_id:
        pt = conn.execute("SELECT * FROM plan_topics WHERE id=?", (plan_topic_id,)).fetchone()
        if not pt:
            conn.close()
            return json_error("The selected plan topic no longer exists", 404)
        if not topic_id and pt["syllabus_topic_id"]:
            topic_id = pt["syllabus_topic_id"]

    if topic_id and not conn.execute("SELECT 1 FROM syllabus_master WHERE id=?", (topic_id,)).fetchone():
        conn.close()
        return json_error("The selected syllabus topic no longer exists", 404)

    conn.execute(
        "INSERT INTO daily_logs (date, topic_id, count_done, unit, notes, plan_topic_id) VALUES (?,?,?,?,?,?)",
        (log_date, topic_id, count_done, unit, notes, plan_topic_id),
    )
    if topic_id:
        conn.execute(
            "UPDATE syllabus_master SET total_done = total_done + ? WHERE id=?",
            (count_done, topic_id),
        )
    conn.commit()
    bump_streak(conn, log_date)
    conn.close()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# API: syllabus master
# ---------------------------------------------------------------------------

@app.route("/api/syllabus")
def api_syllabus():
    conn = db.get_conn()
    topics = syllabus_with_completion(conn)
    conn.close()

    by_section = {s: [] for s in SECTIONS}
    for t in topics:
        by_section[t["section"]].append(t)

    section_stats = {}
    for s in SECTIONS:
        items = by_section[s]
        if items:
            avg_pct = sum(t["completion_pct"] for t in items) / len(items)
        else:
            avg_pct = 0
        section_stats[s] = round(avg_pct, 1)

    return jsonify({"topics": topics, "by_section": by_section, "section_completion_pct": section_stats})


# ---------------------------------------------------------------------------
# API: mocks
# ---------------------------------------------------------------------------

@app.route("/api/mocks", methods=["GET", "POST"])
def api_mocks():
    conn = db.get_conn()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if not data.get("date") or data.get("overall_score") is None:
            conn.close()
            return json_error("date and overall_score are required")
        try:
            mock_date = parse_iso_date(data["date"])
            overall_score = float(data["overall_score"])
        except (TypeError, ValueError):
            conn.close()
            return json_error("Use a valid date and numeric overall score")
        cur = conn.execute(
            "INSERT INTO mocks (date, series_name, overall_score, overall_percentile, notes) VALUES (?,?,?,?,?)",
            (mock_date, data.get("series_name"), overall_score,
             data.get("overall_percentile"), data.get("notes")),
        )
        mock_id = cur.lastrowid
        for sec_data in data.get("sections", []):
            if not sec_data.get("section"):
                continue
            conn.execute(
                """INSERT INTO mock_sections
                   (mock_id, section, attempts, correct, wrong, score, percentile, time_taken_min)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (mock_id, sec_data["section"], sec_data.get("attempts"), sec_data.get("correct"),
                 sec_data.get("wrong"), sec_data.get("score"), sec_data.get("percentile"),
                 sec_data.get("time_taken_min")),
            )
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "mock_id": mock_id})

    mocks = conn.execute("SELECT * FROM mocks ORDER BY date DESC, id DESC").fetchall()
    out = []
    for m in mocks:
        secs = conn.execute("SELECT * FROM mock_sections WHERE mock_id=?", (m["id"],)).fetchall()
        sec_list = []
        for s in secs:
            acc = round((s["correct"] / s["attempts"]) * 100, 1) if s["attempts"] and s["correct"] is not None else None
            sec_list.append({**dict(s), "accuracy_pct": acc})
        out.append({**dict(m), "sections": sec_list})
    conn.close()
    return jsonify({"mocks": out})


# ---------------------------------------------------------------------------
# API: error log
# ---------------------------------------------------------------------------

@app.route("/api/errors", methods=["GET", "POST"])
def api_errors():
    conn = db.get_conn()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if not data.get("date"):
            conn.close()
            return json_error("date is required")
        try:
            error_date = parse_iso_date(data["date"])
        except ValueError as exc:
            conn.close()
            return json_error(str(exc))

        reason_tag = data.get("reason_tag")
        if reason_tag is not None and reason_tag not in REASON_TAGS:
            conn.close()
            return json_error("Invalid reason tag", 400)

        conn.execute(
            """INSERT INTO error_log (date, topic_id, mock_id_nullable, section, reason_tag, notes)
               VALUES (?,?,?,?,?,?)""",
            (error_date, data.get("topic_id"), data.get("mock_id_nullable"),
             data.get("section"), reason_tag, data.get("notes")),
        )
        conn.commit()
        conn.close()
        return jsonify({"ok": True})

    rows = conn.execute("""
         SELECT el.*, sm.topic_name as topic_name, sm.section as topic_section,
             m.date as mock_date, m.series_name as mock_series
        FROM error_log el LEFT JOIN syllabus_master sm ON sm.id = el.topic_id
         LEFT JOIN mocks m ON m.id = el.mock_id_nullable
        ORDER BY el.date DESC, el.id DESC
    """).fetchall()

    breakdown_reason = conn.execute("""
        SELECT reason_tag, COUNT(*) c FROM error_log WHERE reason_tag IS NOT NULL GROUP BY reason_tag
    """).fetchall()
    breakdown_section = conn.execute("""
        SELECT section, COUNT(*) c FROM error_log WHERE section IS NOT NULL GROUP BY section
    """).fetchall()
    total = conn.execute("SELECT COUNT(*) c FROM error_log").fetchone()["c"]
    conn.close()

    return jsonify({
        "entries": [dict(r) for r in rows],
        "reason_tags": REASON_TAGS,
        "breakdown_by_reason": [{"reason": r["reason_tag"], "count": r["c"],
                                  "pct": round(r["c"] / total * 100, 1) if total else 0} for r in breakdown_reason],
        "breakdown_by_section": [{"section": r["section"], "count": r["c"]} for r in breakdown_section],
    })


# ---------------------------------------------------------------------------
# API: predictor
# ---------------------------------------------------------------------------

@app.route("/api/predictor")
def api_predictor():
    conn = db.get_conn()
    mocks = conn.execute("SELECT * FROM mocks ORDER BY date DESC, id DESC LIMIT 3").fetchall()
    sections_by_mock = {}
    for m in mocks:
        secs = conn.execute("SELECT * FROM mock_sections WHERE mock_id=?", (m["id"],)).fetchall()
        sections_by_mock[m["id"]] = secs

    mock_est = predictor.mock_based_estimate(mocks, sections_by_mock)

    topics = syllabus_with_completion(conn)
    total_weight = sum(t["historical_weight"] for t in topics) or 1
    weighted_completion = sum(t["historical_weight"] * t["completion_pct"] for t in topics) / total_weight

    # crude accuracy trend from last up-to-3 mocks' avg section accuracy
    accuracy_trend = None
    accs = []
    for m in reversed(mocks):  # oldest first
        secs = sections_by_mock[m["id"]]
        vals = [ (s["correct"]/s["attempts"]*100) for s in secs if s["attempts"] and s["correct"] is not None ]
        if vals:
            accs.append(sum(vals)/len(vals))
    if len(accs) >= 2:
        diff = accs[-1] - accs[0]
        accuracy_trend = max(-1.0, min(1.0, diff / 20))

    settings = get_settings(conn)
    exam_date = datetime.strptime(settings["exam_date"], "%Y-%m-%d").date()
    prep_est = predictor.prep_based_estimate(weighted_completion, accuracy_trend, exam_date=exam_date)
    conn.close()

    return jsonify({"mock_based": mock_est, "prep_based": prep_est})


# ---------------------------------------------------------------------------
# API: analytics
# ---------------------------------------------------------------------------

@app.route("/api/analytics")
def api_analytics():
    conn = db.get_conn()

    # calendar heatmap: date -> total count_done (last 120 days incl future window irrelevant)
    heat_rows = conn.execute("""
        SELECT date, SUM(count_done) as total FROM daily_logs GROUP BY date ORDER BY date
    """).fetchall()
    heatmap = [{"date": r["date"], "count": r["total"]} for r in heat_rows]

    # section-wise questions logged over time (weekly buckets by ISO week)
    sec_rows = conn.execute("""
        SELECT dl.date, sm.section, SUM(dl.count_done) as total
        FROM daily_logs dl JOIN syllabus_master sm ON sm.id = dl.topic_id
        GROUP BY dl.date, sm.section ORDER BY dl.date
    """).fetchall()
    section_series = {s: [] for s in SECTIONS}
    for r in sec_rows:
        section_series[r["section"]].append({"date": r["date"], "count": r["total"]})

    # weightage vs completion gap per section
    topics = syllabus_with_completion(conn)
    gap_data = []
    for t in topics:
        expected_pct_of_ideal = t["completion_pct"]
        gap_data.append({
            "section": t["section"], "topic_name": t["topic_name"],
            "historical_weight": t["historical_weight"], "completion_pct": expected_pct_of_ideal,
            "gap": round(t["historical_weight"] * (100 - expected_pct_of_ideal) / 100, 1),
        })
    gap_data.sort(key=lambda x: x["gap"], reverse=True)

    # mock trend
    mocks = conn.execute("SELECT date, overall_score, overall_percentile FROM mocks ORDER BY date ASC").fetchall()
    mock_trend = [dict(m) for m in mocks]

    # this week vs last week
    cur_week = current_week_num(conn)
    def week_total(wn):
        row = conn.execute("""
            SELECT COALESCE(SUM(dl.count_done),0) t FROM daily_logs dl
            JOIN plan_topics pt ON pt.id = dl.plan_topic_id
            WHERE pt.week_num = ?
        """, (wn,)).fetchone()
        return row["t"]
    this_week_total = week_total(cur_week)
    last_week_total = week_total(cur_week - 1) if cur_week > 1 else 0

    # mistake reason breakdown (reuse errors logic quickly)
    total_err = conn.execute("SELECT COUNT(*) c FROM error_log").fetchone()["c"]
    reason_breakdown = conn.execute("""
        SELECT reason_tag, COUNT(*) c FROM error_log WHERE reason_tag IS NOT NULL GROUP BY reason_tag
    """).fetchall()

    conn.close()
    return jsonify({
        "heatmap": heatmap,
        "section_series": section_series,
        "gap_data": gap_data[:15],
        "mock_trend": mock_trend,
        "this_week_total": this_week_total,
        "last_week_total": last_week_total,
        "current_week": cur_week,
        "reason_breakdown": [{"reason": r["reason_tag"], "count": r["c"],
                               "pct": round(r["c"]/total_err*100,1) if total_err else 0} for r in reason_breakdown],
    })


# ---------------------------------------------------------------------------
# API: settings
# ---------------------------------------------------------------------------

@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    conn = db.get_conn()
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        fields = []
        vals = []
        for key in ("theme", "persona_frequency", "schedule_adherence_mode", "exam_date"):
            if key in data:
                fields.append(f"{key}=?")
                vals.append(data[key])
        if "persona_frequency" in data and data["persona_frequency"] not in ("once_per_day", "always", "off"):
            conn.close()
            return json_error("Invalid persona frequency")
        if "schedule_adherence_mode" in data and data["schedule_adherence_mode"] not in ("flexible", "strict"):
            conn.close()
            return json_error("Invalid schedule adherence mode")
        if "exam_date" in data:
            try:
                parse_iso_date(data["exam_date"], "exam_date")
            except ValueError as exc:
                conn.close()
                return json_error(str(exc))
        if fields:
            vals.append(1)
            conn.execute(f"UPDATE settings SET {', '.join(fields)} WHERE id=?", vals)
            conn.commit()
        conn.close()
        return jsonify({"ok": True})

    s = get_settings(conn)
    conn.close()
    return jsonify(s)


@app.route("/api/settings/plan_topic/<int:topic_id>", methods=["POST"])
def api_edit_plan_topic(topic_id):
    data = request.get_json(silent=True) or {}
    conn = db.get_conn()
    fields, vals = [], []
    for key in ("target_count", "topic_name", "unit", "week_num"):
        if key in data:
            fields.append(f"{key}=?")
            vals.append(data[key])
    if "target_count" in data:
        try:
            if int(data["target_count"]) < 0:
                raise ValueError
        except (TypeError, ValueError):
            return json_error("Target must be a non-negative whole number")
    if "unit" in data and data["unit"] not in ("q", "set", "psg"):
        return json_error("Unit must be q, set, or psg")
    if fields:
        vals.append(topic_id)
        conn.execute(f"UPDATE plan_topics SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/export/json")
def api_export_json():
    conn = db.get_conn()
    tables = ["weeks", "plan_topics", "syllabus_master", "daily_logs", "mocks",
              "mock_sections", "error_log", "settings", "streak_state"]
    dump = {}
    for t in tables:
        dump[t] = [dict(r) for r in conn.execute(f"SELECT * FROM {t}").fetchall()]
    conn.close()
    return jsonify(dump)


# NOTE: run via `python cat_tracker.py` (see that file for the entrypoint).
