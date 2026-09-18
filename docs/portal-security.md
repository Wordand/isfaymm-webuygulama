# Admin and KDV portal request security

## Scope

- KDV quick notes are rendered using text nodes and DOM event listeners, not
  interpolated HTML or inline JavaScript. Existing note text is not rewritten.
- Dynamic history text and document names on the KDV detail page are escaped.
- Note add/update/delete and history deletion resolve the actual taxpayer from
  the target database record. Specialists require a matching assignment.
  Existing admin, ymm and yonetici access is retained; other roles are denied.
- Admin approve, delete and suspend endpoints accept POST only.
- Flask-WTF validates CSRF for every POST/PUT/PATCH/DELETE in the admin and KDV
  blueprints, including PIN forms, uploads, assignments and password changes.
  Read-only requests do not change records.
- This rollout does not enable CSRF globally for unrelated routes or the mobile
  API. It is not a claim that every application endpoint has been audited.
- Portal responses use Cache-Control: no-store to avoid caching personal data
  or session-bound form tokens.

## Deployment

1. Deploy requirements.txt together with the application changes. Flask-WTF is
   a new dependency; there is no database migration for this change.
2. Keep the application's existing SECRET_KEY configured and stable.
3. Refresh any admin/KDV pages already open after deployment. Old pages lack the
   required token fields or request headers and their changes will be rejected.
4. The default signed CSRF token expires after one hour. Refreshing the page
   creates a fresh token; validation errors instruct the user to refresh.
5. Custom integrations that call the cookie-authenticated KDV portal must send
   X-CSRFToken using the token from their own session's portal page. Do not
   exempt mutation endpoints to make an integration work.

See the separate kdv-document-storage.md instructions for the attachment
storage changes from the first security fix. Those deployment requirements
still apply.

## Isolated regression tests

These tests do not import app.py or run its startup migrations. Server tests
use generated records in a temporary SQLite file, patch the route connections,
and prohibit fallback to real database connections. Document security tests
use synthetic files. Frontend tests use an isolated headless browser with
intercepted synthetic pages and mocked API requests.

```powershell
python -m unittest discover -s tests -p test_portal_mutation_security.py -v
python -m unittest discover -s tests -p test_kdv_document_security.py -v
node --test tests/test_kdv_frontend_security.cjs
```

The JavaScript tests require Playwright on Node's module search path and an
installed browser. To use a local Chrome installation, set
PLAYWRIGHT_BROWSER_CHANNEL=chrome. They do not connect to the running site.

Reference: https://flask-wtf.readthedocs.io/en/1.2.x/csrf/
