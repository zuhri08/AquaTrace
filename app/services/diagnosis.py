import json
import math

from sqlalchemy import select, update

from app import db
from app.config import thresholds
from app.ds.stack import Stack
from app.ds.tree import DecisionNode, DecisionTree
from app.models import Sample, TestResult, WaterSource
from app.services.undo import record_action

MEASUREMENT_FIELDS = {
    "ph": {"label": "pH", "unit": "", "minimum": 0.0, "maximum": 14.0},
    "kekeruhan_ntu": {
        "label": "Kekeruhan",
        "unit": "NTU",
        "minimum": 0.0,
        "maximum": 1000.0,
    },
    "tds_mgl": {
        "label": "TDS",
        "unit": "mg/L",
        "minimum": 0.0,
        "maximum": 5000.0,
    },
}
MEASUREMENT_ORDER = ("ph", "kekeruhan_ntu", "tds_mgl")


def build_decision_tree():
    """Construct the screening tree from the human-editable threshold config."""
    clean = DecisionNode(verdict="BERSIH", message="Indikasi screening: BERSIH.")
    warning_tds = DecisionNode(verdict="WASPADA", message="Indikasi screening: WASPADA.")
    warning_turbidity = DecisionNode(
        verdict="WASPADA", message="Indikasi screening: WASPADA."
    )
    ph_too_high = DecisionNode(
        feature="ph",
        operator=">",
        threshold=thresholds.PH_MAX,
        when_true=DecisionNode(
            verdict="TIDAK_LAYAK",
            message="Indikasi screening: TIDAK_LAYAK (pH di atas rentang contoh).",
        ),
        when_false=DecisionNode(
            feature="kekeruhan_ntu",
            operator=">",
            threshold=thresholds.KEKERUHAN_MAX_NTU,
            when_true=warning_turbidity,
            when_false=DecisionNode(
                feature="tds_mgl",
                operator=">",
                threshold=thresholds.TDS_MAX_MGL,
                when_true=warning_tds,
                when_false=clean,
            ),
        ),
    )
    return DecisionTree(
        DecisionNode(
            feature="ph",
            operator="<",
            threshold=thresholds.PH_MIN,
            when_true=DecisionNode(
                verdict="TIDAK_LAYAK",
                message="Indikasi screening: TIDAK_LAYAK (pH di bawah rentang contoh).",
            ),
            when_false=ph_too_high,
        )
    )


def evaluate_measurements(data):
    """Validate physical ranges, evaluate the recursive tree, and explain it."""
    normalized = validate_measurements(data)
    verdict, trace = build_decision_tree().evaluate(normalized)
    feature_labels = {
        "ph": ("pH", ""),
        "kekeruhan_ntu": ("Kekeruhan", " NTU"),
        "tds_mgl": ("TDS", " mg/L"),
    }
    readable = []
    for step in trace:
        feature = next((name for name in feature_labels if step.startswith(name + " ")), None)
        if feature:
            label, unit = feature_labels[feature]
            step = f"{label}{step[len(feature):]}{unit}"
        readable.append(step)
    return verdict, readable


def validate_measurements(data):
    """Validate all physical measurement bounds and reject non-finite numbers."""
    normalized = {}
    errors = {}
    for field, spec in MEASUREMENT_FIELDS.items():
        try:
            value = float(data[field])
        except (KeyError, TypeError, ValueError):
            errors[field] = "Masukkan nilai angka yang valid."
            continue
        if not math.isfinite(value) or not spec["minimum"] <= value <= spec["maximum"]:
            errors[field] = (
                f"Nilai harus antara {spec['minimum']:g} dan {spec['maximum']:g} "
                f"{spec['unit']}."
            )
            continue
        normalized[field] = value
    if errors:
        raise ValueError(json.dumps(errors, ensure_ascii=False))
    return normalized


def build_diagnosis_trail(measurements):
    """Rebuild the wizard's LIFO trail from persisted session measurements."""
    trail = Stack()
    for field in MEASUREMENT_ORDER:
        if field in measurements:
            trail.push({"field": field, "value": measurements[field]})
    return trail


def save_result(sample_id, tester_id, measurements):
    """Persist result, source status, sample status, and undo action atomically."""
    normalized = validate_measurements(measurements)
    verdict, trace = evaluate_measurements(normalized)
    try:
        if db.session.get_bind().dialect.name == "mysql":
            sample = (
                Sample.query.filter_by(id=sample_id, status="diproses")
                .with_for_update()
                .first()
            )
            if sample is None:
                raise ValueError("Sampel tidak ditemukan atau tidak sedang diproses.")
            sample.status = "selesai"
        else:
            claimed_id = db.session.execute(
                update(Sample)
                .where(Sample.id == sample_id, Sample.status == "diproses")
                .values(status="selesai")
                .returning(Sample.id)
            ).scalar_one_or_none()
            if claimed_id is None:
                raise ValueError("Sampel tidak ditemukan atau tidak sedang diproses.")
            sample = db.session.get(Sample, claimed_id)

        source = (
            WaterSource.query.filter_by(id=sample.source_id)
            .with_for_update()
            .first()
        )
        if source is None:
            raise ValueError("Sumber air untuk sampel tidak ditemukan.")
        result = TestResult(
            sample_id=sample.id,
            source_id=sample.source_id,
            ph=normalized["ph"],
            kekeruhan_ntu=normalized["kekeruhan_ntu"],
            tds_mgl=normalized["tds_mgl"],
            vonis=verdict,
            jejak_keputusan=" → ".join(trace),
            diuji_oleh=tester_id,
        )
        db.session.add(result)
        source.status_terakhir = verdict
        db.session.flush()
        record_action(
            tester_id,
            "simpan_hasil",
            {"sample_id": sample.id, "result_id": result.id},
        )
        db.session.commit()
        return result
    except Exception:
        db.session.rollback()
        raise


def undo_latest_result(tester_id):
    """Undo the user's most recent saved result and recalculate source status."""
    from app.models import EntryAction

    action = (
        EntryAction.query.filter_by(user_id=tester_id, aksi="simpan_hasil")
        .order_by(EntryAction.created_at.desc(), EntryAction.id.desc())
        .with_for_update()
        .first()
    )
    if action is None:
        return None
    try:
        payload = json.loads(action.payload_json)
        sample_id = int(payload["sample_id"])
        result_id = int(payload["result_id"])
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise ValueError("Data aksi undo tidak valid.") from error

    sample = (
        Sample.query.filter_by(id=sample_id, status="selesai")
        .with_for_update()
        .first()
    )
    result = db.session.get(TestResult, result_id)
    if sample is None or result is None or result.sample_id != sample.id:
        raise ValueError("Hasil tidak dapat diurungkan karena status sudah berubah.")
    source_id = sample.source_id
    source = (
        WaterSource.query.filter_by(id=source_id)
        .with_for_update()
        .first()
    )
    db.session.delete(result)
    db.session.delete(action)
    sample.status = "menunggu"
    db.session.flush()
    latest = (
        TestResult.query.filter_by(source_id=source_id)
        .order_by(TestResult.created_at.desc(), TestResult.id.desc())
        .first()
    )
    source.status_terakhir = latest.vonis if latest else "belum_diuji"
    db.session.commit()
    return sample
