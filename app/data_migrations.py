from sqlalchemy import MetaData, inspect, text
from sqlalchemy.schema import CreateTable

from app import db


_ADDITIVE_COLUMNS = {
    "water_sources": (
        ("sumber_data", "VARCHAR(20) NOT NULL DEFAULT 'simulasi'"),
        ("is_simulated", "BOOLEAN NOT NULL DEFAULT 1"),
        ("referensi", "TEXT"),
    ),
    "river_edges": (
        ("sumber_jarak", "VARCHAR(40) NOT NULL DEFAULT 'simulasi'"),
        ("terverifikasi", "BOOLEAN NOT NULL DEFAULT 0"),
    ),
    "test_results": (
        ("sumber_data", "VARCHAR(20) NOT NULL DEFAULT 'simulasi'"),
        ("referensi", "TEXT"),
        ("tanggal_pengambilan", "DATE"),
    ),
}


def _add_missing_columns(connection):
    inspector = inspect(connection)
    for table_name, columns in _ADDITIVE_COLUMNS.items():
        if not inspector.has_table(table_name):
            continue
        existing = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        for column_name, declaration in columns:
            if column_name not in existing:
                table_identifier = connection.dialect.identifier_preparer.quote(
                    table_name
                )
                column_identifier = connection.dialect.identifier_preparer.quote(
                    column_name
                )
                connection.execute(
                    text(
                        f"ALTER TABLE {table_identifier} "
                        f"ADD COLUMN {column_identifier} {declaration}"
                    )
                )
                existing.add(column_name)


def _rebuild_sqlite_table(connection, model, table_name):
    old_columns = {
        column["name"] for column in inspect(connection).get_columns(table_name)
    }
    temporary_name = f"{table_name}_phase_d_new"
    metadata = MetaData()
    metadata.reflect(bind=connection)
    new_table = model.__table__.to_metadata(metadata, name=temporary_name)
    create_statement = CreateTable(new_table).compile(dialect=connection.dialect)
    connection.exec_driver_sql(str(create_statement))

    copy_columns = [
        column.name for column in model.__table__.columns if column.name in old_columns
    ]
    quoted = ", ".join(f'"{column}"' for column in copy_columns)
    connection.execute(
        text(
            f'INSERT INTO "{temporary_name}" ({quoted}) '
            f'SELECT {quoted} FROM "{table_name}"'
        )
    )
    connection.execute(text(f'DROP TABLE "{table_name}"'))
    connection.execute(
        text(f'ALTER TABLE "{temporary_name}" RENAME TO "{table_name}"')
    )
    for index in model.__table__.indexes:
        index.create(bind=connection, checkfirst=True)


def _migrate_sqlite_tables(connection):
    from app.models import Region, TestResult, WaterSource

    inspector = inspect(connection)
    if inspector.has_table("regions"):
        checks = inspector.get_check_constraints("regions")
        level_check = next(
            (check["sqltext"] for check in checks if check.get("name") == "ck_regions_level"),
            "",
        )
        if "kabupaten" not in level_check:
            _rebuild_sqlite_table(connection, Region, "regions")

    inspector = inspect(connection)
    if inspector.has_table("water_sources"):
        columns = {
            column["name"]: column for column in inspector.get_columns("water_sources")
        }
        if any(columns[name]["nullable"] is False for name in ("region_id", "lat", "lng")):
            _rebuild_sqlite_table(connection, WaterSource, "water_sources")

    inspector = inspect(connection)
    if inspector.has_table("test_results"):
        columns = {
            column["name"]: column for column in inspector.get_columns("test_results")
        }
        checks = inspector.get_check_constraints("test_results")
        verdict_check = next(
            (check["sqltext"] for check in checks if check.get("name") == "ck_results_vonis"),
            "",
        )
        if (
            columns["sample_id"]["nullable"] is False
            or columns["vonis"]["nullable"] is False
            or "IS NULL" not in verdict_check.upper()
        ):
            _rebuild_sqlite_table(connection, TestResult, "test_results")


def _migrate_mysql_tables(connection):
    inspector = inspect(connection)
    if inspector.has_table("regions"):
        checks = inspector.get_check_constraints("regions")
        if not any(
            "kabupaten" in check.get("sqltext", "").lower()
            for check in checks
            if check.get("name") == "ck_regions_level"
        ):
            connection.execute(text("ALTER TABLE regions DROP CHECK ck_regions_level"))
            connection.execute(
                text(
                    "ALTER TABLE regions ADD CONSTRAINT ck_regions_level "
                    "CHECK (level IN "
                    "('provinsi', 'kabupaten', 'kota', 'kecamatan', 'desa'))"
                )
            )

    if inspector.has_table("water_sources"):
        connection.execute(
            text(
                "ALTER TABLE water_sources "
                "MODIFY region_id INTEGER NULL, "
                "MODIFY lat FLOAT NULL, MODIFY lng FLOAT NULL"
            )
        )

    if inspector.has_table("test_results"):
        checks = inspect(connection).get_check_constraints("test_results")
        if any(
            check.get("name") == "ck_results_vonis"
            and "IS NULL" not in check.get("sqltext", "").upper()
            for check in checks
        ):
            connection.execute(
                text("ALTER TABLE test_results DROP CHECK ck_results_vonis")
            )
            connection.execute(
                text(
                    "ALTER TABLE test_results ADD CONSTRAINT ck_results_vonis "
                    "CHECK (vonis IS NULL OR vonis IN "
                    "('BERSIH', 'WASPADA', 'TIDAK_LAYAK'))"
                )
            )
        connection.execute(
            text(
                "ALTER TABLE test_results "
                "MODIFY sample_id INTEGER NULL, MODIFY vonis VARCHAR(20) NULL"
            )
        )


def ensure_phase_d_schema():
    """Apply additive provenance columns and safe nullability/check migrations."""
    dialect = db.session.get_bind().dialect.name
    if dialect not in {"sqlite", "mysql"}:
        raise RuntimeError(f"Migrasi Fase D tidak mendukung database {dialect}.")

    if dialect == "sqlite":
        with db.engine.connect() as connection:
            try:
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.commit()
                with connection.begin():
                    _add_missing_columns(connection)
                    _migrate_sqlite_tables(connection)
                    violations = connection.exec_driver_sql(
                        "PRAGMA foreign_key_check"
                    ).fetchall()
                    if violations:
                        raise RuntimeError(
                            "Migrasi Fase D menghasilkan pelanggaran foreign key: "
                            f"{violations}"
                        )
            finally:
                if connection.in_transaction():
                    connection.rollback()
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                connection.commit()
    else:
        with db.engine.begin() as connection:
            _add_missing_columns(connection)
            _migrate_mysql_tables(connection)
