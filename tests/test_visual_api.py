import re

import pytest

from app import create_app, db
from seed import seed_database


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "visual-api-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'visual-api.db'}",
        }
    )
    with application.app_context():
        db.create_all()
        seed_database()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _login(client, email):
    page = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)
    ).group(1)
    return client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": email,
            "password": "AquaTraceDemo123!",
        },
    )


def _assert_envelope(response):
    assert response.status_code == 200
    payload = response.json
    assert "data" in payload
    assert isinstance(payload["last_operation"], str)
    assert payload["complexity"]["time"]
    assert payload["complexity"]["space"]
    return payload["data"]


def test_visual_apis_require_authentication_except_public_read_only_data(app):
    client = app.test_client()
    assert client.get("/api/graph").status_code == 302
    assert client.get("/api/stack").status_code == 302
    public = client.get("/api/public/graph")
    assert public.status_code == 200
    assert "last_operation" in public.json
    assert "email" not in public.get_data(as_text=True)
    public_feed = client.get("/api/public/telemetry/latest")
    assert public_feed.status_code == 200
    assert "last_operation" in public_feed.json


def test_resident_api_access_and_staff_admin_boundaries(app):
    client = app.test_client()
    assert _login(client, "warga@aquatrace.test").status_code == 302

    for path in (
        "/api/queue",
        "/api/linked-list/7",
        "/api/graph",
        "/api/graph/nearest/1",
        "/api/telemetry/latest",
        "/api/telemetry/queue",
        "/api/telemetry/series/1",
    ):
        _assert_envelope(client.get(path))

    for path in (
        "/api/stack",
        "/api/tree/decision",
        "/api/tree/regions",
        "/api/graph/trace/1",
    ):
        assert client.get(path).status_code == 403

def test_staff_and_admin_visualization_endpoints_include_real_dsa_data(app):
    client = app.test_client()
    assert _login(client, "petugas@aquatrace.test").status_code == 302

    queue = _assert_envelope(client.get("/api/queue"))
    assert queue["size"] == len(queue["priority"]) + len(queue["regular"])
    stack = _assert_envelope(client.get("/api/stack"))
    assert stack["size"] == len(stack["items"])
    history = _assert_envelope(client.get("/api/linked-list/7"))
    assert history["length"] == len(history["entries"])
    decision = _assert_envelope(
        client.get("/api/tree/decision?ph=7&kekeruhan_ntu=1&tds_mgl=100")
    )
    assert decision["evaluation"]["verdict"] == "BERSIH"
    assert decision["thresholds"]["is_example"] is True
    _assert_envelope(client.get("/api/graph/trace/1"))
    _assert_envelope(client.get("/api/telemetry/queue"))
    _assert_envelope(client.get("/api/telemetry/latest"))

    client.post("/logout", data={"csrf_token": _csrf(client)})
    assert _login(client, "admin@aquatrace.test").status_code == 302
    regions = _assert_envelope(client.get("/api/tree/regions"))
    assert regions["root"]["type"] == "root"
    assert "jumlah_tercemar" in regions["root"]


def test_api_validation_missing_records_and_history_search(app):
    client = app.test_client()
    assert _login(client, "petugas@aquatrace.test").status_code == 302
    assert client.get("/api/linked-list/99999").status_code == 404
    assert client.get("/api/linked-list/7?search=not-an-id").status_code == 422
    assert client.get("/api/graph/trace/99999").status_code == 404
    assert client.get("/api/tree/decision?ph=7").status_code == 422
    assert client.get("/api/public/telemetry/series/99999").status_code == 404


def _csrf(client):
    response = client.get("/")
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    return match.group(1)
