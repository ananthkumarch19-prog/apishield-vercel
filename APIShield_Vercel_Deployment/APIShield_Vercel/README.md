# APIShield on Vercel — free project demonstration

Deploy this folder on Vercel's **Hobby** plan and connect a **Neon Free** PostgreSQL database. Both services have free usage limits. Keep both resources on their free plans for this personal educational project. No paid plan, domain purchase or Pro trial is required for this setup.

## Why this deployment package is different

Vercel supports Flask as a Python Function. Its application filesystem is read-only and temporary files do not provide shared persistent data across function instances. This hosted version uses PostgreSQL for invoices, users and authorization events. The original local project uses SQLite. Both versions use the same company and role policy.

The public entry point forces vulnerable routes and lab controls off. To demonstrate the vulnerable API, run the original local project on your laptop. The public website provides the protected application.

## Route A — Vercel dashboard and GitHub

1. Create or sign in to a free GitHub account and a personal Vercel **Hobby** account.
2. Extract `APIShield_Vercel_Deployment.zip` on your laptop. Open the `APIShield_Vercel` folder.
3. Create a personal GitHub repository, for example `apishield-vercel`. Upload this folder's **contents**, including its subfolders. The repository root should contain `app.py`, `application.py`, `requirements.txt` and `vercel.json`. The ZIP has no secrets or database credentials.
4. In Vercel choose **Add New > Project**, connect/import that repository, and select the personal Hobby scope. Set the framework to **Flask** if detection does not select it. Leave Build Command and Output Directory at their framework defaults. If you uploaded the outer folder itself, set Root Directory to `APIShield_Vercel`.
5. Click **Deploy**. The initial deployment can show HTTP 503 with `deployment_configuration_required` until the database and secret are configured. This is an intentional closed setup state.
6. In this Vercel project open **Storage > Create Database**, select **Neon** from the Marketplace, and choose its **Free** plan. Use a database region near your Vercel function if offered. Connect it to this project for the environments you intend to deploy, including **Production**. Keep the default environment-variable prefix so it provides `DATABASE_URL`.
7. In project **Settings > Environment Variables**, add `APISHIELD_SECRET_KEY` with a randomly generated value of at least 32 characters. Use the same value for all deployments of this demo so sessions remain stable. Generate a 64-character value on your laptop with one of these commands. Copy it directly into Vercel's secret environment setting.

```powershell
py -3 -c "import secrets; print(secrets.token_hex(32))"
```

If you use Node instead of local Python for this step

```powershell
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

8. In environment-variable settings, enable **System Environment Variables** if the option is off. The app reads Vercel's exact deployment, branch and production hostnames. If necessary, add `APISHIELD_ALLOWED_HOSTS` with your exact production domain, such as `apishield-example.vercel.app`. Use just the host, without `https://` or a slash.
9. Open **Deployments**, select the latest deployment's menu, then **Redeploy**. Environment-variable changes apply to the new deployment.
10. Open its production HTTPS address. The first database request creates the schema and seeds the fictional records. Later requests and redeployments retain edits and logs.

Do not paste the database URL or secret into GitHub files, source code, screenshots or chat. The environment settings pass them to the Python server.

If Vercel asks you to upgrade for the chosen configuration, stop and check that the project uses a personal Hobby scope and a free Neon resource. This package has no paid infrastructure requirement.

## Route B — deploy from Windows without GitHub

You can upload the same source using the Vercel CLI. Install Node.js LTS if `node --version` is unavailable. Open this extracted folder in VS Code, then use PowerShell.

```powershell
node --version
npx vercel@latest login
npx vercel@latest
```

Choose your personal Hobby scope, create the project, and use `.` as the code directory. Accept Flask detection. Then complete steps 6–8 above in the Vercel dashboard. After connecting Neon and setting the secret, deploy production from the same folder.

```powershell
npx vercel@latest --prod
```

The CLI prints the actual deployment address. Share the production alias after completing the checks below.

## Demo accounts

These are public teaching identities. All four use `Demo@2026!`.

| Identity | Email | Permissions |
|---|---|---|
| Alice | `alice@alpha.test` | Read Alpha invoices |
| Alpha Admin | `admin@alpha.test` | Read/update Alpha invoices |
| Bob | `bob@beta.test` | Read Beta invoices |
| Beta Admin | `admin@beta.test` | Read/update Beta invoices |

Any visitor can sign in as these fictional identities. Keep the invoices and customer names fictional. This is a small educational demonstration.

## Verify the live deployment

