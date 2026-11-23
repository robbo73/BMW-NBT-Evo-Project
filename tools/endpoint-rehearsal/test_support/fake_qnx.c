/* Runs the real C main loop with controlled receive/handler results.
 * Does not register names, touch /dev or simulate QNX IPC. */
#include "fake_qnx.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static dispatch_t dispatch;
static dispatch_context_t context;
static int ticks, blocks, handlers, invalid_handlers, detaches, frees;
static const char *scenario(void)
{
    const char *s = getenv("NBT_TEST_SCENARIO");
    return s ? s : "timeout_context";
}

int __wrap_lstat(const char *path, struct stat *out)
{
    const char prefix[] = "/dev/nbt_endpoint_rehearsal.";
    (void)out;
    errno = strncmp(path, prefix, sizeof(prefix) - 1) == 0 ? ENOENT : EPERM;
    return -1;
}

int __wrap_clock_gettime(clockid_t clock, struct timespec *now)
{
    if (clock != CLOCK_MONOTONIC) { errno = EINVAL; return -1; }
    now->tv_sec = ticks++;
    now->tv_nsec = 0;
    return 0;
}

dispatch_t *dispatch_create(void) { return &dispatch; }
dispatch_context_t *dispatch_context_alloc(dispatch_t *d) { (void)d; return &context; }
void dispatch_context_free(dispatch_context_t *c) { if (c == &context) ++frees; }
int dispatch_timeout(dispatch_t *d, struct timespec *t)
{
    (void)d;
    if (t->tv_sec != 0 || t->tv_nsec != 100000000) { errno = EINVAL; return -1; }
    return 0;
}
int dispatch_destroy(dispatch_t *d)
{
    (void)d;
    printf("MOCK_LOOP blocks=%d handlers=%d invalid=%d detaches=%d frees=%d\n",
           blocks, handlers, invalid_handlers, detaches, frees);
    return 0;
}

dispatch_context_t *dispatch_block(dispatch_context_t *c)
{
    const char *s = scenario();
    if (c != &context) { errno = EFAULT; return NULL; }
    ++blocks;
    context.resmgr_context.rcvid = -1;
    if (!strcmp(s, "receive_error")) { errno = EIO; return &context; }
    if (!strcmp(s, "null_error")) { errno = EIO; return NULL; }
    if (!strcmp(s, "missing_error")) { errno = 0; return &context; }
    if (blocks == 1 && !strcmp(s, "null_timeout")) { errno = ETIMEDOUT; return NULL; }
    if (blocks == 1 && !strcmp(s, "interrupted")) { errno = EINTR; return NULL; }
    if (!strncmp(s, "handler_", 8)) {
        context.resmgr_context.rcvid = 41; errno = 0; return &context;
    }
    if (blocks == 2) {
        context.resmgr_context.rcvid = 41;
        errno = ETIMEDOUT; /* A valid request must not be dropped for stale errno. */
    } else if (blocks == 4) {
        context.resmgr_context.rcvid = 0;
        errno = EINTR; /* Pulse is valid too. */
    } else {
        errno = ETIMEDOUT; /* Exact observed non-null context / negative rcvid contract. */
    }
    return &context;
}

int dispatch_handler(dispatch_context_t *c)
{
    if (c->resmgr_context.rcvid < 0) { ++invalid_handlers; return -1; }
    ++handlers;
    if (errno != 0) { errno = EFAULT; return -1; }
    if (!strcmp(scenario(), "handler_error")) { errno = EIO; return -1; }
    if (!strcmp(scenario(), "handler_timeout")) { errno = ETIMEDOUT; return -1; }
    errno = EIO; /* Success may leave errno changed; next receive must reset it. */
    return 0;
}

void iofunc_func_init(unsigned a, resmgr_connect_funcs_t *c, unsigned b, resmgr_io_funcs_t *i)
{ (void)a; (void)b; memset(c, 0, sizeof(*c)); memset(i, 0, sizeof(*i)); }
void iofunc_attr_init(iofunc_attr_t *a, mode_t m, iofunc_attr_t *p, void *v)
{ (void)p; (void)v; memset(a, 0, sizeof(*a)); a->mode = m; }
int iofunc_open_default(resmgr_context_t *c, io_open_t *m, iofunc_attr_t *a, void *v)
{ (void)c; (void)m; (void)a; (void)v; return 0; }
int iofunc_read_verify(resmgr_context_t *c, io_read_t *m, iofunc_ocb_t *o, int *n)
{ (void)c; (void)m; (void)o; (void)n; return 0; }
int resmgr_attach(dispatch_t *d, resmgr_attr_t *r, const char *p, int f, unsigned flags,
                  const resmgr_connect_funcs_t *c, const resmgr_io_funcs_t *i, iofunc_attr_t *a)
{ (void)d; (void)r; (void)p; (void)f; (void)flags; (void)c; (void)i; (void)a; return 7; }
int resmgr_detach(dispatch_t *d, int id, unsigned flags)
{ (void)d; (void)id; (void)flags; ++detaches; return 0; }
