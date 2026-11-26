import re
from datetime import datetime

import pytest

from app import create_app, db
from app.models import Region, Sample, TestResult, User, WaterSource
from app.services.riwayat import (
    build_source_history,
    correct_history_entry,
    delete_history_entry,
    search_history,
)
from app.services.wilayah import build_region_tree, region_dashboard_data
from seed import seed_database


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "history-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'history.db'}",
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


def test_linked_list_history_search_correct_delete_and_recalculate(app):
    with app.app_context():
        source = WaterSource.query.filter_by(nama="Sumber Simulasi 07").one()
        lab = User.query.filter_by(role="petugas_lab").one()
        TestResult.query.filter_by(source_id=source.id).delete(
            synchronize_session=False
        )
        samples = []
        for index in range(2):
            sample = Sample(
                source_id=source.id,
                asal="warga",
                prioritas=False,
                status="selesai",
            )
            db.session.add(sample)
            db.session.flush()
            samples.append(sample)
        first = TestResult(
            sample_id=samples[0].id,
            source_id=source.id,
            ph=7.0,
            kekeruhan_ntu=1.0,
            tds_mgl=100,
            vonis="BERSIH",
            jejak_keputusan="hasil awal",
            diuji_oleh=lab.id,
            created_at=datetime(2025, 1, 1),
        )
        second = TestResult(
            sample_id=samples[1].id,
            source_id=source.id,
            ph=7.0,
            kekeruhan_ntu=10.0,
            tds_mgl=100,
            vonis="WASPADA",
            jejak_keputusan="hasil berikutnya",
            diuji_oleh=lab.id,
            created_at=datetime(2025, 1, 2),
        )
        db.session.add_all([first, second])
        source.status_terakhir = "WASPADA"
        db.session.commit()
        first_id, second_id = first.id, second.id
        sample_ids = [item.id for item in samples]

        history = build_source_history(source.id)
        assert history.length() == 2
        assert [item.id for item in history.traverse()] == [first_id, second_id]
        assert search_history(source.id, second_id).vonis == "WASPADA"

        corrected = correct_history_entry(
            source.id,
            second_id,
            {"ph": 7, "kekeruhan_ntu": 1, "tds_mgl": 100},
        )
        assert corrected.vonis == "BERSIH"
        assert source.status_terakhir == "BERSIH"

        deleted = delete_history_entry(source.id, second_id)
        assert deleted.id == second_id
        assert source.status_terakhir == "BERSIH"
        assert db.session.get(Sample, sample_ids[1]).status == "menunggu"
        assert build_source_history(source.id).length() == 1

        delete_history_entry(source.id, first_id)
        assert source.status_terakhir == "belum_diuji"
        assert search_history(source.id, first_id) is None


def test_recursive_region_tree_counts_contaminated_sources_from_database(app):
    with app.app_context():
        tree, total = build_region_tree()
        serialized, serialized_total = region_dashboard_data()
        expected = WaterSource.query.filter_by(status_terakhir="TIDAK_LAYAK").count()

        assert total == expected == 1
        assert serialized_total == total
        assert tree.hitung_tercemar(
            lambda value: value.get("type") == "source" and value["tercemar"]
        ) == expected

        def find_region(node, name):
            if node["type"] == "region" and node["nama"] == name:
                return node
            for child in node["children"]:
                found = find_region(child, name)
                if found:
                    return found
            return None

        region = find_region(serialized, "Jawa Timur")
        assert region is not None
        expected_in_region = WaterSource.query.filter_by(
            region_id=region["id"], status_terakhir="TIDAK_LAYAK"
        ).count()
        assert region["jumlah_tercemar"] == expected_in_region == 0

        def find_source(node, name):
            if node["type"] == "source" and node["nama"] == name:
                return node
            for child in node["children"]:
                found = find_source(child, name)
                if found:
                    return found
            return None

        demo_source = find_source(serialized, "Sumber Simulasi 09")
        assert demo_source is not None
        assert demo_source["is_simulated"] is True
        assert demo_source["region_known"] is False
        assert demo_source["status"] == "TIDAK_LAYAK"


def test_staff_and_resident_history_pages(app):
    client = app.test_client()
    assert _login(client, "petugas@aquatrace.test").status_code == 302
    staff_page = client.get("/petugas/sumber/7/riwayat")
    assert staff_page.status_code == 200
    assert b"LINKED LIST" in staff_page.data

    client.post("/logout", data={"csrf_token": _csrf(client)})
    assert _login(client, "warga@aquatrace.test").status_code == 302
    public_history = client.get("/warga/sumber/7/riwayat")
    assert public_history.status_code == 200
    assert b"Sumber Simulasi 07" in public_history.data

    client.post("/logout", data={"csrf_token": _csrf(client)})
    assert _login(client, "admin@aquatrace.test").status_code == 302
    dashboard = client.get("/admin/dashboard")
    assert dashboard.status_code == 200
    assert b"Dashboard wilayah" in dashboard.data
    assert b"Jawa Timur" in dashboard.data


def _csrf(client):
    response = client.get("/")
    return re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    ).group(1)
