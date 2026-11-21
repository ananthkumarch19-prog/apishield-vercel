CREATE TABLE IF NOT EXISTS companies (
    id BIGINT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('employee', 'admin'))
);
CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users(lower(email));
CREATE TABLE IF NOT EXISTS invoices (
    id BIGINT PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(id),
    invoice_number TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    amount BIGINT NOT NULL CHECK (amount >= 0 AND amount <= 100000000000),
    status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'overdue')),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_invoices_company ON invoices(company_id, id);
CREATE TABLE IF NOT EXISTS security_events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    company_id BIGINT REFERENCES companies(id),
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
