import sqlite3
import os
import sys
from typing import List, Tuple, Callable
from config import Config
from models import Base

# Registry of versioned migration functions
MIGRATIONS: List[Tuple[int, str, Callable[[sqlite3.Connection], None]]] = []

def register_migration(version: int, description: str):
    def decorator(fn: Callable[[sqlite3.Connection], None]):
        MIGRATIONS.append((version, description, fn))
        MIGRATIONS.sort(key=lambda m: m[0])
        return fn
    return decorator

@register_migration(1, "Initial baseline tables for threads, events, episodes, surfaces, relations, and friction logs")
def migration_v1_baseline(conn: sqlite3.Connection):
    # Baseline tables are created by Base.metadata.create_all
    pass

@register_migration(2, "Add work_packets table with guardrails and authority levels")
def migration_v2_work_packets(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS work_packets (
        id INTEGER PRIMARY KEY,
        thread_id INTEGER NOT NULL,
        desired_outcome TEXT NOT NULL,
        constraints TEXT,
        stop_conditions TEXT,
        authority_level VARCHAR(50) NOT NULL DEFAULT 'EXECUTE_AND_TEST',
        expected_evidence VARCHAR(255) NOT NULL DEFAULT 'Passing test suite & git working set diff',
        review_requirement VARCHAR(50) NOT NULL DEFAULT 'MANDATORY_HUMAN_REVIEW',
        status VARCHAR(50) NOT NULL DEFAULT 'PREPARED',
        result_summary TEXT,
        result_evidence TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        dispatched_at DATETIME,
        completed_at DATETIME,
        FOREIGN KEY(thread_id) REFERENCES threads(id) ON DELETE CASCADE
    )
    """)
    conn.commit()

@register_migration(3, "Add epistemic_nodes and epistemic_edges tables for provenance graph")
def migration_v3_epistemic_graph(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS epistemic_nodes (
        id INTEGER PRIMARY KEY,
        thread_id INTEGER NOT NULL,
        node_type VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,
        statement TEXT NOT NULL,
        confidence FLOAT NOT NULL DEFAULT 1.0,
        status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
        payload_json TEXT,
        actor_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY(actor_id) REFERENCES actors(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS epistemic_edges (
        id INTEGER PRIMARY KEY,
        source_node_id INTEGER NOT NULL,
        target_node_id INTEGER NOT NULL,
        edge_type VARCHAR(50) NOT NULL,
        weight FLOAT NOT NULL DEFAULT 1.0,
        note TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(source_node_id) REFERENCES epistemic_nodes(id) ON DELETE CASCADE,
        FOREIGN KEY(target_node_id) REFERENCES epistemic_nodes(id) ON DELETE CASCADE
    )
    """)
    conn.commit()

def run_migrations(db_path: str = None) -> int:
    """
    Applies all pending migrations safely to the SQLite database.
    Returns the number of migrations applied.
    """
    if not db_path:
        db_uri = Config.SQLALCHEMY_DATABASE_URI
        if db_uri.startswith("sqlite:///"):
            db_path = db_uri.replace("sqlite:///", "")
        else:
            db_path = "codec.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure schema_version table exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        description TEXT NOT NULL,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()

    cursor.execute("SELECT version FROM schema_migrations")
    applied_versions = {row[0] for row in cursor.fetchall()}

    applied_count = 0
    for version, desc, fn in MIGRATIONS:
        if version not in applied_versions:
            print(f"[Migration] Applying version {version}: {desc}...")
            fn(conn)
            cursor.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (version, desc)
            )
            conn.commit()
            applied_count += 1

    conn.close()
    return applied_count

if __name__ == "__main__":
    count = run_migrations()
    print(f"Migrations complete. {count} new migrations applied.")
