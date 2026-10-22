"""Session, login/logout and CSRF behavior for the real organizer adapter."""

import json
import logging

from django.test import Client, TestCase

from .support import PASSWORD, make_organizer


class SessionTests(TestCase):
    def setUp(self):
        self.organizer = make_organizer()
        self.other = make_organizer("other-organizer")

    def test_session_is_anonymous_before_login_and_sets_csrf_cookie(self):
        response = self.client.get("/api/auth/session")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["organizer"])
        self.assertIn("csrftoken", response.cookies)
        self.assertEqual(response.cookies["csrftoken"]["samesite"], "Lax")

    def test_login_uses_a_server_session_and_never_returns_a_password(self):
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": self.organizer.username, "password": PASSWORD}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["organizer"], {
            "id": str(self.organizer.id), "username": self.organizer.username,
        })
        self.assertIn("sessionid", response.cookies)
        self.assertNotIn(PASSWORD, response.content.decode())
        self.assertEqual(
            self.client.get("/api/auth/session").json()["organizer"]["id"],
            str(self.organizer.id),
        )

    def test_invalid_credentials_return_a_clear_but_generic_error(self):
        for payload in [
            {"username": self.organizer.username, "password": "wrong-password"},
            {"username": "missing-organizer", "password": PASSWORD},
        ]:
            with self.subTest(payload=payload):
                response = self.client.post(
                    "/api/auth/login",
                    data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json()["error"]["code"], "invalid_credentials")
                self.assertIn("incorrect", response.json()["error"]["message"])
                self.assertNotIn(payload["password"], response.content.decode())

    def test_inactive_account_cannot_log_in(self):
        inactive = make_organizer("inactive-organizer", active=False)
        response = self.client.post(
            "/api/auth/login",
            data=json.dumps({"username": inactive.username, "password": PASSWORD}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "invalid_credentials")

    def test_missing_fields_and_invalid_json_are_field_or_payload_errors(self):
        response = self.client.post(
            "/api/auth/login", data=json.dumps({"username": ""}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_input")
        self.assertIn("password", response.json()["error"]["fields"])

        response = self.client.post(
            "/api/auth/login", data="{not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_json")

    def test_csrf_is_required_for_login(self):
        client = Client(enforce_csrf_checks=True)
        payload = json.dumps({"username": self.organizer.username, "password": PASSWORD})
        response = client.post(
            "/api/auth/login", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")

        client.get("/api/auth/session")
        token = client.cookies["csrftoken"].value
        response = client.post(
            "/api/auth/login",
            data=payload,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)

    def test_logout_removes_access_to_protected_operations(self):
        self.client.force_login(self.organizer)
        event = {
            "name": "Session Event", "description": "Synthetic",
            "date": "2099-01-01", "time": "10:00", "location": "Hall",
        }
        self.assertEqual(
            self.client.post(
                "/api/events", data=json.dumps(event), content_type="application/json"
            ).status_code,
            201,
        )

        response = self.client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"logged_out": True})
        self.assertIsNone(self.client.get("/api/auth/session").json()["organizer"])
        denied = self.client.post(
            "/api/events", data=json.dumps(event), content_type="application/json"
        )
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(denied.json()["error"]["code"], "authentication_required")

    def test_identity_headers_never_authenticate_a_session(self):
        response = self.client.get(
            "/api/organizer/events", HTTP_X_ORGANIZER_ID=str(self.organizer.id)
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "authentication_required")

    def test_wrong_methods_use_json_errors_and_allow_headers(self):
        response = self.client.get("/api/auth/login")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "POST")
        self.assertEqual(response.json()["error"]["code"], "method_not_allowed")

    def test_login_failure_does_not_log_the_password_or_session_secret(self):
        password = "unique-password-that-must-not-be-logged"
        records = []

        class Capture(logging.Handler):
            def emit(self, record):
                records.append(record.getMessage())

        logger = logging.getLogger()
        handler = Capture(level=logging.DEBUG)
        previous_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            self.client.post(
                "/api/auth/login",
                data=json.dumps({"username": self.organizer.username, "password": password}),
                content_type="application/json",
            )
            self.client.force_login(self.organizer)
            self.client.post("/api/auth/logout")
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)

        combined = "\n".join(records)
        self.assertNotIn(password, combined)
        self.assertNotIn("sessionid", combined.lower())
