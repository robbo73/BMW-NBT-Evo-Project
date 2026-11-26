# Separate held-descriptor reader: Ubuntu build for inspection

26 November 2026. Source/build preparation only. The endpoint which passed the
586-byte vehicle trial is unchanged and is not rebuilt or bundled here.
No vehicle runner or release command is provided. No car connection is needed.

In the extracted nbt-open-handle-reader-prep directory, run on Ubuntu:

```sh
bash build_review.sh
```

The script verifies source hashes, runs 22 Linux host tests, then uses the
existing qnx65-armv7-toolchain:4.9 Docker image to build only
build-qnx/nbt_hold_reader_586. It separately preprocesses/compiles a tiny
SDK-interface capture; neither object nor ARM executable is executed.
It writes metadata and the review archive:

```text
/home/rob/nbt-open-handle-reader-review.tar.gz
```

Upload that archive for ELF/import/compiled-flow and SDK ABI review. Do not
copy or execute the new reader on the BMW. This preparation does not include
a reviewed vehicle controller, complete trace assessor or target-ready bundle.
Existing output directories and review archives are refused, never overwritten.
No milestone-7 source, existing package, BMW library, firmware or candidate is
changed. Host cc, Python 3.8+, readelf and the existing Docker image suffice.

See DESIGN.md for the exact scope, host-test substitutions and remaining
controller/readiness/watchdog requirements. Actual plugin loading and HMI
activation/restart trials remain paused; live RPM is unverified.
