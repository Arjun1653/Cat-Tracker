from datetime import date, datetime
from seed_data import PERCENTILE_BANDS, EXAM_DATE

NOTE_MOCK = (
    "Estimated from blended 2025 coaching-institute data (IMS / Cracku / Career "
    "Launcher / IQuanta). Real cutoffs can shift roughly \u00b13-5 percentile."
)
NOTE_PREP = (
    "Much rougher than the mock-based estimate \u2014 a heuristic from syllabus "
    "coverage, weeks remaining, and (if available) your accuracy trend. Treat as a "
    "vibe check, not a prediction."
)


def _interp_band(value, lo_band, hi_band, key):
    """Interpolate a percentile for `value` between two adjacent bands on `key`."""
    lo_val = sum(lo_band[key]) / 2
    hi_val = sum(hi_band[key]) / 2
    if hi_val == lo_val:
        return lo_band["pct"]
    frac = (value - lo_val) / (hi_val - lo_val)
    frac = max(0.0, min(1.0, frac))
    return lo_band["pct"] + frac * (hi_band["pct"] - lo_band["pct"])


def score_to_percentile_range(value, key="overall"):
    """Map a score to an estimated percentile RANGE using PERCENTILE_BANDS.
    Bands are given high->low percentile. Returns (low_pct, high_pct) or None."""
    if value is None:
        return None
    bands = sorted(PERCENTILE_BANDS, key=lambda b: b["pct"])  # ascending pct
    # bands ascending pct = ascending score too (mostly)
    lows = [sum(b[key]) / 2 for b in bands]

    if value <= lows[0]:
        # below lowest band - extrapolate down a bit, floor at pct - 15
        span_pct = bands[1]["pct"] - bands[0]["pct"]
        span_val = lows[1] - lows[0] if lows[1] != lows[0] else 1
        frac = (value - lows[0]) / span_val
        pct = bands[0]["pct"] + frac * span_pct
        pct = max(pct, 40.0)
        return (round(pct - 3, 1), round(pct + 3, 1))

    if value >= lows[-1]:
        span_pct = bands[-1]["pct"] - bands[-2]["pct"]
        span_val = lows[-1] - lows[-2] if lows[-1] != lows[-2] else 1
        frac = (value - lows[-1]) / span_val
        pct = bands[-1]["pct"] + frac * span_pct
        pct = min(pct, 99.99)
        return (round(pct - 1, 1), round(pct, 1))

    for i in range(len(bands) - 1):
        if lows[i] <= value <= lows[i + 1]:
            pct = _interp_band(value, bands[i], bands[i + 1], key)
            return (round(pct - 2, 1), round(pct + 2, 1))

    return None


def mock_based_estimate(recent_mocks, recent_sections):
    """recent_mocks: list of mock rows (most recent first, up to 3).
    recent_sections: dict mock_id -> list of section rows."""
    if not recent_mocks:
        return None

    overall_vals = [m["overall_score"] for m in recent_mocks if m["overall_score"] is not None]
    avg_overall = sum(overall_vals) / len(overall_vals) if overall_vals else None

    sec_avgs = {}
    for sec_key, col in (("VARC", "varc"), ("DILR", "dilr"), ("QA", "qa")):
        vals = []
        for m in recent_mocks:
            for row in recent_sections.get(m["id"], []):
                if row["section"] == sec_key and row["score"] is not None:
                    vals.append(row["score"])
        if vals:
            sec_avgs[col] = sum(vals) / len(vals)

    overall_range = score_to_percentile_range(avg_overall, "overall") if avg_overall is not None else None

    sec_ranges = {}
    for col, val in sec_avgs.items():
        sec_ranges[col] = score_to_percentile_range(val, col)

    return {
        "basis_mocks": len(recent_mocks),
        "avg_overall_score": round(avg_overall, 1) if avg_overall is not None else None,
        "overall_percentile_range": overall_range,
        "section_percentile_ranges": sec_ranges,
        "note": NOTE_MOCK,
    }


def prep_based_estimate(weighted_completion_pct, accuracy_trend=None, today=None, exam_date=None):
    """Heuristic: base percentile band nudged by completion % and time pressure,
    then nudged further by recent accuracy trend if available."""
    today = today or date.today()
    # The exam date is user-configurable in Settings.  Keep the estimate in
    # sync with the countdown instead of silently using the seeded date.
    exam = exam_date or datetime.strptime(EXAM_DATE, "%Y-%m-%d").date()
    weeks_remaining = max(0, (exam - today).days / 7)

    # base heuristic curve: completion % maps loosely onto a percentile band,
    # discounted if lots of weeks remain untested (less proof of retention),
    # and boosted if very few weeks remain and completion is already high.
    base = 40 + (weighted_completion_pct / 100) * 55  # 40 -> 95 range

    if weeks_remaining > 10:
        base -= 5  # long runway, less signal yet
    elif weeks_remaining < 3:
        base += 3  # crunch time, completion means more

    if accuracy_trend is not None:
        # accuracy_trend: -1 (worsening) .. 0 .. +1 (improving), scale gently
        base += accuracy_trend * 6

    base = max(35.0, min(99.5, base))
    low = round(max(35.0, base - 7), 1)
    high = round(min(99.9, base + 7), 1)

    return {
        "weighted_completion_pct": round(weighted_completion_pct, 1),
        "weeks_remaining": round(weeks_remaining, 1),
        "estimated_percentile_range": (low, high),
        "note": NOTE_PREP,
    }
