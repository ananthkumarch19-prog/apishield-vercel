"""PostgreSQL adapter for the application's existing parameterized queries."""
from pathlib import Path
from urllib.parse import urlsplit

import certifi
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash

from database.seed import COMPANIES, USERS, INVOICES, DEMO_PASSWORD, PASSWORD_METHOD


class PostgresDatabase:
    def __init__(self, url):
        options = {}
        hostname = urlsplit(url).hostname or ""
        if hostname.endswith(".neon.tech"):
            options.update(sslmode="verify-full", sslrootcert=certifi.where())
        self.connection = psycopg.connect(
            url, row_factory=dict_row, autocommit=True, prepare_threshold=None,
            connect_timeout=10, **options
        )
        self.transaction_context = None

    def execute(self, sql, values=()):
        # SQL templates are server-authored and use ? placeholders. Only this
        # placeholder syntax changes. All values remain separate driver parameters.
        return self.connection.execute(sql.replace("?", "%s"), values)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()

    def __enter__(self):
        self.transaction_context = self.connection.transaction()
        self.transaction_context.__enter__()
        return self

    def __exit__(self, *exception):
        return self.transaction_context.__exit__(*exception)

    def initialize_demo(self):
        """Initialize once, retaining edits and serializing concurrent cold starts."""
        schema = Path(__file__).with_name("postgres_schema.sql").read_text(encoding="utf-8")
        with self:
            self.execute("SELECT pg_advisory_xact_lock(20261121)")
            self.connection.execute(schema, prepare=False)
            marker = self.execute("SELECT value FROM metadata WHERE key=?", ("dataset",)).fetchone()
            if marker:
                if marker["value"] != "apishield-fictional-v1":
                    raise RuntimeError("The database is not an APIShield fictional demo.")
                return
            if self.execute("SELECT COUNT(*) AS count FROM companies").fetchone()["count"]:
                raise RuntimeError("Refusing to seed an existing unrecognized database.")
            for company in COMPANIES:
                self.execute("INSERT INTO companies(id,name) VALUES (?,?)", company)
            for user in USERS:
                user_id, company_id, name, email, role = user
                password_hash = generate_password_hash(DEMO_PASSWORD, method=PASSWORD_METHOD)
                self.execute(
                    "INSERT INTO users(id,company_id,name,email,password_hash,role) VALUES (?,?,?,?,?,?)",
                    (user_id, company_id, name, email, password_hash, role),
                )
            for invoice in INVOICES:
                self.execute("INSERT INTO invoices VALUES (?,?,?,?,?,?,?)", invoice)
            self.execute("INSERT INTO metadata(key,value) VALUES (?,?)", ("dataset", "apishield-fictional-v1"))
