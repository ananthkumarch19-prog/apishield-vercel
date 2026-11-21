# APIShield project report

A Python-Based API Authorization and Unauthorized Data Access Prevention System

Cryptography and Network Security mini-projectImplementation and verification reportSubmission deadline 17 November 2026

## Abstract

APIShield is a local Python invoice application that demonstrates why a valid login does not imply permission to access every record. Two fictional companies share one SQLite database. Protected routes enforce the invoice company boundary and role permissions on the server. An isolated, explicitly enabled lab reproduces Broken Object Level Authorization for comparison.

The implementation includes login, invoice listings and details, authorized updates, CSRF protection, a security audit dashboard, and a simulator that compares actual HTTP responses and database states. The completed Linux run passed 75 pytest tests, all 15 HTTP scenario checks, and nine additional live HTTP workflow checks. Windows execution and an actual browser workflow remain unverified. Provided interface images are static renders of captured server HTML, not browser screenshots.

| Verification | Observed result |
| --- | --- |
| Automated suite | 75 passed with CSRF enabled |
| HTTP comparison engine | 15 of 15 checks passed |
| Live application workflow | 9 checks passed |
| Windows and browser | Not executed or verified here |

This report documents the implemented behavior and its limits. It does not claim comprehensive OWASP coverage or production readiness.

# 1 Problem statement and objectives

Modern business APIs expose records through identifiers. An application can correctly verify a password and still return the wrong organization's data if it checks only whether the requester is logged in. Manipulating an invoice identifier can then disclose customer details or change an amount or payment status.

The problem addressed here is insufficient object-level authorization in a multi-tenant invoice application. The goal is to enforce server-side ownership and role checks for each protected operation, maintain company data isolation and record authorization decisions. A deliberately vulnerable local API and the protected API must be evaluated using the same identities, resources and operations.

## Why this project is demonstrable

Alice has a legitimate Alpha account. Invoice 2001 belongs to Beta. The vulnerable endpoint returns that invoice to Alice, while the protected endpoint returns 403 without invoice fields. A similar update comparison checks the stored row before and after the operation. These observations directly connect the security defect, the control and the outcome.

| Objective | Implemented evidence |
| --- | --- |
| Functional business application | Login, company listing, detail and administrator edit pages |
| Object authorization | Central company-and-action policy for HTML and JSON |
| Containment | Loopback-only launch, explicit lab mode and fictional dataset gate |
| Measurable comparison | Real HTTP responses and before/after database rows |
| Learning and submission | Source, tests, report, editable slides and viva preparation |

## Scope

The application focuses on BOLA, supporting role restrictions, CSRF and safe update validation. It does not implement real payment processing, external customer data, invoice deletion or account registration. All companies, people and customers in the database are fictional.

# 2 Threat model and business policy

The requester may possess a valid employee or company administrator account and control URL identifiers, query parameters, headers and JSON bodies. The server code, signing secret, seeded ownership relationships and local database are trusted in this model. A compromised operating system or direct database access can defeat application controls and is outside scope.

| Identity | Own-company read | Own-company update | Other company |
| --- | --- | --- | --- |
| Employee | Allow | Deny | Deny |
| Company admin | Allow | Allow | Deny |
| No valid session | 401 | 401 | 401 |

Authorization uses a combination of role permissions and a company relationship. A role alone is insufficient. The company check applies before administrator privileges, so an administrator has no protected global invoice access.

## Authentication and authorization

Authentication establishes that the requester controls an account. Authorization evaluates whether that account may perform this action on this object. Flask-Login supports the first task. The application policy implements the second task. Browser controls cannot substitute for server enforcement because direct HTTP requests can bypass the interface. [1, 2]

## Deliberate teaching exception

The lab intentionally violates invoice authorization when explicitly enabled. Its direct endpoints use the current fictional database. The dashboard lab controls are an additional fixture-management capability for local administrators and run comparisons in a separate disposable database. These exceptions are labeled and are never described as normal protected privileges.

## Acceptance criteria

A cross-company protected read must return no invoice data. A cross-company or employee update must not change any invoice field. A permitted administrator update must really persist. Unauthenticated requests must receive 401. Invalid resources receive 404. Identity fields submitted by the client must not change these decisions.

