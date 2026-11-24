from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

from app import create_app, db
from app.models import Region, Sample, User, WaterSource
from app.services.antrean import build_sample_queue, process_next_sample, queue_position


def _new_sample(source_id, user_id, priority, created_at):
    sample = Sample(
        source_id=source_id,
        diajukan_oleh=user_id,
        asal="warga",
        prioritas=priority,
        status="menunggu",
        created_at=created_at,
    )
    db.session.add(sample)
    db.session.flush()
    return sample


def test_queue_prioritizes_urgent_then_preserves_fifo(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'queue.db'}",
        }
    )
    with app.app_context():
        db.create_all()
        user = User(
            nama="Petugas", email="petugas@test.local", password_hash="x", role="warga"
        )
        region = Region(nama="Desa", level="desa")
        db.session.add_all([user, region])
        db.session.flush()
        source = WaterSource(
            nama="Sumur", tipe="sumur", region_id=region.id, lat=0, lng=0
        )
        db.session.add(source)
        db.session.flush()
        t0 = datetime(2025, 1, 1)
        regular_first = _new_sample(source.id, user.id, False, t0)
        priority_first = _new_sample(source.id, user.id, True, t0)
        priority_second = _new_sample(source.id, user.id, True, t0)
        regular_second = _new_sample(
            source.id, user.id, False, t0.replace(minute=1)
        )
        db.session.commit()

        assert queue_position(priority_first.id) == 1
        assert queue_position(priority_second.id) == 2
        assert queue_position(regular_first.id) == 3
        queue = build_sample_queue()
        assert queue.size() == 4
        assert [process_next_sample().id for _ in range(4)] == [
            priority_first.id,
            priority_second.id,
            regular_first.id,
            regular_second.id,
        ]
        assert process_next_sample() is None


def test_two_concurrent_workers_cannot_claim_same_sample(tmp_path):
    database_path = tmp_path / "concurrent.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "connect_args": {"check_same_thread": False, "timeout": 5}
            },
        }
    )
    with app.app_context():
        db.create_all()
        user = User(
            nama="Warga", email="warga@test.local", password_hash="x", role="warga"
        )
        region = Region(nama="Desa", level="desa")
        db.session.add_all([user, region])
        db.session.flush()
        source = WaterSource(
            nama="Sungai", tipe="sungai", region_id=region.id, lat=0, lng=0
        )
        db.session.add(source)
        db.session.flush()
        first = _new_sample(
            source.id, user.id, True, datetime(2025, 1, 1)
        )
        second = _new_sample(
            source.id,
            user.id,
            False,
            datetime(2025, 1, 1, 0, 1),
        )
        expected = {first.id, second.id}
        db.session.commit()

    barrier = Barrier(2)

    def claim():
        with app.app_context():
            barrier.wait(timeout=5)
            sample = process_next_sample()
            return None if sample is None else sample.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: claim(), range(2)))

    assert len(set(results)) == 2
    assert set(results) == expected
