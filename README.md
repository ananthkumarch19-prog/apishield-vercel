# APIShield

**A Python-Based API Authorization and Unauthorized Data Access Prevention System**

A local CNS mini-project demonstrating Broken Object Level Authorization (BOLA) in a fictional invoice application. The protected application combines authenticated sessions, company ownership checks and role permissions. An explicitly enabled vulnerable blueprint demonstrates the missing checks. The simulator compares actual HTTP responses and database state on a disposable local server.

## Verified build

- 75 pytest tests passed with CSRF enabled.
- 15 real HTTP scenario checks passed, including all requested scenarios A-H and extra role, CSRF and mass-assignment checks.
- Tested on Linux with Python 3.12.14. Windows execution has not been tested in this environment.
- A real browser could not be launched here. Browser automation and browser screenshots are unverified. Captures in `screenshots/rendered_http_pages/` are static renders of actual HTTP HTML, not browser screenshots. See `screenshots/README.md` and `report/evidence/`.
- Results establish these tested behaviors, not universal security, penetration-test certification or coverage of every OWASP risk.

## Windows quick start in VS Code

Install Python 3.12 for Windows with the Python launcher and VS Code. The application needs no Node, React, Docker, GPU, database server, cloud account or API key. Internet is needed only to install the Python packages initially. The running application loads no CDN assets.

Extract the ZIP. Open its `APIShield` folder in VS Code using **File > Open Folder**. Open **Terminal > New Terminal** and select PowerShell. Run these commands from the folder containing `app.py`:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py init-db
python app.py serve --lab
```

The ZIP includes an initialized fictional database. `init-db` safely leaves an initialized database unchanged. If the database file is absent, it creates and seeds it.

If PowerShell blocks activation, use the virtual environment directly without changing execution policy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py init-db
.\.venv\Scripts\python.exe app.py serve --lab
```

Keep the server terminal open. In another PowerShell terminal:

```powershell
Start-Process "http://127.0.0.1:5000"
```

Use **127.0.0.1**, not a LAN address or a public tunnel. The application intentionally trusts only that host and rejects remote client addresses. Do not start it through another server that binds publicly.

## Fictional demo logins

All four accounts use `Demo@2026!`. These are public teaching credentials, never real credentials.

| Name | Email | Company | Role |
|---|---|---|---|
| Alice | alice@alpha.test | Alpha Traders | employee |
| Alpha Admin | admin@alpha.test | Alpha Traders | admin |
| Bob | bob@beta.test | Beta Enterprises | employee |
| Beta Admin | admin@beta.test | Beta Enterprises | admin |

Each account has a different salted scrypt password hash in SQLite. The shared demonstration password appears only in seed/simulator teaching code and these instructions. It is never stored as a plaintext database password or written into audit events.

## Demonstrate the project in five minutes

1. Sign in as Alice. Open Company invoices and INV-1001. Explain that authentication establishes identity and the company filter restricts the list.
2. Navigate to `http://127.0.0.1:5000/api/invoices/2001`. Observe 403 and no Beta invoice data.
3. In lab mode, open `http://127.0.0.1:5000/lab/invoices/2001` using the same Alice session. Observe 200 and fictional Beta data. This endpoint intentionally skips authorization.
4. Sign out. Sign in as Alpha Admin. Open INV-1001 > Manage invoice. Change its amount or payment status and save. Reopen it to verify persistence.
5. Open Security lab > Run All Security Tests. The server launches a disposable loopback server, logs in real demo clients and issues HTTP requests through Requests. Expand B-P, C-P, C-L and E to inspect responses and before/after database values.
6. Open Security monitoring. Explain ALLOW, DENY and LAB_BYPASS. Denial alone does not establish malicious intent.
7. Use Reset Demo. It restores all eight fictional dashboard invoices and clears saved simulation results while retaining users and audit history.

The web controls require a signed-in company administrator and local lab mode. That does not make the administrator global: protected cross-company reads and updates still return 403. The demo controls are a deliberate local fixture-management capability. Never attach a real business dataset to this application.

## Run the scenarios and automated tests

In a second activated PowerShell terminal, from the project folder:

```powershell
python -m simulator.run --output report\my_run
python -m pytest -q --junitxml=report\my_run\pytest_results.xml
```

