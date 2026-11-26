/* held-controller-1 C supervisor, revision 2: inert 586-byte held-descriptor expiry trial.
 *
 * Offline review build. NOT run on QNX; Linux host tests do not establish QNX
 * compatibility. Emits PROPOSED held-expiry-log/1 (proposal revision 2) records
 * and never judges the trial. No plugin, XML, RPM, HMI, firmware or coding
 * operation. See ARCHITECTURE.md.
 *
 * Process roles (one executable):
 *   launcher L  = the process the caller starts. Owns S as an unreaped child,
 *                 forwards HUP/INT/TERM to S, hard-stops S at 30 s, and exits
 *                 with S's status (or a launcher code). Signals nothing else.
 *   supervisor S = the contract's controller_pid and the reader's direct parent.
 *                 Owns the provider and reader; signals only those, while unreaped.
 */
#define _POSIX_C_SOURCE 200809L
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* ---- Fixed production paths. No build or test substitutes these. ---- */
#define NBT_ROOT_PARENT "/ramdisk"
#define NBT_ROOT "/ramdisk/mm"
#define NBT_ENDPOINT_PREFIX "/dev/nbt_large_endpoint_586."
#define NBT_PROVIDER_BIN "/dev/shmem/nbt_large_endpoint_586_8f502b6394a0"
#define NBT_READER_BIN "/dev/shmem/nbt_hold_reader_586_9a54c7f4dba5"
#define NBT_REVISION "held-controller-1"

/* Host-only builds. Each refuses to compile for a QNX target. */
#if (defined(NBT_TEST_UNINTERRUPTIBLE_OUTPUT) || defined(NBT_UNIT_TEST)) && defined(__QNX__)
#error "NBT_TEST_UNINTERRUPTIBLE_OUTPUT and NBT_UNIT_TEST are Linux host-test builds only"
#endif
/* Deadlines, milliseconds from each process's own start. Only the namespace-free
 * unit build (NBT_UNIT_TEST, never a target) shortens them. */
#ifdef NBT_UNIT_TEST
enum { TRIAL_MS = NBT_UNIT_TRIAL_MS, OUTPUT_MS = NBT_UNIT_OUTPUT_MS,
       HARD_MS = NBT_UNIT_HARD_MS, SELF_KILL_MS = NBT_UNIT_SELF_KILL_MS };
#else
enum { TRIAL_MS = 25000, OUTPUT_MS = 28000, HARD_MS = 30000, SELF_KILL_MS = 31000 };
#endif
enum {
    READY_MS = 3000, HELD_MS = 3000, REAP_MS = 2000, GIVEUP_MS = 2000,
    POLL_MS = 20, REPEAT_MS = 100, WAIT_RETRIES = 64,
    CAPTURE_CAP = 4096, LOG_CAP = 65536, LINE_LIMIT = 512,
    OUTPUT_TICKS = (OUTPUT_MS - TRIAL_MS) / REPEAT_MS,   /* kernel ticks after the trial deadline */
    GIVEUP_TICKS = GIVEUP_MS / REPEAT_MS,
    REAP_ITERATIONS = REAP_MS / POLL_MS
};
/* Exit status of the launcher, i.e. of the whole controller. Only 0 may be accepted. */
enum {
    EXIT_COMPLETE = 0,            /* protocol complete, output complete and on time */
    EXIT_ABORTED = 1,             /* ABORT or WATCHDOG_FIRED recorded */
    EXIT_REFUSED = 2,             /* refused to start; no child of S was started */
    EXIT_OUTPUT = 3,              /* log incomplete, late, or its timing unverifiable */
    EXIT_LAUNCHER_WAIT_ERROR = 122, /* S collected, but launcher saw wait errors */
    EXIT_HARD_STOP = 123,         /* launcher SIGKILLed S at its hard deadline */
    EXIT_STATUS_LOST = 124,       /* ECHILD for S: S never signalled again */
    EXIT_UNCOLLECTED = 125        /* S still not collected after the hard stop bound */
    /* 128+n: S was terminated by signal n, not by the launcher */
};

enum reap_result { CHILD_RUNNING = 0, CHILD_COLLECTED = 1, CHILD_LOST = 2, CHILD_WAIT_ERROR = 3 };
struct child {
    const char *name;
    pid_t pid;
    int owned;        /* started, status not yet collected, PID still reserved for us */
    int collected;    /* waitpid returned this PID: ownership ended, status valid */
    int lost;         /* ECHILD: ownership ended without a status */
    int recorded, wait_errors, status;
};
struct capture { unsigned char data[CAPTURE_CAP + 1]; size_t len; int overflow, error; };

