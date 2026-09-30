#!/usr/bin/env python3
"""Build a zip of this folder that is safe to give to another Habitica player.

The archive omits config.json, virtual environments, and log files so a User ID
and API Token are not packed by accident.
"""

from __future__ import annotations

import argparse
import stat
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE_ROOT = "HabiticaQuestAccept"
SKIP_DIR_NAMES = {".venv", "__pycache__", "dist", ".git"}
SKIP_FILE_NAMES = {"config.json", ".DS_Store", "STATE.md"}
EXECUTABLE_SUFFIXES = {".command", ".sh"}


def files_to_pack(root: Path = ROOT) -> list[Path]:
    """Return project files that belong in a player-facing zip."""
    chosen: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIR_NAMES for part in relative.parts):
            continue
        if path.name in SKIP_FILE_NAMES or path.suffix == ".log" or path.suffix == ".pyc":
            continue
        chosen.append(path)
    return sorted(chosen)


def build_zip(destination: Path | None = None) -> Path:
    """Write the zip and return its path."""
    stamp = date.today().isoformat()
    target = destination or (ROOT / "dist" / f"HabiticaQuestAccept-{stamp}.zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files_to_pack():
            info = zipfile.ZipInfo.from_file(path, arcname=f"{ARCHIVE_ROOT}/{path.relative_to(ROOT).as_posix()}")
            mode = path.stat().st_mode
            if path.suffix in EXECUTABLE_SUFFIXES:
                mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
            info.external_attr = (mode & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes())
    return target


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper around build_zip."""
    parser = argparse.ArgumentParser(description="Zip this project for other Habitica players.")
    parser.add_argument("--output", type=Path, help="Zip path to write")
    args = parser.parse_args(argv)
    target = build_zip(args.output)
    names = zipfile.ZipFile(target).namelist()
    leaked = [name for name in names if name.endswith("config.json") or ".venv/" in name or name.endswith(".log")]
    if leaked:
        print("Refusing to leave a zip that contains credentials or logs:")
        for name in leaked:
            print(f"  {name}")
        return 1
    print(f"Wrote {target} ({len(names)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