The simulator starts and stops its own temporary server; the dashboard server does not need to be running. The full run has 15 comparisons. A PASS for a vulnerable route means the intended flaw was successfully reproduced, not that the route is safe. The process exits with code 1 if a comparison fails. The output JSON contains real responses, behavioral checks, exact before/after rows and real audit events. CSV provides a portable results table.

Run a smaller group:

```powershell
python -m simulator.run --group bola --output report\bola_run
python -m simulator.run --group modification --output report\modification_run
```

CSRF stays enabled in tests. Tests obtain a token, submit login, obtain a new token after login rotates the session, and send `X-CSRFToken` for PATCH. Tests run against temporary databases and never reset your dashboard database.

## Reset and protected-only startup

Stop the server with Ctrl+C before a CLI reset:

```powershell
python app.py reset-demo --lab --confirm-reset
python app.py serve --lab
```

For protected-only mode, stop the server, remove any explicit lab-mode environment setting and restart:

```powershell
Remove-Item Env:APISHIELD_LAB_MODE -ErrorAction SilentlyContinue
python app.py serve
```

`/lab/invoices/...` then returns 404, the vulnerable blueprint is not registered and lab controls are disabled. Debug mode is always off in the supplied launcher. To use another loopback port:

```powershell
python app.py serve --lab --port 5001
Start-Process "http://127.0.0.1:5001"
```

## Business policy

| Identity | Own-company read/list | Own-company update | Other-company read/update |
|---|---|---|---|
| Employee | Allow | Deny | Deny |
| Company administrator | Allow | Allow | Deny |
| Unauthenticated | 401 | 401 | 401 |

Unknown roles and unsupported actions are denied. The application implements no create or delete invoice endpoint. Existing invoices can be read and updated as requested. Role and company are reloaded from the database on every authenticated request. The browser's `company_id`, `user_id`, headers and role claims never establish permissions.

## Routes

| Method | Path | Behavior |
|---|---|---|
| GET, POST | `/login` | Login form and CSRF-protected login |
| GET | `/auth/csrf` | Issue a CSRF token tied to this session |
| POST | `/logout` | CSRF-protected logout |
| GET | `/dashboard` | Company-scoped invoice overview |
| GET | `/invoices` | Company-scoped invoice listing |
| GET | `/invoices/<id>` | Authorized HTML invoice details |
| GET, POST | `/invoices/<id>/edit` | Administrator form using the same policy |
| GET | `/api/invoices` | Protected company-scoped JSON collection |
| GET, PATCH | `/api/invoices/<id>` | Protected object read and update |
| GET, PATCH | `/lab/invoices/<id>` | Intentionally vulnerable, only in local lab mode |
| GET | `/security-lab` | Lab instructions and operator controls |
| POST | `/security-lab/run` | Real HTTP comparison on a disposable server |
| POST | `/security-lab/reset` | Restore fictional fixtures, retain audit history |
| GET | `/security-monitoring` | Latest actual stored events in the user's scope |
| GET | `/test-results` | Current operator's actual saved simulation result |
| GET | `/health` | Local initialization and mode check |

API responses use 401 for no valid session, 403 for failed authorization, 404 for a nonexistent object, and 400 for invalid data or CSRF failures. Malformed routes and unsupported methods may return 404/405. A production API may return 404 for inaccessible objects to reduce existence disclosure. This teaching API intentionally shows 403 and an explanatory reason.

Example protected PATCH payload:

```json
{"amount": "45250.00", "status": "paid"}
```

Only `customer_name`, `amount` and `status` can be updated. Amounts are stored as integer paise and returned as decimal strings in INR. Unknown fields, ownership reassignment, NaN, infinity, negative amounts and fractional paise are rejected.

## Structure and reading order