# 3 System architecture and request flow

The protected and deliberately vulnerable paths share authentication but differ at object authorization. Successful protected writes and their audit entry commit together. The database also provides persisted records for the security monitoring page.

![Architecture of the implemented local application. The dashed lab branch is a deliberate exception.](report/architecture.png)

The simulator creates another instance of this architecture on an OS-selected loopback port. Both comparison paths in that instance operate on the same disposable database. There is no public deployment or external request destination.

# 4 Database and fictional sample data

| Table | Important fields and constraints |
| --- | --- |
| companies | id primary key, unique name |
| users | id, company_id foreign key, name, unique email, password_hash, employee/admin role |
| invoices | id, company_id foreign key, unique invoice_number, customer_name, amount, status, created_at |
| security_events | id, nullable user_id/company_id foreign keys, resource_type/id, action, decision, reason, timestamp |
| metadata | key/value marker identifying the fictional fixture dataset |

Foreign keys are enabled for each connection. Indexes support users by company, invoices by company/id, events by company/time and events by user. Parameterized values prevent submitted text from becoming SQL syntax. The actual complete schema is in database/schema.sql.

| Company | Invoice | Fictional customer | Amount INR | Status |
| --- | --- | --- | --- | --- |
| Alpha | INV-1001 | Cedar Office Supplies | 42,500.00 | pending |
| Alpha | INV-1002 | Maple Retail Studio | 18,750.00 | paid |
| Alpha | INV-1003 | Harbor Packaging | 68,225.00 | overdue |
| Alpha | INV-1004 | Summit Workspace | 12,300.00 | pending |
| Beta | INV-2001 | Orchid Logistics | 96,000.00 | pending |
| Beta | INV-2002 | Pebble Design House | 24,850.00 | paid |
| Beta | INV-2003 | Horizon Components | 154,750.00 | overdue |
| Beta | INV-2004 | Willow Hospitality | 36,500.00 | pending |

The amount column stores integer paise. API output uses two-decimal INR strings. This avoids binary floating-point storage errors. Customer names and payment statuses are editable; company and invoice identity are not.

# 5 Authentication and password protection

Four seeded identities provide employee and administrator roles in both companies. Login selects the account with a parameterized email lookup, verifies its stored hash and starts a fresh session. A failed login returns a generic message. This implementation does not provide rate limiting, registration or password recovery.

| Account | Email | Role |
| --- | --- | --- |
| Alice | alice@alpha.test | employee |
| Alpha Admin | admin@alpha.test | admin |
| Bob | bob@beta.test | employee |
| Beta Admin | admin@beta.test | admin |

The shared public demonstration password is Demo@2026!. Each database account has a different salted scrypt hash. The database does not store the plaintext password. Demo credentials remain in the fixture/simulator code so the project is reproducible.

## Password derivation

```python
generate_password_hash(password,
                       method="scrypt:32768:8:3")
check_password_hash(stored_hash, submitted_password)
```

Scrypt is a password-based key derivation function with memory and work parameters. The selected N=32768, r=8, p=3 configuration is one of the OWASP documented alternatives. A unique salt prevents identical passwords from sharing the same stored value. Ordinary unsalted SHA-256 is a fast digest and is not a substitute for this password protection. [4, 5]

## Session identity

Flask sessions are signed, not encrypted. The signing secret is generated locally and excluded from the package. Flask-Login stores a user identifier, while its user loader re-reads the current company and role from SQLite on each request. Submitted role/company fields are not used as authority. Login clears previous session state; clients fetch a new CSRF token afterward. [7]

# 6 Central authorization and safe updates

All protected detail and update paths use one policy. Its core is small enough to explain during a viva. A missing or unknown permission never creates access.

```python
def policy(user, invoice_company_id, action):
    if not user.is_authenticated:
        return False, "authentication_required"
    if user.company_id != invoice_company_id:
        return False, "company_mismatch"
    if action not in ROLE_ACTIONS.get(user.role, frozenset()):
        return False, "role_not_permitted"
    return True, "same_company_and_permitted_role"
```

