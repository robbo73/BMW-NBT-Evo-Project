/* SYNTHETIC Linux host fault unit. Never a target build (the included source
 * refuses NBT_UNIT_TEST with __QNX__). Includes the unchanged supervisor source,
 * routing clock_gettime, waitpid, write, kill, pread and fork through wrappers
 * whose faults are selected per scenario. No production path is used: in-process
 * scenarios call individual functions; launcher scenarios fork real stand-in
 * supervisor bodies chosen by NBT_UNIT_CHILD. Timing is shortened only here. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define NBT_UNIT_TEST 1
#define NBT_UNIT_TRIAL_MS 400
#define NBT_UNIT_OUTPUT_MS 700
#define NBT_UNIT_HARD_MS 1000
#define NBT_UNIT_SELF_KILL_MS 1500

int unit_clock_gettime(clockid_t id, struct timespec *t);
int unit_timer_getoverrun(timer_t timer);
pid_t unit_waitpid(pid_t pid, int *status, int flags);
ssize_t unit_write(int fd, const void *data, size_t length);
int unit_kill(pid_t pid, int sig);
ssize_t unit_pread(int fd, void *data, size_t length, off_t offset);
pid_t unit_fork(void);
#define timer_getoverrun unit_timer_getoverrun
#define clock_gettime unit_clock_gettime
#define waitpid unit_waitpid
#define write unit_write
#define kill unit_kill
#define pread unit_pread
#define fork unit_fork
#define main nbt_program_main
#include NBT_SUPERVISOR_SOURCE
#undef main
#undef timer_getoverrun
#undef clock_gettime
#undef waitpid
#undef write
#undef kill
#undef pread
#undef fork

/* ---- fault state ---- */
static enum { CLOCK_REAL, CLOCK_FAIL, CLOCK_FAKE } clock_mode = CLOCK_REAL;
static long long fake_now;
static int overrun_injected, overrun_value;
static enum { WAIT_REAL, WAIT_RUNNING, WAIT_ECHILD, WAIT_EIO, WAIT_EINTR_THEN_EXIT0, WAIT_EIO_THEN_REAL } wait_mode = WAIT_REAL;
static int wait_countdown;
static enum { WRITE_REAL, WRITE_LATE, WRITE_ONTIME, WRITE_HALF_LATE } write_mode = WRITE_REAL;
static int kill_record_only;
static int kill_calls, kill_usr1, kill_kill;
static enum { PREAD_REAL, PREAD_HELD, PREAD_HELD_TICK } pread_mode = PREAD_REAL;

static void note(const char *text) { (void)!write(2, text, strlen(text)); }

