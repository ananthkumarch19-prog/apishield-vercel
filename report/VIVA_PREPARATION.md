# APIShield viva preparation

## A one minute introduction

APIShield is a Python and Flask invoice application for two fictional companies. Its main problem is Broken Object Level Authorization: a logged-in user may change an invoice ID and read another company's invoice when the server checks login but not ownership. We built a centralized policy that checks both the invoice's company and the user's role. Employees can read their company's invoices, and company administrators can also update them. A separate local lab intentionally omits those checks. The simulator sends actual HTTP requests to both versions and checks the database before and after updates. In the recorded Linux run, all 75 pytest tests and 15 HTTP scenario checks passed. Windows and real browser verification remain to be performed.

## Questions and answers

**1. What is the exact problem you solve?**
We prevent an authenticated user from reading or changing another company's invoice through the protected application's implemented routes. Knowing an invoice ID must not grant permission to use it.

**2. Why is this a strong business problem?**
Invoices contain customer identities, payable amounts and payment status. Reading another company's invoice violates confidentiality. Changing its amount or status violates integrity. A legitimate account can trigger the flaw without guessing another person's password.

**3. What is an API?**
An API is a defined interface through which software requests a service or data. Here, GET reads an invoice and PATCH changes selected invoice fields.

**4. Authentication versus authorization?**
Authentication checks who the requester is. Authorization checks whether that identity may perform this action on this specific object. Alice's valid password proves that she is Alice, not that she owns Beta's invoice.

**5. What does BOLA mean?**
Broken Object Level Authorization. The server fails to check the requester's permission on the particular object identified in a request. Our lab reproduces it by changing the invoice ID to 2001 in an Alice request.

**6. Is hiding the invoice ID enough?**
No. An identifier may be observed, guessed or shared. Unpredictable IDs can make enumeration harder, but every request still needs an authorization check. The demonstration intentionally uses readable integer IDs.

**7. What is multi-tenancy?**
Several companies share an application and database while each sees only its own permitted records. `company_id` expresses the ownership relationship in this project.

**8. Why must authorization happen on the server?**
A requester can bypass a webpage and send HTTP requests directly, change parameters or alter browser code. A server policy controls the actual data access. Hiding a Manage button is only a usability feature.

**9. Where is the policy implemented?**
In `security/authorization.py`. The `policy` function checks authentication, company equality and allowed action for the role. `authorize_invoice` fetches the object, applies that function, logs the result and stops denied requests.

**10. Why check company before administrator role?**
An administrator administers one company. Checking ownership first prevents the admin role from becoming global access. Alpha Admin still receives 403 for Beta's invoice.

**11. What does deny by default mean?**
Access is allowed only when an explicit policy rule permits it. Unknown roles and unsupported operations receive no allowed action. Missing authentication and mismatched companies also deny access.

**12. What if the browser sends company_id=2 or role=admin?**
The server uses the authenticated user ID and reloads company/role from SQLite. Browser claims are ignored for authorization. An attempted ownership field in an otherwise authorized PATCH is rejected by the update allowlist.

**13. Does Flask-Login implement your authorization?**
No. It manages user sessions and identifies the logged-in user. Our policy separately checks the object owner and operation permission.

**14. How are passwords protected?**
Werkzeug stores salted scrypt hashes with N=32768, r=8 and p=3. Login uses `check_password_hash`. Plaintext passwords are not stored in the users table.

**15. Why not use ordinary SHA-256?**
Basic SHA-256 is deliberately fast. That lets attackers try many password guesses cheaply if hashes are stolen. A salted password KDF such as scrypt intentionally uses time and memory, increasing guessing cost. It does not make weak passwords impossible to guess.

**16. What does a salt do?**
A unique random salt makes identical passwords produce different stored hashes and reduces the usefulness of precomputed tables. A salt is not a secret encryption key.

**17. Are the session cookies encrypted?**
No. Flask's default cookie session is signed to detect tampering. Sensitive secrets should not be stored in it. The project reloads permission attributes from the server database.

**18. What is CSRF, and why protect PATCH?**
A browser automatically sends cookies with eligible requests. An attacker may try to induce a state-changing request using the victim's session. Flask-WTF checks a token tied to the legitimate session. PATCH modifies data, so it needs the same protection as POST. SameSite is an additional control, not a replacement for the CSRF token.

