#!/usr/bin/env python3
"""Remove two unused iostream includes from the reviewed source revision."""
import hashlib
from pathlib import Path
import sys

EXPECTED = {
    "rhmiapp/b58/b58_telemetry.hpp": "a03fd610999321acf126738d15176ff543b14d04149f1569c72709a02f44f270",
    "rhmiapp/b58/b58_rhmi_bridge.cpp": "d3cd58395964f1ef3b265bbe3c9f2adb50a1fde446f246eb5ee4b61eb0032da7",
}


def main():
    if len(sys.argv) > 2:
        raise SystemExit("Usage: prepare_stream_cleanup.py [milestone-7-directory]")
    root = Path(sys.argv[1]).expanduser() if len(sys.argv) == 2 else Path.home() / "milestone-7"
    prepared = []
    for relative, expected in EXPECTED.items():
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise SystemExit("No files changed: missing or linked source: " + str(path))
        original = path.read_bytes()
        if hashlib.sha256(original).hexdigest() != expected:
            raise SystemExit("No files changed: source revision differs: " + str(path))
        if original.count(b"#include <iostream>\n") != 1:
            raise SystemExit("No files changed: unexpected include count: " + str(path))
        backup = path.with_name(path.name + ".before-20261117-stream-cleanup")
        if backup.exists() or backup.is_symlink():
            raise SystemExit("No files changed: backup already exists: " + str(backup))
        prepared.append((path, backup, original, original.replace(b"#include <iostream>\n", b"")))
    for path, backup, original, updated in prepared:
        with backup.open("xb") as stream:
            stream.write(original)
    for path, backup, original, updated in prepared:
        path.write_bytes(updated)
        print("Updated:", path)
        print("Backup:", backup)
    print("Source cleanup only. Rebuild for offline inspection; do not run a BMW probe or activate the plugin.")


if __name__ == "__main__":
    main()
