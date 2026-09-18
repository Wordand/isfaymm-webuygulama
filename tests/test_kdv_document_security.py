from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flask import Flask
from werkzeug.datastructures import FileStorage

from routes import kdv_routes
from services.kdv_document_service import (
    document_path,
    document_storage_root,
    init_kdv_document_storage,
    save_document,
)


DOCUMENT_BYTES = b"%PDF-1.4\nsynthetic security test document\n"


class DocumentDatabase:
    def __init__(self):
        self.assigned = True
        self.document = {
            "id": 42, "file_id": 17, "mukellef_id": 9,
            "file_path": "document.pdf", "name": "report.pdf", "type": "Rapor",
        }
        self.commits = 0

    @contextmanager
    def connect(self):
        yield DocumentConnection(self)


class DocumentConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self, **kwargs):
        return DocumentCursor(self.database)

    def commit(self):
        self.database.commits += 1


class DocumentCursor:
    def __init__(self, database):
        self.database = database
        self.rows = []
        self.lastrowid = 42

    def execute(self, query, params=()):
        query = " ".join(query.lower().split())
        self.rows = []
        if "from kdv_user_assignments" in query or "join kdv_user_assignments" in query:
            self.rows = [{"allowed": 1}] if self.database.assigned else []
        elif query.startswith("select f.period"):
            self.rows = [{"period": "2026/01", "unvan": "Synthetic client", "type": "Rapor"}]
        elif "from kdv_documents d" in query:
            if self.database.document and params[0] == self.database.document["id"]:
                self.rows = [dict(self.database.document)]
        elif "insert into kdv_documents" in query:
            self.database.document = {
                "id": 42, "file_id": int(params[0]), "mukellef_id": 9,
                "type": params[1], "name": params[2], "date": params[3],
                "file_path": params[4],
            }
        elif "delete from kdv_documents" in query:
            self.database.document = None
        elif "from kdv_documents" in query:
            self.rows = [dict(self.database.document)] if self.database.document else []
        elif "select f.*" in query:
            self.rows = [{"id": 17, "mukellef_id": 9, "period": "2026/01"}]
        elif "from kdv_files f" in query:
            self.rows = [{"period": "2026/01", "unvan": "Synthetic client"}]
        elif "from kdv_history" not in query and "from kdv_notes" not in query:
            raise AssertionError(f"Unexpected test query: {query}")

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="kdv-document-security-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.public = self.root / "static"
        self.legacy = self.public / "uploads" / "kdv_docs"
        self.legacy.mkdir(parents=True)
        self.app = Flask(
            __name__, root_path=str(self.root), static_folder=str(self.public),
            instance_path=str(self.root / "instance"),
        )
        self.app.config.update(TESTING=True, SECRET_KEY="synthetic-test-key")
        self.private = document_storage_root(self.app)

    def private_document(self, filename="document.pdf"):
        self.private.mkdir(parents=True, exist_ok=True)
        path = self.private / filename
        path.write_bytes(DOCUMENT_BYTES)
        return path


