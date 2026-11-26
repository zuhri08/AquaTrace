import re

import pytest

from app import create_app, db
from app.models import Sample, User, WaterSource
from app.services.antrean import process_next_sample, submit_sample
from seed import seed_database


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "ui-smoke-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'ui-smoke.db'}",
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
    response = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    ).group(1)
    return client.post(
        "/login",
        data={
            "csrf_token": token,
            "email": email,
            "password": "AquaTraceDemo123!",
        },
    )


def _get_all(client, paths):
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, (
            f"{path} returned {response.status_code}: "
            f"{response.get_data(as_text=True)[:500]}"
        )


def test_public_routes_render_without_login(app):
    client = app.test_client()
    _get_all(client, ["/", "/publik", "/publik/telemetri", "/login", "/register"])
    landing = client.get("/")
    assert b"cdn.tailwindcss.com" not in landing.data
    stylesheet = client.get("/static/css/aquatrace.css")
    assert stylesheet.status_code == 200
    assert b"montserrat-v31-300.ttf" in stylesheet.data
    assert client.get("/static/fonts/montserrat-v31-300.ttf").status_code == 200
    assert client.get("/static/fonts/jetbrains-mono-v24-400.ttf").status_code == 200
    assert client.get("/static/fonts/material-symbols-outlined-v387.ttf").status_code == 200
    assert client.get("/api/public/graph").status_code == 200
    assert client.get("/api/public/telemetry/latest").status_code == 200


def test_warga_routes_render_and_visual_apis_are_present(app):
    client = app.test_client()
    assert _login(client, "warga@aquatrace.test").status_code == 302
    with app.app_context():
        warga = User.query.filter_by(email="warga@aquatrace.test").one()
        source = WaterSource.query.filter_by(dibuat_oleh=warga.id).first()
        if source is None:
            source = WaterSource.query.order_by(WaterSource.id).first()
        sample = Sample.query.filter_by(diajukan_oleh=warga.id).first()
        if sample is None:
            sample = submit_sample(source.id, warga.id)
        source_id = source.id
        sample_id = sample.id
    paths = [
        "/warga/dashboard",
        "/warga/sumber/baru",
        "/warga/sampel/baru",
        f"/warga/sampel/{sample_id}",
        f"/warga/sumber/{source_id}/riwayat",
        "/warga/terdekat",
    ]
    _get_all(client, paths)
    detail = client.get(f"/warga/sampel/{sample_id}").get_data(as_text=True)
    assert 'data-visual="queue"' in detail
    assert 'data-visual="linked-list"' in detail


def test_staff_routes_render_with_api_backed_visualizations(app):
    client = app.test_client()
    assert _login(client, "petugas@aquatrace.test").status_code == 302
    with app.app_context():
        sample = Sample.query.filter_by(status="diproses").first()
        if sample is None:
            sample = process_next_sample()
        assert sample is not None
        sample_id = sample.id
        source_id = sample.source_id
    paths = [
        "/petugas/dashboard",
        "/petugas/antrean",
        f"/petugas/diagnosis/{sample_id}",
        "/petugas/riwayat-entri",
        f"/petugas/sumber/{source_id}/riwayat",
        "/petugas/lacak-dampak",
        "/petugas/telemetri",
    ]
    _get_all(client, paths)
    page = client.get(f"/petugas/diagnosis/{sample_id}").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    response = client.post(
        f"/petugas/diagnosis/{sample_id}",
        data={"csrf_token": token, "field": "ph", "value": "7"},
    )
    assert response.status_code == 302
    diagnosis = client.get(f"/petugas/diagnosis/{sample_id}").get_data(as_text=True)
    assert 'data-visual="stack"' in diagnosis
    stack = client.get(f"/api/stack/diagnosis/{sample_id}")
    assert stack.status_code == 200
    assert stack.json["data"]["items"] == [{"field": "ph", "value": 7.0}]
    assert 'data-visual="decision-tree"' not in diagnosis
    telemetry = client.get("/petugas/telemetri").get_data(as_text=True)
    assert 'data-visual="telemetry-queue"' in telemetry
    assert 'data-visual="telemetry-feed"' in telemetry


def test_admin_routes_and_styleguide_render_with_visualization_apis(app):
    client = app.test_client()
    assert _login(client, "admin@aquatrace.test").status_code == 302
    _get_all(
        client,
        [
            "/admin/dashboard",
            "/admin/jaringan",
            "/admin/telemetri/perangkat",
            "/styleguide",
            "/petugas/dashboard",
            "/petugas/antrean",
            "/petugas/riwayat-entri",
            "/petugas/lacak-dampak",
            "/petugas/telemetri",
        ],
    )
    styleguide = client.get("/styleguide").get_data(as_text=True)
    for visual in (
        "queue",
        "stack",
        "linked-list",
        "decision-tree",
        "region-tree",
        "graph",
        "telemetry-feed",
        "sparkline",
    ):
        assert f'data-visual="{visual}"' in styleguide


def test_styleguide_is_role_protected(app):
    client = app.test_client()
    assert client.get("/styleguide").status_code == 302
    assert _login(client, "warga@aquatrace.test").status_code == 302
    assert client.get("/styleguide").status_code == 403
    client = app.test_client()
    assert _login(client, "petugas@aquatrace.test").status_code == 302
    assert client.get("/styleguide").status_code == 403