The helper retrieves the requested invoice, calls the policy using its stored company, logs the outcome and stops denied requests before serialization or mutation. Invoice collections use a company-scoped SQL query. HTML forms and JSON PATCH routes call the same update service. [1, 2]

## Update sequence

After authentication and CSRF validation, the update service checks ownership and the update permission. It then accepts only customer_name, amount and status. Decimal validation rejects negative values, non-finite numbers and fractional paise. Ownership and role fields are not writable.

The SQL statement uses a fixed validator allowlist for column names and placeholders for submitted values. The WHERE clause retains both the invoice ID and the already-checked stored company. The change and its ALLOW event execute within one SQLite transaction. Denied requests stop before this transaction.

## Response policy

| HTTP | Meaning here |
| --- | --- |
| 200 | Permitted read or applied update |
| 401 | No authenticated session |
| 403 | Company or role authorization failed |
| 404 | Requested resource missing or lab disabled |
| 400 | Invalid payload or failed CSRF validation |

A production system may return 404 for inaccessible objects to reduce existence disclosure. This educational application deliberately returns 403 with a reason.

# 7 CSRF and local lab containment

Cookie-authenticated changes require CSRF protection because browsers attach cookies to eligible requests. Flask-WTF validates tokens for POST, PUT, PATCH and DELETE. Tests do not disable this feature. Missing, forged and other-session tokens are covered. Authentication is checked first for API requests, so a request without a session returns 401. [3, 6]

| Control | Implementation |
| --- | --- |
| Local bind | Supplied launcher binds only to 127.0.0.1, debug off |
| Peer and Host checks | Real remote address must be loopback; Host must be 127.0.0.1 |
| Explicit opt-in | --lab or APISHIELD_LAB_MODE=1; disabled otherwise |
| Separate vulnerable module | api/vulnerable_lab.py is registered only in lab mode |
| Dataset restriction | Known fictional dataset marker required |
| Simulator target restriction | Internally created loopback server; no arbitrary URL input |
| Safe restoration | Disposable simulator database and explicit fixture reset |
| Session and response controls | HttpOnly, SameSite Strict, no-store, CSP and frame denial |

The lab preserves login, CSRF and payload validation while intentionally omitting object and role authorization. Direct lab updates can change the current fictional invoice database. The Reset Demo control restores fixtures. Dashboard comparison buttons instead use a separate temporary database and leave dashboard invoices unchanged.

Secure cookies are disabled only because this application intentionally uses HTTP on loopback. TLS is not implemented. Forwarded headers are not trusted and no reverse-proxy or public deployment is supported. These choices must not be copied into a production deployment unchanged.

# 8 Actual vulnerable and protected behavior

The following values are taken from report/evidence/security_results.json. B-L and B-P use the same authenticated Alice session and invoice 2001. C-P and C-L additionally use the same PATCH body. The protected request leaves the initial data unchanged before the vulnerable comparison.

| Test | Operation | HTTP | Observed behavior |
| --- | --- | --- | --- |
| B-L | GET /lab/invoices/2001 | 200 | Beta customer data exposed |
| B-P | GET /api/invoices/2001 | 403 | No confidential invoice fields |
| C-P | PATCH /api/invoices/2001 | 403 | Full database row unchanged |
| C-L | PATCH /lab/invoices/2001 | 200 | Unauthorized INR 1.00 amount persisted |

## Actual protected error body

```python
{
  "error": "Access denied",
  "reason": "company_mismatch"
}
```

## Actual vulnerable exposure

The lab response includes invoice_number INV-2001, company_id 2, customer_name Orchid Logistics and amount 96000.00. The protected response contains only error and reason. The test checks both the response structure and absence of those confidential target values.

## What a PASS means

A PASS on a vulnerable case means the intentionally incorrect behavior was successfully reproduced. It is not a security success for that route. A PASS on a protected denial requires the expected status and its behavioral checks, including unchanged data for rejected writes.

No responses or results are fabricated. The server and Requests clients run locally, and the JSON evidence includes the observed audit events and timestamps.

# 9 Database integrity evidence