static struct child provider = {"PROVIDER", 0, 0, 0, 0, 0, 0, 0};
static struct child reader = {"READER", 0, 0, 0, 0, 0, 0, 0};
static struct child supervisor = {"SUPERVISOR", 0, 0, 0, 0, 0, 0, 0};   /* launcher's view */
static volatile sig_atomic_t ticks, external_signal;                    /* supervisor */
static volatile sig_atomic_t launcher_ticks, pending_hup, pending_int, pending_term;
static timer_t interrupt_timer, self_kill_timer, launcher_timer;
static int interrupt_armed, self_kill_armed, launcher_armed;
static long long start_ms;
static int clock_failed, clock_seen;
static long long last_clock_ms;
static pid_t self;
static char logbuf[LOG_CAP];
static size_t loglen;
static int log_overflow, trial_failed, abort_recorded, trial_fired, fixture_made, alias_made;
static unsigned seq;
static char fixture[128], alias_path[160], endpoint[96], ready_line[160], held_prefix[400];
static const char *const stream_name[4] = {"provider.stdout", "provider.stderr", "reader.stdout", "reader.stderr"};
static const char *const capture_file[4] = {"provider.out", "provider.err", "reader.out", "reader.err"};
static char capture_path[4][176];
static int capture_made[4], capture_w[4] = {-1, -1, -1, -1}, capture_r[4] = {-1, -1, -1, -1};
static struct capture caps[4];

static const char trace_summary[] = "TRACE_SUMMARY events=2 dropped=0 overflow=0 elapsed_ms=";
static const char trace_tail[] =
    "\nTRACE_READ index=0 before=0 requested=100 xtype=0 count=100 after=100 rc=-1\n"
    "TRACE_SEEK index=1 before=100 offset_bits=0000000000000000 whence=1 after=100 rc=-1\n"
    "DETACHED reason=deadline; endpoint server exiting\n";

#ifdef NBT_UNIT_TEST
void nbt_unit_child_body(void);
#define SUPERVISOR_ENTRY nbt_unit_child_body
#else
#define SUPERVISOR_ENTRY supervisor_main
#endif

/* ---------------- clock: explicit failure, never an invented timestamp ---------------- */
static int read_clock(long long *ms)
{
    struct timespec t;
    long long now;
    /* A transient failure must not re-enable a later release/deadline check. */
    if (clock_failed) return -1;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0) { clock_failed = 1; return -1; }
    now = (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
    if (clock_seen && now < last_clock_ms) { clock_failed = 1; return -1; }
    last_clock_ms = now;
    clock_seen = 1;
    *ms = now;
    return 0;
}
static int read_elapsed(long long *ms)
{
    long long now;
    if (read_clock(&now) != 0) return -1;
    if (now < start_ms) { clock_failed = 1; return -1; }     /* a monotonic clock went backwards */
    *ms = now - start_ms;
    return 0;
}
/* Kernel ticks decide even when clock reads are wrong; a clock failure counts as expired. */
static int trial_expired(void)
{
    long long e;
    if (ticks > 0) return 1;
    if (read_elapsed(&e) != 0) return 1;
    return e >= TRIAL_MS;
}
/* With a failed clock, output stays bounded by kernel ticks and both hard stops;
 * the exit status is already nonzero in that case (see supervisor_exit_code). */
static int output_expired(void)
{
    long long e;
    if (ticks > OUTPUT_TICKS) return 1;
    if (read_elapsed(&e) != 0) return 0;
    return e >= OUTPUT_MS;
}
static void sleep_ms(long ms)
{
    struct timespec t;
    t.tv_sec = ms / 1000;
    t.tv_nsec = (ms % 1000) * 1000000L;
    (void)nanosleep(&t, NULL);          /* EINTR simply ends the slice; no clock read needed */
}
static void close_from(int first)
{
    long max = sysconf(_SC_OPEN_MAX), fd;
    if (max < 0 || max > 4096) max = 4096;
    for (fd = first; fd < max; ++fd) (void)close((int)fd);
}
static void stop_message(const char *text)
{
    (void)!write(STDERR_FILENO, "STOP: ", 6);
    (void)!write(STDERR_FILENO, text, strlen(text));
    (void)!write(STDERR_FILENO, "\n", 1);
}

/* ---------------- log buffer (written once, at the end) ---------------- */
static void log_bytes(const void *bytes, size_t n)
{
    if (log_overflow) return;
    if (n > sizeof(logbuf) - loglen) { log_overflow = 1; return; }
    memcpy(logbuf + loglen, bytes, n);
    loglen += n;
}
static void record(const char *format, ...)
{
    char line[600];
    int head, body;
    va_list args;
    head = snprintf(line, sizeof(line), "HXC1 seq=%u ", ++seq);
    va_start(args, format);
    body = vsnprintf(line + head, sizeof(line) - (size_t)head, format, args);
    va_end(args);
    if (head < 0 || body < 0 || (size_t)head + (size_t)body + 1 >= sizeof(line)) { log_overflow = 1; return; }
    line[head + body] = '\n';
    log_bytes(line, (size_t)head + (size_t)body + 1);
}
static void abort_once(const char *reason)
{
    trial_failed = 1;
    if (abort_recorded) return;
    abort_recorded = 1;
    record("ABORT reason=%s", reason);
}

/* ---------------- child ownership (shared by launcher and supervisor) ---------------- */
static int decode_status(int raw)
{
    if (WIFEXITED(raw)) return WEXITSTATUS(raw);
    if (WIFSIGNALED(raw)) return 128 + WTERMSIG(raw) > 255 ? 255 : 128 + WTERMSIG(raw);
    return 255;
}
/* Only a returned PID ends ownership with a status. ECHILD ends ownership without
 * one (the PID is no longer reserved for us). Anything else keeps ownership. */
