# Launcher/supervisor r2: offline build review

Owner-supplied Claude revision 2, adopted with the local clock/signal corrections
in [REVIEW.md](REVIEW.md). Current local results are **34 passed, 16 namespace
checks skipped**. All examples/stand-ins are synthetic. No QNX run has occurred.
The [original architecture](ARCHITECTURE.md) is an attributed design record.

From the standalone nbt-supervisor-r2-prep root on Ubuntu:

```sh
bash tools/held-expiry-supervisor/build_review.sh
```

This checks hashes, runs the Linux host suites and cross-builds only the new
supervisor using the existing qnx65-armv7-toolchain:4.9 Docker image. It captures
SDK declarations/macros/ABI sizes and the actual executable's ELF metadata.
Neither the ARM executable nor the API object is executed. Review output:

```text
/home/rob/nbt-supervisor-r2-review.tar.gz
```

Upload that archive for inspection. Do not transfer/run the new supervisor on
the BMW. The existing reader and endpoint are not rebuilt; milestone-7, hidden
candidates, firmware and HMI configuration are untouched. No new dependencies
are installed. Existing output paths are refused rather than overwritten.

gate_trial.py runs locally and requires the real launcher exit status plus
unchanged-assessor PASS. It is not a transport/capture wrapper; entering 0 by
hand cannot establish that a trial completed. A target-ready package still
requires compiled/runtime review and a reviewed status-preserving capture path.