class DocumentStorageTests(StorageTestCase):
    def test_startup_moves_legacy_documents_without_changing_bytes(self):
        source = self.legacy / "document.pdf"
        source.write_bytes(DOCUMENT_BYTES)
        init_kdv_document_storage(self.app)
        self.assertFalse(source.exists())
        self.assertEqual((self.private / source.name).read_bytes(), DOCUMENT_BYTES)
        with self.app.app_context():
            self.assertEqual(document_path("uploads/kdv_docs/document.pdf"), self.private / source.name)

    def test_identical_private_copy_removes_only_legacy_copy(self):
        self.private_document()
        source = self.legacy / "document.pdf"
        source.write_bytes(DOCUMENT_BYTES)
        init_kdv_document_storage(self.app)
        self.assertFalse(source.exists())
        self.assertEqual((self.private / source.name).read_bytes(), DOCUMENT_BYTES)

    def test_conflicting_copy_is_not_overwritten_or_discarded(self):
        destination = self.private_document()
        source = self.legacy / "document.pdf"
        source.write_bytes(b"different synthetic document")
        with self.assertLogs(self.app.logger, level="ERROR"):
            init_kdv_document_storage(self.app)
        self.assertEqual(source.read_bytes(), b"different synthetic document")
        self.assertEqual(destination.read_bytes(), DOCUMENT_BYTES)
        self.assertEqual(self.app.test_client().get("/static/uploads/kdv_docs/document.pdf").status_code, 404)

    def test_failed_migration_preserves_source_and_blocks_public_access(self):
        source = self.legacy / "document.pdf"
        source.write_bytes(DOCUMENT_BYTES)
        with patch("services.kdv_document_service.os.link", side_effect=PermissionError), self.assertLogs(
            self.app.logger, level="ERROR"
        ):
            init_kdv_document_storage(self.app)
        self.assertTrue(source.exists())
        self.assertEqual(list(self.private.iterdir()), [])
        self.assertEqual(self.app.test_client().get("/static/uploads/kdv_docs/document.pdf").status_code, 404)

    def test_public_storage_configuration_is_rejected(self):
        for root in (self.public / "private", self.root):
            with self.subTest(root=root):
                self.app.config["KDV_DOCUMENT_STORAGE_PATH"] = str(root)
                with self.assertRaises(ValueError):
                    init_kdv_document_storage(self.app)

    def test_configured_private_storage_migrates_legacy_documents(self):
        configured = self.root / "private-mount" / "kdv_documents"
        self.app.config["KDV_DOCUMENT_STORAGE_PATH"] = str(configured)
        source = self.legacy / "document.pdf"
        source.write_bytes(DOCUMENT_BYTES)
        init_kdv_document_storage(self.app)
        self.assertFalse(source.exists())
        self.assertEqual((configured / source.name).read_bytes(), DOCUMENT_BYTES)

    def test_invalid_stored_paths_are_rejected(self):
        with self.app.app_context():
            for value in (
                None, "", "..", "../outside.pdf", "/outside.pdf", "C:\\outside.pdf",
                "uploads/kdv_docs/../../outside.pdf", "uploads/kdv_docs/nested/file.pdf",
                "document.pdf:stream", "document\x00.pdf",
            ):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    document_path(value)

    def test_existing_private_document_cannot_be_overwritten(self):
        destination = self.private_document()
        upload = FileStorage(stream=BytesIO(b"replacement"), filename="document.pdf")
        with self.app.app_context(), self.assertRaises(FileExistsError):
            save_document(upload, "document.pdf")
        self.assertEqual(destination.read_bytes(), DOCUMENT_BYTES)

    def test_failed_upload_removes_partial_file_after_closing_it(self):
        class BrokenUpload:
            def save(self, target):
                target.write(b"partial synthetic data")
                raise OSError("Synthetic interrupted upload")

        with self.app.app_context(), self.assertRaises(OSError):
            save_document(BrokenUpload(), "broken.pdf")
        self.assertFalse((self.private / "broken.pdf").exists())

    def test_concurrent_migration_accepts_only_identical_complete_copy(self):
        source = self.legacy / "document.pdf"
        source.write_bytes(DOCUMENT_BYTES)

        def publish_competing_copy(temporary_path, destination):
            destination.write_bytes(DOCUMENT_BYTES)
            raise FileExistsError

        with patch("services.kdv_document_service.os.link", side_effect=publish_competing_copy):
            init_kdv_document_storage(self.app)
        self.assertFalse(source.exists())
        self.assertEqual((self.private / source.name).read_bytes(), DOCUMENT_BYTES)
        self.assertEqual(list(self.private.iterdir()), [self.private / source.name])