static enum reap_result reap_check(struct child *c)
{
    int raw = 0, tries;
    pid_t got;
    if (!c->owned) return c->lost ? CHILD_LOST : CHILD_COLLECTED;
    for (tries = 0; tries < WAIT_RETRIES; ++tries) {
        got = waitpid(c->pid, &raw, WNOHANG);
        if (got == 0) return CHILD_RUNNING;
        if (got == c->pid) {
            c->owned = 0;
            c->collected = 1;
            c->status = decode_status(raw);
            return CHILD_COLLECTED;
        }
        if (got < 0 && errno == EINTR) continue;
        if (got < 0 && errno == ECHILD) {
            c->owned = 0;
            c->lost = 1;
            return CHILD_LOST;
        }
        break;
    }
    ++c->wait_errors;
    return CHILD_WAIT_ERROR;
}
/* The only place a signal is sent to a child. */
static int signal_owned(struct child *c, int sig)
{
    if (!c->owned) { errno = ESRCH; return -1; }
    return kill(c->pid, sig);
}
static void record_reaped(struct child *c)
{
    if (!c->collected || c->recorded) return;
    c->recorded = 1;
    record("%s_REAPED pid=%ld status=%d", c->name, (long)c->pid, c->status);
}
/* Trial-time child check: 0 running, 1 collected now (recorded), -1 failure (ABORT recorded). */
static int child_event(struct child *c)
{
    switch (reap_check(c)) {
    case CHILD_RUNNING: return 0;
    case CHILD_COLLECTED: record_reaped(c); return 1;
    case CHILD_LOST: abort_once("child_status_lost"); return -1;
    default: abort_once("child_wait_error"); return -1;
    }
}

/* ---------------- signals and kernel timers ---------------- */
/* Preserve the interrupted syscall's errno, including a timer query failure.
 * Saturate before arithmetic so a large overrun cannot wrap sig_atomic_t. */
static void add_timer_ticks(volatile sig_atomic_t *counter, timer_t timer)
{
    int saved_errno = errno;
    int over = timer_getoverrun(timer);
    if (over < 0) over = 0;
    if (*counter < 1000000) {
        if (over >= 1000000 - *counter) *counter = 1000000;
        else *counter += 1 + over;
    }
    errno = saved_errno;
}
static void on_tick(int number)
{
    (void)number;
    add_timer_ticks(&ticks, interrupt_timer);
}
static void on_external(int number) { (void)number; external_signal = 1; }
static void on_launcher_tick(int number)
{
    (void)number;
    add_timer_ticks(&launcher_ticks, launcher_timer);
}
static void on_launcher_signal(int number)
{
    if (number == SIGHUP) pending_hup = 1;
    else if (number == SIGINT) pending_int = 1;
    else pending_term = 1;
}
static int set_disposition(int number, void (*handler)(int))
{
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = handler;
    action.sa_flags = 0;                /* no SA_RESTART, no SA_NOCLDWAIT */
    if (sigemptyset(&action.sa_mask) != 0) return -1;
    return sigaction(number, &action, NULL);
}
static int clear_mask(void)
{
    sigset_t none;
    if (sigemptyset(&none) != 0) return -1;
    return sigprocmask(SIG_SETMASK, &none, NULL);
}
static int arm_timer(timer_t *timer, int signo, long first_ms, long interval_ms)
{
    struct sigevent event;
    struct itimerspec when;
    memset(&event, 0, sizeof(event));
    event.sigev_notify = SIGEV_SIGNAL;
    event.sigev_signo = signo;
    if (timer_create(CLOCK_MONOTONIC, &event, timer) != 0) return -1;
    memset(&when, 0, sizeof(when));
    when.it_value.tv_sec = first_ms / 1000;
    when.it_value.tv_nsec = (first_ms % 1000) * 1000000L;
    when.it_interval.tv_sec = interval_ms / 1000;
    when.it_interval.tv_nsec = (interval_ms % 1000) * 1000000L;
    if (timer_settime(*timer, 0, &when, NULL) != 0) { (void)timer_delete(*timer); return -1; }
    return 0;
}
/* Kernel-owned hard stop addressed to this process itself: no PID, no clock read. */
static int arm_self_kill_timer(void)
{
    if (arm_timer(&self_kill_timer, SIGKILL, SELF_KILL_MS, 0) != 0) return -1;
    self_kill_armed = 1;
    return 0;
}
static void reset_child_signals(void)
{
    static const int numbers[] = {SIGHUP, SIGINT, SIGTERM, SIGALRM, SIGPIPE, SIGCHLD};
    size_t i;
    for (i = 0; i < sizeof(numbers) / sizeof(numbers[0]); ++i) (void)set_disposition(numbers[i], SIG_DFL);
    (void)clear_mask();
}
static int spawn(struct child *c, const char *path, char *const argv[], int out_fd, int err_fd)
{
    pid_t pid = fork();
    if (pid < 0) return -1;
    if (pid == 0) {
        static const char exec_failed[] = "held-supervisor: execv failed\n";
        int null_fd;
        reset_child_signals();
        null_fd = open("/dev/null", O_RDONLY);
        if (null_fd < 0 || dup2(null_fd, 0) < 0 || dup2(out_fd, 1) < 0 || dup2(err_fd, 2) < 0) _exit(126);
        close_from(3);
        execv(path, argv);
        (void)!write(2, exec_failed, sizeof(exec_failed) - 1);
        _exit(127);
    }
    c->pid = pid;
    c->owned = 1;
    return 0;
}
static const char *owned_target(void)
{
    if (provider.owned && reader.owned) return "both";
    if (provider.owned) return "provider";
    if (reader.owned) return "reader";
    return NULL;
}
/* Trial stop check: external signal, clock failure, or the trial deadline. */
static int stopped(void)
{
    if (external_signal) { abort_once("external_signal"); return 1; }
    if (trial_expired()) {
        if (clock_failed) { abort_once("clock_failure"); return 1; }
        if (!trial_fired) {
            const char *target = owned_target();
            trial_fired = 1;
            if (target) { trial_failed = 1; record("WATCHDOG_FIRED target=%s", target); }
            else abort_once("deadline_before_children");
        }
        return 1;
    }
    return 0;
}

