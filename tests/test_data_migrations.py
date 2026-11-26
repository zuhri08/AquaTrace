from sqlalchemy import inspect, text

from app import create_app, db
from app.data_migrations import ensure_phase_d_schema
from app.models import TestResult, WaterSource


def test_legacy_sqlite_schema_migrates_without_losing_rows_or_foreign_keys(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "migration-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'legacy.db'}",
        }
    )
    with app.app_context():
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, nama VARCHAR(120) NOT NULL, "
                "email VARCHAR(255) NOT NULL, password_hash VARCHAR(255) NOT NULL, "
                "role VARCHAR(20) NOT NULL, aktif BOOLEAN NOT NULL, created_at DATETIME NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE regions (id INTEGER PRIMARY KEY, nama VARCHAR(120) NOT NULL, "
                "level VARCHAR(20) NOT NULL, parent_id INTEGER REFERENCES regions(id) "
                "ON DELETE RESTRICT, CONSTRAINT ck_regions_level CHECK "
                "(level IN ('provinsi', 'kota', 'kecamatan', 'desa')))"
            )
            connection.exec_driver_sql(
                "CREATE TABLE water_sources (id INTEGER PRIMARY KEY, nama VARCHAR(160) NOT NULL, "
                "tipe VARCHAR(20) NOT NULL, region_id INTEGER NOT NULL REFERENCES regions(id), "
                "lat FLOAT NOT NULL, lng FLOAT NOT NULL, status_terakhir VARCHAR(20) NOT NULL, "
                "status_sensor VARCHAR(20) NOT NULL, dibuat_oleh INTEGER REFERENCES users(id), "
                "created_at DATETIME NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE samples (id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL "
                "REFERENCES water_sources(id), diajukan_oleh INTEGER REFERENCES users(id), "
                "asal VARCHAR(10) NOT NULL, prioritas BOOLEAN NOT NULL, status VARCHAR(20) NOT NULL, "
                "created_at DATETIME NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE river_edges (id INTEGER PRIMARY KEY, dari_source_id INTEGER NOT NULL "
                "REFERENCES water_sources(id) ON DELETE CASCADE, ke_source_id INTEGER NOT NULL "
                "REFERENCES water_sources(id) ON DELETE CASCADE, jarak_km FLOAT NOT NULL)"
            )
            connection.exec_driver_sql(
                "CREATE TABLE test_results (id INTEGER PRIMARY KEY, sample_id INTEGER NOT NULL "
                "REFERENCES samples(id) ON DELETE CASCADE, source_id INTEGER NOT NULL "
                "REFERENCES water_sources(id), ph FLOAT NOT NULL, kekeruhan_ntu FLOAT NOT NULL, "
                "tds_mgl FLOAT NOT NULL, vonis VARCHAR(20) NOT NULL, jejak_keputusan TEXT NOT NULL, "
                "diuji_oleh INTEGER REFERENCES users(id), created_at DATETIME NOT NULL, "
                "CONSTRAINT ck_results_vonis CHECK "
                "(vonis IN ('BERSIH', 'WASPADA', 'TIDAK_LAYAK')))"
            )
            connection.execute(
                text(
                    "INSERT INTO users VALUES "
                    "(1, 'Petugas', 'lab@example.test', 'hash', 'petugas_lab', 1, :created)"
                ),
                {"created": "2025-01-01 00:00:00"},
            )
            connection.execute(
                text("INSERT INTO regions VALUES (1, 'Jawa Timur', 'provinsi', NULL)")
            )
            connection.execute(
                text(
                    "INSERT INTO water_sources VALUES "
                    "(1, 'Sumber lama', 'sungai', 1, -7.4, 112.4, 'BERSIH', "
                    "'belum_ada', NULL, :created)"
                ),
                {"created": "2025-01-01 00:00:00"},
            )
            connection.execute(
                text(
                    "INSERT INTO samples VALUES "
                    "(1, 1, 1, 'warga', 0, 'selesai', :created)"
                ),
                {"created": "2025-01-01 00:00:00"},
            )
            connection.execute(
                text(
                    "INSERT INTO test_results VALUES "
                    "(1, 1, 1, 7.0, 1.0, 100.0, 'BERSIH', 'hasil lama', 1, :created)"
                ),
                {"created": "2025-01-01 00:00:00"},
            )

        ensure_phase_d_schema()
        ensure_phase_d_schema()

        inspector = inspect(db.engine)
        region_checks = inspector.get_check_constraints("regions")
        source_columns = {
            column["name"]: column for column in inspector.get_columns("water_sources")
        }
        result_columns = {
            column["name"]: column for column in inspector.get_columns("test_results")
        }
        assert any(
            "kabupaten" in check.get("sqltext", "")
            for check in region_checks
            if check.get("name") == "ck_regions_level"
        )
        assert source_columns["region_id"]["nullable"] is True
        assert source_columns["lat"]["nullable"] is True
        assert source_columns["lng"]["nullable"] is True
        assert result_columns["sample_id"]["nullable"] is True
        assert result_columns["vonis"]["nullable"] is True
        edge_columns = {
            column["name"] for column in inspector.get_columns("river_edges")
        }
        assert {"sumber_jarak", "terverifikasi"}.issubset(edge_columns)

        source = db.session.get(WaterSource, 1)
        old_result = db.session.get(TestResult, 1)
        assert source.nama == "Sumber lama"
        assert source.lat == -7.4
        assert old_result.jejak_keputusan == "hasil lama"
        assert db.session.execute(text("PRAGMA foreign_key_check")).all() == []
        assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1

        db.session.execute(
            text(
                "INSERT INTO regions (id, nama, level, parent_id) "
                "VALUES (2, 'Kabupaten Contoh', 'kabupaten', 1)"
            )
        )
        db.session.execute(
            text(
                "INSERT INTO water_sources "
                "(id, nama, tipe, region_id, lat, lng, status_terakhir, status_sensor, "
                "sumber_data, is_simulated, referensi, created_at) "
                "VALUES (2, 'Titik belum terverifikasi', 'sungai', NULL, NULL, NULL, "
                "'belum_diuji', 'belum_ada', 'osm', 0, 'TODO', :created)"
            ),
            {"created": "2025-01-01 00:00:00"},
        )
        db.session.execute(
            text(
                "INSERT INTO test_results "
                "(id, sample_id, source_id, ph, kekeruhan_ntu, tds_mgl, vonis, "
                "jejak_keputusan, sumber_data, referensi, tanggal_pengambilan, created_at) "
                "VALUES (2, NULL, 2, 7.0, 1.0, 100.0, NULL, 'publikasi', "
                "'publikasi', 'referensi', '2024-01-01', :created)"
            ),
            {"created": "2025-01-01 00:00:00"},
        )
        db.session.commit()
        assert db.session.get(WaterSource, 2).lat is None
        assert db.session.get(TestResult, 2).vonis is None
