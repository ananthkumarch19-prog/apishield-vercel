import sqlite3
from pathlib import Path
from flask import current_app, g


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA busy_timeout = 10000")
    return db


def get_db():
    if "db" not in g:
        if current_app.config.get("DATABASE_URL"):
            from database.postgres import PostgresDatabase
            db = PostgresDatabase(current_app.config["DATABASE_URL"])
            try:
                with current_app.extensions["database_initialization_lock"]:
                    if not current_app.extensions["database_initialized"]:
                        db.initialize_demo()
                        current_app.extensions["database_initialized"] = True
            except Exception:
                db.close()
                raise
            g.db = db
        else:
            g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    path = Path(current_app.config["DATABASE"])
    path.parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
    db.commit()


def is_demo_database():
    try:
        row = get_db().execute("SELECT value FROM metadata WHERE key = ?", ("dataset",)).fetchone()
        return row is not None and row["value"] == "apishield-fictional-v1"
    except sqlite3.OperationalError:
        return False
