from app import db
from app.ds.linked_list import LinkedList
from app.models import Sample, TestResult, WaterSource
from app.services.diagnosis import evaluate_measurements


def build_source_history(source_id):
    """Build the source's chronological linked-list history from database rows."""
    history = LinkedList(id_getter=lambda result: result.id)
    results = (
        TestResult.query.filter_by(source_id=source_id)
        .order_by(TestResult.created_at.asc(), TestResult.id.asc())
        .all()
    )
    for result in results:
        history.insert_tail(result)
    return history


def search_history(source_id, result_id):
    """Search a source history using LinkedList.search, O(n)."""
    return build_source_history(source_id).search(result_id)


def _recalculate_source_status(source):
    latest = (
        TestResult.query.filter_by(source_id=source.id)
        .filter(TestResult.vonis.isnot(None))
        .order_by(TestResult.created_at.desc(), TestResult.id.desc())
        .first()
    )
    source.status_terakhir = latest.vonis if latest else "belum_diuji"


def delete_history_entry(source_id, result_id):
    """Delete one history node, requeue its sample, and recalculate source status."""
    try:
        source = WaterSource.query.filter_by(id=source_id).with_for_update().first()
        if source is None:
            return None
        history = build_source_history(source_id)
        result = history.delete(result_id)
        if result is None:
            return None
        persisted = db.session.get(TestResult, result.id)
        if persisted is None:
            return None
        if persisted.sumber_data == "publikasi":
            raise ValueError("Hasil publikasi hanya dapat diperbarui melalui data sumbernya.")
        sample = db.session.get(Sample, persisted.sample_id)
        db.session.delete(persisted)
        if sample is not None:
            sample.status = "menunggu"
        db.session.flush()
        _recalculate_source_status(source)
        db.session.commit()
        return result
    except Exception:
        db.session.rollback()
        raise


def correct_history_entry(source_id, result_id, measurements):
    """Correct a result in-place via LinkedList search and recompute the verdict."""
    try:
        source = WaterSource.query.filter_by(id=source_id).with_for_update().first()
        if source is None:
            return None
        history = build_source_history(source_id)
        result = history.search(result_id)
        if result is None:
            return None
        persisted = db.session.get(TestResult, result.id)
        if persisted is None:
            return None
        if persisted.sumber_data == "publikasi":
            raise ValueError("Hasil publikasi tidak dapat dikoreksi dengan ambang contoh.")
        verdict, trace = evaluate_measurements(measurements)
        persisted.ph = float(measurements["ph"])
        persisted.kekeruhan_ntu = float(measurements["kekeruhan_ntu"])
        persisted.tds_mgl = float(measurements["tds_mgl"])
        persisted.vonis = verdict
        persisted.jejak_keputusan = " → ".join(trace)
        db.session.flush()
        _recalculate_source_status(source)
        db.session.commit()
        return persisted
    except Exception:
        db.session.rollback()
        raise
