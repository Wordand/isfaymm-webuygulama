# Private KDV document storage

This change applies to attachments in the KDV refund/tracking panel, not the
financial declaration upload pipeline.

## Storage and authorization

- Default local storage: `instance/kdv_documents`.
- Set `KDV_DOCUMENT_STORAGE_PATH` to use a different private directory.
- The storage directory cannot be inside, or contain, the public static directory.
- Downloads use `/api/kdv/document/<document_id>/download` and require a signed-in
  session, KDV portal permission, a verified portal PIN, and an allowed role.
- Specialists must be assigned to the document's taxpayer.
- Responses disable caching. File paths are not included in document API responses.
- Old `/static/uploads/kdv_docs/...` URLs are blocked, including for administrators.

## Existing documents

On startup, available files in `static/uploads/kdv_docs` are copied into private
storage. A complete copy is published before the original is removed. Different
files with the same name are never overwritten; migration failures are logged
and public access remains blocked.

Existing database keys such as `uploads/kdv_docs/<stored_filename>` remain valid.
No database rewrite is necessary. If restoring backups directly into private
storage, preserve the stored UUID filenames, not just the original display names.
Already missing documents cannot be recovered by this migration.

## Render deployment

1. Back up the current attachments and database BEFORE changing disk settings or
   deploying. Attaching a Render disk triggers a deployment.
2. Use private persistent storage, for example a disk mounted at `/var/data`.
3. Set `KDV_DOCUMENT_STORAGE_PATH=/var/data/kdv_documents`.
4. Restore the backed-up attachments into that directory using their stored
   filenames. Ensure the service user can read and write there.
5. Deploy the new code. Do not configure public static hosting for this directory.
6. Confirm authorized downloads work and direct legacy static URLs return 404.

Render's default filesystem is ephemeral: files outside a persistent disk's mount
path do not survive deployments/restarts. Persistent disks require a paid service.
See [Render's persistent disk documentation](https://render.com/docs/disks).

If a CDN previously cached document URLs, purge those cached responses separately.
Previously downloaded copies cannot be recalled by this change.

## Isolated regression tests

With the application dependencies installed:

```console
python -m unittest discover -s tests -p test_kdv_document_security.py -v
```

These tests use temporary synthetic files and a fake database. They do not import
`app.py`, run application startup migrations, or access customer document data.
