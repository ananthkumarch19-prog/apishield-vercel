# APIShield code walkthrough

Start with the business rule: an employee may read their company's invoices; an administrator may also update their company's invoices. Neither may use the protected application to access another company's invoices.

## The central policy line by line

Open `security/authorization.py`.

| Lines | Meaning |
|---|---|
| 2-5 | Import HTTP rejection, authenticated identity, database access and audit recording. |
| 7 | Define the only known roles and their explicitly allowed operations. A frozen set cannot be accidentally extended in place. |
| 10 | `policy` receives the trusted user, the invoice's stored company ID and a server-selected action. |
| 11-12 | No authenticated identity means no permission. |
| 13-14 | Different companies means denial, including for administrators. This is the object ownership boundary. |
| 15-16 | Look up allowed actions. An unknown role gets an empty set, so it gains no permissions. |
| 17 | Allow only after both ownership and operation checks succeed. |
| 20-23 | The invoice helper checks identity first and records a denied unauthenticated attempt. |
| 25-27 | Fetch one invoice using a placeholder, never SQL string interpolation of its ID. Reject out-of-range SQLite integer IDs as nonexistent. |
| 28-30 | A missing invoice creates an audit event and returns 404. |
| 31 | Apply the centralized policy to the actual stored owner. |
| 32-34 | Record the reason and stop immediately with 403 when permission fails. |
| 35-37 | Record an allowed read and return the row to the calling route. Update authorization defers its allowed event until the write commits. |
| 40-48 | Authorize the collection and select only the authenticated company's rows. A safe detail endpoint alone would not protect an unsafe list endpoint. |

## Follow one protected read

`GET /api/invoices/2001` arrives with Alice's session cookie. `app.py` checks the real peer address and trusted host. Flask-Login verifies the signed session and uses `load_user` to reload Alice's database identity. `api/protected.py` calls `authorize_invoice(2001)`. The invoice exists and belongs to company 2, but Alice belongs to company 1. `policy` returns `False, company_mismatch`. The helper inserts a DENY event and raises HTTP 403. The JSON error handler returns only `error` and `reason`; it never calls `serialize_invoice` for the rejected object.

In contrast, `GET /lab/invoices/2001` reaches the deliberately vulnerable blueprint only in local lab mode with the fictional marker present. It still requires login, but it fetches and serializes the invoice without calling the ownership policy. The real comparison returns 200 for that route and 403 for the protected route with the same Alice identity and target.

## Follow one protected update

1. Authentication executes before global CSRF validation for API paths, so a missing identity returns 401.
2. Flask-WTF checks the session-bound CSRF token on PATCH. Missing/invalid tokens stop the request with 400.
3. `update_invoice` calls `authorize_invoice(id, 'update', audit_allow=False)`. A different company or an employee role stops execution with 403.
4. `validate_changes` accepts only customer name, amount and payment status. Ownership fields are rejected. Decimal arithmetic validates and converts INR to integer paise.
5. The SQL update uses a fixed allowlist for column names and placeholders for all submitted values. The WHERE clause also retains the already-authorized stored company.
6. The invoice update and ALLOW audit event occur inside the same SQLite transaction. An exception rolls back both.
7. The API serializes the updated row. The simulator independently reads the database to verify an actual update, instead of trusting the response status alone.

## Authentication and cryptography

`seed_demo` generates four different salted scrypt hashes using `scrypt:32768:8:3`. The same demo password produces different stored hashes because Werkzeug generates independent salts. Login verifies a submitted password with `check_password_hash`; the application never decrypts a password. Scrypt is a deliberately costly password-based key derivation function. A simple unsalted SHA-256 digest is fast and unsuitable as a substitute.

The signed Flask cookie contains a user identifier and session state. It is not encrypted storage. The server re-reads role and company from SQLite instead of trusting browser-supplied identity claims. `session.clear()` removes previous login/CSRF state before establishing the new session. API clients therefore fetch a new token after login.

## Database and audit

`database/db.py` opens one SQLite connection per request and enables foreign keys. `close_db` closes it when the request/app context finishes. `schema.sql` defines companies, users, invoices and security events plus a small metadata table identifying the fictional dataset. Indexes support company invoice lookup and audit filtering.

`security/audit.py` stores fixed metadata: actor, actor company, resource ID, action, decision, reason and UTC time. It never copies request bodies, passwords, cookies or CSRF/session tokens. DENY is an observed access decision, not a claim of an attack. LAB_BYPASS explicitly identifies the educational weakness. SQLite logs can be changed by someone with local file access, so they are not tamper-evident evidence.

## Simulator internals

`run_scenarios` creates a temporary directory and application, seeds the same fictional records, binds a Werkzeug server to 127.0.0.1 on an OS-selected port and starts its server thread. Requests clients log in with real credentials and obtain real CSRF tokens. No target URL is accepted from the user, and proxy environment settings are ignored.

`perform` captures the database row before the request, makes an actual HTTP request, captures the row afterward and checks the HTTP status plus the expected behavior. It stores the JSON response and non-secret evidence. The protected and vulnerable modification scenarios use the same Alice account, invoice ID and amount payload, with identical initial data. After a successful demonstration update, `restore` repairs only the disposable fixture for the next case. A `finally` block closes clients/database/server and the temporary directory is removed.

The dashboard launches this same engine. It stores each operator's returned results as JSON under `instance/results/`. The results page displays those saved observations. Its PASS badges are not fixed demo values. `export_results` produces portable JSON and CSV, while pytest additionally checks the engine itself.

## Frontend and reusable checks

Jinja renders the authenticated business pages and escapes displayed customer text. HTML forms contain Flask-WTF CSRF fields. The small JavaScript file only disables a run button and shows progress while submitting; it makes no authorization decisions. Hiding an edit link improves usability, while the server still rejects direct attempts to access the edit route.

Read tests in this order: `test_authorization.py` for the company/role matrix, `test_security_controls.py` for CSRF and input/host/session controls, and `test_workflows.py` for HTML updates, logs, reset and real HTTP simulation. Each test uses a disposable database, and CSRF is never disabled.

## Honest explanation of scope

This is an application-level prevention mechanism and audit monitor for the tested invoice endpoints. It is not a network intrusion detection system, a commercial API gateway or a proof against every attack. It does not claim RSA, DES, Kerberos, IPSec, SAML, WS-Security, MFA or TLS implementation. Windows/browser testing and high-load testing remain distinct from the completed Python/HTTP checks.