| Test | HTTP | Before INR | After INR | Full-row comparison |
| --- | --- | --- | --- | --- |
| C-P | 403 | 96,000.00 | 96,000.00 | Unchanged |
| C-L | 200 | 96,000.00 | 1.00 | Changed |
| E | 200 | 42,500.00 | 45,250.00 | Changed |
| F-P | 403 | 96,000.00 | 96,000.00 | Unchanged |
| H-P | 403 | 96,000.00 | 96,000.00 | Unchanged |
| I | 403 | 42,500.00 | 42,500.00 | Unchanged |
| J | 400 | 42,500.00 | 42,500.00 | Unchanged |
| K | 400 | 42,500.00 | 42,500.00 | Unchanged |

C-P proves the protected cross-company update did not change the stored invoice. C-L proves the same operation really can change data when authorization is deliberately omitted. E proves that the protected update function still supports legitimate administrator work.

The tests compare every stored field, not only the amount displayed above. Company identity, invoice number, customer, status and creation time also remain unchanged for the denied update. The simulator repairs successful changes after recording evidence, then deletes the temporary database at the end of the run.

## Independent live workflow

A separate live HTTP workflow submitted the HTML administrator form with INR 43,123.45 and paid status, then re-read the API response to verify persistence. It ran the dashboard simulator and confirmed that value remained unchanged by the isolated run. Reset Demo restored INR 42,500.00 and pending status. The workflow also verified that logout produced 401 for subsequent protected access.

The nine live workflow checks are recorded in report/evidence/live_workflow.json. They use Requests, not a browser. They therefore verify server behavior rather than browser layout or JavaScript execution.

# 10 Simulation engine and audit monitoring

The engine creates a temporary directory, application and fictional database. Werkzeug binds an actual HTTP server to 127.0.0.1 on an available port. Requests clients obtain CSRF tokens, log in through the real endpoint and fetch new tokens. No test identity is injected directly into the session.

Each scenario records the expected status, actual status, actor, method, resource, response, expected behavior and observed checks. For mutations it also records the full before/after row. Status matching alone is insufficient: protected reads are checked for confidential data and blocked writes are checked for unchanged storage.

## Isolation and cleanup

The main dashboard starts the same engine, then saves results for the signed-in operator. The temporary app disables nested simulator controls. Requests ignores proxy environment settings and follows no redirects. A finally block closes clients, database and HTTP server. The temporary directory is removed even if the run fails.

## Stored security events

The application records ALLOW, DENY and LAB_BYPASS decisions with actor/company, resource, action, reason and UTC time. It never copies passwords, cookies, tokens or request bodies into logs. A successful update and its authorization event commit together. Denied or invalid attempts leave an explanatory event.

The monitoring page queries real SQLite rows. Administrators see actors in their own company; employees see their own activity. Anonymous events remain in SQLite without a company association. Events from isolated comparisons are included with each run on Test Results. A denied event is not automatically classified as malicious.

## Limits of this monitor

This is application event monitoring and access prevention. It is not a packet-based intrusion detection system. SQLite audit logs are not cryptographically tamper-evident and can be altered by someone controlling the local database file.

# 11 Scenario results

Recorded on 14 November 2026 with Python 3.12.14 on Linux. All 15 comparisons passed. This table summarizes the actual evidence; the full requested expected/observed behavior table is also supplied as Test_Results.pdf and CSV.

| Test | Scenario | Expected | Actual | Result |
| --- | --- | --- | --- | --- |
| A | Normal authorized access | 200 | 200 | PASS |
| B-L | BOLA read through vulnerable lab | 200 | 200 | PASS |
| B-P | Same BOLA read through protected API | 403 | 403 | PASS |
| C-P | Cross-company modification blocked | 403 | 403 | PASS |
| C-L | Same modification through vulnerable lab | 200 | 200 | PASS |
| D | Unauthenticated request | 401 | 401 | PASS |
| E | Authorized company administrator update | 200 | 200 | PASS |
| F | Cross-company administrator read | 403 | 403 | PASS |
| F-P | Cross-company administrator update | 403 | 403 | PASS |
| G | Nonexistent invoice | 404 | 404 | PASS |
| H | Forged company and role claims | 403 | 403 | PASS |
| H-P | Forged ownership in PATCH body | 403 | 403 | PASS |
| I | Employee cannot update own invoice | 403 | 403 | PASS |
| J | Missing CSRF token on authorized PATCH | 400 | 400 | PASS |
| K | Mass assignment rejected | 400 | 400 | PASS |