/* ---------------- captures: raw bytes, never normalized ---------------- */
static void read_capture(int i)
{
    struct capture *c = &caps[i];
    int interrupts = 0;
    c->len = 0; c->overflow = 0; c->error = 0;
    if (capture_r[i] < 0) { c->error = 1; return; }
    while (c->len < sizeof(c->data)) {
        ssize_t n = pread(capture_r[i], c->data + c->len, sizeof(c->data) - c->len, (off_t)c->len);
        if (n < 0) {
            if (errno == EINTR && ++interrupts < WAIT_RETRIES && !output_expired()) continue;
            c->error = 1;
            return;
        }
        if (n == 0) break;
        c->len += (size_t)n;
    }
    if (c->len > CAPTURE_CAP) { c->overflow = 1; c->len = CAPTURE_CAP; }
}
static void read_all(void) { int i; for (i = 0; i < 4; ++i) read_capture(i); }
static int frameable(const struct capture *c)
{
    size_t i, line = 0;
    if (c->error || c->overflow) return 0;
    for (i = 0; i < c->len; ++i) {
        unsigned char b = c->data[i];
        if (b == '\n') {
            if (i - line > LINE_LIMIT) return 0;
            if (i - line >= 5 && memcmp(c->data + line, "HXC1 ", 5) == 0) return 0;
            line = i + 1;
        } else if (b < 0x20 || b > 0x7e) {
            return 0;
        }
    }
    return c->len == 0 || c->data[c->len - 1] == '\n';
}
static int is_empty(const struct capture *c) { return !c->error && !c->overflow && c->len == 0; }
static int is_exact(const struct capture *c, const char *expected)
{
    size_t n = strlen(expected);
    return !c->error && !c->overflow && c->len == n && memcmp(c->data, expected, n) == 0;
}
static int is_prefix(const struct capture *c, const char *expected)
{
    return !c->error && !c->overflow && c->len <= strlen(expected) && memcmp(c->data, expected, c->len) == 0;
}
static int control_trace_ok(const struct capture *c)
{
    size_t at, digits = 0, rl = strlen(ready_line), sl = sizeof(trace_summary) - 1, tl = sizeof(trace_tail) - 1;
    if (!frameable(c) || c->len < rl + sl + 1 + tl) return 0;
    if (memcmp(c->data, ready_line, rl) != 0 || memcmp(c->data + rl, trace_summary, sl) != 0) return 0;
    at = rl + sl;
    while (at + digits < c->len && c->data[at + digits] >= '0' && c->data[at + digits] <= '9') ++digits;
    if (digits < 5 || digits > 19 || c->data[at] == '0') return 0;
    if (digits == 5 && memcmp(c->data + at, "10000", 5) < 0) return 0;
    if (digits == 19 && memcmp(c->data + at, "9223372036854775807", 19) > 0) return 0;
    at += digits;
    return c->len - at == tl && memcmp(c->data + at, trace_tail, tl) == 0;
}
static int endpoint_absent(void)
{
    struct stat info;
    char target[128];
    ssize_t n;
    errno = 0;
    if (lstat(endpoint, &info) == 0 || errno != ENOENT) return 0;
    if (lstat(alias_path, &info) != 0 || !S_ISLNK(info.st_mode)) return 0;
    n = readlink(alias_path, target, sizeof(target));
    if (n < 0 || (size_t)n != strlen(endpoint) || memcmp(target, endpoint, (size_t)n) != 0) return 0;
    errno = 0;
    return stat(alias_path, &info) != 0 && errno == ENOENT;
}

