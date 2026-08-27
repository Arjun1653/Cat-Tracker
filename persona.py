"""
Persona commentary rule engine.

Each rule is a function(ctx) -> str|None. `ctx` is a dict of pre-computed
data (see build_context in app.py). A rule returns a message string if its
condition fires on the CURRENT data, or None if it has nothing to say.

To add a new rule: write a function(ctx) -> str|None following the pattern
below, and append it to RULES. Nothing else needs to change.
"""

from datetime import datetime


def rule_untouched_section(ctx):
    """A section untouched for N+ days while others were logged."""
    gaps = ctx.get("section_days_since_log", {})
    if not gaps:
        return None
    touched = [(s, d) for s, d in gaps.items() if d is not None]
    untouched = [(s, d) for s, d in gaps.items() if d is None]
    # "untouched" here means never logged at all - only flag if other sections HAVE logs
    if untouched and touched:
        stale_names = ", ".join(s for s, _ in untouched)
        return f"{stale_names} hasn't seen a single logged question yet, while other sections are moving. Might be worth a short session there."
    # or logged before but gone stale
    stale = [(s, d) for s, d in touched if d is not None and d >= 4]
    if stale and len(stale) < len(touched):
        s, d = max(stale, key=lambda x: x[1])
        return f"{s} has gone quiet for {d} days while you've kept up elsewhere. A quick touch-in would keep it from cooling off."
    return None


def rule_accuracy_vs_attempts(ctx):
    """A mock's accuracy dropped despite more attempts (or vice versa), comparing
    the two most recent mocks section by section."""
    pairs = ctx.get("mock_pairs_by_section", {})
    for section, (prev, curr) in pairs.items():
        if not prev or not curr:
            continue
        pa, pc = prev.get("attempts"), prev.get("accuracy")
        ca, cc = curr.get("attempts"), curr.get("accuracy")
        if None in (pa, pc, ca, cc):
            continue
        if ca > pa and cc < pc - 5:
            return f"In {section}, attempts went up in your latest mock but accuracy slipped by {round(pc - cc)} points. Reaching further isn't paying off there yet \u2014 might be worth dialling back and consolidating."
        if ca < pa and cc > pc + 5:
            return f"In {section}, you attempted fewer questions last mock but accuracy jumped {round(cc - pc)} points. That trade looks like it's working \u2014 worth testing if you can nudge attempts up while holding accuracy."
    return None


def rule_high_weight_untouched(ctx):
    """A high-weightage topic at 0% while low-weightage ones are fully done."""
    topics = ctx.get("syllabus_topics", [])
    if not topics:
        return None
    zero_high = [t for t in topics if t["completion_pct"] == 0 and t["historical_weight"] >= 15]
    done_low = [t for t in topics if t["completion_pct"] >= 95 and t["historical_weight"] <= 6]
    if zero_high and done_low:
        t = max(zero_high, key=lambda x: x["historical_weight"])
        return f"{t['topic_name']} has shown up {t['historical_weight']} times across the last 5 papers and you're at 0% there, while some low-frequency topics are already wrapped. Worth reordering."
    return None


def rule_mock_improvement(ctx):
    """A real improvement across the last 2-3 mocks."""
    scores = ctx.get("recent_overall_scores", [])
    if len(scores) >= 3 and scores[0] < scores[1] < scores[2]:
        gain = round(scores[2] - scores[0], 1)
        return f"Your overall mock score has climbed for three mocks running, up {gain} points total. Whatever you changed, it's working \u2014 keep the pattern going."
    if len(scores) == 2 and scores[1] - scores[0] >= 8:
        gain = round(scores[1] - scores[0], 1)
        return f"Your last mock jumped {gain} points over the one before. Worth noting what was different about that prep block."
    return None


def rule_streak_milestone(ctx):
    streak = ctx.get("current_streak", 0)
    if streak in (7, 14, 21, 30, 45, 60):
        return f"{streak}-day logging streak. That consistency is the whole game \u2014 keep the chain going."
    return None


def rule_para_jumbles_volatility(ctx):
    """Gentle nudge about the flagged-volatile topic, shown only if it's
    being over-weighted relative to its own recent (2024-25) signal."""
    topics = ctx.get("syllabus_topics", [])
    pj = next((t for t in topics if t["topic_name"] == "Para Jumbles" and t.get("volatile_flag")), None)
    if pj and pj["completion_pct"] < 20:
        others_done = [t for t in topics if t["section"] == "VARC" and t["topic_name"] != "Para Jumbles"]
        if others_done and sum(t["completion_pct"] for t in others_done) / len(others_done) > 60:
            return "Para Jumbles is flagged volatile \u2014 CAT 2024 had zero across all slots after a steady run in 2021-23. Worth some coverage, but don't over-invest relative to the rest of VARC."
    return None


RULES = [
    rule_untouched_section,
    rule_accuracy_vs_attempts,
    rule_high_weight_untouched,
    rule_mock_improvement,
    rule_streak_milestone,
    rule_para_jumbles_volatility,
]


def generate_persona_lines(ctx, max_lines=2):
    lines = []
    for rule in RULES:
        try:
            msg = rule(ctx)
        except Exception:
            msg = None
        if msg:
            lines.append(msg)
        if len(lines) >= max_lines:
            break
    return lines
