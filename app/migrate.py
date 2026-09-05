"""Transactional forward SQL migrations; serialize runners and verify checksums."""
import hashlib
import os
from pathlib import Path

import psycopg


def migrate(database_url):
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(190001)")
        connection.execute("""CREATE TABLE IF NOT EXISTS schema_migration (
            name text PRIMARY KEY, checksum text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now())""")
        for path in sorted((Path(__file__).resolve().parents[1] / "migrations").glob("*.sql")):
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            old = connection.execute(
                "SELECT checksum FROM schema_migration WHERE name = %s", (path.name,)
            ).fetchone()
            if old:
                if old[0] != checksum:
                    raise ValueError(f"Applied migration changed: {path.name}")
                continue
            connection.execute(sql)
            connection.execute(
                "INSERT INTO schema_migration (name, checksum) VALUES (%s, %s)",
                (path.name, checksum),
            )


if __name__ == "__main__":
    migrate(os.environ["DATABASE_URL"])
    print("Migrations applied and checksums verified.")
