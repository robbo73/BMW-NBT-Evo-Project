# Capture the existing QNX SDK resource-manager interfaces

23 November 2026. Run on **Ubuntu only**, using the already available
qnx65-armv7-toolchain:4.9 Docker image. No BMW connection is needed.

The next design question is a process-owned manifest endpoint, whose
absence could prevent future plugin discovery when a guard dies. The car
libc exports resource-manager/dispatch functions; their presence alone is
not proof of endpoint lifetime, reader compatibility or recovery. The
observed OMAP /proc directory has only `as`, so the Linux /proc/PID/cwd or
fd approach has no observed support.

This capture obtains the exact SDK declarations/macros needed to assess a
QNX-native approach. It **does not implement or activate one**. Future code
must first be an inert, isolated prototype and prove its endpoint behavior
under normal expiry, handled signals and forced process death. No live
plugin trial is authorized by collecting these headers.

## Ubuntu commands

Save nbt-resource-api-prep.tar.gz in your Ubuntu home folder:

```sh
cd ~
tar -xzkf nbt-resource-api-prep.tar.gz
cd nbt-resource-api-prep
sha256sum -c SHA256SUMS
bash capture_resource_api.sh
```

Stop on any error. Existing output folders/archives are refused; a failed
capture preserves partial output for inspection. Do not delete or bypass
those checks to retry without reviewing the error.

Enter your Ubuntu sudo password if prompted. The script preprocesses a
small include-only C file twice with the existing QNX ARM compiler: once
for declarations and once for macros. It records compiler version and
checksums, then produces:

```text
/home/rob/nbt-qnx-resource-api-review.tar.gz
```

Upload that archive for private offline inspection. Preprocessed output
contains declarations from your installed SDK; it is not to be committed
to GitHub. The repository contains only our include list/capture script and
notes, not vendor headers. No compiler installation or toolchain change is
requested.

The script does not mount milestone-7, rebuild either plugin, create an ARM
executable, run target code, contact the BMW or change factory files. SDK
interfaces collected here are not live vehicle data. Actual plugin loading
and HMI restarts remain paused.
