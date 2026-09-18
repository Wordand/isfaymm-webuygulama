import hashlib
import os
from pathlib import Path
import posixpath
import tempfile

from flask import abort, current_app, g, request


LEGACY_DOCUMENT_PREFIX = "uploads/kdv_docs/"


def document_storage_root(app=None):
    app = app or current_app
    configured = app.config.get("KDV_DOCUMENT_STORAGE_PATH")
    root = Path(configured or Path(app.instance_path) / "kdv_documents").resolve()
    public_root = Path(app.static_folder).resolve()
    if root.is_relative_to(public_root) or public_root.is_relative_to(root):
        raise ValueError("KDV document storage must be separate from the static directory.")
    return root


def _document_filename(stored_path):
    if not isinstance(stored_path, str):
        raise ValueError("Invalid document path.")
    filename = stored_path.replace("\\", "/")
    if filename.startswith(LEGACY_DOCUMENT_PREFIX):
        filename = filename[len(LEGACY_DOCUMENT_PREFIX):]
    if (
        not filename or filename in {".", ".."}
        or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for char in filename)
    ):
        raise ValueError("Invalid document path.")
    return filename


def _contained_path(root, filename):
    path = root / filename
    if path.is_symlink() or path.resolve().parent != root:
        raise ValueError("Document path escapes its storage directory.")
    return path


def _legacy_storage_root(app):
    public_root = Path(app.static_folder).resolve()
    root = public_root / "uploads" / "kdv_docs"
    if root.resolve() != root:
        raise ValueError("Legacy document storage must not contain directory symlinks.")
    return root


def _file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def _migrate_document(filename, app):
    private_root = document_storage_root(app)
    private_path = _contained_path(private_root, filename)
    legacy_root = _legacy_storage_root(app)
    legacy_path = _contained_path(legacy_root, filename)
    if not legacy_path.is_file():
        return private_path

    private_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary_path = None
    try:
        digest = hashlib.sha256()
        with legacy_path.open("rb") as source, tempfile.NamedTemporaryFile(
            dir=private_root, prefix=".migrate-", delete=False
        ) as target:
            temporary_path = Path(target.name)
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                target.write(chunk)
                digest.update(chunk)
            target.flush()
            os.fsync(target.fileno())

        # Publish a complete copy without overwriting files or racing other workers.
        try:
            os.link(temporary_path, private_path)
        except FileExistsError:
            if _file_digest(private_path) != digest.digest():
                raise ValueError("Conflicting private document; legacy file was not removed.")
        legacy_path.unlink(missing_ok=True)
    except FileNotFoundError:
        if not private_path.is_file():
            raise
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return private_path


def document_path(stored_path):
    return _migrate_document(_document_filename(stored_path), current_app)


def save_document(upload, filename):
    root = document_storage_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = _contained_path(root, _document_filename(filename))
    created = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        descriptor = os.open(path, flags, 0o600)
        with os.fdopen(descriptor, "wb") as target:
            created = True
            upload.save(target)
    except Exception:
        if created:
            path.unlink(missing_ok=True)
        raise
    return path


def init_kdv_document_storage(app):
    private_root = document_storage_root(app)
    legacy_root = (Path(app.static_folder) / "uploads" / "kdv_docs").resolve()

    @app.before_request
    def block_public_kdv_documents():
        if request.endpoint != "static":
            return None
        filename = (request.view_args or {}).get("filename", "").replace("\\", "/")
        normalized = posixpath.normpath(filename).lstrip("/").casefold()
        try:
            candidate = (Path(app.static_folder) / filename).resolve()
        except (OSError, ValueError):
            g.private_kdv_document = True
            abort(404)
        if (
            normalized == LEGACY_DOCUMENT_PREFIX.rstrip("/")
            or normalized.startswith(LEGACY_DOCUMENT_PREFIX)
            or candidate.is_relative_to(legacy_root)
            or candidate.is_relative_to(private_root)
        ):
            g.private_kdv_document = True
            abort(404)
        return None

    @app.after_request
    def prevent_document_caching(response):
        if getattr(g, "private_kdv_document", False) or request.endpoint in {
            "kdv.download_document", "kdv.upload_document", "kdv.delete_document", "kdv.get_file"
        }:
            response.headers["Cache-Control"] = "private, no-store"
            response.headers["Pragma"] = "no-cache"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    if legacy_root.is_dir():
        with app.app_context():
            try:
                paths = list(_legacy_storage_root(app).iterdir())
            except (OSError, ValueError):
                app.logger.exception("Legacy KDV document storage could not be migrated.")
                return
            for path in paths:
                if path.is_dir():
                    continue
                try:
                    _migrate_document(_document_filename(path.name), app)
                except (OSError, ValueError):
                    # Public access stays blocked even if a file cannot be migrated.
                    app.logger.exception("A legacy KDV document could not be migrated.")
