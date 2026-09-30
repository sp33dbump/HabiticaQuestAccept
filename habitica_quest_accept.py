#!/usr/bin/env python3
"""Accept a Habitica party quest invitation that is still waiting for an answer.

Reads the User ID and API Token from config.json in this folder, or from the
environment variables HABITICA_USER_ID / HABITICA_UID and HABITICA_API_TOKEN.
Writes a line log to logs/quest-accept.log. Never prints the API token.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
LOG_PATH = ROOT / "logs" / "quest-accept.log"
API_BASE = "https://habitica.com/api/v3"

# Left blank in the published source so the author's Habitica User ID is not
# shipped. Habitica still requires x-client. client_header uses
# HABITICA_AUTHOR_ID when set, and otherwise the player User ID already
# required for the API call.
AUTHOR_USER_ID = ""
APP_NAME = "HabiticaQuestAccept"

_MISSING = object()
Transport = Callable[[str, str, bytes | None, dict[str, str]], tuple[int, dict]]


@dataclass
class Decision:
    """What the daily run should do for this account."""

    action: str
    quest_key: str = ""
    party_name: str = ""


class HabiticaError(Exception):
    """Habitica returned an error, or the response was not JSON."""

    def __init__(self, status: int, error: str, message: str) -> None:
        self.status = status
        self.error = error
        self.message = message
        super().__init__(f"Habitica {status} {error}: {message}")


def redact(text: str, secrets: list[str]) -> str:
    """Remove credential values from a line before it is shown or saved."""
    cleaned = text
    for secret in secrets:
        if secret:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def log_line(message: str, secrets: list[str] | None = None) -> None:
    """Append one timestamped line to the log and echo it."""
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"{stamp} {redact(message, secrets or [])}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_config() -> dict[str, str]:
    """Load credentials. Environment variables win over config.json."""
    file_user = ""
    file_token = ""
    if CONFIG_PATH.is_file():
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        file_user = str(raw.get("user_id") or "").strip()
        file_token = str(raw.get("api_token") or "").strip()
    user_id = (
        os.environ.get("HABITICA_USER_ID")
        or os.environ.get("HABITICA_UID")
        or file_user
    ).strip()
    api_token = (os.environ.get("HABITICA_API_TOKEN") or file_token).strip()
    return {"user_id": user_id, "api_token": api_token}


def client_header(user_id: str) -> str:
    """x-client value Habitica requires on authenticated calls."""
    author = os.environ.get("HABITICA_AUTHOR_ID", "").strip() or AUTHOR_USER_ID or user_id
    return f"{author}-{APP_NAME}"


def urllib_transport(
    method: str,
    url: str,
    body: bytes | None,
    headers: dict[str, str],
) -> tuple[int, dict]:
    """Perform one HTTPS call with the standard library."""
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    try:
        parsed = json.loads(payload) if payload else {}
    except json.JSONDecodeError as exc:
        raise HabiticaError(status, "BadResponse", "Habitica did not return JSON") from exc
    if not isinstance(parsed, dict):
        raise HabiticaError(status, "BadResponse", "Habitica returned an unexpected document")
    return status, parsed


class HabiticaClient:
    """Small client for the three calls this job needs."""

    def __init__(self, user_id: str, api_token: str, transport: Transport | None = None) -> None:
        self.user_id = user_id
        self.api_token = api_token
        self.transport = transport or urllib_transport

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-user": self.user_id,
            "x-api-key": self.api_token,
            "x-client": client_header(self.user_id),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        """Call one API path. Raises HabiticaError when success is false."""
        payload = None if body is None else json.dumps(body).encode("utf-8")
        status, parsed = self.transport(
            method,
            API_BASE + path,
            payload,
            self._headers(),
        )
        if status == 429:
            raise HabiticaError(status, "TooManyRequests", "Habitica rate limit reached")
        if not parsed.get("success", status < 400):
            raise HabiticaError(
                status,
                str(parsed.get("error") or "Error"),
                str(parsed.get("message") or "request failed"),
            )
        if status >= 400:
            raise HabiticaError(status, "HTTPError", str(parsed.get("message") or "request failed"))
        return parsed

    def get_user(self) -> dict:
        """Return the authenticated user document."""
        return self.request("GET", "/user")["data"]

    def get_party(self) -> dict | None:
        """Return the party document, or None when this account has no party."""
        try:
            return self.request("GET", "/groups/party")["data"]
        except HabiticaError as exc:
            if exc.status == 404:
                return None
            raise

    def accept_quest(self) -> dict:
        """Accept the current party quest invitation."""
        return self.request("POST", "/groups/party/quests/accept", {})


def decide(user: dict | None, party: dict | None, user_id: str) -> Decision:
    """Classify the quest invitation without calling the network.

    Habitica stores an unanswered invite as null on party.quest.members, and
    sets the user's party.quest.RSVPNeeded flag. true means accepted and false
    means declined.
    """
    if not user:
        return Decision("no-user")
    party_id = (user.get("party") or {}).get("_id")
    if not party_id or party is None:
        return Decision("no-party")
    quest = party.get("quest") or {}
    quest_key = str(quest.get("key") or "")
    party_name = str(party.get("name") or "")
    if not quest_key:
        return Decision("no-quest", party_name=party_name)
    members = quest.get("members") or {}
    rsvp = members.get(user_id, _MISSING)
    needs_reply = bool(((user.get("party") or {}).get("quest") or {}).get("RSVPNeeded"))
    base = Decision("not-invited", quest_key=quest_key, party_name=party_name)
    if rsvp is False and not needs_reply:
        base.action = "declined"
        return base
    if rsvp is True and not needs_reply:
        base.action = "accepted"
        return base
    if needs_reply or rsvp is None:
        base.action = "pending"
        return base
    if rsvp is _MISSING and not quest.get("active"):
        base.action = "pending"
        return base
    return base


def outcome_message(decision: Decision, accepted_now: bool, check_only: bool) -> tuple[int, str]:
    """Turn a decision into an exit code and a log message."""
    key = decision.quest_key or "quest"
    party = f" in party {decision.party_name}" if decision.party_name else ""
    if decision.action == "pending" and check_only:
        return 0, f"OK pending {key}{party}; check only, left unanswered"
    if decision.action == "pending" and accepted_now:
        return 0, f"OK accepted {key}{party}"
    messages = {
        "accepted": f"OK already accepted {key}{party}",
        "declined": f"OK {key}{party} stays declined",
        "no-party": "OK not in a party",
        "no-quest": f"OK no quest invitation{party}",
        "not-invited": f"OK no invitation on {key}{party}",
        "no-user": "FAIL Habitica returned no user",
    }
    text = messages.get(decision.action, f"FAIL unexpected state {decision.action}")
    return (0 if text.startswith("OK") else 1), text


def run_once(
    credentials: dict[str, str],
    check_only: bool = False,
    transport: Transport | None = None,
) -> int:
    """Look up the party quest and accept it when the invitation is unanswered."""
    secrets = [credentials.get("api_token", ""), credentials.get("user_id", "")]
    user_id = credentials.get("user_id", "")
    api_token = credentials.get("api_token", "")
    if not user_id or not api_token:
        log_line(
            "FAIL missing Habitica User ID or API Token. "
            "Run install again. Credentials page: https://habitica.com/user/settings/api",
            secrets,
        )
        return 1
    client = HabiticaClient(user_id, api_token, transport=transport)
    try:
        user = client.get_user()
        party = client.get_party()
        decision = decide(user, party, user_id)
        accepted_now = False
        if decision.action == "pending" and not check_only:
            client.accept_quest()
            accepted_now = True
        code, message = outcome_message(decision, accepted_now, check_only)
    except HabiticaError as exc:
        if exc.status in (401, 403):
            message = (
                "FAIL Habitica rejected the User ID or API Token. "
                "Copy both again from https://habitica.com/user/settings/api"
            )
        else:
            message = f"FAIL {exc.error}: {exc.message}"
        log_line(message, secrets)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log_line(f"FAIL network: {exc}", secrets)
        return 1
    log_line(message, secrets)
    return code


def self_test() -> int:
    """Run the invitation rules against fixed examples. No network."""
    user_id = "11111111-1111-1111-1111-111111111111"
    other = "22222222-2222-2222-2222-222222222222"

    def user(rsvp: bool | None = None, party_id: str | None = "party") -> dict:
        quest: dict = {}
        if rsvp is not None:
            quest["RSVPNeeded"] = rsvp
        return {"party": {"_id": party_id, "quest": quest}}

    def party(members: dict, key: str = "whale", active: bool = False) -> dict:
        return {"name": "Friends", "quest": {"key": key, "active": active, "members": members}}

    cases = [
        ("pending-null", user(), party({user_id: None}), "pending"),
        ("pending-flag", user(True), party({user_id: True}), "pending"),
        ("accepted", user(False), party({user_id: True}), "accepted"),
        ("declined", user(False), party({user_id: False}), "declined"),
        ("no-quest", user(), {"name": "Friends", "quest": {}}, "no-quest"),
        ("no-party", user(party_id=None), None, "no-party"),
        ("active-other", user(), party({other: True}, active=True), "not-invited"),
        ("invite-stage-missing", user(), party({other: True}, active=False), "pending"),
    ]
    failed = 0
    for name, user_doc, party_doc, expected in cases:
        got = decide(user_doc, party_doc, user_id).action
        if got != expected:
            print(f"FAIL {name}: expected {expected}, got {got}")
            failed += 1
        else:
            print(f"OK {name}")
    sample = redact(f"token {user_id} stays out of logs", [user_id])
    if user_id in sample or "[redacted]" not in sample:
        print("FAIL redact")
        failed += 1
    else:
        print("OK redact")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry: daily accept, --check, or --self-test."""
    parser = argparse.ArgumentParser(description="Accept a pending Habitica party quest invitation.")
    parser.add_argument("--check", action="store_true", help="Report a waiting invitation without accepting it")
    parser.add_argument("--self-test", action="store_true", help="Run built-in invitation rules and exit")
    parser.add_argument("--version", action="store_true", help="Print the version and exit")
    args = parser.parse_args(argv)
    if args.version:
        print(VERSION)
        return 0
    if args.self_test:
        return self_test()
    credentials = load_config()
    secrets = [credentials.get("api_token", ""), credentials.get("user_id", "")]
    log_line(f"START habitica-quest-accept {VERSION}", secrets)
    try:
        code = run_once(credentials, check_only=args.check)
    except Exception:
        log_line("FAIL " + redact(traceback.format_exc(), secrets), secrets)
        code = 1
    log_line(f"END exit={code}", secrets)
    return code


if __name__ == "__main__":
    sys.exit(main())