**19. How do tests use CSRF correctly?**
They fetch a token, submit login with it, then fetch a fresh token after login clears session state. PATCH requests send that token in `X-CSRFToken`. Missing, forged and other-session token tests verify rejection. CSRF stays enabled.

**20. Why use 401, 403, 404 and 400?**
401 means no valid authenticated session. 403 means the identity lacks permission. 404 means the requested object is missing. 400 means invalid payload or failed CSRF validation here. Production systems may deliberately return 404 for inaccessible objects to reduce existence disclosure.

**21. How do you prove a blocked modification did not occur?**
The simulator reads the full invoice row before the request and after it, then compares all fields. C-P returns 403 and the rows match. It also tests an allowed administrator update and observes a real changed amount.

**22. Are the vulnerable and protected comparisons fair?**
Yes. B uses the same authenticated Alice client and invoice 2001. C uses the same Alice client, invoice and amount payload. The initial row is identical because the protected request changes nothing. Only the path changes between protected and vulnerable implementations.

**23. What happens in the vulnerable endpoint?**
It checks that the requester is logged in but skips the invoice company policy. The lab PATCH additionally omits the role check. CSRF and input validation remain enabled so the demonstrated defect is authorization.

**24. How is the lab contained?**
The launcher binds to 127.0.0.1, checks the real peer and trusted Host, and does not enable debug mode. Vulnerable routes are registered only with explicit lab mode and require the fictional dataset marker. The simulator accepts no arbitrary URL and uses a disposable local database.

**25. Do lab buttons change dashboard invoices?**
No. They use a temporary app and database shared by the comparison routes. Direct requests to the dashboard server's `/lab/` endpoints can modify its fictional invoices, which Reset Demo restores. This distinction is documented.

**26. How are SQL injection and mass assignment addressed?**
All submitted SQL values use placeholders. Update column names come from a fixed server allowlist. The application permits only customer name, amount and status changes, and rejects ownership or role fields.

**27. Why store money as integer paise?**
Binary floating-point can introduce rounding errors for decimal currency. The application validates INR with Decimal, stores whole paise and returns amounts as fixed two-decimal strings.

**28. What is recorded in an audit event?**
Actor ID, actor company, resource type/ID, action, decision, reason and UTC timestamp. Passwords, cookies, tokens and full request bodies are not logged. Successful protected updates and their audit event commit in one transaction.

**29. Is every DENY event an attack?**
No. It could be a mistake, an expired session, a test or a malicious attempt. The interface reports decisions and reasons without labeling every rejection as a confirmed attack.

**30. Is this an intrusion detection system?**
It demonstrates application-layer unauthorized-access prevention and audit monitoring. It does not inspect network packets, classify attackers or provide a general network IDS.

**31. What did testing establish?**
The recorded environment passed 75 pytest tests and 15 HTTP comparisons. The checks cover both companies, both roles, unauthenticated requests, forged claims, bad payloads, CSRF, host/loopback restrictions, lab gating, HTML workflows and stored events. Nine additional live HTTP workflow checks passed. These results do not prove absence of every possible bug.

**32. What remains unverified?**
Windows execution and an actual browser workflow/layout have not been verified here. Static HTML response renders are provided instead of claiming browser screenshots. Load testing, multi-process concurrency and production deployment are outside the validated scope.

**33. Which CNS modules are connected?**
Module 1 covers attacks and defense principles such as least privilege. Module 2 connects to salted password KDFs. Module 3 connects to authentication, identity and authorization. Module 4 connects to API/web service security and application access prevention/monitoring.

**34. Does it implement RSA, DES or Kerberos?**
No. Do not claim those mechanisms. This implementation uses scrypt password protection, signed application sessions, CSRF tokens and server-side authorization.

**35. What would you improve for production?**
Remove the vulnerable blueprint and public demo accounts, deploy behind HTTPS with secure cookies, add stronger identity lifecycle controls, rate limiting, central session revocation, hardened secret management, reliable tamper-evident audit storage and operational testing. Each is future work, not an implemented result.

## Demonstration recovery

If an amount was changed during a direct lab demonstration, use Reset Demo. If lab routes return 404, check that the launcher used `--lab`. If a PATCH returns 400 instead of the expected authorization result, fetch a fresh CSRF token with the same session. If port 5000 is busy, use `--port 5001`. If the examiner asks whether a PASS on C-L means security, explain that it means the intended vulnerable behavior was observed.
