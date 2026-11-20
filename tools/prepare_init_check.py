#!/usr/bin/env python3
"""Generate a separate lifecycle-only source copy; never edit the RPM source."""
import argparse
import hashlib
from pathlib import Path


BEFORE = "1b3b8e343dcabea75036e2c473ccc71a51a2cbd240c84d5de5eb070e0accf853"
AFTER = "d742b624263cc16f30d7809d942e6ac1e5267466fa312db985977f9a3dc3c776"


def prepare(original):
    if hashlib.sha256(original).hexdigest() != BEFORE:
        raise SystemExit("No files changed: RPM source differs from reviewed revision")
    result = original
    start = result.index(b"bool appOnInit(bmw::PluginApp* self) {")
    end = result.index(b"\nvoid appOnError(", start)
    result = result[:start] + b'''bool appOnInit(bmw::PluginApp* self) {
    alog("INIT CHECK: onInit entered");
    const bool ok = self->onInit();
    alog("INIT CHECK: base onInit returned %d", (int)ok);
    return ok;
}
''' + result[end:]
    start = result.index(b"void appOnFinalize(bmw::PluginApp* self) {")
    end = result.index(b"\nbmw::PluginApp* createApp(", start)
    result = result[:start] + b'''void appOnFinalize(bmw::PluginApp* self) {
    alog("INIT CHECK: onFinalize entered");
    g_runApp = NULL;
    self->onFinalize();
}
''' + result[end:]
    old = b'#define NBT_AAD_APP_VERSION "rhmiapp-54-cpcompat (" __DATE__ " " __TIME__ ")"'
    new = b'#define NBT_AAD_APP_VERSION "init-check-1 (" __DATE__ " " __TIME__ ")"'
    if result.count(old) != 1:
        raise SystemExit("No files changed: unexpected version declaration")
    result = result.replace(old, new)
    if hashlib.sha256(result).hexdigest() != AFTER:
        raise SystemExit("No files changed: generated source differs from review")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.home() / "milestone-7")
    parser.add_argument("--write-copy", action="store_true", help="Create the separate source with exclusive creation")
    args = parser.parse_args()
    source = args.root.expanduser() / "rhmiapp/nbt_aad_app.cpp"
    target = source.with_name("nbt_aad_app_init_check.cpp")
    if source.is_symlink() or not source.is_file():
        raise SystemExit("No files changed: RPM source is missing or linked")
    original = source.read_bytes()
    generated = prepare(original)
    if target.is_symlink():
        raise SystemExit("No files changed: initialization-check path is linked")
    if target.exists():
        if not target.is_file() or target.read_bytes() != generated:
            raise SystemExit("No files changed: initialization-check source already differs")
        print("Existing separate initialization-check source verified:", target)
    elif args.write_copy:
        with target.open("xb") as stream:
            stream.write(generated)
        print("Created separate initialization-check source:", target)
    else:
        print("CHECK PASSED; no files changed. Use --write-copy to create the separate source.")
    if source.is_symlink() or source.read_bytes() != original:
        raise SystemExit("RPM source changed concurrently; stop and inspect")
    print("Initialization-check source SHA-256:", AFTER)
    print("RPM source unchanged. Vehicle execution remains paused.")


if __name__ == "__main__":
    main()
