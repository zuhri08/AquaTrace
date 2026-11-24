import re

import pytest
from werkzeug.security import check_password_hash

from app import create_app, db
from app.models import User
from seed import seed_database


@pytest.fixture
def app():
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
        }
    )
    with application.app_context():
        db.create_all()
        seed_database()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


def _csrf_token(client, path):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    assert match
    return match.group(1)


def _login(client, email, password="AquaTraceDemo123!"):
    token = _csrf_token(client, "/login")
    return client.post(
        "/login",
        data={"csrf_token": token, "email": email, "password": password},
        follow_redirects=False,
    )


def test_registration_creates_hashed_warga_account(client, app):
    token = _csrf_token(client, "/register")
    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "nama": "Warga Baru",
            "email": "BARU@example.test",
            "password": "password-yang-cukup",
        },
    )

    assert response.status_code == 302
    with app.app_context():
        user = User.query.filter_by(email="baru@example.test").one()
        assert user.role == "warga"
        assert user.aktif is True
        assert user.password_hash != "password-yang-cukup"
        assert check_password_hash(user.password_hash, "password-yang-cukup")
    assert client.get("/warga/dashboard").status_code == 200


def test_post_without_csrf_token_is_rejected(client):
    response = client.post(
        "/login", data={"email": "warga@aquatrace.test", "password": "wrong"}
    )
    assert response.status_code == 400


def test_role_access_is_enforced_on_server(client):
    assert _login(client, "warga@aquatrace.test").status_code == 302
    assert client.get("/petugas/dashboard").status_code == 403
    assert client.get("/admin/dashboard").status_code == 403


def test_staff_role_access_and_admin_staff_dashboard(client):
    assert _login(client, "petugas@aquatrace.test").status_code == 302
    assert client.get("/petugas/dashboard").status_code == 200
    assert client.get("/admin/dashboard").status_code == 403

    client.post("/logout", data={"csrf_token": _csrf_token(client, "/")})
    assert _login(client, "admin@aquatrace.test").status_code == 302
    assert client.get("/admin/dashboard").status_code == 200
    assert client.get("/petugas/dashboard").status_code == 200


def test_inactive_account_cannot_login(client, app):
    with app.app_context():
        user = User.query.filter_by(email="warga@aquatrace.test").one()
        user.aktif = False
        db.session.commit()

    response = _login(client, "warga@aquatrace.test")
    assert response.status_code == 401
    assert "tidak aktif" in response.get_data(as_text=True)


def test_logout_clears_session(client):
    assert _login(client, "warga@aquatrace.test").status_code == 302
    token = _csrf_token(client, "/")
    response = client.post("/logout", data={"csrf_token": token})
    assert response.status_code == 302
    assert client.get("/warga/dashboard").status_code == 302


def test_unknown_route_has_friendly_404(client):
    response = client.get("/tidak-ada")
    assert response.status_code == 404
    assert b"Halaman yang dicari tidak ditemukan" in response.data
