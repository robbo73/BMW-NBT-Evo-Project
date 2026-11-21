/* Inert filesystem rehearsal. Never scans/links Plugins, loads a library,
 * accesses HMI, reads a payload or restarts anything. No activation mode. */
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t stopped;

static void stop_signal(int number) { stopped = number; }

static int join_path(char *out, const char *parent, const char *child)
{
    int size = snprintf(out, PATH_MAX, "%s/%s", parent, child);
    if (size < 0 || size >= PATH_MAX) {
        errno = ENAMETOOLONG;
        return -1;
    }
    return 0;
}

static int milliseconds(long long *value)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return -1;
    *value = (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
    return 0;
}

static int remove_own_link(const char *link_path, const char *target)
{
    char observed[PATH_MAX];
    ssize_t count = readlink(link_path, observed, sizeof(observed) - 1);
    if (count < 0) return errno == ENOENT ? 0 : -1;
    observed[count] = '\0';
    if (strcmp(observed, target) != 0) {
        errno = EINVAL; /* Preserve a replaced/retargeted entry. */
        return -1;
    }
    if (unlink(link_path) != 0) return -1;
    return 0;
}

static int remove_empty(const char *path)
{
    /* libc rmdir(), not the missing shell utility. Never recursive. */
    if (rmdir(path) == 0 || errno == ENOENT) return 0;
    return -1;
}

static void usage(const char *program)
{
#ifdef NBT_HOST_REHEARSAL
    printf("Usage: %s --host-rehearse /absolute/temporary/root milliseconds\n", program);
#else
    printf("Usage: %s --rehearse\n", program);
    puts("Creates dummy paths under /ramdisk/mm for a 10-second filesystem rehearsal.");
#endif
    puts("No plugin activation, library loading, HMI access or restart is implemented.");
}

int main(int argc, char **argv)
{
    const char *root;
    long lease_ms = 10000;
    char resolved[PATH_MAX], base[PATH_MAX], target[PATH_MAX], discovery[PATH_MAX];
    char link_path[PATH_MAX], name[80];
    struct stat info;
    struct sigaction action;
    struct timespec pause_time;
    long long now, deadline;
    int base_owned = 0, target_owned = 0, discovery_owned = 0, link_owned = 0;
    int failed = 0, setup_complete = 0;
    const char *reason = "setup-error";

    if (argc == 1 || (argc == 2 && strcmp(argv[1], "--help") == 0)) {
        usage(argv[0]);
        return 0;
    }
#ifdef NBT_HOST_REHEARSAL
    if (argc != 4 || strcmp(argv[1], "--host-rehearse") != 0) {
        usage(argv[0]); return 2;
    }
    {
        char *end;
        lease_ms = strtol(argv[3], &end, 10);
        if (!*argv[3] || *end || lease_ms < 100 || lease_ms > 30000) return 2;
    }
    root = argv[2];
#else
    if (argc != 2 || strcmp(argv[1], "--rehearse") != 0) {
        usage(argv[0]); return 2;
    }
#ifndef __QNXNTO__
    fputs("Target rehearsal requires a QNX build.\n", stderr);
    return 2;
#endif
    root = "/ramdisk/mm";
#endif

    /* Pin the directory before any writes; refuse links and aliases. */
    if (root[0] != '/' || lstat(root, &info) != 0 || !S_ISDIR(info.st_mode) ||
        !realpath(root, resolved) || strcmp(root, resolved) != 0) {
        fputs("STOP: expected a canonical, non-linked directory root\n", stderr);
        return 1;
    }
    memset(&action, 0, sizeof(action));
    sigemptyset(&action.sa_mask);
    action.sa_handler = stop_signal;
    if (sigaction(SIGTERM, &action, NULL) != 0 ||
        sigaction(SIGINT, &action, NULL) != 0 ||
        sigaction(SIGHUP, &action, NULL) != 0) { perror("sigaction"); return 1; }
    action.sa_handler = SIG_IGN;
    if (sigaction(SIGPIPE, &action, NULL) != 0) { perror("SIGPIPE"); return 1; }

    snprintf(name, sizeof(name), ".nbt-lease-rehearsal.%ld", (long)getpid());
    if (join_path(base, root, name) != 0 ||
        join_path(target, base, "dummy-target") != 0 ||
        join_path(discovery, base, "dummy-discovery") != 0 ||
        join_path(link_path, discovery, "DummyTrial") != 0) {
        perror("path"); return 1;
    }
    if (mkdir(base, 0700) != 0) { perror("mkdir unique base"); return 1; }
    base_owned = 1;
    if (mkdir(target, 0700) != 0) { perror("mkdir dummy target"); failed = 1; goto cleanup; }
    target_owned = 1;
    if (mkdir(discovery, 0700) != 0) { perror("mkdir dummy discovery"); failed = 1; goto cleanup; }
    discovery_owned = 1;
    if (milliseconds(&now) != 0) { perror("monotonic clock"); failed = 1; goto cleanup; }
    deadline = now + lease_ms;
    if (symlink(target, link_path) != 0) { perror("dummy link"); failed = 1; goto cleanup; }
    link_owned = 1;
    if (stat(link_path, &info) != 0 || !S_ISDIR(info.st_mode)) {
        fputs("STOP: dummy directory link did not resolve\n", stderr);
        failed = 1; goto cleanup;
    }
    setup_complete = 1;
    printf("READY pid=%ld base=%s lease_ms=%ld\n", (long)getpid(), base, lease_ms);
    fflush(stdout); /* An absent client is not a reason to abandon cleanup. */

    pause_time.tv_sec = 0;
    pause_time.tv_nsec = 20000000;
    for (;;) {
        if (stopped) { reason = "signal"; break; }
        if (milliseconds(&now) != 0) {
            perror("monotonic clock"); failed = 1; reason = "clock-error"; break;
        }
        if (now >= deadline) { reason = "deadline"; break; }
        if (nanosleep(&pause_time, NULL) != 0 && errno != EINTR) {
            perror("nanosleep"); failed = 1; reason = "sleep-error"; break;
        }
    }

cleanup:
    /* Revoke discovery before removing empty owned directories. Do not
     * unload anything, delete recursively or follow a replaced link. */
    if (link_owned && remove_own_link(link_path, target) != 0) {
        perror("STOP: could not revoke unchanged dummy link; preserving fixture");
        return 1;
    }
    if (target_owned && remove_empty(target) != 0) { perror("preserve nonempty dummy target"); failed = 1; }
    if (discovery_owned && remove_empty(discovery) != 0) { perror("preserve nonempty dummy discovery"); failed = 1; }
    if (base_owned && remove_empty(base) != 0) { perror("preserve nonempty rehearsal base"); failed = 1; }
    if (failed || !setup_complete) return 1;
    printf("REVOKED reason=%s; dummy fixture removed\n", reason);
    fflush(stdout);
    return stopped ? 2 : 0;
}
