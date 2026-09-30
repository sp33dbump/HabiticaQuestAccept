"""Installer and zip packing. These tests do not register a scheduled job."""

from __future__ import annotations

import stat
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import install  # noqa: E402
import make_dist  # noqa: E402
import schedule_setup as schedule  # noqa: E402
import uninstall  # noqa: E402


class ScheduleTests(unittest.TestCase):
    def test_time_parsing(self) -> None:
        self.assertEqual(schedule.parse_time("08:00"), (8, 0))
        self.assertEqual(schedule.parse_time("8:05"), (8, 5))
        with self.assertRaises(ValueError):
            schedule.parse_time("25:00")

    def test_plist_has_schedule_and_no_secret_slot(self) -> None:
        xml = schedule.launchd_plist(
            Path("/tmp/python"),
            ROOT / "habitica_quest_accept.py",
            ROOT,
            ROOT / "logs" / "scheduled-output.log",
            ROOT / "logs" / "scheduled-error.log",
            8,
            0,
        )
        self.assertIn("<key>Hour</key>", xml)
        self.assertIn("<integer>8</integer>", xml)
        self.assertIn(schedule.LABEL, xml)
        self.assertNotIn("api_token", xml)
        self.assertNotIn("x-api-key", xml)

    def test_windows_xml_survives_a_space_in_the_path(self) -> None:
        xml = schedule.windows_task_xml(
            Path(r"C:\Users\Alex Smith\HabiticaQuestAccept\run_daily.bat"),
            Path(r"C:\Users\Alex Smith\HabiticaQuestAccept"),
            8,
            30,
        )
        self.assertIn("08:30:00", xml)
        self.assertIn("Alex Smith", xml)
        self.assertIn("<StartWhenAvailable>true</StartWhenAvailable>", xml)
        self.assertNotIn("api_token", xml)

    def test_systemd_units_have_no_secret_slot(self) -> None:
        service = schedule.systemd_service(
            Path("/home/alex smith/venv/bin/python"),
            Path("/home/alex smith/HabiticaQuestAccept/habitica_quest_accept.py"),
            Path("/home/alex smith/HabiticaQuestAccept"),
            Path("/home/alex smith/HabiticaQuestAccept/logs/scheduled-output.log"),
            Path("/home/alex smith/HabiticaQuestAccept/logs/scheduled-error.log"),
        )
        timer = schedule.systemd_timer(8, 15)
        self.assertIn("Type=oneshot", service)
        self.assertIn('"/home/alex smith/venv/bin/python"', service)
        self.assertIn("OnCalendar=*-*-* 08:15:00", timer)
        self.assertIn("Persistent=true", timer)
        self.assertNotIn("api_token", service + timer)
        self.assertNotIn("x-api-key", service + timer)

    def test_cron_line_is_marked_and_quoted(self) -> None:
        line = schedule.cron_line(
            Path("/usr/bin/python3"),
            Path("/home/alex smith/habitica_quest_accept.py"),
            Path("/home/alex smith"),
            8,
            5,
            Path("/home/alex smith/logs/scheduled-output.log"),
        )
        self.assertTrue(line.startswith("5 8 * * * "))
        self.assertIn("'/home/alex smith'", line)
        self.assertIn(f"# {schedule.CRON_MARK}", line)
        self.assertNotIn("api_token", line)

    def test_uuid_check(self) -> None:
        self.assertTrue(install.looks_like_uuid("12345678-90ab-416b-cdef-1234567890ab"))
        self.assertFalse(install.looks_like_uuid("not-a-token"))
        self.assertFalse(install.looks_like_uuid(""))


class DryRunTests(unittest.TestCase):
    def test_install_dry_run_does_not_write_config(self) -> None:
        config = ROOT / "config.json"
        existed = config.exists()
        code = install.main(["--dry-run", "--time", "08:15"])
        self.assertEqual(code, 0)
        self.assertEqual(config.exists(), existed)

    def test_uninstall_dry_run(self) -> None:
        code = uninstall.main(["--dry-run", "--keep-config"])
        self.assertEqual(code, 0)


class DistTests(unittest.TestCase):
    def test_pack_list_skips_secrets_and_venv(self) -> None:
        names = {path.name for path in make_dist.files_to_pack()}
        self.assertIn("README.txt", names)
        self.assertIn("install.py", names)
        self.assertIn("habitica_quest_accept.py", names)
        self.assertNotIn("config.json", names)

    def test_zip_excludes_a_config_file(self) -> None:
        config = ROOT / "config.json"
        created = False
        if not config.exists():
            config.write_text('{"user_id":"secret","api_token":"secret"}\n', encoding="utf-8")
            created = True
        try:
            target = ROOT / "dist" / "test-pack.zip"
            if target.exists():
                target.unlink()
            built = make_dist.build_zip(target)
            names = zipfile.ZipFile(built).namelist()
            self.assertTrue(any(name.endswith("README.txt") for name in names))
            self.assertFalse(any(name.endswith("config.json") or name.endswith("STATE.md") for name in names))
            self.assertFalse(any(".venv/" in name or name.endswith(".log") for name in names))
            command = zipfile.ZipFile(built).getinfo("HabiticaQuestAccept/install.command")
            mode = (command.external_attr >> 16) & 0xFFFF
            self.assertTrue(mode & stat.S_IXUSR)
        finally:
            if created and config.exists():
                config.unlink()
            leftover = ROOT / "dist" / "test-pack.zip"
            if leftover.exists():
                leftover.unlink()
