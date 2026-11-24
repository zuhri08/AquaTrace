from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from app import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('warga', 'petugas_lab', 'admin')", name="ck_users_role"
        ),
        Index("ix_users_role_aktif", "role", "aktif"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="warga")
    aktif = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    sources = db.relationship("WaterSource", back_populates="creator")
    samples = db.relationship("Sample", back_populates="submitter")


class Region(db.Model):
    __tablename__ = "regions"
    __table_args__ = (
        CheckConstraint(
            "level IN ('provinsi', 'kota', 'kecamatan', 'desa')",
            name="ck_regions_level",
        ),
        Index("ix_regions_parent_level", "parent_id", "level"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(120), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("regions.id", ondelete="RESTRICT"))

    parent = db.relationship(
        "Region", remote_side=[id], back_populates="children"
    )
    children = db.relationship("Region", back_populates="parent")
    sources = db.relationship("WaterSource", back_populates="region")


class WaterSource(db.Model):
    __tablename__ = "water_sources"
    __table_args__ = (
        CheckConstraint(
            "tipe IN ('sumur', 'sungai', 'pdam', 'mata_air')",
            name="ck_water_sources_tipe",
        ),
        CheckConstraint(
            "status_terakhir IN "
            "('belum_diuji', 'BERSIH', 'WASPADA', 'TIDAK_LAYAK')",
            name="ck_water_sources_status_lab",
        ),
        CheckConstraint(
            "status_sensor IN "
            "('belum_ada', 'BERSIH', 'WASPADA', 'TIDAK_LAYAK')",
            name="ck_water_sources_status_sensor",
        ),
        CheckConstraint("lat >= -90 AND lat <= 90", name="ck_sources_lat"),
        CheckConstraint("lng >= -180 AND lng <= 180", name="ck_sources_lng"),
        Index("ix_water_sources_region_status", "region_id", "status_terakhir"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(160), nullable=False, index=True)
    tipe = db.Column(db.String(20), nullable=False)
    region_id = db.Column(
        db.Integer, db.ForeignKey("regions.id", ondelete="RESTRICT"), nullable=False
    )
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    status_terakhir = db.Column(db.String(20), nullable=False, default="belum_diuji")
    status_sensor = db.Column(db.String(20), nullable=False, default="belum_ada")
    dibuat_oleh = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    region = db.relationship("Region", back_populates="sources")
    creator = db.relationship("User", back_populates="sources")
    samples = db.relationship("Sample", back_populates="source")
    test_results = db.relationship("TestResult", back_populates="source")
    outgoing_edges = db.relationship(
        "RiverEdge", foreign_keys="RiverEdge.dari_source_id", back_populates="source_from"
    )
    incoming_edges = db.relationship(
        "RiverEdge", foreign_keys="RiverEdge.ke_source_id", back_populates="source_to"
    )
    iot_devices = db.relationship("IotDevice", back_populates="source")
    sensor_readings = db.relationship("SensorReading", back_populates="source")


class Sample(db.Model):
    __tablename__ = "samples"
    __table_args__ = (
        CheckConstraint("asal IN ('warga', 'iot')", name="ck_samples_asal"),
        CheckConstraint(
            "status IN ('menunggu', 'diproses', 'selesai')", name="ck_samples_status"
        ),
        Index("ix_samples_status_prioritas_created", "status", "prioritas", "created_at"),
        Index("ix_samples_source_status", "source_id", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(
        db.Integer, db.ForeignKey("water_sources.id", ondelete="RESTRICT"), nullable=False
    )
    diajukan_oleh = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    asal = db.Column(db.String(10), nullable=False, default="warga")
    prioritas = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="menunggu")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    source = db.relationship("WaterSource", back_populates="samples")
    submitter = db.relationship("User", back_populates="samples")
    test_results = db.relationship("TestResult", back_populates="sample")


class TestResult(db.Model):
    __test__ = False

    __tablename__ = "test_results"
    __table_args__ = (
        CheckConstraint("ph >= 0 AND ph <= 14", name="ck_results_ph"),
        CheckConstraint(
            "kekeruhan_ntu >= 0 AND kekeruhan_ntu <= 1000",
            name="ck_results_turbidity",
        ),
        CheckConstraint("tds_mgl >= 0 AND tds_mgl <= 5000", name="ck_results_tds"),
        CheckConstraint(
            "vonis IN ('BERSIH', 'WASPADA', 'TIDAK_LAYAK')",
            name="ck_results_vonis",
        ),
        UniqueConstraint("sample_id", name="uq_test_results_sample"),
        Index("ix_test_results_source_created", "source_id", "created_at"),
        Index("ix_test_results_sample", "sample_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(
        db.Integer, db.ForeignKey("samples.id", ondelete="CASCADE"), nullable=False
    )
    source_id = db.Column(
        db.Integer, db.ForeignKey("water_sources.id", ondelete="RESTRICT"), nullable=False
    )
    ph = db.Column(db.Float, nullable=False)
    kekeruhan_ntu = db.Column(db.Float, nullable=False)
    tds_mgl = db.Column(db.Float, nullable=False)
    vonis = db.Column(db.String(20), nullable=False)
    jejak_keputusan = db.Column(db.Text, nullable=False)
    diuji_oleh = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    sample = db.relationship("Sample", back_populates="test_results")
    source = db.relationship("WaterSource", back_populates="test_results")
    tester = db.relationship("User")


class RiverEdge(db.Model):
    __tablename__ = "river_edges"
    __table_args__ = (
        UniqueConstraint(
            "dari_source_id", "ke_source_id", name="uq_river_edges_direction"
        ),
        CheckConstraint("jarak_km > 0", name="ck_river_edges_distance"),
        CheckConstraint(
            "dari_source_id != ke_source_id", name="ck_river_edges_not_self"
        ),
        Index("ix_river_edges_from", "dari_source_id"),
        Index("ix_river_edges_to", "ke_source_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    dari_source_id = db.Column(
        db.Integer, db.ForeignKey("water_sources.id", ondelete="CASCADE"), nullable=False
    )
    ke_source_id = db.Column(
        db.Integer, db.ForeignKey("water_sources.id", ondelete="CASCADE"), nullable=False
    )
    jarak_km = db.Column(db.Float, nullable=False)

    source_from = db.relationship(
        "WaterSource", foreign_keys=[dari_source_id], back_populates="outgoing_edges"
    )
    source_to = db.relationship(
        "WaterSource", foreign_keys=[ke_source_id], back_populates="incoming_edges"
    )


class EntryAction(db.Model):
    __tablename__ = "entry_actions"
    __table_args__ = (Index("ix_entry_actions_user_created", "user_id", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    aksi = db.Column(db.String(40), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    user = db.relationship("User")


class IotDevice(db.Model):
    __tablename__ = "iot_devices"
    __table_args__ = (
        Index("ix_iot_devices_source_aktif", "source_id", "aktif"),
    )

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(
        db.Integer, db.ForeignKey("water_sources.id", ondelete="RESTRICT"), nullable=False
    )
    kode = db.Column(db.String(80), nullable=False, unique=True)
    nama = db.Column(db.String(120), nullable=False)
    api_key_hash = db.Column(db.String(64), nullable=False)
    aktif = db.Column(db.Boolean, nullable=False, default=True)
    last_seen = db.Column(db.DateTime)
    last_ingested_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    source = db.relationship("WaterSource", back_populates="iot_devices")
    readings = db.relationship("SensorReading", back_populates="device")


class SensorReading(db.Model):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        CheckConstraint("ph >= 0 AND ph <= 14", name="ck_readings_ph"),
        CheckConstraint(
            "kekeruhan_ntu >= 0 AND kekeruhan_ntu <= 1000",
            name="ck_readings_turbidity",
        ),
        CheckConstraint("tds_mgl >= 0 AND tds_mgl <= 5000", name="ck_readings_tds"),
        CheckConstraint(
            "status IN ('antri', 'diproses')", name="ck_readings_status"
        ),
        CheckConstraint(
            "vonis IS NULL OR vonis IN ('BERSIH', 'WASPADA', 'TIDAK_LAYAK')",
            name="ck_readings_vonis",
        ),
        UniqueConstraint(
            "device_id", "ts_sensor", name="uq_sensor_readings_device_timestamp"
        ),
        Index("ix_sensor_readings_device_received", "device_id", "diterima_at"),
        Index("ix_sensor_readings_queue", "status", "diterima_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(
        db.Integer, db.ForeignKey("iot_devices.id", ondelete="RESTRICT"), nullable=False
    )
    source_id = db.Column(
        db.Integer, db.ForeignKey("water_sources.id", ondelete="RESTRICT"), nullable=False
    )
    ph = db.Column(db.Float, nullable=False)
    kekeruhan_ntu = db.Column(db.Float, nullable=False)
    tds_mgl = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="antri")
    vonis = db.Column(db.String(20))
    jejak_keputusan = db.Column(db.Text)
    ts_sensor = db.Column(db.DateTime)
    diterima_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    diproses_at = db.Column(db.DateTime)

    device = db.relationship("IotDevice", back_populates="readings")
    source = db.relationship("WaterSource", back_populates="sensor_readings")
