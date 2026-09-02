"""
Seed data extracted from:
    - CAT_2026_Schedule_Updated_7Week.md  (7-week schedule, 3 Sep - 20 Oct 2026)
  - CAT_2026_Syllabus.pdf (chapter-wise question-frequency totals, CAT 2021-2025, all slots)

This module is pure data + is only ever read at first-run seed time.
"""

# ---------------------------------------------------------------------------
# WEEKS  (week_num, start_date, end_date)
# ---------------------------------------------------------------------------
WEEKS = [
    (1, "2026-09-03", "2026-09-09"),
    (2, "2026-09-10", "2026-09-16"),
    (3, "2026-09-17", "2026-09-23"),
    (4, "2026-09-24", "2026-09-30"),
    (5, "2026-10-01", "2026-10-07"),
    (6, "2026-10-08", "2026-10-14"),
    (7, "2026-10-15", "2026-10-20"),
]

EXAM_DATE = "2026-11-29"

# ---------------------------------------------------------------------------
# PLAN TOPICS  (week_num, section, topic_name, target_count, unit)
# unit is exactly as printed in the schedule for that row (q / set / psg)
# ---------------------------------------------------------------------------
PLAN_TOPICS = [
    # Week 1
    (1, "QA", "Averages", 100, "q"),
    (1, "QA", "Percentages", 60, "q"),
    (1, "QA", "Mixtures & Alligations", 40, "q"),
    (1, "QA", "Ratio, Proportion & Variation", 16, "q"),
    (1, "DILR", "Seating Arrangements", 25, "set"),
    (1, "DILR", "Bar Graphs", 25, "set"),
    (1, "DILR", "Caselets", 1, "set"),
    (1, "VARC", "Reading Comprehension", 62, "psg"),

    # Week 2
    (2, "QA", "Ratio, Proportion & Variation", 44, "q"),
    (2, "QA", "Progressions", 50, "q"),
    (2, "QA", "Profit & Loss", 80, "q"),
    (2, "QA", "Time & Work", 42, "q"),
    (2, "DILR", "Caselets", 24, "set"),
    (2, "DILR", "Column Graphs", 25, "set"),
    (2, "DILR", "Line Charts", 2, "set"),
    (2, "VARC", "Reading Comprehension", 62, "psg"),

    # Week 3
    (3, "QA", "Time & Work", 58, "q"),
    (3, "QA", "Time Speed Distance", 80, "q"),
    (3, "QA", "Races", 20, "q"),
    (3, "QA", "Pipes, Trains & Boats", 40, "q"),
    (3, "QA", "Interest", 18, "q"),
    (3, "DILR", "Line Charts", 23, "set"),
    (3, "DILR", "Cubes", 15, "set"),
    (3, "DILR", "Pie Charts", 13, "set"),
    (3, "VARC", "Reading Comprehension", 62, "psg"),

    # Week 4
    (4, "QA", "Interest", 42, "q"),
    (4, "QA", "Linear & Quadratic Equations", 100, "q"),
    (4, "QA", "Inequalities", 74, "q"),
    (4, "DILR", "Pie Charts", 27, "set"),
    (4, "DILR", "Tables", 24, "set"),
    (4, "VARC", "Reading Comprehension", 62, "psg"),

    # Week 5
    (5, "QA", "Inequalities", 6, "q"),
    (5, "QA", "Logarithms", 25, "q"),
    (5, "QA", "Maxima Minima", 25, "q"),
    (5, "QA", "Functions", 80, "q"),
    (5, "QA", "Set Theory", 40, "q"),
    (5, "QA", "Number System", 40, "q"),
    (5, "DILR", "Tables", 11, "set"),
    (5, "DILR", "Venn Diagrams", 35, "set"),
    (5, "DILR", "Games & Tournaments", 5, "set"),
    (5, "VARC", "Reading Comprehension", 32, "psg"),
    (5, "VARC", "Odd One Out", 30, "q"),

    # Week 6
    (6, "QA", "Number System", 160, "q"),
    (6, "QA", "Geometry", 56, "q"),
    (6, "DILR", "Games & Tournaments", 20, "set"),
    (6, "DILR", "Syllogisms", 20, "q"),
    (6, "DILR", "Clocks", 11, "q"),
    (6, "VARC", "Odd One Out", 15, "q"),
    (6, "VARC", "Para Summary", 47, "q"),

    # Week 7
    (7, "QA", "Geometry", 44, "q"),
    (7, "QA", "Coordinate Geometry", 50, "q"),
    (7, "QA", "Probability", 40, "q"),
    (7, "QA", "Permutations & Combinations", 80, "q"),
    (7, "DILR", "Clocks", 9, "q"),
    (7, "DILR", "Logical Sequence & Series", 20, "q"),
    (7, "DILR", "Logical Connectives & Other Reasoning", 20, "q"),
    (7, "VARC", "Para Summary", 13, "q"),
    (7, "VARC", "Para Jumbles", 45, "q"),
]