/* ---------------- the trial (supervisor) ---------------- */
static int open_captures(void)
{
    int i;
    for (i = 0; i < 4; ++i) {
        int size = snprintf(capture_path[i], sizeof(capture_path[i]), "%s/%s", fixture, capture_file[i]);
        if (size < 0 || (size_t)size >= sizeof(capture_path[i])) return -1;
        capture_w[i] = open(capture_path[i], O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (capture_w[i] < 0) return -1;
        capture_made[i] = 1;
        capture_r[i] = open(capture_path[i], O_RDONLY);
        if (capture_r[i] < 0 || fcntl(capture_w[i], F_SETFD, FD_CLOEXEC) != 0 ||
            fcntl(capture_r[i], F_SETFD, FD_CLOEXEC) != 0) return -1;
    }
    return 0;
}
static void close_writer(int i) { if (capture_w[i] >= 0) { (void)close(capture_w[i]); capture_w[i] = -1; } }
static int elapsed_at_least(long long until)
{
    long long e;
    return read_elapsed(&e) != 0 || e >= until;
}
/* Final gate: checks, reads, then the deadline again after the reads, then release. */
static int final_release_gate(void)
{
    int event;
    if (stopped()) return -1;
    event = child_event(&reader);
    if (event < 0) return -1;
    if (event == 1) { abort_once("reader_exited_early"); return -1; }
    read_capture(2); read_capture(3);
    if (!is_exact(&caps[2], held_prefix) || !is_empty(&caps[3])) { abort_once("reader_output_unexpected"); return -1; }
    if (stopped()) return -1;                 /* a read that completed late cannot release */
    if (signal_owned(&reader, SIGUSR1) != 0) { abort_once("release_failed"); return -1; }
    record("RELEASE_SENT reader=%ld signal=USR1", (long)reader.pid);
    return 0;
}

static int run_trial(void)
{
    struct stat info;
    char cpid[16], ppid[16], target[128];
    char *provider_argv[3], *reader_argv[5];
    long long until = 0;
    ssize_t n;
    int event;

    if (mkdir(fixture, 0700) != 0) { abort_once("fixture_create"); return -1; }
    fixture_made = 1;
    if (lstat(fixture, &info) != 0 || !S_ISDIR(info.st_mode)) { abort_once("fixture_create"); return -1; }
    if (open_captures() != 0) { abort_once("capture_create"); return -1; }
    if (stopped()) return -1;

    provider_argv[0] = (char *)NBT_PROVIDER_BIN; provider_argv[1] = (char *)"--serve"; provider_argv[2] = NULL;
    if (spawn(&provider, NBT_PROVIDER_BIN, provider_argv, capture_w[0], capture_w[1]) != 0) {
        abort_once("provider_spawn"); return -1;
    }
    close_writer(0); close_writer(1);
    record("PROVIDER_STARTED pid=%ld", (long)provider.pid);
    if (snprintf(endpoint, sizeof(endpoint), "%s%ld", NBT_ENDPOINT_PREFIX, (long)provider.pid) >= (int)sizeof(endpoint) ||
        snprintf(ready_line, sizeof(ready_line), "READY pid=%ld path=%s bytes=586 lease_ms=10000\n",
                 (long)provider.pid, endpoint) >= (int)sizeof(ready_line)) { abort_once("format"); return -1; }

    if (read_elapsed(&until) == 0) until += READY_MS;
    for (;;) {                                       /* READY: exact line, nothing else */
        if (stopped()) return -1;
        event = child_event(&provider);
        if (event < 0) return -1;
        if (event == 1) { abort_once("provider_exited_early"); return -1; }
        read_capture(0); read_capture(1);
        if (!is_empty(&caps[1])) { abort_once("provider_stderr"); return -1; }
        if (!is_prefix(&caps[0], ready_line)) { abort_once("provider_output_unexpected"); return -1; }
        if (is_exact(&caps[0], ready_line)) break;
        if (elapsed_at_least(until)) { abort_once("provider_not_ready"); return -1; }
        sleep_ms(POLL_MS);
    }
    record("PROVIDER_READY pid=%ld path=%s", (long)provider.pid, endpoint);

    /* No stat of the live endpoint: the supervisor never sends requests to the provider. */
    if (symlink(endpoint, alias_path) != 0) { abort_once("alias_create"); return -1; }
    alias_made = 1;
    n = readlink(alias_path, target, sizeof(target));
    if (lstat(alias_path, &info) != 0 || !S_ISLNK(info.st_mode) || n < 0 ||
        (size_t)n != strlen(endpoint) || memcmp(target, endpoint, (size_t)n) != 0) { abort_once("alias_create"); return -1; }
    record("ALIAS_CREATED path=%s target=%s", alias_path, endpoint);
    if (stopped()) return -1;

    (void)snprintf(cpid, sizeof(cpid), "%ld", (long)self);
    (void)snprintf(ppid, sizeof(ppid), "%ld", (long)provider.pid);
    reader_argv[0] = (char *)NBT_READER_BIN; reader_argv[1] = (char *)"--hold-alias";
    reader_argv[2] = cpid; reader_argv[3] = ppid; reader_argv[4] = NULL;
    if (spawn(&reader, NBT_READER_BIN, reader_argv, capture_w[2], capture_w[3]) != 0) {
        abort_once("reader_spawn"); return -1;
    }
    close_writer(2); close_writer(3);
    record("READER_STARTED pid=%ld parent=%ld provider=%ld", (long)reader.pid, (long)self, (long)provider.pid);
    if (snprintf(held_prefix, sizeof(held_prefix),
                 "CONTROL_BEGIN name=read100\nCONTROL_END name=read100 rc=100 errno=0\n"
                 "CONTROL_BEGIN name=seek_current\nCONTROL_END name=seek_current rc=100 errno=0\n"
                 "HELD pid=%ld parent=%ld provider=%ld offset=100\n",
                 (long)reader.pid, (long)self, (long)provider.pid) >= (int)sizeof(held_prefix)) {
        abort_once("format"); return -1;
    }

    if (read_elapsed(&until) == 0) until += HELD_MS;
    for (;;) {                                       /* HELD: exact five-line prefix */
        if (stopped()) return -1;
        event = child_event(&reader);
        if (event < 0) return -1;
        if (event == 1) { abort_once("reader_exited_early"); return -1; }
        event = child_event(&provider);
        if (event < 0) return -1;
        if (event == 1) { abort_once("provider_exited_early"); return -1; }
        read_all();
        if (!is_empty(&caps[1])) { abort_once("provider_stderr"); return -1; }
        if (!is_exact(&caps[0], ready_line)) { abort_once("provider_output_unexpected"); return -1; }
        if (!is_empty(&caps[3])) { abort_once("reader_stderr"); return -1; }
        if (!is_prefix(&caps[2], held_prefix)) { abort_once("reader_output_unexpected"); return -1; }
        if (is_exact(&caps[2], held_prefix)) break;
        if (elapsed_at_least(until)) { abort_once("held_not_observed"); return -1; }
        sleep_ms(POLL_MS);
    }
    record("HELD_OBSERVED reader=%ld", (long)reader.pid);

    for (;;) {                                       /* hold until the provider exits */
        if (stopped()) return -1;
        event = child_event(&reader);
        if (event < 0) return -1;
        if (event == 1) { abort_once("reader_exited_early"); return -1; }
        read_capture(2); read_capture(3);
        if (!is_exact(&caps[2], held_prefix) || !is_empty(&caps[3])) { abort_once("reader_output_unexpected"); return -1; }
        event = child_event(&provider);              /* records PROVIDER_REAPED when collected */
        if (event < 0) return -1;
        if (event == 1) break;
        sleep_ms(POLL_MS);
    }
    if (provider.status != 0) { abort_once("provider_abnormal_exit"); return -1; }
    if (!endpoint_absent()) { abort_once("endpoint_present"); return -1; }
    record("ENDPOINT_ABSENT path=%s alias=dangling", endpoint);
    read_capture(0); read_capture(1);
    if (!control_trace_ok(&caps[0]) || !is_empty(&caps[1])) { abort_once("control_trace_invalid"); return -1; }
    if (stopped()) return -1;
    record("CONTROL_TRACE_OK provider=%ld events=2", (long)provider.pid);
    if (final_release_gate() != 0) return -1;

    for (;;) {                                       /* probes run under the reader's own alarms */
        if (stopped()) return -1;
        event = child_event(&reader);                /* records READER_REAPED when collected */
        if (event < 0) return -1;
        if (event == 1) break;
        sleep_ms(POLL_MS);
    }
    return 0;
}

/* SIGKILL every still-owned child, then collect for a bounded number of polls.
 * Iteration-counted, so it ends even when the clock has failed. */
static int force_collect_children(void)
{
    int i;
    if (provider.owned) (void)signal_owned(&provider, SIGKILL);
    if (reader.owned) (void)signal_owned(&reader, SIGKILL);
    for (i = 0; i < REAP_ITERATIONS && (provider.owned || reader.owned); ++i) {
        if (provider.owned) (void)reap_check(&provider);
        if (reader.owned) (void)reap_check(&reader);
        if (output_expired()) break;
        if (provider.owned || reader.owned) sleep_ms(POLL_MS);
    }
    record_reaped(&provider);
    record_reaped(&reader);
    if (provider.lost || reader.lost) abort_once("child_status_lost");
    if (provider.wait_errors || reader.wait_errors) abort_once("child_wait_error");
    if (provider.owned || reader.owned) abort_once("child_unreaped");
    /* Fixture may be cleaned only when every child's status was collected. */
    return !(provider.owned || reader.owned || provider.lost || reader.lost);
}

static int cleanup_fixture(void)
{
    struct stat info;
    DIR *dir;
    struct dirent *entry;
    int i;
    for (i = 0; i < 4; ++i) {
        close_writer(i);
        if (capture_r[i] >= 0) { (void)close(capture_r[i]); capture_r[i] = -1; }
    }
    if (lstat(NBT_ROOT, &info) != 0 || !S_ISDIR(info.st_mode)) return -1;
    if (lstat(fixture, &info) != 0 || !S_ISDIR(info.st_mode)) return -1;
    if (alias_made) {
        if (lstat(alias_path, &info) != 0 || !S_ISLNK(info.st_mode) || unlink(alias_path) != 0) return -1;
    }
    for (i = 0; i < 4; ++i) {
        if (!capture_made[i]) continue;
        if (lstat(capture_path[i], &info) != 0 || !S_ISREG(info.st_mode) || unlink(capture_path[i]) != 0) return -1;
    }
    dir = opendir(fixture);
    if (!dir) return -1;
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") != 0 && strcmp(entry->d_name, "..") != 0) { (void)closedir(dir); return -1; }
    }
    (void)closedir(dir);
    if (rmdir(fixture) != 0) return -1;
    errno = 0;
    return lstat(fixture, &info) != 0 && errno == ENOENT ? 0 : -1;
}

