from contextlib import closing, contextmanager
from html.parser import HTMLParser
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from flask import Blueprint, Flask, jsonify, render_template
from flask_wtf.csrf import generate_csrf
from jinja2 import ChoiceLoader, DictLoader

import auth
from routes import admin_routes, kdv_routes
from services import db
from services.request_security import init_request_security


ROOT = Path(__file__).resolve().parents[1]
NOTE_TEXT = 'Synthetic note: "quotes", `backticks`, ${literal}\nsecond line'


class ObservedConnection(db.FakeConnection):
    def __init__(self, database):
        super().__init__(str(database.path))
        self.database = database
        self.conn.set_trace_callback(database.queries.append)

    def commit(self):
        self.database.commits += 1
        super().commit()


class SyntheticDatabase:
    def __init__(self, path):
        self.path = path
        self.queries = []
        self.commits = 0
        with closing(sqlite3.connect(str(path))) as conn:
            conn.executescript("""
                CREATE TABLE kdv_files (id INTEGER PRIMARY KEY, mukellef_id INTEGER);
                CREATE TABLE kdv_notes (
                    id INTEGER PRIMARY KEY, file_id INTEGER, note_text TEXT,
                    created_at TEXT, updated_at TEXT
                );
                CREATE TABLE kdv_history (id INTEGER PRIMARY KEY, file_id INTEGER);
                CREATE TABLE kdv_user_assignments (user_id INTEGER, mukellef_id INTEGER);
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY, username TEXT, is_approved INTEGER DEFAULT 0,
                    is_suspended INTEGER DEFAULT 0, role TEXT, has_kdv_access INTEGER DEFAULT 0,
                    created_at TEXT, last_login TEXT, admin_notes TEXT, password TEXT
                );
                INSERT INTO kdv_files VALUES (17, 9), (18, 99);
                INSERT INTO kdv_notes (id, file_id, note_text) VALUES
                    (41, 17, 'Owned note'), (42, 18, 'Other client note');
                INSERT INTO kdv_history VALUES (71, 17), (72, 18);
                INSERT INTO kdv_user_assignments VALUES (10, 9);
                INSERT INTO users (id, username, role, is_approved) VALUES
                    (1, 'admin', 'admin', 1), (2, 'synthetic-user', 'user', 0);
            """)

    @contextmanager
    def connect(self):
        connection = ObservedConnection(self)
        try:
            yield connection
        finally:
            connection.close()

    def scalar(self, sql, params=()):
        with closing(sqlite3.connect(str(self.path))) as conn:
            row = conn.execute(sql, params).fetchone()
            return row[0] if row else None


class FormParser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms = []
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.current = {"method": attrs.get("method", "GET").upper(),
                            "action": attrs.get("action", ""), "token": None}
            self.forms.append(self.current)
        if tag == "input" and self.current and attrs.get("name") == "csrf_token":
            self.current["token"] = attrs.get("value")

    def handle_endtag(self, tag):
        if tag == "form":
            self.current = None


class PortalSecurityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="synthetic-portal-security-")
        self.addCleanup(temporary.cleanup)
        self.database = SyntheticDatabase(Path(temporary.name) / "test.sqlite")
        self.app = Flask(__name__, template_folder=str(ROOT / "templates"))
        self.app.config.update(TESTING=True, SECRET_KEY="synthetic-session-key")
        init_request_security(self.app)
        self.app.register_blueprint(admin_routes.bp)
        self.app.register_blueprint(kdv_routes.bp)
        self.app.jinja_env.filters["safe_date"] = lambda value: value or "-"
        self.app.jinja_env.filters["tlformat"] = str
        self.app.add_url_rule("/", "main.home", lambda: "Synthetic home")
        self.app.add_url_rule("/login", "auth.login", lambda: "Synthetic login")
        self.app.add_url_rule("/test-token", "test_token", lambda: jsonify(token=generate_csrf()))
        other = Blueprint("synthetic_mobile", __name__)
        other.add_url_rule("/synthetic-mobile", "api", lambda: "unchanged", methods=["POST"])
        self.app.register_blueprint(other)
        self.client = self.app.test_client()

        # Never fall through to configured production or local customer databases.
        for module in (db, auth):
            patcher = patch.object(module, "get_conn", side_effect=AssertionError("Real database forbidden"))
            patcher.start()
            self.addCleanup(patcher.stop)
        for module in (admin_routes, kdv_routes):
            patcher = patch.object(module, "get_conn", side_effect=self.database.connect)
            patcher.start()
            self.addCleanup(patcher.stop)

    def login(self, role="uzman", access=True, pin=True):
        with self.client.session_transaction() as session:
            session.update(logged_in=True, user_id=10, role=role,
                           username="admin" if role == "admin" else "synthetic-user",
                           has_kdv_access=access, kdv_portal_pin_verified=pin)

    def token(self, client=None):
        return (client or self.client).get("/test-token").json["token"]

    def change(self, method, url, payload=None, token=True, **options):
        headers = {"X-CSRFToken": self.token()} if token else {}
        return self.client.open(url, method=method, json=payload, headers=headers, **options)

    def assert_unchanged(self):
        self.assertEqual(self.database.commits, 0)
        self.assertFalse(any(q.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
                             for q in self.database.queries))

    def test_specialist_cannot_add_note_to_unassigned_client(self):
        self.login()
        response = self.change("POST", "/api/kdv/note/add", {"file_id": 18, "text": NOTE_TEXT})
        self.assertEqual(response.status_code, 403)
        self.assert_unchanged()

    def test_specialist_cannot_update_unassigned_note_using_spoofed_file(self):
        self.login()
        response = self.change("POST", "/api/kdv/note/update",
                               {"id": 42, "file_id": 17, "mukellef_id": 9, "text": NOTE_TEXT})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.database.scalar("SELECT note_text FROM kdv_notes WHERE id=42"), "Other client note")
        self.assert_unchanged()

    def test_specialist_cannot_delete_unassigned_note(self):
        self.login()
        self.assertEqual(self.change("DELETE", "/api/kdv/note/delete/42").status_code, 403)
        self.assert_unchanged()

    def test_specialist_cannot_delete_unassigned_history(self):
        self.login()
        self.assertEqual(self.change("DELETE", "/api/kdv/history/delete/72").status_code, 403)
        self.assert_unchanged()

    def test_specialist_can_add_note_for_assigned_client_without_altering_text(self):
        self.login()
        self.assertEqual(self.change("POST", "/api/kdv/note/add", {"file_id": 17, "text": NOTE_TEXT}).status_code, 200)
        self.assertEqual(self.database.scalar("SELECT note_text FROM kdv_notes ORDER BY id DESC LIMIT 1"), NOTE_TEXT)

    def test_specialist_can_update_assigned_note(self):
        self.login()
        self.assertEqual(self.change("POST", "/api/kdv/note/update", {"id": 41, "text": NOTE_TEXT}).status_code, 200)
        self.assertEqual(self.database.scalar("SELECT note_text FROM kdv_notes WHERE id=41"), NOTE_TEXT)

    def test_specialist_can_delete_assigned_note(self):
        self.login()
        self.assertEqual(self.change("DELETE", "/api/kdv/note/delete/41").status_code, 200)
        self.assertIsNone(self.database.scalar("SELECT id FROM kdv_notes WHERE id=41"))

    def test_specialist_can_delete_assigned_history_and_missing_history_returns_404(self):
        self.login()
        self.assertEqual(self.change("DELETE", "/api/kdv/history/delete/71").status_code, 200)
        self.assertIsNone(self.database.scalar("SELECT id FROM kdv_history WHERE id=71"))
        self.assertEqual(self.change("DELETE", "/api/kdv/history/delete/71").status_code, 404)

    def test_existing_privileged_roles_can_manage_notes_across_clients(self):
        for role in ("admin", "ymm", "yonetici"):
            with self.subTest(role=role):
                self.login(role)
                self.assertEqual(self.change("POST", "/api/kdv/note/update", {"id": 42, "text": NOTE_TEXT}).status_code, 200)

    def test_unpermitted_roles_cannot_mutate_notes_or_history(self):
        for role in ("user", "editor", ""):
            self.login(role)
            for method, url, payload in self.note_requests():
                with self.subTest(role=role, url=url):
                    self.assertEqual(self.change(method, url, payload).status_code, 403)
        self.assert_unchanged()

    @staticmethod
    def note_requests():
        return [
            ("POST", "/api/kdv/note/add", {"file_id": 17, "text": NOTE_TEXT}),
            ("POST", "/api/kdv/note/update", {"id": 41, "text": NOTE_TEXT}),
            ("DELETE", "/api/kdv/note/delete/41", None),
            ("DELETE", "/api/kdv/history/delete/71", None),
        ]

    def test_anonymous_mutations_are_denied_even_with_valid_csrf(self):
        for method, url, payload in self.note_requests():
            with self.subTest(url=url):
                self.assertEqual(self.change(method, url, payload).status_code, 401)
        self.assert_unchanged()

    def test_portal_permission_and_pin_remain_required(self):
        for access, pin in ((False, True), (True, False)):
            self.login(access=access, pin=pin)
            for method, url, payload in self.note_requests():
                with self.subTest(access=access, pin=pin, url=url):
                    self.assertEqual(self.change(method, url, payload).status_code, 403)
        self.assert_unchanged()

    def test_missing_records_return_404_without_writes(self):
        self.login()
        for method, url, payload in [
            ("POST", "/api/kdv/note/add", {"file_id": 999, "text": NOTE_TEXT}),
            ("POST", "/api/kdv/note/update", {"id": 999, "text": NOTE_TEXT}),
            ("DELETE", "/api/kdv/note/delete/999", None),
            ("DELETE", "/api/kdv/history/delete/999", None),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.change(method, url, payload).status_code, 404)
        self.assert_unchanged()

    def test_malformed_note_payloads_return_400_without_queries(self):
        self.login()
        for url, key in (("/api/kdv/note/add", "file_id"), ("/api/kdv/note/update", "id")):
            for value in (None, [], "text", {}, {key: True, "text": "x"},
                          {key: [17], "text": "x"}, {key: -1, "text": "x"},
                          {key: 17.5, "text": "x"}, {key: 17, "text": {}},
                          {key: 17, "text": "  "}, {key: "9" * 30, "text": "x"}):
                with self.subTest(url=url, value=value):
                    self.assertEqual(self.change("POST", url, value).status_code, 400)
        self.assertEqual(self.database.queries, [])

    def test_missing_csrf_blocks_all_note_mutations_before_database(self):
        self.login()
        for method, url, payload in self.note_requests():
            with self.subTest(url=url):
                response = self.change(method, url, payload, token=False)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json["status"], "error")
        self.assertEqual(self.database.queries, [])

    def test_other_session_token_is_rejected(self):
        self.login()
        token = self.token(self.app.test_client())
        response = self.client.post("/api/kdv/note/update", json={"id": 41, "text": NOTE_TEXT},
                                    headers={"X-CSRFToken": token})
        self.assertEqual(response.status_code, 400)
        self.assert_unchanged()

    def test_expired_csrf_is_rejected(self):
        self.login()
        token = self.token()
        self.app.config["WTF_CSRF_TIME_LIMIT"] = -1
        response = self.client.post("/api/kdv/note/update", json={"id": 41, "text": NOTE_TEXT},
                                    headers={"X-CSRFToken": token})
        self.assertEqual(response.status_code, 400)
        self.assert_unchanged()

    def test_other_kdv_mutations_also_require_csrf(self):
        self.login("admin")
        for method, url in (("POST", "/api/kdv/update-pin"), ("POST", "/api/kdv/update-status"),
                            ("POST", "/api/kdv/upload-doc"), ("DELETE", "/api/kdv/document/delete/42"),
                            ("POST", "/api/kdv/assign-mukellef")):
            with self.subTest(url=url):
                self.assertEqual(self.change(method, url, {}, token=False).status_code, 400)
        self.assertEqual(self.database.queries, [])

    def test_admin_get_links_cannot_change_users(self):
        self.login("admin")
        for action in ("approve", "reject", "suspend"):
            with self.subTest(action=action):
                self.assertEqual(self.client.get(f"/{action}/2").status_code, 405)
                self.assertEqual(self.client.head(f"/{action}/2").status_code, 405)
        self.assert_unchanged()

    def test_admin_changes_require_csrf(self):
        self.login("admin")
        for url in ("/approve/2", "/reject/2", "/suspend/2", "/update_username/2",
                    "/change_role/2", "/reset_password/2", "/delete_all_logs"):
            with self.subTest(url=url):
                response = self.client.post(url, data={"new_username": "changed"})
                self.assertEqual(response.status_code, 400)
                self.assertIn("Sayfayı yenileyip", response.get_data(as_text=True))
        self.assertEqual(self.database.queries, [])

    def test_valid_csrf_does_not_grant_admin_permission(self):
        self.login()
        for action in ("approve", "reject", "suspend"):
            with self.subTest(action=action):
                response = self.client.post(f"/{action}/2", data={"csrf_token": self.token()})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, "/")
        self.assert_unchanged()

    def test_admin_can_approve_user_with_form_token(self):
        self.login("admin")
        response = self.client.post("/approve/2", data={"csrf_token": self.token()})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.database.scalar("SELECT is_approved FROM users WHERE id=2"), 1)

    def test_admin_can_suspend_and_unsuspend_with_form_token(self):
        self.login("admin")
        for expected in (1, 0):
            self.assertEqual(self.client.post("/suspend/2", data={"csrf_token": self.token()}).status_code, 302)
            self.assertEqual(self.database.scalar("SELECT is_suspended FROM users WHERE id=2"), expected)

    def test_admin_can_delete_regular_user_but_not_admin_account(self):
        self.login("admin")
        self.assertEqual(self.client.post("/reject/1", data={"csrf_token": self.token()}).status_code, 302)
        self.assertEqual(self.database.commits, 0)
        self.assertEqual(self.client.post("/reject/2", data={"csrf_token": self.token()}).status_code, 302)
        self.assertIsNone(self.database.scalar("SELECT id FROM users WHERE id=2"))
        self.assertEqual(self.database.scalar("SELECT username FROM users WHERE id=1"), "admin")

    def test_missing_user_delete_is_handled_without_writes(self):
        self.login("admin")
        self.assertEqual(self.client.post("/reject/999", data={"csrf_token": self.token()}).status_code, 302)
        self.assert_unchanged()

    def test_admin_forms_render_valid_tokens_and_post_actions(self):
        self.login("admin")
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        forms = FormParser(response.get_data(as_text=True)).forms
        post_forms = {form["action"]: form for form in forms if form["method"] == "POST"}
        for action in ("/approve/2", "/reject/2", "/suspend/2", "/update_username/2"):
            with self.subTest(action=action):
                self.assertTrue(post_forms[action]["token"])
        response = self.client.post("/approve/2", data={"csrf_token": post_forms["/approve/2"]["token"]})
        self.assertEqual(response.status_code, 302)

    def test_password_reset_form_has_csrf_and_valid_submission_still_works(self):
        self.login("admin")
        response = self.client.get("/reset_password/2")
        self.assertEqual(response.status_code, 200)
        form = FormParser(response.get_data(as_text=True)).forms[0]
        self.assertTrue(form["token"])
        response = self.client.post("/reset_password/2", data={"csrf_token": form["token"],
                                    "new_password": "Synthetic123", "new_password_confirm": "Synthetic123"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.database.scalar("SELECT password FROM users WHERE id=2"))

    def test_token_does_not_survive_session_reset(self):
        self.login("admin")
        token = self.token()
        with self.client.session_transaction() as session:
            session.clear()
        self.login("admin")
        self.assertEqual(self.client.post("/approve/2", data={"csrf_token": token}).status_code, 400)
        self.assert_unchanged()

    def test_https_request_with_cross_origin_referrer_is_rejected(self):
        self.login()
        token = self.token()
        response = self.client.post("/api/kdv/note/update", json={"id": 41, "text": NOTE_TEXT},
                                    headers={"X-CSRFToken": token, "Referer": "https://untrusted.invalid/"},
                                    base_url="https://localhost")
        self.assertEqual(response.status_code, 400)
        self.assert_unchanged()

    def test_https_request_with_same_origin_referrer_is_accepted(self):
        self.login()
        response = self.client.post("/api/kdv/note/update", json={"id": 41, "text": NOTE_TEXT},
                                    headers={"X-CSRFToken": self.token(), "Referer": "https://localhost/kdv-detay/17"},
                                    base_url="https://localhost")
        self.assertEqual(response.status_code, 200)

    def test_pin_form_contains_a_session_bound_token(self):
        self.app.jinja_loader = ChoiceLoader([
            DictLoader({"layout.html": "{% block content %}{% endblock %}"}),
            self.app.jinja_loader,
        ])
        self.app.add_url_rule("/synthetic-pin-form", "synthetic_pin_form",
                              lambda: render_template("kdv/verify_pin.html"))
        response = self.client.get("/synthetic-pin-form")
        form = FormParser(response.get_data(as_text=True)).forms[0]
        self.assertEqual(form["method"], "POST")
        self.assertTrue(form["token"])
        response = self.client.post(form["action"], data={"csrf_token": form["token"], "pin": "0000"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/login")

    def test_scope_does_not_change_unrelated_mobile_api(self):
        self.assertEqual(self.client.post("/synthetic-mobile").status_code, 200)

    def test_changed_templates_compile(self):
        for path in list((ROOT / "templates/kdv").glob("*.html")) + list((ROOT / "templates/admin").glob("*.html")):
            with self.subTest(template=path.name):
                self.app.jinja_env.get_template(path.relative_to(ROOT / "templates").as_posix())


if __name__ == "__main__":
    unittest.main()
