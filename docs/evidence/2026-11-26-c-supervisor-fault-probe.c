/* Private host unit probes. No trial, fork, child signal or target path IO. */
static int fail_clock;
static long long fake_now;
#define clock_gettime review_clock_gettime
#define write review_write
#define waitpid review_waitpid
#define main supplied_supervisor_main
#if defined(__QNX__)
#error "Host review unit only; never compile for a target"
#endif
#ifndef NBT_REVIEW_SOURCE
#error "Define NBT_REVIEW_SOURCE to the supplied supervisor C filename"
#endif
#include NBT_REVIEW_SOURCE
#undef main
#undef clock_gettime
#undef write
#undef waitpid
int review_clock_gettime(clockid_t id, struct timespec *t)
{
    (void)id;
    if (fail_clock) { errno=EIO; return -1; }
    t->tv_sec=(time_t)(fake_now/1000);
    t->tv_nsec=(long)(fake_now%1000)*1000000L;
    return 0;
}
ssize_t review_write(int fd, const void *data, size_t length)
{
    (void)fd;(void)data;
    fake_now=OUTPUT_MS+100;  /* write completed late but before HARD_MS */
    return (ssize_t)length;
}
pid_t review_waitpid(pid_t pid, int *status, int flags)
{
    (void)pid;(void)status;(void)flags;errno=EIO;return -1;
}
int main(void)
{
    long long bad_elapsed;
    int stop, write_result, reaped;
    struct child probe={"PROBE",4242,1,0,0,0,0};
    start_ms=123456789000LL;
    fail_clock=1;
    bad_elapsed=elapsed();stop=stopped();
    fail_clock=0;start_ms=0;fake_now=OUTPUT_MS-1;
    loglen=1;logbuf[0]='x';
    write_result=write_log();
    reaped=reap_check(&probe);
    printf("{\"clock_failure\":{\"elapsed_ms\":%lld,\"stop_reported\":%d},",bad_elapsed,stop);
    printf("\"late_write\":{\"completed_at_ms\":%lld,\"output_bound_ms\":%d,\"write_log_result\":%d},",fake_now,OUTPUT_MS,write_result);
    printf("\"waitpid_eio\":{\"reap_check_result\":%d,\"owned\":%d,\"reaped\":%d,\"lost\":%d}}\n",reaped,probe.owned,probe.reaped,probe.lost);
    return 0;
}
