"""Only fictional records. Seeding never silently overwrites an existing DB."""
from werkzeug.security import generate_password_hash
from database.db import get_db, init_db, is_demo_database

DEMO_PASSWORD = "Demo@2026!"
PASSWORD_METHOD = "scrypt:32768:8:3"
COMPANIES = [(1, "Alpha Traders"), (2, "Beta Enterprises")]
USERS = [
    (1, 1, "Alice", "alice@alpha.test", "employee"),
    (2, 1, "Alpha Admin", "admin@alpha.test", "admin"),
    (3, 2, "Bob", "bob@beta.test", "employee"),
    (4, 2, "Beta Admin", "admin@beta.test", "admin"),
]
INVOICES = [
    (1001, 1, "INV-1001", "Cedar Office Supplies", 4250000, "pending", "2026-11-01T09:00:00+00:00"),
    (1002, 1, "INV-1002", "Maple Retail Studio", 1875000, "paid", "2026-11-03T10:30:00+00:00"),
    (1003, 1, "INV-1003", "Harbor Packaging", 6822500, "overdue", "2026-11-05T08:15:00+00:00"),
    (1004, 1, "INV-1004", "Summit Workspace", 1230000, "pending", "2026-11-09T11:45:00+00:00"),
    (2001, 2, "INV-2001", "Orchid Logistics", 9600000, "pending", "2026-11-02T09:20:00+00:00"),
    (2002, 2, "INV-2002", "Pebble Design House", 2485000, "paid", "2026-11-04T12:00:00+00:00"),
    (2003, 2, "INV-2003", "Horizon Components", 15475000, "overdue", "2026-11-07T14:10:00+00:00"),
    (2004, 2, "INV-2004", "Willow Hospitality", 3650000, "pending", "2026-11-10T10:00:00+00:00"),
]


def seed_demo(password_hashes=None):
    init_db()
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM companies").fetchone()[0]:
        raise ValueError("Database already contains companies. Use reset-demo to restore fictional invoices.")
    hashes = password_hashes or [generate_password_hash(DEMO_PASSWORD, method=PASSWORD_METHOD) for _ in USERS]
    with db:
        db.executemany("INSERT INTO companies(id, name) VALUES (?, ?)", COMPANIES)
        db.executemany(
            "INSERT INTO users(id, company_id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?, ?)",
            [(*u[:4], hashes[i], u[4]) for i, u in enumerate(USERS)],
        )
        db.executemany("INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?)", INVOICES)
        db.execute("INSERT INTO metadata VALUES (?, ?)", ("dataset", "apishield-fictional-v1"))


def reset_invoices():
    """Restore fixtures only. Preserve users, salted hashes, and audit history."""
    if not is_demo_database():
        raise ValueError("Reset is restricted to the marked fictional demonstration database.")
    db = get_db()
    with db:
        db.execute("DELETE FROM invoices")
        db.executemany("INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?)", INVOICES)
