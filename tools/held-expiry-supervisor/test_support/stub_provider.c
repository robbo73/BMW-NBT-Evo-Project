/* SYNTHETIC Linux host stand-in for the 586-byte endpoint. Never a target build.
 * It is NOT a resource manager: the "endpoint" is a regular file holding the
 * real body (from the unchanged large_body.c) and the trace lines are canned.
 * Mode comes from NBT_STUB_PROVIDER. Lease is 3 s instead of 10 s. */
#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include "large_body.h"

static void out(int fd, const char *text, size_t n)
{
    while (n) {
        ssize_t w = write(fd, text, n);
        if (w <= 0) _exit(90);
        text += w; n -= (size_t)w;
    }
}
static void say(const char *text) { out(1, text, strlen(text)); }
static void pause_seconds(int seconds)
{
    struct timespec t = {seconds, 0};
    while (nanosleep(&t, &t) != 0) { }
}

int main(int argc, char **argv)
{
    const char *mode = getenv("NBT_STUB_PROVIDER");
    char endpoint[96], line[256], litter[160];
    int fd;
    if (!mode) mode = "normal";
    if (argc != 2 || strcmp(argv[1], "--serve") != 0) return 2;
    if (strcmp(mode, "never_ready") == 0) { pause_seconds(600); return 0; }
    snprintf(endpoint, sizeof(endpoint), "/dev/nbt_large_endpoint_586.%ld", (long)getpid());
    nbt_body_init();
    fd = open(endpoint, O_WRONLY | O_CREAT | O_EXCL, 0444);
    if (fd < 0) return 3;
    out(fd, (const char *)nbt_body_data(), nbt_body_length());
    close(fd);
    if (strcmp(mode, "nul_before_ready") == 0) out(1, "\0", 1);
    snprintf(line, sizeof(line), "READY pid=%ld path=%s bytes=586 lease_ms=10000\n", (long)getpid(), endpoint);
    say(line);
    if (strcmp(mode, "litter") == 0) {
        snprintf(litter, sizeof(litter), "/ramdisk/mm/.nbt-held-alias-586.%ld/litter", (long)getppid());
        fd = open(litter, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (fd >= 0) close(fd);
    }
    if (strcmp(mode, "early_exit") == 0) { unlink(endpoint); return 0; }
    if (strcmp(mode, "hang") == 0) { pause_seconds(600); return 0; }
    pause_seconds(3);
    if (strcmp(mode, "keep_endpoint") != 0) unlink(endpoint);
    if (strcmp(mode, "nul_in_trace") == 0) {
        static const char with_nul[] = "TRACE_SUMMARY events=2 dropped=0\0overflow=0 elapsed_ms=10021\n";
        out(1, with_nul, sizeof(with_nul) - 1);
    }
    else {
        say("TRACE_SUMMARY events=2 dropped=0 overflow=0 elapsed_ms=10021\n");
    }
    if (strcmp(mode, "requested101") == 0)
        say("TRACE_READ index=0 before=0 requested=101 xtype=0 count=100 after=100 rc=-1\n");
    else
        say("TRACE_READ index=0 before=0 requested=100 xtype=0 count=100 after=100 rc=-1\n");
    say("TRACE_SEEK index=1 before=100 offset_bits=0000000000000000 whence=1 after=100 rc=-1\n");
    if (strcmp(mode, "no_detached") != 0) say("DETACHED reason=deadline; endpoint server exiting\n");
    if (strcmp(mode, "stderr") == 0) out(2, "synthetic provider diagnostic\n", sizeof("synthetic provider diagnostic\n") - 1);
    return strcmp(mode, "exit1") == 0 ? 1 : 0;
}
