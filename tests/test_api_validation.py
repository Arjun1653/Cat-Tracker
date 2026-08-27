import json

from app import app
import db


def setup_function():
    db.init_db()


def test_log_rejects_missing_plan_topic_even_when_topic_id_exists():
    client = app.test_client()
    response = client.post(
        "/api/log",
        data=json.dumps({"topic_id": 1, "plan_topic_id": 999, "count_done": 3, "unit": "q"}),
        content_type="application/json",
    )
    assert response.status_code == 404
    assert b"The selected plan topic no longer exists" in response.data


def test_error_log_rejects_invalid_reason_tag():
    client = app.test_client()
    response = client.post(
        "/api/errors",
        data=json.dumps({"date": "2026-08-28", "reason_tag": "bad"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert b"Invalid reason tag" in response.data
