import sqlite3


def test_sqlite_is_available_for_local_development():
    connection = sqlite3.connect(":memory:")
    try:
        assert connection.execute("SELECT 1").fetchone() == (1,)
    finally:
        connection.close()
