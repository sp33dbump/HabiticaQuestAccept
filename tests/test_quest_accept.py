"""Invitation rules and the HTTP client, with no live Habitica calls."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import habitica_quest_accept as app  # noqa: E402


USER = "11111111-1111-1111-1111-111111111111"
TOKEN = "22222222-2222-2222-2222-222222222222"


class DecideTests(unittest.TestCase):
    def setUp(self) -> None:
        self._log = app.LOG_PATH
        self._tmp = tempfile.TemporaryDirectory()
        app.LOG_PATH = Path(self._tmp.name) / "quest-accept.log"

    def tearDown(self) -> None:
        app.LOG_PATH = self._log
        self._tmp.cleanup()

    def test_self_test_passes(self) -> None:
        self.assertEqual(app.self_test(), 0)

    def test_pending_posts_accept_and_declined_does_not(self) -> None:
        calls: list[tuple[str, str]] = []

        def transport(method, url, body, headers):
            path = url.removeprefix(app.API_BASE)
            calls.append((method, path))
            self.assertEqual(headers["x-api-key"], TOKEN)
            self.assertIn("HabiticaQuestAccept", headers["x-client"])
            self.assertNotIn(TOKEN, headers["x-client"])
            if path == "/user":
                data = {"party": {"_id": "p", "quest": {"RSVPNeeded": True}}}
            elif path == "/groups/party":
                data = {"name": "Friends", "quest": {"key": "whale", "active": False, "members": {USER: None}}}
            elif path == "/groups/party/quests/accept":
                data = {"quest": {"key": "whale"}}
            else:
                raise AssertionError(path)
            return 200, {"success": True, "data": data}

        code = app.run_once({"user_id": USER, "api_token": TOKEN}, transport=transport)
        self.assertEqual(code, 0)
        self.assertIn(("POST", "/groups/party/quests/accept"), calls)

        calls.clear()

        def declined(method, url, body, headers):
            path = url.removeprefix(app.API_BASE)
            calls.append((method, path))
            if path == "/user":
                data = {"party": {"_id": "p", "quest": {"RSVPNeeded": False}}}
            else:
                data = {"name": "Friends", "quest": {"key": "whale", "active": False, "members": {USER: False}}}
            return 200, {"success": True, "data": data}

        code = app.run_once({"user_id": USER, "api_token": TOKEN}, transport=declined)
        self.assertEqual(code, 0)
        self.assertNotIn(("POST", "/groups/party/quests/accept"), calls)

    def test_check_does_not_post(self) -> None:
        calls: list[str] = []

        def transport(method, url, body, headers):
            path = url.removeprefix(app.API_BASE)
            calls.append(method + " " + path)
            if path == "/user":
                data = {"party": {"_id": "p", "quest": {"RSVPNeeded": True}}}
            else:
                data = {"name": "Friends", "quest": {"key": "atom1", "active": False, "members": {USER: None}}}
            return 200, {"success": True, "data": data}

        code = app.run_once({"user_id": USER, "api_token": TOKEN}, check_only=True, transport=transport)
        self.assertEqual(code, 0)
        self.assertFalse(any(item.startswith("POST") for item in calls))

    def test_unauthorized_is_a_failure(self) -> None:
        def transport(method, url, body, headers):
            return 401, {"success": False, "error": "NotAuthorized", "message": "There is no account that uses those credentials."}

        code = app.run_once({"user_id": USER, "api_token": TOKEN}, transport=transport)
        self.assertEqual(code, 1)

    def test_missing_party_is_success(self) -> None:
        def transport(method, url, body, headers):
            path = url.removeprefix(app.API_BASE)
            if path == "/user":
                return 200, {"success": True, "data": {"party": {}}}
            return 404, {"success": False, "error": "NotFound", "message": "Party not found."}

        code = app.run_once({"user_id": USER, "api_token": TOKEN}, transport=transport)
        self.assertEqual(code, 0)

    def test_log_redacts_token(self) -> None:
        app.log_line(f"blew up with {TOKEN}", [TOKEN])
        text = app.LOG_PATH.read_text(encoding="utf-8")
        self.assertNotIn(TOKEN, text)
        self.assertIn("[redacted]", text)


class ClientHeaderTests(unittest.TestCase):
    def test_header_uses_player_id_when_author_unset(self) -> None:
        header = app.client_header(USER)
        self.assertEqual(header, f"{USER}-HabiticaQuestAccept")
        self.assertFalse(app.AUTHOR_USER_ID)
        self.assertNotIn(TOKEN, header)
