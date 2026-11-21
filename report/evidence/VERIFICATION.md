# Recorded verification

All results below were obtained by executing the application on Linux with Python 3.12.14. The original evidence files include execution timestamps. No security result was fabricated.

| Check | Observed result | Evidence |
|---|---|---|
| pytest suite with CSRF enabled | 75 passed; 0 failures, errors or skipped tests | `pytest_output.txt`, `pytest_results.xml` |
| Standalone Requests simulator | 15 of 15 comparisons passed | `security_results.json`, `security_results.csv` |
| Additional live HTTP form/application workflow | Nine checks passed | `live_workflow.json` |
| SQLite integrity | `ok` | Direct `PRAGMA integrity_check` during packaging |
| SQLite foreign keys | No violations | Direct `PRAGMA foreign_key_check` during packaging |
| Installed Python dependencies | No broken requirements | `python -m pip check` during packaging |
| PowerPoint package and layout | Passed automated validation; all 18 slide renders visually reviewed | `presentation_validation.json` |

The simulator compares the same Alice identity, target invoice and operation across vulnerable and protected routes. It also compares the actual SQLite row before and after writes. The JSON includes behavioral assertions and real audit events. A PASS for a vulnerable endpoint means the intended weakness was reproduced.

The separate live HTTP workflow covers login, scoped HTML listing, denied cross-company HTML access, direct lab/protected comparison, a persistent administrator update, web-triggered real simulations, stored monitoring events, reset and logout. It used Requests, not a browser.

## Verification limits

- Windows execution was not available in this Linux environment.
- An actual local browser could not launch. A separate browser could not reach the application's loopback interface. The environment's approval policy rejected elevated browser execution because sandbox escalation was disabled.
- Consequently, native browser screenshots, browser interaction, JavaScript behavior and responsive layout remain unverified. The supplied images are explicitly labeled HTML response renders.
- PowerPoint was exported and validated without opening Microsoft PowerPoint on Windows. Its font may be substituted if DejaVu Sans is absent; the PDF preview preserves the reviewed appearance.
- Load, concurrency, production hosting and comprehensive penetration testing were not performed.

Use `screenshots/README.md` for the remaining Windows browser checks. Use README commands to rerun the actual tests and simulator locally.
