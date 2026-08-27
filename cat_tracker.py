"""
CAT 2026 Prep Tracker - entry point.

Run with:  python cat_tracker.py

Starts a local Flask server on 127.0.0.1:5055 and opens it in your default
browser. Your data lives in cat_tracker.db, next to this file. Nothing is
exposed outside your machine and nothing requires internet after the
one-time `pip install -r requirements.txt`.
"""
import webbrowser
import threading

import db
from app import app

HOST = "127.0.0.1"
PORT = 5055


def _open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}/")


if __name__ == "__main__":
    db.init_db()
    threading.Timer(1.0, _open_browser).start()
    print(f"\nCAT 2026 Prep Tracker running at http://{HOST}:{PORT}")
    print("Your data lives in cat_tracker.db, next to this file.")
    print("Press Ctrl+C to stop.\n")
    app.run(host=HOST, port=PORT, debug=False)
