PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('employee', 'admin'))
);
CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id);
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    invoice_number TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    -- Integer paise avoids binary floating-point money errors.
    amount INTEGER NOT NULL CHECK (amount >= 0 AND amount <= 100000000000),
    status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'overdue')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_invoices_company ON invoices(company_id, id);
CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    -- This is the ACTOR's company, never an untrusted submitted company.
    company_id INTEGER REFERENCES companies(id),
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    action TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW', 'DENY', 'LAB_BYPASS')),
    reason TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_company_time ON security_events(company_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_events_user ON security_events(user_id);
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
