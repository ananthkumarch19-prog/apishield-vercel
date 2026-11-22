# Verification of the Vercel preparation

Recorded on 21 November 2026 on Linux with Python 3.12.14.

- 101 pytest tests passed, with no failures, errors or skips.
- The original 75 tests exercised local SQLite behavior, including the actual HTTP simulator.
- 26 additional checks exercised the public profile and actual temporary PostgreSQL 16.2 databases.
- The PostgreSQL checks covered both companies and roles, denied reads and writes, actual permitted writes, missing CSRF, forged claims, missing resources, secure cookies, exact hosts, disabled lab controls, persistence across application instances, shared signed sessions, concurrent initialization and rollback when audit insertion fails.
- Installed dependencies passed pip check.
- The Vercel configuration was parsed and checked for the Flask entrypoint and function settings.

The PostgreSQL server used loopback TCP in the test environment. The Neon cloud service was not connected. Vercel build execution, live TLS/routing/proxy behavior, the CDN, live database connectivity and the browser workflow have not been verified. The package has not been published and has no verified live URL. Vercel account connection, Neon Free provisioning, the signing secret and a deployment are required to complete those checks.

The hosted app uses PostgreSQL. The original local mini-project continues using SQLite. Runtime secrets and credentials are absent from the ZIP.