class DocumentAccessTests(StorageTestCase):
    def setUp(self):
        super().setUp()
        init_kdv_document_storage(self.app)
        self.app.register_blueprint(kdv_routes.bp)
        self.client = self.app.test_client()
        self.database = DocumentDatabase()
        connection_patch = patch.object(kdv_routes, "get_conn", side_effect=self.database.connect)
        self.connection_mock = connection_patch.start()
        self.addCleanup(connection_patch.stop)
        for patcher in (patch.object(kdv_routes, "kdv_log_action"), patch("services.db.USE_SQLITE", True)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.private_document()

    def log_in(self, role="uzman", access=True, pin=True):
        with self.client.session_transaction() as session:
            session.update(
                logged_in=True, user_id=10, role=role,
                username="admin" if role == "admin" else "synthetic-user",
                has_kdv_access=access, kdv_portal_pin_verified=pin,
            )

    def download(self):
        response = self.client.get("/api/kdv/document/42/download")
        self.addCleanup(response.close)
        return response

    def test_anonymous_download_is_denied(self):
        self.assertEqual(self.download().status_code, 401)
        self.connection_mock.assert_not_called()

    def test_unverified_pin_is_denied(self):
        self.log_in(pin=False)
        self.assertEqual(self.download().status_code, 403)
        self.connection_mock.assert_not_called()

    def test_missing_portal_permission_is_denied(self):
        self.log_in(access=False)
        self.assertEqual(self.download().status_code, 403)
        self.connection_mock.assert_not_called()

    def test_unpermitted_role_is_denied(self):
        self.log_in(role="user")
        self.assertEqual(self.download().status_code, 403)
        self.connection_mock.assert_not_called()

    def test_unassigned_specialist_cannot_download_or_migrate_legacy_document(self):
        self.log_in()
        self.database.assigned = False
        self.database.document["file_path"] = "uploads/kdv_docs/legacy.pdf"
        source = self.legacy / "legacy.pdf"
        source.write_bytes(DOCUMENT_BYTES)
        self.assertEqual(self.download().status_code, 403)
        self.assertTrue(source.exists())
        self.assertFalse((self.private / source.name).exists())

    def test_assigned_specialist_download_is_private_and_noncacheable(self):
        self.log_in()
        response = self.download()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, DOCUMENT_BYTES)
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        self.assertIn("report.pdf", response.headers["Content-Disposition"])
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("ETag", response.headers)

    def test_management_roles_can_download(self):
        self.database.assigned = False
        for role in ("admin", "ymm", "yonetici"):
            with self.subTest(role=role):
                self.log_in(role=role)
                self.assertEqual(self.download().status_code, 200)

    def test_missing_document_record_returns_not_found(self):
        self.log_in()
        self.database.document = None
        self.assertEqual(self.download().status_code, 404)

    def test_missing_document_file_returns_not_found(self):
        self.log_in()
        (self.private / "document.pdf").unlink()
        self.assertEqual(self.download().status_code, 404)

    def test_unsafe_database_path_cannot_read_outside_storage(self):
        self.log_in()
        (self.root / "outside.pdf").write_bytes(DOCUMENT_BYTES)
        self.database.document["file_path"] = "../../outside.pdf"
        self.assertEqual(self.download().status_code, 404)

    def test_legacy_database_path_downloads_through_authorized_endpoint(self):
        self.log_in()
        source = self.legacy / "legacy.pdf"
        source.write_bytes(DOCUMENT_BYTES)
        self.database.document["file_path"] = "uploads/kdv_docs/legacy.pdf"
        response = self.download()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, DOCUMENT_BYTES)
        self.assertFalse(source.exists())

    def test_old_static_urls_are_blocked_even_for_logged_in_users(self):
        source = self.legacy / "legacy.pdf"
        source.write_bytes(DOCUMENT_BYTES)
        for logged_in in (False, True):
            if logged_in:
                self.log_in(role="admin")
            for url in (
                "/static/uploads/kdv_docs/legacy.pdf",
                "/static/uploads/KDV_DOCS/legacy.pdf",
                "/static/uploads/other/../kdv_docs/legacy.pdf",
                "/static/uploads%5Ckdv_docs%5Clegacy.pdf",
            ):
                with self.subTest(logged_in=logged_in, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 404)
                    self.assertNotIn(DOCUMENT_BYTES, response.data)
                    self.assertIn("no-store", response.headers["Cache-Control"])

    def test_public_assets_are_still_available(self):
        (self.public / "example.css").write_bytes(b"body { color: black; }")
        response = self.client.get("/static/example.css")
        self.addCleanup(response.close)
        self.assertEqual(response.status_code, 200)

    def test_upload_saves_only_in_private_storage(self):
        self.log_in(role="admin")
        response = self.client.post("/api/kdv/upload-doc", data={
            "file": (BytesIO(DOCUMENT_BYTES), "uploaded.pdf"),
            "file_id": "17", "doc_type": "Rapor",
        })
        self.assertEqual(response.status_code, 200)
        document = response.get_json()["doc"]
        self.assertNotIn("file_path", document)
        self.assertEqual(document["download_url"], "/api/kdv/document/42/download")
        stored_path = self.database.document["file_path"]
        self.assertEqual((self.private / stored_path).read_bytes(), DOCUMENT_BYTES)
        self.assertEqual(list(self.legacy.iterdir()), [])

    def test_unassigned_specialist_cannot_upload(self):
        self.log_in()
        self.database.assigned = False
        response = self.client.post("/api/kdv/upload-doc", data={
            "file": (BytesIO(DOCUMENT_BYTES), "uploaded.pdf"),
            "file_id": "17", "doc_type": "Rapor",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(list(self.private.iterdir()), [self.private / "document.pdf"])

    def test_failed_database_save_removes_upload_and_does_not_expose_internal_error(self):
        self.log_in(role="admin")
        with patch.object(DocumentConnection, "commit", side_effect=OSError("sensitive private path")), self.assertLogs(
            self.app.logger, level="ERROR"
        ):
            response = self.client.post("/api/kdv/upload-doc", data={
                "file": (BytesIO(DOCUMENT_BYTES), "uploaded.pdf"),
                "file_id": "17", "doc_type": "Rapor",
            })
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("sensitive private path", response.get_data(as_text=True))
        self.assertEqual(list(self.private.iterdir()), [self.private / "document.pdf"])

    def test_document_listing_contains_authorized_download_url_not_storage_path(self):
        self.log_in(role="admin")
        response = self.client.get("/api/kdv/file/17")
        self.assertEqual(response.status_code, 200)
        document = response.get_json()["documents"][0]
        self.assertNotIn("file_path", document)
        self.assertEqual(document["download_url"], "/api/kdv/document/42/download")

    def test_unassigned_specialist_cannot_delete(self):
        self.log_in()
        self.database.assigned = False
        response = self.client.delete("/api/kdv/document/delete/42")
        self.assertEqual(response.status_code, 403)
        self.assertTrue((self.private / "document.pdf").exists())
        self.assertIsNotNone(self.database.document)

    def test_authorized_delete_removes_private_file(self):
        self.log_in()
        response = self.client.delete("/api/kdv/document/delete/42")
        self.assertEqual(response.status_code, 200)
        self.assertFalse((self.private / "document.pdf").exists())
        self.assertIsNone(self.database.document)

    def test_failed_file_deletion_preserves_database_record(self):
        self.log_in()
        with patch.object(Path, "unlink", side_effect=PermissionError), self.assertLogs(self.app.logger, level="ERROR"):
            response = self.client.delete("/api/kdv/document/delete/42")
        self.assertEqual(response.status_code, 500)
        self.assertIsNotNone(self.database.document)
        self.assertTrue((self.private / "document.pdf").exists())

    def test_authorized_delete_also_handles_legacy_database_path(self):
        self.log_in()
        source = self.legacy / "legacy.pdf"
        source.write_bytes(DOCUMENT_BYTES)
        self.database.document["file_path"] = "uploads/kdv_docs/legacy.pdf"
        response = self.client.delete("/api/kdv/document/delete/42")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(source.exists())
        self.assertFalse((self.private / source.name).exists())


if __name__ == "__main__":
    unittest.main()