int unit_timer_getoverrun(timer_t timer)
{
    if (!overrun_injected) return timer_getoverrun(timer);
    errno = EINVAL; return overrun_value;
}
int unit_clock_gettime(clockid_t id, struct timespec *t)
{
    if (clock_mode == CLOCK_FAIL) { errno = EINVAL; return -1; }
    if (clock_mode == CLOCK_FAKE) {
        t->tv_sec = (time_t)(fake_now / 1000);
        t->tv_nsec = (long)(fake_now % 1000) * 1000000L;
        return 0;
    }
    return clock_gettime(id, t);
}
pid_t unit_waitpid(pid_t pid, int *status, int flags)
{
    switch (wait_mode) {
    case WAIT_RUNNING: return 0;
    case WAIT_ECHILD: errno = ECHILD; return -1;
    case WAIT_EIO: errno = EIO; return -1;
    case WAIT_EINTR_THEN_EXIT0:
        if (wait_countdown-- > 0) { errno = EINTR; return -1; }
        *status = 0;                       /* WIFEXITED, status 0 */
        return pid;
    case WAIT_EIO_THEN_REAL:
        if (wait_countdown-- > 0) { errno = EIO; return -1; }
        return waitpid(pid, status, flags);
    default: return waitpid(pid, status, flags);
    }
}
ssize_t unit_write(int fd, const void *data, size_t length)
{
    if (fd == 1 && write_mode == WRITE_LATE) { fake_now = OUTPUT_MS + 100; return (ssize_t)length; }
    if (fd == 1 && write_mode == WRITE_ONTIME) { fake_now = OUTPUT_MS - 1; return (ssize_t)length; }
    if (fd == 1 && write_mode == WRITE_HALF_LATE) { fake_now = OUTPUT_MS + 100; return (ssize_t)(length / 2 ? length / 2 : 1); }
    return write(fd, data, length);
}
int unit_kill(pid_t pid, int sig)
{
    char line[80];
    ++kill_calls;
    if (sig == SIGUSR1) ++kill_usr1;
    if (sig == SIGKILL) ++kill_kill;
    snprintf(line, sizeof(line), "UNIT_KILL pid=%ld sig=%d\n", (long)pid, sig);
    note(line);
    if (kill_record_only) return 0;
    return kill(pid, sig);
}
ssize_t unit_pread(int fd, void *data, size_t length, off_t offset)
{
    const char *content = NULL;
    size_t n;
    if (pread_mode == PREAD_REAL) return pread(fd, data, length, offset);
    if (fd == 102) content = held_prefix;
    else content = "";
    if (pread_mode == PREAD_HELD_TICK) ticks = 1;      /* the deadline passes during the read */
    n = strlen(content);
    if ((size_t)offset >= n) return 0;
    n -= (size_t)offset;
    if (n > length) n = length;
    memcpy(data, content + offset, n);
    return (ssize_t)n;
}
pid_t unit_fork(void) { note("UNIT_FORK\n"); return fork(); }

/* ---- stand-in supervisor bodies for launcher process scenarios ---- */
static void write_pid_file(void)
{
    const char *path = getenv("NBT_UNIT_READY");
    FILE *f;
    if (!path) return;
    f = fopen(path, "w");
    if (f) { fprintf(f, "%ld\n", (long)getpid()); fclose(f); }
}
static void block_everything_and_sleep(void)
{
    sigset_t all;
    sigfillset(&all);
    sigprocmask(SIG_BLOCK, &all, NULL);
    for (;;) sleep_ms(1000);
}
static int record_fd = -1;
static void on_recorded(int number)
{
    char c = (char)('0' + number % 10), d = (char)('0' + number / 10);
    if (record_fd >= 0) { (void)!write(record_fd, &d, 1); (void)!write(record_fd, &c, 1); (void)!write(record_fd, "\n", 1); }
    if (number == SIGTERM) _exit(1);
}
void nbt_unit_child_body(void)
{
    const char *body = getenv("NBT_UNIT_CHILD");
    clock_mode = CLOCK_REAL; wait_mode = WAIT_REAL; kill_record_only = 0;   /* faults are the launcher's */
    if (!body) _exit(99);
    if (strncmp(body, "exit:", 5) == 0) { write_pid_file(); _exit(atoi(body + 5)); }
    if (strncmp(body, "signal:", 7) == 0) {
        int number = atoi(body + 7);
        write_pid_file();
        signal(number, SIG_DFL);
        raise(number);
        _exit(98);
    }
    if (strcmp(body, "hang") == 0) { write_pid_file(); block_everything_and_sleep(); }
    if (strcmp(body, "selfkill") == 0) {
        if (arm_self_kill_timer() != 0) _exit(97);
        write_pid_file();
        block_everything_and_sleep();
    }
    if (strcmp(body, "record_signals") == 0) {
        pid_t grandchild;
        record_fd = open(getenv("NBT_UNIT_RECORD"), O_WRONLY | O_CREAT | O_APPEND, 0600);
        grandchild = fork();
        if (grandchild == 0) {           /* records any signal it ever receives */
            int null_fd = open("/dev/null", O_RDWR);   /* do not hold the test's pipes open */
            if (null_fd >= 0) { dup2(null_fd, 0); dup2(null_fd, 1); dup2(null_fd, 2); }
            record_fd = open(getenv("NBT_UNIT_GRANDCHILD_RECORD"), O_WRONLY | O_CREAT | O_APPEND, 0600);
            set_disposition(SIGHUP, on_recorded); set_disposition(SIGINT, on_recorded);
            set_disposition(SIGTERM, on_recorded); set_disposition(SIGUSR1, on_recorded);
            for (;;) pause();
        }
        {
            const char *gpath = getenv("NBT_UNIT_GRANDCHILD_PID");
            FILE *f = gpath ? fopen(gpath, "w") : NULL;
            if (f) { fprintf(f, "%ld\n", (long)grandchild); fclose(f); }
        }
        set_disposition(SIGHUP, on_recorded); set_disposition(SIGINT, on_recorded); set_disposition(SIGTERM, on_recorded);
        clear_mask();
        write_pid_file();
        for (;;) pause();
    }
    if (strcmp(body, "supervisor") == 0) supervisor_main();
    _exit(96);
}

