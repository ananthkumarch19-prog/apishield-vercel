# Start APIShield

1. Open this folder in VS Code. The folder must contain `app.py`.
2. Follow the exact PowerShell commands in `README.md`, under Windows quick start.
3. Start with `python app.py serve --lab` and open `http://127.0.0.1:5000`.
4. Sign in with `alice@alpha.test` or `admin@alpha.test`; password: `Demo@2026!`.
5. Use the README's five-minute demonstration, then read the code walkthrough and viva guide.

## What is included

| File or folder | Purpose |
|---|---|
| `README.md` | Setup, accounts, demonstration, tests, reset and limitations |
| `app.py` and Python modules | Complete local Flask application |
| `database/apishield.sqlite` | Two fictional companies, four users, eight original invoices, real demonstration audit history |
| `tests/` | 75 automated tests; CSRF stays enabled |
| `simulator/` | Actual HTTP comparisons on a disposable local database |
| `report/APIShield_Project_Report.pdf` | Project report, architecture, results and syllabus connection |
| `report/APIShield_Project_Report.md` | Editable report text |
| `report/Test_Results.pdf` | Expected and observed security results |
| `report/CODE_WALKTHROUGH.md` | Module guide and central policy explained line by line |
| `report/Viva_Preparation.pdf` | Introduction, demonstration and 35 viva questions with answers |
| `presentation/APIShield_Presentation.pptx` | 18 editable slides with speaker notes |
| `presentation/APIShield_Presentation_Preview.pdf` | Visual preview of the slides |
| `report/evidence/` | Actual HTTP results, pytest output/XML and live workflow records |
| `screenshots/` | Clearly labeled static renders of server HTML and a Windows browser checklist |
| `MANIFEST.sha256` | File hashes for checking the extracted package |

## Verified scope

The Linux/Python 3.12.14 run passed 75 pytest tests, 15 HTTP comparisons and nine additional live HTTP workflow checks. Database integrity and foreign keys were checked. The application has no external runtime services or assets.

Windows and actual browser interaction/layout remain unverified. The images supplied are static renders of actual server responses, not browser screenshots. Take real browser screenshots on your Windows laptop using the included checklist before submission.

The vulnerable routes work only when lab mode is explicitly enabled. Use fictional data and the supplied launcher, which binds only to `127.0.0.1`. The project is an educational demonstration of invoice authorization, not a production deployment.
