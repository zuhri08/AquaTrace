import re

import pytest

from app import create_app, db
from app.config import thresholds
from app.models import EntryAction, Sample, TestResult, User, WaterSource
from app.services.diagnosis import (
    build_diagnosis_trail,
    evaluate_measurements,
    save_result,
    undo_latest_result,
    validate_measurements,
)
from seed import seed_database


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "diagnosis-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'diagnosis.db'}",
        }
    )
    with application.app_context():
        db.create_all()
        seed_database()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _client_login(client, email="petugas@aquatrace.test"):
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


def test_decision_tree_uses_example_threshold_config_and_evaluates_branches():
    assert thresholds.IS_EXAMPLE is True
    assert thresholds.REGULATION_SOURCE is None
    cases = (
        ({"ph": 6.4, "kekeruhan_ntu": 1, "tds_mgl": 100}, "TIDAK_LAYAK"),
        ({"ph": 8.6, "kekeruhan_ntu": 1, "tds_mgl": 100}, "TIDAK_LAYAK"),
        ({"ph": 7, "kekeruhan_ntu": 5.1, "tds_mgl": 100}, "WASPADA"),
        ({"ph": 7, "kekeruhan_ntu": 5, "tds_mgl": 501}, "WASPADA"),
        ({"ph": 7, "kekeruhan_ntu": 5, "tds_mgl": 500}, "BERSIH"),
    )
    for data, expected in cases:
        verdict, trace = evaluate_measurements(data)
        assert verdict == expected
        assert trace


@pytest.mark.parametrize(
    "field,value",
    [
        ("ph", -0.01),
        ("ph", 14.01),
        ("kekeruhan_ntu", 1000.1),
        ("tds_mgl", -1),
        ("ph", float("nan")),
        ("tds_mgl", float("inf")),
    ],
)
def test_physical_measurement_range_rejects_invalid_values(field, value):
    values = {"ph": 7, "kekeruhan_ntu": 1, "tds_mgl": 100}
    values[field] = value
    with pytest.raises(ValueError):
        validate_measurements(values)


def test_diagnosis_trail_is_lifo_and_result_undo_recalculates_source(app):
    with app.app_context():
        lab = User.query.filter_by(role="petugas_lab").one()
        first = Sample.query.filter_by(id=5).one()
        source = db.session.get(WaterSource, first.source_id)
        first.status = "diproses"
        trail = build_diagnosis_trail(
            {"ph": 7.0, "kekeruhan_ntu": 1.0, "tds_mgl": 100.0}
        )
        assert [item["field"] for item in trail.to_list()] == [
            "tds_mgl",
            "kekeruhan_ntu",
            "ph",
        ]
        first_result = save_result(
            first.id,
            lab.id,
            {"ph": 7.0, "kekeruhan_ntu": 1.0, "tds_mgl": 100.0},
        )
        assert first_result.vonis == "BERSIH"
        assert first.status == "selesai"
        assert source.status_terakhir == "BERSIH"

        second = Sample.query.filter_by(id=6).one()
        second.source_id = first.source_id
        second.status = "diproses"
        db.session.commit()
        second_result = save_result(
            second.id,
            lab.id,
            {"ph": 7.0, "kekeruhan_ntu": 12.0, "tds_mgl": 100.0},
        )
        assert second_result.vonis == "WASPADA"
        assert source.status_terakhir == "WASPADA"
        assert EntryAction.query.filter_by(user_id=lab.id).count() == 2

        undone = undo_latest_result(lab.id)
        assert undone.id == second.id
        assert second.status == "menunggu"
        assert source.status_terakhir == "BERSIH"
        assert TestResult.query.filter_by(sample_id=second.id).count() == 0
        assert EntryAction.query.filter_by(user_id=lab.id).count() == 1


def test_wizard_validates_inputs_and_saves_result(app):
    client = app.test_client()
    assert _client_login(client).status_code == 302
    csrf = re.search(
        r'name="csrf_token" value="([^"]+)"',
        client.get("/petugas/diagnosis/5").get_data(as_text=True),
    ).group(1)

    bad = client.post(
        "/petugas/diagnosis/5",
        data={"csrf_token": csrf, "field": "ph", "value": "99"},
    )
    assert bad.status_code == 302
    assert "rentang fisik" in client.get(
        "/petugas/diagnosis/5"
    ).get_data(as_text=True)

    for field, value in (
        ("ph", "7"),
        ("kekeruhan_ntu", "1"),
        ("tds_mgl", "100"),
    ):
        page = client.get("/petugas/diagnosis/5").get_data(as_text=True)
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        response = client.post(
            "/petugas/diagnosis/5",
            data={"csrf_token": csrf, "field": field, "value": value},
        )
        assert response.status_code == 302

    review = client.get("/petugas/diagnosis/5")
    assert b"BERSIH" in review.data
    csrf = re.search(
        r'name="csrf_token" value="([^"]+)"',
        review.get_data(as_text=True),
    ).group(1)
    saved = client.post(
        "/petugas/diagnosis/5",
        data={"csrf_token": csrf, "action": "save"},
    )
    assert saved.status_code == 302
    with app.app_context():
        sample = db.session.get(Sample, 5)
        assert sample.status == "selesai"
        assert sample.test_results[0].vonis == "BERSIH"