/* After cleanup: WATCHDOG_CANCELLED only if the trial deadline still has not
 * expired (clock and kernel ticks). Output deadline and hard stops stay armed. */
static void record_watchdog_status(void)
{
    if (trial_fired) return;
    if (trial_expired()) abort_once(clock_failed ? "clock_failure" : "deadline_during_cleanup");
    else record("WATCHDOG_CANCELLED");
}

/* The deadline is checked before every write and after every successful write,
 * so a write that completes after OUTPUT_MS is a failure even if the whole log
 * was delivered. The caller must gate acceptance on the exit status. */
static int write_log(void)
{
    size_t done = 0;
#ifdef NBT_TEST_UNINTERRUPTIBLE_OUTPUT
    sigset_t blocked;
    (void)sigemptyset(&blocked);
    (void)sigaddset(&blocked, SIGALRM);
    (void)sigprocmask(SIG_BLOCK, &blocked, NULL);
#endif
    while (done < loglen) {
        ssize_t n;
#ifndef NBT_TEST_UNINTERRUPTIBLE_OUTPUT
        if (output_expired()) return -1;
#endif
        n = write(STDOUT_FILENO, logbuf + done, loglen - done);
        if (n > 0) {
            done += (size_t)n;
#ifndef NBT_TEST_UNINTERRUPTIBLE_OUTPUT
            if (output_expired()) return -1;
#endif
            continue;
        }
        if (n < 0 && errno == EINTR) continue;
        return -1;                                  /* EPIPE (SIGPIPE ignored) or other error */
    }
    return 0;
}
static int supervisor_exit_code(int output_ok)
{
    if (!output_ok) return EXIT_OUTPUT;
    if (trial_failed) return EXIT_ABORTED;
    if (clock_failed) return EXIT_OUTPUT;          /* timing of the delivered log unverifiable */
    return EXIT_COMPLETE;
}

