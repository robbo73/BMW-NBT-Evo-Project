/* SYNTHETIC Linux host stand-in reader, for cases the real reader cannot produce
 * on demand. Never a target build. Mode comes from NBT_STUB_READER. It prints the
 * reader's exact HELD prefix using its real PIDs, then misbehaves as requested. */
#define _POSIX_C_SOURCE 200809L
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static void out(const char *text, size_t n)
{
    while (n) {
        ssize_t w = write(1, text, n);
        if (w <= 0) _exit(90);
        text += w; n -= (size_t)w;
    }
}
static void say(const char *text) { out(text, strlen(text)); }

int main(int argc, char **argv)
{
    const char *mode = getenv("NBT_STUB_READER");
    char line[256];
    sigset_t set;
    int got;
    struct timespec second = {1, 0};
    if (!mode) mode = "nul_after_release";
    if (argc != 4 || strcmp(argv[1], "--hold-alias") != 0) return 2;
    sigemptyset(&set);
    if (strcmp(mode, "ignore_release") == 0) sigfillset(&set);
    else sigaddset(&set, SIGUSR1);
    sigprocmask(SIG_BLOCK, &set, NULL);
    say("CONTROL_BEGIN name=read100\nCONTROL_END name=read100 rc=100 errno=0\n"
        "CONTROL_BEGIN name=seek_current\nCONTROL_END name=seek_current rc=100 errno=0\n");
    snprintf(line, sizeof(line), "HELD pid=%ld parent=%s provider=%s offset=100\n", (long)getpid(), argv[2], argv[3]);
    say(line);
    if (strcmp(mode, "die_after_held") == 0) { nanosleep(&second, NULL); return 3; }
    if (strcmp(mode, "extra_before_release") == 0) { say("unexpected extra line\n"); }
    if (strcmp(mode, "ignore_release") == 0) { for (;;) nanosleep(&second, NULL); }
    if (sigwait(&set, &got) != 0 || got != SIGUSR1) return 4;
    snprintf(line, sizeof(line), "RELEASED sender=%s\n", argv[2]);
    say(line);
    say("OP_BEGIN name=read64_a\n");
    {   /* one injected NUL; length from the literal, not hand-counted */
        static const char with_nul[] = "OP_END name=read64_a rc=-1 errno=9\0 elapsed_ms=0\n";
        out(with_nul, sizeof(with_nul) - 1);
    }
    say("OP_BEGIN name=seek_start\nOP_END name=seek_start rc=-1 errno=9 elapsed_ms=0\n"
        "OP_BEGIN name=read64_b\nOP_END name=read64_b rc=-1 errno=9 elapsed_ms=0\n"
        "OP_BEGIN name=close\nOP_END name=close rc=0 errno=0 elapsed_ms=0\n"
        "OBSERVED: held-reader-1; three probes failed; requires provider/trace assessment\n");
    return 0;
}
