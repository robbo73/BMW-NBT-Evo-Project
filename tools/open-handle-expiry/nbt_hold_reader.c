/* Separate 586-byte raw-fd observer. No server, XML, plugin or HMI operation. */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include "large_body.h"

static long long started;
static int clock_ms(long long *value)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return -1;
    *value = (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
    return 0;
}
/* All active output, including a blocked write, remains under a phase alarm. */
static int record(const char *format, ...)
{
    char line[256];
    size_t used = 0;
    int length;
    va_list args;
    va_start(args, format);
    length = vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    if (length < 0 || (size_t)length >= sizeof(line)) return -1;
    while (used < (size_t)length) {
        ssize_t count = write(STDOUT_FILENO, line + used, (size_t)length - used);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return -1;
        used += (size_t)count;
    }
    return 0;
}
/* Round remaining whole-run time upwards; native bound may be 1 s later. */
static int arm(unsigned phase_seconds)
{
    long long now, remaining;
    unsigned seconds;
    if (clock_ms(&now) != 0) return -1;
    remaining = 25000 - (now - started);
    if (remaining <= 0 || remaining > 25000) return -1;
    seconds = (unsigned)((remaining + 999) / 1000);
    if (seconds > phase_seconds) seconds = phase_seconds;
    alarm(seconds);
    return 0;
}
static int pid_value(const char *text, unsigned long *value)
{
    unsigned long number = 0;
    const unsigned char *p = (const unsigned char *)text;
    if (!p || *p < '1' || *p > '9') return 0;
    do {
        unsigned digit;
        if (*p < '0' || *p > '9') return 0;
        digit = *p - '0';
        if (number > (2147483647UL - digit) / 10UL) return 0;
        number = number * 10UL + digit;
    } while (*++p);
    if (number <= 1) return 0;
    *value = number;
    return 1;
}
static int elapsed(long long before, long long *duration)
{
    long long now;
    if (clock_ms(&now) != 0 || now < before) return -1;
    *duration = now - before;
    return 0;
}
static void usage(const char *name)
{
    printf("Usage: %s --hold-alias SHELL_PID PROVIDER_PID\n", name);
    puts("Revision: held-reader-1; fixed 586-byte dummy alias; help performs no file reads.");
    puts("Offline review build only. Release requires parent SIGUSR1; no provider-exit proof inside reader.");
}
int main(int argc, char **argv)
{
    unsigned long parent, provider;
    char directory[128], path[160], target[128], actual[128];
    unsigned char buffer[100];
    struct stat info;
    struct sigaction action;
    sigset_t release_set;
    siginfo_t sender;
    int fd = -1, result = 1, size, saved, received, close_result;
    ssize_t count;
    off_t offset;
    long long before, duration;

    if (argc == 1 || (argc == 2 && strcmp(argv[1], "--help") == 0)) {
        usage(argv[0]); return 0;
    }
    if (argc != 4 || strcmp(argv[1], "--hold-alias") != 0 ||
        !pid_value(argv[2], &parent) || !pid_value(argv[3], &provider) ||
        parent == provider) { usage(argv[0]); return 2; }
    if ((unsigned long)getppid() != parent) return 2;
    memset(&action, 0, sizeof(action));
    action.sa_handler = SIG_DFL;
    if (sigemptyset(&action.sa_mask) != 0 ||
        sigaction(SIGALRM, &action, NULL) != 0) return 1;
    action.sa_handler = SIG_IGN;
    if (sigaction(SIGPIPE, &action, NULL) != 0) return 1;
    /* SIGALRM must remain unblocked even if the invoking shell masked it. */
    if (sigemptyset(&release_set) != 0 || sigaddset(&release_set, SIGALRM) != 0 ||
        sigprocmask(SIG_UNBLOCK, &release_set, NULL) != 0) return 1;
    alarm(5);
    if (clock_ms(&started) != 0) return 1;
    if (sigemptyset(&release_set) != 0 || sigaddset(&release_set, SIGUSR1) != 0 ||
        sigprocmask(SIG_BLOCK, &release_set, NULL) != 0) return 1;
    action.sa_handler = SIG_DFL;
    if (sigaction(SIGUSR1, &action, NULL) != 0) return 1;
    size = snprintf(directory, sizeof(directory), "/ramdisk/mm/.nbt-held-alias-586.%lu", parent);
    if (size < 0 || (size_t)size >= sizeof(directory)) goto done;
    size = snprintf(path, sizeof(path), "%s/dummy-body.bin", directory);
    if (size < 0 || (size_t)size >= sizeof(path)) goto done;
    size = snprintf(target, sizeof(target), "/dev/nbt_large_endpoint_586.%lu", provider);
    if (size < 0 || (size_t)size >= sizeof(target)) goto done;
    if (lstat("/ramdisk/mm", &info) != 0 || !S_ISDIR(info.st_mode) ||
        lstat(directory, &info) != 0 || !S_ISDIR(info.st_mode) ||
        lstat(path, &info) != 0 || !S_ISLNK(info.st_mode)) goto done;
    count = readlink(path, actual, sizeof(actual));
    if (count != (ssize_t)strlen(target) || memcmp(actual, target, (size_t)count) != 0) goto done;
    fd = open(path, O_RDONLY);
    if (fd < 0) goto done;
    if (fstat(fd, &info) != 0 || !S_ISREG(info.st_mode) || info.st_size != 586) goto done;
    nbt_body_init();
    if (record("CONTROL_BEGIN name=read100\n") != 0) goto done;
    count = read(fd, buffer, sizeof(buffer));
    saved = count < 0 ? errno : 0;
    if (record("CONTROL_END name=read100 rc=%ld errno=%d\n", (long)count, saved) != 0) goto done;
    if (count != 100 || memcmp(buffer, nbt_body_data(), 100) != 0) goto done;
    if (record("CONTROL_BEGIN name=seek_current\n") != 0) goto done;
    offset = lseek(fd, (off_t)0, SEEK_CUR);
    saved = offset == (off_t)-1 ? errno : 0;
    if (record("CONTROL_END name=seek_current rc=%lld errno=%d\n", (long long)offset, saved) != 0 || offset != 100) goto done;
    if (arm(18) != 0 || record("HELD pid=%ld parent=%lu provider=%lu offset=100\n", (long)getpid(), parent, provider) != 0) goto done;
    do {
        memset(&sender, 0, sizeof(sender));
        received = sigwaitinfo(&release_set, &sender);
    } while (received < 0 && errno == EINTR);
    /* A reader is not entitled to infer provider death from this signal. */
    if (received != SIGUSR1 || (unsigned long)sender.si_pid != parent) goto done;
    if (arm(3) != 0 || record("RELEASED sender=%ld\n", (long)sender.si_pid) != 0) goto done;

    if (arm(3) != 0 || record("OP_BEGIN name=read64_a\n") != 0 || clock_ms(&before) != 0) goto done;
    count = read(fd, buffer, 64);
    saved = count < 0 ? errno : 0;
    if (elapsed(before, &duration) != 0 ||
        record("OP_END name=read64_a rc=%ld errno=%d elapsed_ms=%lld\n", (long)count, saved, duration) != 0) goto done;
    if (count != -1 || duration >= 3000) goto done;

    if (arm(3) != 0 || record("OP_BEGIN name=seek_start\n") != 0 || clock_ms(&before) != 0) goto done;
    offset = lseek(fd, (off_t)0, SEEK_SET);
    saved = offset == (off_t)-1 ? errno : 0;
    if (elapsed(before, &duration) != 0 ||
        record("OP_END name=seek_start rc=%lld errno=%d elapsed_ms=%lld\n", (long long)offset, saved, duration) != 0) goto done;
    if (offset != (off_t)-1 || duration >= 3000) goto done;

    if (arm(3) != 0 || record("OP_BEGIN name=read64_b\n") != 0 || clock_ms(&before) != 0) goto done;
    count = read(fd, buffer, 64);
    saved = count < 0 ? errno : 0;
    if (elapsed(before, &duration) != 0 ||
        record("OP_END name=read64_b rc=%ld errno=%d elapsed_ms=%lld\n", (long)count, saved, duration) != 0) goto done;
    if (count != -1 || duration >= 3000) goto done;
    result = 0;
done:
    if (fd >= 0) {
        if (arm(3) != 0 || record("OP_BEGIN name=close\n") != 0 || clock_ms(&before) != 0) return 1;
        close_result = close(fd);
        saved = close_result < 0 ? errno : 0;
        if (elapsed(before, &duration) != 0 ||
            record("OP_END name=close rc=%d errno=%d elapsed_ms=%lld\n", close_result, saved, duration) != 0 || duration >= 3000) return 1;
        /* close is observational: either return value is recorded, not inferred. */
    }
    if (result == 0) {
        if (arm(3) != 0 || record("OBSERVED: held-reader-1; three probes failed; requires provider/trace assessment\n") != 0) result = 1;
    } else {
        if (arm(3) == 0) (void)record("STOP: held-reader-1 incomplete or unexpected result\n");
    }
    /* Leave release blocked until exit, avoiding a late second SIGUSR1 killing us. */
    alarm(0);
    return result;
}