1. Open `/health` on the HTTPS production address. Expect HTTP 200, `initialized: true` and `lab_mode: false`.
2. Log in as Alice. Open `/api/invoices/1001` and expect HTTP 200. Open `/api/invoices/2001` with the same session and expect HTTP 403 with no invoice data.
3. Open `/lab/invoices/2001` and expect 404.
4. Log in as Alpha Admin. Edit INV-1001, save, then reopen it and confirm the saved amount/status.
5. Open `/security-monitoring`. Confirm that real stored allow/deny events appear and that the page identifies PostgreSQL storage.
6. Redeploy the Vercel project. Reopen the invoice and verify that the saved edit and events still exist.
7. Open the HTTPS address from another device and check login and invoice navigation.

These checks require the actual hosting account and connected database. A successful local test run alone does not verify Vercel's live routing, certificate, proxy headers, database credentials, or browser behavior.

## Configuration

| Setting | Source | Purpose |
|---|---|---|
| `DATABASE_URL` | Neon/Vercel integration | Pooled PostgreSQL connection string |
| `APISHIELD_SECRET_KEY` | Owner-generated Vercel secret setting | Stable signed session/CSRF secret |
| `VERCEL_URL` | Vercel system variable | Exact generated deployment host |
| `VERCEL_BRANCH_URL` | Vercel system variable | Exact branch host, when present |
| `VERCEL_PROJECT_PRODUCTION_URL` | Vercel system variable | Exact production domain |
| `APISHIELD_ALLOWED_HOSTS` | Optional comma-separated host list | Explicit aliases/custom domains |

The public factory uses HTTPS and Secure/HttpOnly/SameSite cookies, recognizes Vercel's forwarded protocol, and validates exact Host values. It keeps company and role checks on the server. The hosted profile cannot register the vulnerable blueprint even if `APISHIELD_LAB_MODE=1` is accidentally configured.

PostgreSQL connections open for a request and close during Flask teardown. Parameters remain separate from SQL text. Neon connections verify the server certificate using the bundled CA certificates. The first cold start serializes schema/seed initialization with a transaction advisory lock. Concurrent starts cannot duplicate the fixtures, and an existing marked demo is retained. Updates and successful authorization events commit in one transaction.

Assets live under `public/static/` for Vercel's CDN. `app.py` exports the Flask instance. `application.py` retains the application factory and local CLI. `database/postgres.py` adapts the existing parameterized queries to PostgreSQL. No session signing key or durable application data is written to the function filesystem.

## Tests and their limits

Install test dependencies in a local virtual environment.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

The recorded run passed **101 tests**, comprising the original 75 regression tests and 26 Vercel/PostgreSQL checks. The original SQLite regression tests remain included. Additional integration tests start an actual temporary PostgreSQL server, covering company/role matrices, persistent changes, signed sessions across app instances, CSRF, audit rollback, exact hosts, disabled lab routes and concurrent initialization. The PostgreSQL test fixture uses the binaries supplied by `pgserver`, listed only in development requirements. The recorded execution uses Linux/Python 3.12 with PostgreSQL 16.2. Windows execution of this test fixture has not been verified.

See `deployment/pytest_output.txt` and `deployment/pytest_results.xml` for observed results. Live Vercel/Neon and browser checks remain pending until the owner connects the hosting account and publishes the project. General production identity lifecycle, rate limiting, tamper-evident audit storage and load testing remain future work.

## Troubleshooting

- **HTTP 503 with deployment_configuration_required** — connect Neon, add the signing secret, enable system variables or set an exact allowed host, and redeploy.
- **HTTP 503 with database_unavailable** — check Runtime Logs and the Neon connection in Storage. Verify that `DATABASE_URL` is present in Production, then redeploy. Driver details are kept out of the response to avoid exposing connection information.
- **HTTP 400 untrusted_host** — add the exact address you opened to `APISHIELD_ALLOWED_HOSTS`, or enable Vercel's system environment variables, and redeploy.
- **HTTP 400 CSRF validation** — refresh the page and sign in through the HTTPS domain using the same browser session.
- **CSS missing** — verify that `public/static/style.css` and `public/static/app.js` reached the repository and that the correct Root Directory is selected.
- **Wrong framework or build error** — select Flask and Python 3.12. Leave framework build/output defaults in place.
- **Changes disappear** — confirm the deployment uses the intended Neon database/branch. Each preview branch may have its own database. Persistence should be checked on the same production project and database.
- **Only visitors signed into Vercel can open it** — inspect Deployment Protection for the Production environment and configure the audience for your intended public demonstration.

## Official references

Checked 21 November 2026.

- https://vercel.com/docs/frameworks/backend/flask
- https://vercel.com/docs/functions/runtimes/python
- https://vercel.com/docs/plans/hobby
- https://vercel.com/docs/marketplace-storage
- https://vercel.com/docs/environment-variables/system-environment-variables
- https://vercel.com/docs/headers/request-headers
- https://neon.com/docs/guides/vercel-managed-integration
- https://neon.com/pricing
