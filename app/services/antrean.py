from sqlalchemy import select, update

from app import db
from app.ds.queue import PriorityAwareQueue
from app.models import Sample, utcnow


def build_sample_queue():
    """Rebuild FIFO priority lanes from the database, the source of truth."""
    rows = (
        Sample.query.filter_by(status="menunggu")
        .order_by(Sample.prioritas.desc(), Sample.created_at.asc(), Sample.id.asc())
        .all()
    )
    queue = PriorityAwareQueue()
    for sample in rows:
        queue.enqueue(sample, priority=sample.prioritas)
    return queue


def queue_position(sample_id):
    """Return one-based position in service order, or None if not waiting."""
    queue = build_sample_queue()
    for index, sample in enumerate(
        queue.display()["priority"] + queue.display()["regular"], start=1
    ):
        if sample.id == sample_id:
            return index
    return None


def submit_sample(source_id, submitter_id, priority=False, origin="warga"):
    """Persist a sample and return it; callers decide eligibility/access."""
    if origin not in {"warga", "iot"}:
        raise ValueError("asal sampel tidak valid")
    sample = Sample(
        source_id=source_id,
        diajukan_oleh=submitter_id,
        asal=origin,
        prioritas=bool(priority),
        status="menunggu",
    )
    db.session.add(sample)
    db.session.commit()
    return sample


def process_next_sample():
    """Atomically claim the next sample; priority then FIFO.

    On SQLite the ordered scalar subquery and conditional UPDATE are one
    database statement. SQLite serializes writers, and `status='menunggu'`
    ensures a concurrent worker cannot claim a row already changed to
    `diproses`. On MySQL, SELECT FOR UPDATE locks the selected row.
    """
    dialect = db.session.get_bind().dialect.name
    try:
        if dialect == "mysql":
            sample = (
                Sample.query.filter_by(status="menunggu")
                .order_by(Sample.prioritas.desc(), Sample.created_at.asc(), Sample.id.asc())
                .with_for_update()
                .first()
            )
            if sample is None:
                db.session.rollback()
                return None
            sample.status = "diproses"
            db.session.commit()
            return sample

        candidate_id = (
            select(Sample.id)
            .where(Sample.status == "menunggu")
            .order_by(Sample.prioritas.desc(), Sample.created_at.asc(), Sample.id.asc())
            .limit(1)
            .scalar_subquery()
        )
        claimed_id = db.session.execute(
            update(Sample)
            .where(Sample.id == candidate_id, Sample.status == "menunggu")
            .values(status="diproses")
            .returning(Sample.id)
        ).scalar_one_or_none()
        if claimed_id is None:
            db.session.rollback()
            return None
        sample = db.session.get(Sample, claimed_id)
        db.session.commit()
        return sample
    except Exception:
        db.session.rollback()
        raise


def reopen_sample(sample_id):
    """Return a previously processed sample to the waiting queue."""
    sample = db.session.get(Sample, sample_id)
    if sample is None or sample.status != "diproses":
        return False
    sample.status = "menunggu"
    db.session.commit()
    return True