Scenarios A-H requested in the brief are all represented. Additional comparisons cover the vulnerable modification, cross-company administrator update, employee update restriction, missing CSRF and ownership-field rejection.

# 12 Automated validation and coverage

| Suite | Count | What it verifies |
| --- | --- | --- |
| Authorization | 30 | Both tenants and roles, reads/writes, lists, forged identity, missing objects and session tampering |
| Security controls | 38 | CSRF, login behavior, payload validation, escaping, password KDF, audit metadata, local/Host guards and lab gating |
| Workflows | 7 | HTML policy, admin update, event scope, reset, actual HTTP engine and dashboard simulation |
| Total | 75 | All passed with CSRF enabled |

The tests create temporary databases and use the same salted KDF configuration as the application. The role/tenant matrix specifies expected outcomes for both employees and both administrators. Update tests inspect the database after rejected requests. The simulator test runs actual HTTP rather than a mocked transport.

## Observed output

```python
........................................................................ [ 96%]
...                                                                      [100%]
75 passed in 15.68s
```

## Meaning of the result

These tests support the stated properties for the implemented paths and fixtures. They do not establish resistance to every attack, arbitrary deployment configurations or untested future features. This project has no full penetration test, load test or formal verification claim.

## Remaining checks

Windows execution has not been performed in this Linux environment. Chromium execution was blocked, and the separate browser could not access the local loopback server. Elevated browser execution was rejected by the approval policy. Actual browser behavior, responsive layout and browser screenshots therefore remain unverified. The Windows checklist in screenshots/README.md identifies the remaining steps.

# 13 Interface evidence from actual responses

The images below are static HTML-to-PDF renders of responses returned by the running server. They are not browser screenshots. CSRF fields were redacted before the HTML was saved. The renderer does not execute browser JavaScript or verify browser cookie behavior.

![Actual Alice overview HTTP response rendered as a document. The four listed records belong to Alpha.](screenshots/rendered_http_pages/02_alice_overview.png)

The overview calculates its count, amount total and unpaid count from company-scoped database rows. The invoice details and administrator management pages reuse the same server policy as the API. Static capture layout can differ from a browser.

# 14 Interface response and monitoring evidence

![Actual HTTP 403 HTML response to Alice requesting Beta invoice 2001. This is a static response render.](screenshots/rendered_http_pages/05_cross_company_denied.png)

![Actual security monitoring HTTP response rendered as a document. Its rows originate in SQLite.](screenshots/rendered_http_pages/10_security_monitoring.png)

Additional captured HTML, PDFs and PNGs cover login, invoice listing/detail, administrator editing, saved updates, lab controls and test results. Real browser screenshots remain to be captured on Windows.

# 15 CNS syllabus connection

| Module | Implemented connection | What to explain |
| --- | --- | --- |
| 1 | Cyber attacks and defense principles | BOLA, confidentiality/integrity, least privilege, deny by default and server-side checks |
| 2 | Cryptographic concepts in password protection | Unique salts, scrypt work/memory cost and the difference between a fast hash and a password KDF |
| 3 | Authentication and identity | Password verification, signed sessions, fresh database identity and the distinction between identity and permission |
| 4 | Web service security and access prevention | API method/status handling, CSRF, company isolation and stored authorization-event monitoring |

## A precise presentation claim

The project implements object-level authorization for the demonstrated invoice paths and records security decisions. It combines a company relationship with role permissions and uses a password KDF for stored credentials. This gives concrete CNS connections without claiming unrelated cryptographic protocols.

## Mechanisms not implemented

RSA, DES, Kerberos, IPSec, SAML and WS-Security are not implemented. The session cookie signature does not establish that the project implements RSA. The local HTTP interface does not implement TLS. The audit table is not a complete IDS or a tamper-evident logging system.

