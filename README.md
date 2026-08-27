# CAT 2026 Prep Tracker

A local web-app tracker for CAT 2026 prep: a nine-week plan, syllabus master
with five-year weightage, practice logging, mocks, error analysis, a
percentile predictor, analytics, and configurable study feedback. Runs
entirely on your machine — no accounts, no cloud, nothing leaves your
computer.

> **Note on the browser change:** the original spec called for a terminal
> UI (`textual`). Per your instruction this build is a local web app instead
> — a small Python (Flask) server on your machine, opened in your default
> browser, with a single SQLite file next to the app. Everything else (data
> model, screens, rules, "no random numbers", offline-forever) is unchanged.

## One-time setup

```bash
pip install -r requirements.txt
```

That installs Flask — the only dependency. No `npm`, no build step, no
Chart.js CDN — the charts are hand-rolled SVG so the app never needs the
internet after this one install.

## Running it

```bash
python cat_tracker.py
```

This starts a local server at `http://127.0.0.1:5055` and opens it in your
default browser automatically. Leave the terminal window open while you use
the app; close it (Ctrl+C) when you're done. Nothing is exposed outside your
machine — it only listens on `127.0.0.1` (localhost).

If your browser doesn't open automatically, just visit
`http://127.0.0.1:5055` yourself.

## Where your data lives

Everything you enter is stored in a single file: **`cat_tracker.db`**, in
the same folder as the app. It's a plain SQLite database — nothing leaves
your machine, no accounts, no sync.

On the very first run, the app seeds this file with:
- the 9-week schedule (topics + target counts, 30 Aug – 30 Oct 2026), from
  your schedule PDF
- the full syllabus master list with 5-year (2021–2025) question-frequency
  weightage per topic, from your syllabus PDF, with **Para Jumbles** flagged
  `volatile` (CAT 2024 had zero across all three slots after a steady 2–3
  per slot in 2021–23)

After that first seed, the file is entirely yours — every number you see
anywhere in the app (question counts, mock scores, accuracy, streak) comes
from what you've typed in, never randomly generated or auto-filled.

## What is included

- **Home:** days-to-exam countdown, current week, plan completion, streak,
  highest-priority syllabus gap, persona feedback, and a quick log form.
- **This Week:** week-by-week schedule with targets, completion bars, and
  editable topic targets, names, units, and week assignments.
- **Syllabus:** section filters, historical weightage, completion tracking,
  and volatile-topic flags. Logs for matching topics roll up automatically.
- **Mocks:** record overall and section scores, attempts, correct and wrong
  answers, time taken, percentiles, notes, and review/delete existing mocks.
- **Error Log:** record mistakes against topics or mocks with reason tags such
  as concept gap, misread, time pressure, and silly error.
- **Predictor:** mock-based percentile ranges plus a clearly labelled,
  rougher prep-based estimate using coverage, time remaining, and accuracy
  trend.
- **Analytics:** practice totals, section comparisons, error-reason
  breakdowns, syllabus gaps, mock trends, and this-week versus last-week
  activity.
- **Settings:** change the exam date, theme, persona frequency, schedule
  adherence mode, and export a JSON snapshot.

The interface is a single-page Flask app with keyboard tab shortcuts,
accessible navigation, responsive layouts, and dependency-free SVG charts.

## Privacy and publishing

The repository contains application code and seeded reference data only. Your
personal study history is stored locally in `cat_tracker.db`, which is
excluded by `.gitignore` and must not be committed. JSON snapshots exported
from the app are also personal data; keep them outside the repository and do
not upload them. If a database was ever committed in an earlier revision,
remove it from Git history before making the repository public.

## Backing it up

Two ways, both built in:

1. **Copy the file.** `cat_tracker.db` is the entire app state. Copy it
   anywhere (another folder, a USB drive, cloud storage if you want) and
   you have a full backup. To restore, just put it back next to `app.py`
   before starting the app.
2. **JSON snapshot.** In the app, go to **Settings → Backup & export →
   Download JSON snapshot**. This dumps every table to a human-readable
   `.json` file in your Downloads folder.

## Project layout

```
cat_tracker.py       <- entry point (imports app.py, run this)
app.py               <- Flask routes / API
db.py                <- SQLite schema + first-run seeding
seed_data.py          <- the plan + syllabus data extracted from your PDFs
persona.py            <- the persona commentary rule engine (see below)
predictor.py          <- percentile interpolation + prep-based heuristic
templates/index.html  <- single-page app shell (tab navigation)
static/css/style.css  <- design system
static/js/app.js      <- screen rendering + API calls
static/js/charts.js   <- dependency-free SVG chart helpers (no CDN)
requirements.txt
cat_tracker.db        <- created on first run, ignored local data (never commit)
```

## Extending the persona rule engine

Open `persona.py`. Each rule is a plain Python function that takes a `ctx`
dict (pre-computed data: section gaps, mock deltas, syllabus completion,
streak) and returns a message string, or `None` if it has nothing to say.
Add a new function following the existing pattern, then add it to the
`RULES` list at the bottom of the file — nothing else needs to change. The
app caps how many lines show per Home-load in Settings.

## Notes on the data extraction

- **Weekly plan**: pulled directly from the 9-week schedule PDF, topic by
  topic, with the exact target counts and units (questions / sets /
  passages) as printed for each week.
- **Syllabus master weights**: pulled from the "Total" column (all slots,
  2021–2025) in the syllabus PDF's chapter-wise tables, at the leaf-topic
  level (e.g. "Averages", "Time & Work" — not the parent category rows like
  "Arithmetics", which are just sums of their children and are skipped to
  avoid double-counting).
- A few weekly-plan topic names don't have an exact 1:1 match in the
  syllabus master's leaf list (e.g. "Races", "Pipes, Trains & Boats" vs. the
  syllabus table's "Pipes & Cisterns / Clocks") — that mismatch exists in
  the source PDFs themselves, so daily logs against those specific plan
  topics won't auto-roll-up into a syllabus-master weight. Logging against
  any topic that *does* match rolls up correctly.
