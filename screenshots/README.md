# Evidence capture provenance

Actual automated browser screenshots were unavailable in the execution environment. A local Chromium process could not start, the browser tool could not reach the application's loopback server, and the approval policy rejected elevated browser execution. No screenshots or browser success claims were fabricated.

`rendered_http_pages/` contains static renders of HTML responses actually returned by the running application. They are produced by an HTML-to-PDF renderer with CSS, then rasterized. They are **not browser screenshots** and do not verify browser JavaScript, responsive behavior, browser cookie enforcement or final browser layout. CSRF fields are removed before saving HTML. Captions in the report and presentation retain this distinction.

The authoritative execution evidence is in `report/evidence/security_results.json`, `security_results.csv`, `pytest_results.xml`, `pytest_output.txt` and `live_workflow.json`.

## Capture real screenshots on Windows

1. Start `python app.py serve --lab` and open `http://127.0.0.1:5000`.
2. Sign in as Alice. Capture Login, Overview, Company invoices and INV-1001.
3. Open `/api/invoices/2001` and `/lab/invoices/2001` in the same session. Capture the actual JSON responses.
4. Sign in as Alpha Admin. Update INV-1001 and capture the resulting saved amount.
5. Run All Security Tests. Capture the results and expand C-P to show unchanged before/after records.
6. Open Security monitoring and capture actual events. Do not expose session cookies or tokens in developer tools.
7. Use Win+Shift+S, then save each image into this folder with a descriptive filename. Record the date and browser used.

## Browser validation checklist still to perform on Windows

- Login/logout works through visible forms; browser Back does not restore an active session after logout.
- Alice sees four Alpha invoices and cannot open Beta invoice details or edit an invoice.
- Alpha Admin's saved amount persists after refresh.
- Test buttons display the real run and return from the progress state.
- Reset restores the eight invoice fixtures and retains the audit trail.
- The layout remains usable at desktop and narrow/mobile widths.
- No browser console errors or blocked first-party resources occur.

Server behavior for these workflows has automated coverage. The checklist is specifically for the remaining browser/platform verification.