## Learning outcome

A student can trace one request from HTTP input through session identity, the SQLite resource lookup, company/role checks, allow or deny handling and the audit record. They can change the policy deliberately in a disposable copy, observe a regression test fail and explain why the test detects the security problem.

# 16 Windows setup and demonstration

Extract the ZIP, open the APIShield folder in VS Code and use a PowerShell terminal from the directory containing app.py. Python 3.12 is the recommended interpreter because that version was exercised here.

```python
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py init-db
python app.py serve --lab
```

Open a second PowerShell terminal and launch the dashboard:

```python
Start-Process "http://127.0.0.1:5000"
```

If activation is blocked, use .\.venv\Scripts\python.exe in place of python. The seeded database is included and init-db is safe to repeat. Every installation generates a fresh signing secret. No virtual environment or signing secret is distributed.

## Run independent checks

```python
python -m simulator.run --output report\my_run
python -m pytest -q
```

## Reset and protected-only mode

```python
python app.py reset-demo --lab --confirm-reset
python app.py serve
```

Stop the current server with Ctrl+C before reset/restart. Remove APISHIELD_LAB_MODE if previously set before protected-only startup. Use the README for the exact removal command, alternate port and full troubleshooting steps.

## Evaluation sequence

Show Alice reading Alpha, then the same Alice request for Beta on both APIs. Show Alpha Admin updating Alpha and being denied Beta. Run all comparisons, expand the unchanged database evidence and open the real audit dashboard. End by explaining the test scope and remaining Windows/browser checks.

# 17 Limitations and future work

The completed result is a working local educational application with verified Python and HTTP behavior. Its vulnerable branch is deliberately unsafe and must remain local with fictional data. Normal protected routes enforce the demonstrated business policy, but this report makes no claim that every OWASP API risk is solved.

| Current limitation | Possible future extension |
| --- | --- |
| Local HTTP and development server | Separate hardened HTTPS deployment after removing the lab |
| Public demo accounts | Real identity lifecycle, password recovery, MFA and rate limiting |
| Signed cookie sessions | Central revocation and hardened production secret management |
| Local SQLite audit trail | Protected external audit storage and operational alerting |
| Single-laptop workload | Load tests, multi-process concurrency review and database migration |
| Windows/browser unverified | Run provided commands and browser checklist on the submission laptop |

## Deliverables

The package includes modular source code, the seeded fictional SQLite database, requirements and lockfile, README with PowerShell commands, 75 automated tests, simulator JSON/CSV evidence, nine live workflow checks, static captured response renders, this report, a detailed results PDF, code walkthrough, viva preparation and an editable PowerPoint.

## Conclusion

The recorded experiment demonstrates a specific cause and effect: when object authorization is omitted, Alice receives or modifies Beta data; when the company-and-role policy is applied, the equivalent protected requests are denied without exposing the object or changing its row. Legitimate administrator updates continue to work. This is the tested contribution of APIShield.

# 18 References and evidence index

[1] OWASP API Security Top 10 2023 API1 Broken Object Level Authorizationhttps://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/

[2] OWASP Authorization Cheat Sheethttps://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

[3] Flask Security Considerationshttps://flask.palletsprojects.com/en/stable/web-security/

[4] OWASP Password Storage Cheat Sheethttps://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

[5] Werkzeug Security Helpershttps://werkzeug.palletsprojects.com/en/stable/utils/

[6] Flask-WTF CSRF Protectionhttps://flask-wtf.readthedocs.io/en/1.2.x/csrf/

[7] Flask-Login Documentationhttps://flask-login.readthedocs.io/en/latest/

Technical references were consulted on 14 November 2026. Framework documentation can describe a newer or different release; requirements.txt pins the versions actually executed for this package.

| Evidence file | Purpose |
| --- | --- |
| security_results.json / .csv | 15 real HTTP comparisons and database evidence |
| pytest_results.xml / pytest_output.txt | 75 passing automated tests |
| live_workflow.json | 9 live application HTTP workflow checks |
| requirements-lock.txt | Exact installed Python packages |
| screenshots/README.md | Capture provenance and remaining browser checklist |