static void finish_and_exit(void)
{
    int settled, i, output_ok;
    settled = force_collect_children();
    if (fixture_made) {
        read_all();
        for (i = 0; i < 4; ++i) if (!frameable(&caps[i])) abort_once("capture_invalid");
        for (i = 0; i < 4; ++i) {
            record("SECTION_BEGIN stream=%s bytes=%lu", stream_name[i], (unsigned long)caps[i].len);
            log_bytes(caps[i].data, caps[i].len);
            record("SECTION_END stream=%s", stream_name[i]);
        }
        if (settled) {
            if (cleanup_fixture() == 0) record("FIXTURE_CLEANED path=%s", fixture);
            else abort_once("cleanup_failed");
        }
    }
    record_watchdog_status();
    record("END result=%s", trial_failed ? "aborted" : "complete");
    output_ok = !log_overflow && write_log() == 0;
    if (interrupt_armed) (void)timer_delete(interrupt_timer);
    if (self_kill_armed) (void)timer_delete(self_kill_timer);
    _exit(supervisor_exit_code(output_ok));
}

static void ensure_standard_descriptors(void)
{
    int fd;
    for (fd = 0; fd <= 2; ++fd) {
        if (fcntl(fd, F_GETFD) == -1 && errno == EBADF) {
            int opened = open("/dev/null", O_RDWR);
            if (opened >= 0 && opened != fd) { (void)dup2(opened, fd); (void)close(opened); }
        }
    }
}
static int preflight(void)
{
    struct stat info;
    const char *bins[2] = {NBT_PROVIDER_BIN, NBT_READER_BIN};
    int i;
    if (lstat(NBT_ROOT_PARENT, &info) != 0 || !S_ISDIR(info.st_mode) ||
        lstat(NBT_ROOT, &info) != 0 || !S_ISDIR(info.st_mode)) { stop_message("RAM root unavailable or linked"); return -1; }
    for (i = 0; i < 2; ++i) {
        if (lstat(bins[i], &info) != 0 || !S_ISREG(info.st_mode) || access(bins[i], X_OK) != 0) {
            stop_message("pinned RAM executable unavailable"); return -1;
        }
    }
    return 0;
}
static int setup_supervisor_signals(void)
{
    if (set_disposition(SIGCHLD, SIG_DFL) != 0 || set_disposition(SIGPIPE, SIG_IGN) != 0 ||
        set_disposition(SIGALRM, on_tick) != 0 || set_disposition(SIGHUP, on_external) != 0 ||
        set_disposition(SIGINT, on_external) != 0 || set_disposition(SIGTERM, on_external) != 0) return -1;
    return clear_mask();
}