| Path | Purpose |
|---|---|
| `app.py`, `config.py` | Factory, local/host guards, CSRF, error handling, CLI |
| `database/` | Parameterized SQLite, schema, seed and reset logic, sample database |
| `authentication/routes.py` | Session identity, salted password verification and logout |
| `security/authorization.py` | Central ownership and role policy |
| `security/invoices.py` | Safe serialization, input validation and updates |
| `security/audit.py` | Fixed, non-secret audit metadata |
| `api/protected.py` | Thin protected HTTP routes |
| `api/vulnerable_lab.py` | Isolated, explicitly labeled educational flaw |
| `web.py`, `templates/`, `static/` | Dashboard and business workflow |
| `simulator/` | Disposable real-HTTP test engine and export CLI |
| `tests/` | 75 automated checks, including an actual HTTP run |
| `report/` | Report, viva, walkthrough and real test evidence |
| `presentation/` | Editable PowerPoint and speaker notes |
| `screenshots/` | Capture provenance and actual-response renders |

Runtime files are generated under `instance/`: a random local signing secret and per-operator saved results. The ZIP excludes the signing secret, virtual environment and session cookies. Do not copy an `instance/secret.key` from someone else. The included SQLite database contains only fictional fixtures.

## Design details and limits

The protected route checks session identity before invoice authorization. The policy checks company equality before operation permissions. Collections use a company-scoped query. Both the HTML form and JSON API call the same update service. Successful updates and their authorization event commit together. Denied requests return without updating the invoice.

Flask-Login provides session management, not object permissions. Flask's session is signed, not encrypted. A random secret is generated for each extracted installation. Cookies are HttpOnly, SameSite=Strict and expire with a 30-minute session lifetime. `Secure=False` is intentional for the loopback HTTP demonstration; a future HTTPS deployment would require different deployment controls. CSRF uses Flask-WTF on POST, PUT, PATCH and DELETE. Tokens and cookies are never logged.

The direct `/lab/` endpoints intentionally bypass ownership and role checks against the current fictional database; use Reset Demo to undo direct lab updates. Dashboard simulations use a **separate temporary database** shared by their own lab and protected routes. Thus the comparison preserves the same identity, target record and payload without changing dashboard invoices. The simulator restores changed fixture rows after capturing evidence and destroys the temporary database at completion.

Audit history is stored in SQLite and is not cryptographically tamper-evident. Administrators see events performed by actors in their own company; employees see their own events. Anonymous events are kept in SQLite with null user/company and are not disclosed through company dashboards. Simulation events are stored inside each saved run result. Audit storage failure prevents the operation from being reported successful, but this mini-project does not implement high-availability log storage.

Not implemented: TLS, MFA, password reset, registration, rate limiting, global session revocation, production WSGI deployment, enterprise alerting, concurrency/load assurance or a network IDS. No RSA, DES, Kerberos, IPSec, SAML or WS-Security implementation is claimed. BOLA prevention in the demonstrated protected paths is the main objective.

## Troubleshooting

- **`py` not recognized:** install Python 3.12 from its official distribution with the Windows launcher, then reopen VS Code.
- **`ModuleNotFoundError`:** select `.venv` in VS Code and install requirements using that interpreter. Use the explicit `.venv\Scripts\python.exe` commands if activation is blocked.
- **Database already initialized:** this is normal for the packaged sample. Use Reset Demo to restore amounts/statuses without removing audit history.
- **Port in use:** stop the earlier server or use `--port 5001`; continue using 127.0.0.1.
- **HTTP 400 CSRF:** refresh the form. API clients must fetch a new token after login and send it with the same session cookie.
- **HTTP 400 untrusted host:** use exactly `http://127.0.0.1:5000` (or the chosen port).
- **Lab returns 404:** restart with `--lab`. A fictional dataset marker is also required.
- **Employees cannot run the lab controls:** sign in as a company administrator. The scenarios themselves use an independent Alice session.
- **Several app instances conflict:** use one dashboard server per project directory. The built-in simulator owns its separate temporary instance safely.

## Technical references

Consulted 14 November 2026. These sources motivate the design; the evidence files record what this implementation actually did.

1. [OWASP API1:2023 Broken Object Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)
2. [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
3. [Flask Security Considerations](https://flask.palletsprojects.com/en/stable/web-security/)
4. [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
5. [Werkzeug security helpers](https://werkzeug.palletsprojects.com/en/stable/utils/#module-werkzeug.security)
6. [Flask-WTF CSRF documentation](https://flask-wtf.readthedocs.io/en/1.2.x/csrf/)
7. [Flask-Login documentation](https://flask-login.readthedocs.io/en/latest/)
