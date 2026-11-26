import csv
from pathlib import Path

import pytest

from app import create_app, db
from app.models import TestResult, WaterSource
from app.services.riwayat import correct_history_entry, delete_history_entry
from scripts.import_data_nyata import (
    _parse_publication_csv,
    import_publication_results,
)
from seed import seed_database


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "data-import-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'data-import.db'}",
        }
    )
    with application.app_context():
        db.create_all()
        seed_database()
    yield application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            ("titik", "tanggal", "ph", "kekeruhan_ntu", "tds_mgl", "sumber", "referensi")
        )
        writer.writerows(rows)


def test_publication_csv_template_is_empty_and_accepted():
    template = Path(__file__).parents[1] / "data" / "nyata" / "hasil_uji.csv"
    assert _parse_publication_csv(template) == []


def test_publication_import_preserves_measurements_without_invented_verdict(
    app, tmp_path, monkeypatch
):
    import app as app_package

    with app.app_context():
        source = WaterSource.query.filter_by(is_simulated=False).first()
        assert source is not None
        source_name = source.nama
        source_id = source.id

    csv_path = tmp_path / "hasil_uji.csv"
    _write_csv(
        csv_path,
        [
            (
                source_name,
                "2024-06-15",
                "7.1",
                "2.5",
                "120",
                "Publikasi contoh",
                "https://example.org/studi-air",
            )
        ],
    )
    monkeypatch.setattr(app_package, "create_app", lambda: app)
    import_publication_results(csv_path)
    import_publication_results(csv_path)

    with app.app_context():
        result = TestResult.query.filter_by(
            source_id=source_id, sumber_data="publikasi"
        ).one()
        assert result.sample_id is None
        assert result.vonis is None
        assert result.ph == 7.1
        assert result.tanggal_pengambilan.isoformat() == "2024-06-15"
        assert result.referensi == (
            "Publikasi contoh | https://example.org/studi-air"
        )
        assert TestResult.query.filter_by(
            source_id=source_id, sumber_data="publikasi"
        ).count() == 1
        with pytest.raises(ValueError, match="ambang contoh"):
            correct_history_entry(
                source_id,
                result.id,
                {"ph": 7, "kekeruhan_ntu": 1, "tds_mgl": 100},
            )
        with pytest.raises(ValueError, match="publikasi"):
            delete_history_entry(source_id, result.id)
        assert db.session.get(TestResult, result.id) is not None


@pytest.mark.parametrize(
    "values",
    [
        ("Titik", "2024-02-30", "7", "1", "1", "Sumber", "referensi"),
        ("Titik", "2024-02-01", "nan", "1", "1", "Sumber", "referensi"),
    ],
)
def test_publication_csv_rejects_invalid_measurement_or_date(tmp_path, values):
    csv_path = tmp_path / "invalid.csv"
    _write_csv(csv_path, [values])
    with pytest.raises(ValueError, match="Baris 2"):
        _parse_publication_csv(csv_path)
