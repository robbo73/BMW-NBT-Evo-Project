#!/usr/bin/env python3
"""Check or prepare the reviewed initial RPM get change in an Ubuntu source tree."""
import argparse
import hashlib
from pathlib import Path


BEFORE = "1fa48b7a903cfb7aeb2d59abb703b3bdafe291bbc8ebc7c28a109eeb262510be"
AFTER = "1b3b8e343dcabea75036e2c473ccc71a51a2cbd240c84d5de5eb070e0accf853"
EDITS = [
    (b"    void cdsAddPropertyChangedEventHandler(BasicString<char>& property, unsigned id, const CdsDelegate& handler);\n",
     b"    void cdsAddPropertyChangedEventHandler(BasicString<char>& property, unsigned id, const CdsDelegate& handler);\n"
     b"    void cdsGetPropertyAsync(BasicString<char>& property, const CdsDelegate& handler);\n"),
    (b'        alog("B58 CDS handler registered for %s",\n'
     b'             kB58RpmProperty);\n',
     b'        alog("B58 CDS subscription call returned for %s",\n'
     b'             kB58RpmProperty);\n'
     b'        // Use the same copied delegate for initial and ongoing responses.\n'
     b'        // One explicit get per subscription-runnable execution; no polling.\n'
     b'        alog("B58 CDS initial async-get invoking for %s", kB58RpmProperty);\n'
     b'        g_runApp->cdsGetPropertyAsync(rpmProp, rpmDelegate);\n'
     b'        alog("B58 CDS initial async-get call returned for %s", kB58RpmProperty);\n'),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.home() / "milestone-7")
    parser.add_argument("--apply", action="store_true", help="Preserve a backup and edit the matching source")
    args = parser.parse_args()
    path = args.root.expanduser() / "rhmiapp/nbt_aad_app.cpp"
    if path.is_symlink() or not path.is_file():
        raise SystemExit("No files changed: source missing or linked: " + str(path))
    original = path.read_bytes()
    current = digest(original)
    if current == AFTER:
        print("Already prepared; no files changed:", path)
        return
    if current != BEFORE:
        raise SystemExit("No files changed: source revision differs (SHA-256 " + current + ")")
    updated = original
    for old, new in EDITS:
        if updated.count(old) != 1:
            raise SystemExit("No files changed: source context differs")
        updated = updated.replace(old, new)
    if digest(updated) != AFTER:
        raise SystemExit("No files changed: prepared output differs from review")
    backup = path.with_name(path.name + ".before-20261120-initial-get")
    if backup.exists() or backup.is_symlink():
        raise SystemExit("No files changed: backup already exists: " + str(backup))
    if not args.apply:
        print("CHECK PASSED: reviewed source matches; no files changed.")
        print("Prepared source SHA-256:", AFTER)
        return
    with backup.open("xb") as stream:
        stream.write(original)
    if path.is_symlink() or path.read_bytes() != original:
        raise SystemExit("Source changed during preparation; backup preserved, source not edited")
    path.write_bytes(updated)
    if digest(path.read_bytes()) != AFTER:
        raise SystemExit("Output verification failed; original is preserved at " + str(backup))
    print("Updated:", path)
    print("Backup:", backup)
    print("Source preparation only. Rebuild for offline inspection; vehicle loading remains paused.")


if __name__ == "__main__":
    main()
