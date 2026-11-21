# Slide 1 APIShield

Introduce APIShield as a local Python CNS mini-project. Explain that every company must retain control of its invoices even when another company user is already logged in. This is an implementation and evidence presentation for the requested 17 November 2026 submission.

# Slide 2 The authorization problem

A legitimate account is sufficient to exercise the deliberately vulnerable endpoint. Manipulating the invoice identifier is the attack input. Disclosure affects confidentiality and changing the invoice affects integrity. This is specifically BOLA, not a claim to cover every OWASP risk. Reference: https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/

# Slide 3 Authentication and authorization

Authentication verifies identity. Authorization checks the specific action against the actual stored object's owner. Flask-Login manages sessions but does not implement our invoice permissions. References: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html and https://flask-login.readthedocs.io/en/latest/

# Slide 4 Company ownership and role permissions

Read the policy matrix. Administrators belong to one company and gain no global protected access. Unknown roles and unsupported actions deny by default. Source: security/authorization.py and tests/test_authorization.py. Reference: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

# Slide 5 Protected and vulnerable request paths

The diagram separates the intentional lab exception. Before these paths, app.py checks loopback and the trusted Host. Authentication precedes the object operation and CSRF applies to writes. The protected path fetches the stored owner then applies company and role checks. Success and denials create audit records. The lab deliberately bypasses ownership and role checks, and is only enabled in local lab mode. The simulator duplicates this application on a disposable database.

# Slide 6 SQLite data model

The requested four tables are implemented with foreign keys and indexes. A small metadata table marks the fictional dataset. amount is integer paise. created_at and audit timestamps use ISO-formatted UTC strings. Source: database/schema.sql and database/seed.py.

# Slide 7 The centralized policy

Walk through the company comparison before discussing the role. ROLE_ACTIONS grants employees read/list and administrators read/list/update. The helper first verifies authentication, handles missing resources, then logs a decision. Both HTML and JSON routes call it. Client company_id and role fields never replace database identity. Source: security/authorization.py.

# Slide 8 Password and session protection

Werkzeug scrypt hashes use N=32768, r=8, p=3, independently salted per user. This is a password KDF, not ordinary unsalted SHA-256. Flask sessions are signed, not encrypted, and permissions are reloaded from SQLite. Login rotates session/CSRF state. HttpOnly, SameSite Strict and no-store are configured. Secure cookies and HTTPS are not implemented in this loopback HTTP demo. References: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html, https://flask.palletsprojects.com/en/stable/web-security/, https://flask-login.readthedocs.io/en/latest/

# Slide 9 State changes require CSRF validation

Flask-WTF protects POST, PUT, PATCH and DELETE. The tests use real CSRF tokens. Clients fetch a token, log in, fetch another token after session rotation and send X-CSRFToken on PATCH. The missing-token test uses an otherwise authorized admin and verifies that the database stays unchanged. Source: scenario J and test_patch_csrf_protection. References: https://flask-wtf.readthedocs.io/en/1.2.x/csrf/ and https://flask.palletsprojects.com/en/stable/web-security/

# Slide 10 BOLA read comparison

These are real values from report/evidence/security_results.json, not mock outputs. B-L and B-P use the same authenticated Alice client and target invoice 2001. Only the endpoint path changes. The protected result is checked for absence of invoice fields and actual target values. Reference for the problem: https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/

# Slide 11 Proving whether a write occurred

C-P and C-L use Alice, invoice 2001 and the identical amount payload. Protected comparison runs first, changes nothing and leaves the same initial data for the lab request. E is a separate legitimate Alpha Admin update. Full before/after rows are stored and compared, including company, customer and status, not just amount. Source: report/evidence/security_results.json.

# Slide 12 The invoice application

This image comes from the actual /dashboard HTTP response for Alice, captured using Requests and rendered with an HTML-to-PDF engine. It is explicitly not a browser screenshot. The values came from the company-scoped database query. Real browser layout and JavaScript behavior remain unverified in this environment. Source: screenshots/rendered_http_pages/02_alice_overview.html and report/evidence/live_workflow.json.

# Slide 13 Recorded test outcomes

The final pytest suite passed 75 tests. It includes 30 authorization tests, 38 security control tests and 7 workflow tests. The standalone simulator passed 15 comparisons, including every requested A-H scenario and additional controls. A separate live Requests workflow passed nine checks. Tests ran on Linux, Python 3.12.14. These are test results, not statistical accuracy scores or proof of total security. Sources: report/evidence/pytest_results.xml, security_results.json and live_workflow.json.

# Slide 14 Audit monitoring uses stored decisions

The actual monitoring response is rendered here as a static document. Its events come from the live SQLite audit table. Administrators see actors in their company and employees see their own events. Anonymous events remain in SQLite. Simulation audit events appear with the disposable run. A rejected request can be an error or authorized test, so DENY is not automatically called an attack. Logs contain metadata rather than credentials. Source: security/audit.py and web.py.

# Slide 15 CNS syllabus connections

Use these exact claims in the evaluation. Module 1: BOLA and least privilege. Module 2: salted password KDFs. Module 3: authentication, sessions and authorization. Module 4: API access prevention and application audit monitoring. No RSA, DES, Kerberos, IPSec, SAML or WS-Security is implemented. This is not a packet-level network IDS.

# Slide 16 Local Windows demonstration

Use the full PowerShell instructions in README.md. Python 3.12 is recommended. If Activate.ps1 is blocked, use the virtual environment python.exe directly. The initialized fictional SQLite database is included and init-db is safe to repeat. The launcher always binds 127.0.0.1. With --lab, vulnerable routes are intentionally enabled. Start without --lab and remove any APISHIELD_LAB_MODE environment setting to disable them. Windows commands were prepared but not executed in this Linux environment.

# Slide 17 Validated scope and remaining work

Be candid about the evidence. Python tests, actual HTTP comparison and live HTTP form workflow passed. Windows execution and actual browser workflow/layout were not tested here. The local browser could not launch and the separate browser could not access loopback. Elevated browser execution was rejected by the approval policy. Static HTTP response renders must not be presented as browser screenshots. Load/concurrency tests, TLS, MFA, rate limiting and tamper-evident logging are future work. The Windows browser checklist is supplied.

# Slide 18 References and demonstration evidence

References consulted 14 November 2026. https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/
https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
https://flask.palletsprojects.com/en/stable/web-security/
https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
https://flask-wtf.readthedocs.io/en/1.2.x/csrf/
https://flask-login.readthedocs.io/en/latest/
Werkzeug: https://werkzeug.palletsprojects.com/en/stable/utils/
Primary implementation evidence is included in the ZIP under report/evidence. Finish by opening the actual results file or running the simulator. Do not claim a browser screenshot or Windows validation that has not occurred.