/* Supervisor S. Timers come first so that startup work is covered as well. */
static void supervisor_main(void)
{
    long long now;
    if (arm_self_kill_timer() != 0) { stop_message("self hard-stop timer unavailable"); _exit(EXIT_REFUSED); }
    if (setup_supervisor_signals() != 0) { stop_message("signal setup"); _exit(EXIT_REFUSED); }
    if (arm_timer(&interrupt_timer, SIGALRM, TRIAL_MS, REPEAT_MS) != 0) {
        stop_message("interrupt timer unavailable"); _exit(EXIT_REFUSED);
    }
    interrupt_armed = 1;
    if (read_clock(&now) != 0) { stop_message("monotonic clock unavailable at startup"); _exit(EXIT_REFUSED); }
    start_ms = now;
    ensure_standard_descriptors();
    (void)umask(077);
    if (preflight() != 0) _exit(EXIT_REFUSED);
    self = getpid();
    if (snprintf(fixture, sizeof(fixture), "%s/.nbt-held-alias-586.%ld", NBT_ROOT, (long)self) >= (int)sizeof(fixture) ||
        snprintf(alias_path, sizeof(alias_path), "%s/dummy-body.bin", fixture) >= (int)sizeof(alias_path)) {
        stop_message("path formatting"); _exit(EXIT_REFUSED);
    }
    record("BEGIN contract=held-expiry-log/1 controller=" NBT_REVISION " controller_pid=%ld provider_bin="
           NBT_PROVIDER_BIN " reader_bin=" NBT_READER_BIN " fixture=%s", (long)self, fixture);
    (void)run_trial();
    finish_and_exit();
}

/* Launcher L. Never reads the clock for a deadline: kernel ticks only. */
static int launcher_main(void)
{
    long long probe;
    int killed = 0;
    pid_t pid;
    if (set_disposition(SIGCHLD, SIG_DFL) != 0 || set_disposition(SIGPIPE, SIG_IGN) != 0 ||
        set_disposition(SIGALRM, on_launcher_tick) != 0 || set_disposition(SIGHUP, on_launcher_signal) != 0 ||
        set_disposition(SIGINT, on_launcher_signal) != 0 || set_disposition(SIGTERM, on_launcher_signal) != 0 ||
        clear_mask() != 0) { stop_message("launcher signal setup"); return EXIT_REFUSED; }
    if (read_clock(&probe) != 0) { stop_message("monotonic clock unavailable at startup"); return EXIT_REFUSED; }
    if (arm_timer(&launcher_timer, SIGALRM, HARD_MS, REPEAT_MS) != 0) {
        stop_message("launcher hard-stop timer unavailable"); return EXIT_REFUSED;
    }
    launcher_armed = 1;
    pid = fork();
    if (pid < 0) { (void)timer_delete(launcher_timer); stop_message("supervisor fork"); return EXIT_REFUSED; }
    if (pid == 0) { SUPERVISOR_ENTRY(); _exit(EXIT_REFUSED); }
    supervisor.pid = pid;
    supervisor.owned = 1;
    for (;;) {
        enum reap_result r = reap_check(&supervisor);
        if (r == CHILD_COLLECTED) break;
        if (r == CHILD_LOST) { (void)timer_delete(launcher_timer); return EXIT_STATUS_LOST; }
        /* CHILD_RUNNING or CHILD_WAIT_ERROR: ownership retained either way. */
        if (pending_hup) { pending_hup = 0; (void)signal_owned(&supervisor, SIGHUP); }
        if (pending_int) { pending_int = 0; (void)signal_owned(&supervisor, SIGINT); }
        if (pending_term) { pending_term = 0; (void)signal_owned(&supervisor, SIGTERM); }
        if (launcher_ticks > 0 && !killed) { killed = 1; (void)signal_owned(&supervisor, SIGKILL); }
        if (killed && launcher_ticks > GIVEUP_TICKS) { (void)timer_delete(launcher_timer); return EXIT_UNCOLLECTED; }
        sleep_ms(POLL_MS);
    }
    (void)timer_delete(launcher_timer);
    if (killed) return EXIT_HARD_STOP;
    if (supervisor.wait_errors) return EXIT_LAUNCHER_WAIT_ERROR;
    return supervisor.status;
}

static void usage(const char *name)
{
    printf("Usage: %s --trial\n", name);
    puts("Revision: " NBT_REVISION " (C launcher + supervisor, revision 2); default/help does nothing.");
    puts("Inert dummy held-descriptor expiry trial; no plugin, XML, RPM or HMI operation.");
    puts("Accept an assessor PASS only when this program exits 0.");
#ifdef NBT_TEST_UNINTERRUPTIBLE_OUTPUT
    puts("HOST TEST BUILD: uninterruptible output (hard-stop test); not a target build.");
#endif
}

int main(int argc, char **argv)
{
    if (argc == 1 || (argc == 2 && strcmp(argv[1], "--help") == 0)) { usage(argv[0]); return 0; }
    if (argc != 2 || strcmp(argv[1], "--trial") != 0) { usage(argv[0]); return EXIT_REFUSED; }
    return launcher_main();
}