/* ---- in-process scenarios ---- */
static void reset(void)
{
    clock_mode = CLOCK_FAKE; fake_now = 1000; start_ms = 1000; clock_failed = 0; clock_seen = 0; last_clock_ms = 0; ticks = 0;
    wait_mode = WAIT_REAL; write_mode = WRITE_REAL; pread_mode = PREAD_REAL;
    kill_record_only = 1; kill_calls = kill_usr1 = kill_kill = 0;
    loglen = 0; seq = 0; log_overflow = 0; trial_failed = 0; abort_recorded = 0; trial_fired = 0; external_signal = 0;
    memset(&provider, 0, sizeof(provider)); provider.name = "PROVIDER";
    memset(&reader, 0, sizeof(reader)); reader.name = "READER";
}
static int log_has(const char *text)
{
    size_t n = strlen(text), i;
    for (i = 0; i + n <= loglen; ++i) if (memcmp(logbuf + i, text, n) == 0) return 1;
    return 0;
}
static void print_log_flags(void)
{
    printf("\"trial_failed\":%d,\"clock_failed\":%d,\"kill_calls\":%d,\"kill_usr1\":%d,\"kill_kill\":%d,"
           "\"abort_clock\":%d,\"abort_wait_error\":%d,\"abort_lost\":%d,\"abort_unreaped\":%d,"
           "\"watchdog_reader\":%d,\"watchdog_provider\":%d,\"watchdog_cancelled\":%d,\"abort_cleanup_deadline\":%d,"
           "\"release_sent\":%d}\n",
           trial_failed, clock_failed, kill_calls, kill_usr1, kill_kill,
           log_has("ABORT reason=clock_failure"), log_has("ABORT reason=child_wait_error"),
           log_has("ABORT reason=child_status_lost"), log_has("ABORT reason=child_unreaped"),
           log_has("WATCHDOG_FIRED target=reader"), log_has("WATCHDOG_FIRED target=provider"),
           log_has("WATCHDOG_CANCELLED"), log_has("ABORT reason=deadline_during_cleanup"),
           log_has("RELEASE_SENT"));
}
static int in_process(const char *name)
{
    reset();
    printf("{\"scenario\":\"%s\",", name);
    if (strcmp(name, "clock_recovers_after_failure") == 0) {
        int first, recovered;
        clock_mode = CLOCK_FAIL; first = trial_expired();
        clock_mode = CLOCK_FAKE; fake_now = 1100; recovered = trial_expired();
        printf("\"first_expired\":%d,\"recovered_expired\":%d,\"stopped\":%d,", first, recovered, stopped());
    } else if (strcmp(name, "clock_backwards_after_good_read") == 0) {
        long long first = 0, second = 0; int r1, r2;
        fake_now = 1200; r1 = read_elapsed(&first);
        fake_now = 1150; r2 = read_elapsed(&second);
        printf("\"first_result\":%d,\"second_result\":%d,", r1, r2);
    } else if (strcmp(name, "handler_preserves_errno") == 0) {
        int supervisor_errno, launcher_errno;
        overrun_injected = 1; overrun_value = -1;
        errno = EIO; on_tick(SIGALRM); supervisor_errno = errno;
        errno = ECHILD; on_launcher_tick(SIGALRM); launcher_errno = errno;
        printf("\"supervisor_errno\":%d,\"launcher_errno\":%d,\"expected_eio\":%d,\"expected_echild\":%d,", supervisor_errno, launcher_errno, EIO, ECHILD);
    } else if (strcmp(name, "handler_saturates_overrun") == 0) {
        overrun_injected = 1; overrun_value = INT_MAX; ticks = launcher_ticks = 1;
        on_tick(SIGALRM); on_launcher_tick(SIGALRM);
        printf("\"ticks\":%d,\"launcher_ticks\":%d,", (int)ticks, (int)launcher_ticks);
    } else if (strcmp(name, "clock_fails_mid_trial") == 0) {
        int expired;
        provider.pid = 4242; provider.owned = 1;
        clock_mode = CLOCK_FAIL;
        expired = trial_expired();
        printf("\"trial_expired\":%d,\"stopped\":%d,\"output_expired\":%d,", expired, stopped(), output_expired());
    } else if (strcmp(name, "clock_goes_backwards") == 0) {
        fake_now = 500;
        printf("\"trial_expired\":%d,\"stopped\":%d,", trial_expired(), stopped());
    } else if (strcmp(name, "ticks_override_stuck_clock") == 0) {
        int t0, o0, o1;
        reader.pid = 4343; reader.owned = 1;
        t0 = trial_expired();
        ticks = OUTPUT_TICKS; o0 = output_expired();
        ticks = OUTPUT_TICKS + 1; o1 = output_expired();
        ticks = 1;
        printf("\"before_tick\":%d,\"output_at_limit\":%d,\"output_past_limit\":%d,\"stopped\":%d,", t0, o0, o1, stopped());
    } else if (strcmp(name, "clock_fails_during_forced_collection") == 0) {
        int settled;
        provider.pid = 4242; provider.owned = 1;
        wait_mode = WAIT_RUNNING; clock_mode = CLOCK_FAIL;
        settled = force_collect_children();
        printf("\"settled\":%d,\"still_owned\":%d,", settled, provider.owned);
    } else if (strcmp(name, "deadline_during_cleanup") == 0) {
        ticks = 1;
        record_watchdog_status();
    } else if (strcmp(name, "clock_fails_during_cleanup") == 0) {
        clock_mode = CLOCK_FAIL;
        record_watchdog_status();
    } else if (strcmp(name, "cleanup_on_time") == 0) {
        record_watchdog_status();
    } else if (strcmp(name, "write_completes_late") == 0) {
        start_ms = 0; fake_now = OUTPUT_MS - 1; loglen = 10; memcpy(logbuf, "HXC1 test\n", 10);
        write_mode = WRITE_LATE;
        { int r = write_log(); printf("\"write_log\":%d,\"exit_code\":%d,", r, supervisor_exit_code(r == 0)); }
    } else if (strcmp(name, "partial_write_late") == 0) {
        start_ms = 0; fake_now = OUTPUT_MS - 1; loglen = 10; memcpy(logbuf, "HXC1 test\n", 10);
        write_mode = WRITE_HALF_LATE;
        { int r = write_log(); printf("\"write_log\":%d,\"exit_code\":%d,", r, supervisor_exit_code(r == 0)); }
    } else if (strcmp(name, "write_on_time") == 0) {
        start_ms = 0; fake_now = OUTPUT_MS - 2; loglen = 10; memcpy(logbuf, "HXC1 test\n", 10);
        write_mode = WRITE_ONTIME;
        { int r = write_log(); printf("\"write_log\":%d,\"exit_code\":%d,", r, supervisor_exit_code(r == 0)); }
    } else if (strcmp(name, "clock_failed_but_written") == 0) {
        clock_failed = 1;
        printf("\"exit_code\":%d,", supervisor_exit_code(1));
    } else if (strcmp(name, "waitpid_echild") == 0) {
        int r;
        reader.pid = 4343; reader.owned = 1; wait_mode = WAIT_ECHILD;
        r = reap_check(&reader);
        printf("\"result\":%d,\"owned\":%d,\"lost\":%d,\"collected\":%d,\"signal_owned\":%d,\"settled\":%d,",
               r, reader.owned, reader.lost, reader.collected, signal_owned(&reader, SIGKILL), force_collect_children());
    } else if (strcmp(name, "waitpid_eio") == 0) {
        int r, e;
        reader.pid = 4343; reader.owned = 1; wait_mode = WAIT_EIO;
        r = reap_check(&reader);
        e = child_event(&reader);
        printf("\"result\":%d,\"owned\":%d,\"wait_errors\":%d,\"child_event\":%d,\"signal_owned\":%d,\"settled\":%d,",
               r, reader.owned, reader.wait_errors, e, signal_owned(&reader, SIGKILL), force_collect_children());
    } else if (strcmp(name, "waitpid_eintr_then_collect") == 0) {
        int r;
        reader.pid = 4343; reader.owned = 1; wait_mode = WAIT_EINTR_THEN_EXIT0; wait_countdown = 5;
        r = reap_check(&reader);
        printf("\"result\":%d,\"owned\":%d,\"collected\":%d,\"status\":%d,", r, reader.owned, reader.collected, reader.status);
    } else if (strcmp(name, "waitpid_eintr_forever") == 0) {
        int r;
        reader.pid = 4343; reader.owned = 1; wait_mode = WAIT_EINTR_THEN_EXIT0; wait_countdown = 1000000;
        r = reap_check(&reader);
        printf("\"result\":%d,\"owned\":%d,\"wait_errors\":%d,", r, reader.owned, reader.wait_errors);
    } else if (strcmp(name, "release_deadline_during_final_read") == 0 ||
               strcmp(name, "release_on_time") == 0) {
        int r;
        reader.pid = 4343; reader.owned = 1; wait_mode = WAIT_RUNNING;
        snprintf(held_prefix, sizeof(held_prefix), "HELD synthetic prefix\n");
        capture_r[2] = 102; capture_r[3] = 103;
        pread_mode = strcmp(name, "release_on_time") == 0 ? PREAD_HELD : PREAD_HELD_TICK;
        r = final_release_gate();
        capture_r[2] = capture_r[3] = -1;
        printf("\"gate\":%d,", r);
    } else {
        printf("\"unknown\":1}\n");
        return 2;
    }
    print_log_flags();
    return 0;
}

int main(int argc, char **argv)
{
    const char *fault = getenv("NBT_UNIT_FAULT");
    if (argc == 3 && strcmp(argv[1], "in-process") == 0) return in_process(argv[2]);
    if (fault) {
        if (strcmp(fault, "clock_fail") == 0) clock_mode = CLOCK_FAIL;
        else if (strcmp(fault, "wait_echild") == 0) wait_mode = WAIT_ECHILD;
        else if (strcmp(fault, "wait_eio") == 0) wait_mode = WAIT_EIO;
        else if (strcmp(fault, "wait_eio_twice") == 0) { wait_mode = WAIT_EIO_THEN_REAL; wait_countdown = 2; }
    }
    if (argc == 2 && strcmp(argv[1], "launcher") == 0) return launcher_main();
    if (argc == 2 && strcmp(argv[1], "supervisor") == 0) { supervisor_main(); return 95; }
    note("usage: fault_unit in-process NAME | launcher | supervisor\n");
    return 2;
}