# ---------------------------------------------------------------------------
# SYLLABUS MASTER  (section, topic_name, historical_weight, volatile_flag)
# historical_weight = Total column (CAT 2021-2025, all slots) from the
# chapter-wise split tables in the syllabus PDF, at leaf-topic granularity.
# ---------------------------------------------------------------------------
SYLLABUS_MASTER = [
    # --- QA ---
    ("QA", "Arithmetics (Ratio & Proportion)", 22, False),
    ("QA", "Averages", 19, False),
    ("QA", "Time Speed Distance", 18, False),
    ("QA", "Profit & Loss", 17, False),
    ("QA", "Time & Work", 15, False),
    ("QA", "Percentage", 13, False),
    ("QA", "Simple Interest, Compound Interest", 12, False),
    ("QA", "Mixture & Alligation", 7, False),
    ("QA", "Pipes & Cisterns / Clocks", 2, False),
    ("QA", "Equations & Polynomials", 34, False),
    ("QA", "Progressions & Series", 28, False),
    ("QA", "Logarithms & Exponents", 20, False),
    ("QA", "Functions & Graphs", 15, False),
    ("QA", "Inequalities & Absolute Value", 12, False),
    ("QA", "Lines & Angles", 19, False),
    ("QA", "Quadrilaterals", 12, False),
    ("QA", "Circles", 6, False),
    ("QA", "Coordinate Geometry", 5, False),
    ("QA", "Polygons", 4, False),
    ("QA", "Mensuration", 1, False),
    ("QA", "Number System", 27, False),
    ("QA", "Factors / Factorials", 7, False),
    ("QA", "Miscellaneous (Number System)", 7, False),
    ("QA", "Properties & Simplification", 6, False),
    ("QA", "Divisibility Rules", 4, False),
    ("QA", "Remainders", 3, False),
    ("QA", "HCF & LCM", 0, False),
    ("QA", "Number System Conversion", 0, False),
    ("QA", "Miscellaneous (Modern Math)", 7, False),
    ("QA", "Permutation, Combination & Probability", 6, False),
    ("QA", "Set Theory", 3, False),

    # --- DILR ---
    ("DILR", "Analytical Reasoning", 16, False),
    ("DILR", "Puzzles", 6, False),
    ("DILR", "Mathematical Reasoning", 4, False),
    ("DILR", "Games & Tournaments", 4, False),
    ("DILR", "Sitting / Standing Arrangement", 3, False),
    ("DILR", "Order & Ranking", 2, False),
    ("DILR", "Set Theory (LR)", 1, False),
    ("DILR", "Group Arrangement", 0, False),
    ("DILR", "Binary & Conditional Logic", 0, False),
    ("DILR", "Logic Based DI", 14, False),
    ("DILR", "Line & Bar Charts", 9, False),
    ("DILR", "Data Tabulation", 6, False),
    ("DILR", "Caselets", 1, False),
    ("DILR", "Pie Charts", 0, False),

    # --- VARC ---
    ("VARC", "Reading Comprehension", 60, False),
    ("VARC", "Para Summary", 39, False),
    ("VARC", "Para Jumbles", 30, True),  # CAT 2024: 0 across all 3 slots after 2-3/slot in 2021-23
    ("VARC", "Missing Sentence / Para Completion", 27, False),
    ("VARC", "Odd One Out", 24, False),
]

# ---------------------------------------------------------------------------
# PREDICTOR TABLE - blended 2025 coaching-institute score->percentile bands
# (overall_low, overall_high, varc_low, varc_high, dilr_low, dilr_high,
#  qa_low, qa_high, percentile)
# ---------------------------------------------------------------------------
PERCENTILE_BANDS = [
    {"pct": 99.9, "overall": (115, 121), "varc": (50, 54), "dilr": (42, 46), "qa": (38, 46)},
    {"pct": 99.0, "overall": (83, 90), "varc": (39, 42), "dilr": (30, 33), "qa": (28, 31)},
    {"pct": 95.0, "overall": (64, 67), "varc": (29, 32), "dilr": (22, 24), "qa": (20, 23)},
    {"pct": 90.0, "overall": (50, 56), "varc": (21, 25), "dilr": (16, 18), "qa": (15, 17)},
    {"pct": 80.0, "overall": (37, 42), "varc": (16, 22), "dilr": (10, 14), "qa": (11, 13)},
]
