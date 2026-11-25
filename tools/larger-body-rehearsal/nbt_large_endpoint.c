/* Separate inert larger-body endpoint. No XML, plugin, HMI or arbitrary path. */
#include "large_body.h"
#include "trace_log.h"

#ifndef NBT_LARGE_TYPES_ONLY
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#ifdef NBT_LARGE_TEST_RUNTIME
#include "test_support/fake_qnx.h"
#else
#include <sys/iofunc.h>
#include <sys/dispatch.h>
#endif
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#endif

static int endpoint_open(resmgr_context_t *ctp, io_open_t *msg,
                         iofunc_attr_t *attr, void *extra)
{
    if (!nbt_body_open_allowed(msg->connect.ioflag, _IO_FLAG_WR,
                                   O_CREAT | O_TRUNC)) return EROFS;
    return iofunc_open_default(ctp, msg, attr, extra);
}

static int endpoint_read(resmgr_context_t *ctp, io_read_t *msg,
                         iofunc_ocb_t *ocb)
{
    size_t start = 0, count = 0;
    long long before = ocb->offset, requested = msg->i.nbytes;
    unsigned long xtype = msg->i.xtype;
    int result = iofunc_read_verify(ctp, msg, ocb, NULL);
    if (result) goto done;
    if (msg->i.xtype != _IO_XTYPE_NONE) { result = ENOSYS; goto done; }
    result = nbt_body_slice(ocb->offset, msg->i.nbytes, &start, &count);
    if (result) goto done;
    _IO_SET_READ_NBYTES(ctp, count);
    if (!count) { result = _RESMGR_NPARTS(0); goto done; }
    ocb->offset += count;
    ocb->attr->flags |= IOFUNC_ATTR_ATIME;
    result = _RESMGR_PTR(ctp, nbt_body_data() + start, count);
done:
    nbt_trace_read(before, requested, xtype, count, ocb->offset, result);
    return result;
}

static int endpoint_lseek(resmgr_context_t *ctp, io_lseek_t *msg,
                          iofunc_ocb_t *ocb)
{
    long long before = ocb->offset;
    unsigned long long bits = msg->i.offset;
    int whence = msg->i.whence;
    int result = iofunc_lseek_default(ctp, msg, ocb);
    /* Preserve the SDK reply/OCB; msg is a union and may now contain output. */
    nbt_trace_seek(before, bits, whence, ocb->offset, result);
    return result;
}

static int endpoint_write(resmgr_context_t *ctp, io_write_t *msg,
                          iofunc_ocb_t *ocb)
{
    (void)ctp; (void)msg; (void)ocb;
    return EROFS;
}

static void endpoint_handlers(resmgr_connect_funcs_t *connect,
                              resmgr_io_funcs_t *io)
{
    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, connect, _RESMGR_IO_NFUNCS, io);
    connect->open = endpoint_open;
    connect->unlink = NULL;
    connect->rename = NULL;
    connect->mknod = NULL;
    connect->link = NULL;
    connect->mount = NULL;
    io->read = endpoint_read;
    io->lseek = endpoint_lseek;
    io->write = endpoint_write;
    io->chmod = NULL;
    io->chown = NULL;
    io->utime = NULL;
    io->space = NULL;
    io->mmap = NULL;
    /* Retain standard descriptor-control defaults (e.g. F_GETFL).
     * Actual writes and metadata changes remain refused separately. */
    io->msg = NULL;
    io->shutdown = NULL;
    io->power = NULL;
    io->sync = NULL;
}

#ifndef NBT_LARGE_TYPES_ONLY
static volatile sig_atomic_t stopped;
static void stop_signal(int number) { stopped = number; }

static int milliseconds(long long *value)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return -1;
    *value = (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
    return 0;
}

static void usage(const char *name)
{
    printf("Usage: %s --serve\n", name);
    printf("Revision: larger-body-1; compiled_bytes=%lu cap=%u\n", (unsigned long)nbt_body_length(), NBT_BODY_CAP);
    puts("Inert ten-second binary endpoint: /dev/nbt_large_endpoint_<bytes>.<pid>");
    puts("No plugin, manifest, RPM request, library loading or HMI operation.");
}

int main(int argc, char **argv)
{
    dispatch_t *dpp = NULL;
    dispatch_context_t *context = NULL, *next;
    resmgr_connect_funcs_t connect;
    resmgr_io_funcs_t io;
    resmgr_attr_t resource;
    iofunc_attr_t attr;
    struct sigaction action;
    struct stat info;
    struct timespec poll;
    char path[128];
    int id = -1, failed = 0, ready = 0, size, receive_error;
    enum nbt_dispatch_action action_result;
    long long now, deadline, started = 0, elapsed = -1;
    const char *reason = "setup-error";

    if (argc == 1 || (argc == 2 && strcmp(argv[1], "--help") == 0)) {
        usage(argv[0]); return 0;
    }
    if (argc != 2 || strcmp(argv[1], "--serve") != 0) {
        usage(argv[0]); return 2;
    }
    nbt_body_init();
    nbt_trace_reset();
    memset(&action, 0, sizeof(action));
    sigemptyset(&action.sa_mask);
    action.sa_handler = stop_signal;
    if (sigaction(SIGHUP, &action, NULL) != 0 ||
        sigaction(SIGINT, &action, NULL) != 0 ||
        sigaction(SIGTERM, &action, NULL) != 0) { perror("signals"); return 1; }
    action.sa_handler = SIG_IGN;
    if (sigaction(SIGPIPE, &action, NULL) != 0) { perror("SIGPIPE"); return 1; }
    size = snprintf(path, sizeof(path), "/dev/nbt_large_endpoint_%lu.%ld", (unsigned long)nbt_body_length(), (long)getpid());
    if (size < 0 || (size_t)size >= sizeof(path)) return 1;
    if (lstat(path, &info) == 0 || errno != ENOENT) {
        fputs("STOP: endpoint name is not absent; refusing attach\n", stderr);
        return 1;
    }
    if (milliseconds(&now) != 0) { perror("clock"); return 1; }
    started = now;
    deadline = now + 10000;
    dpp = dispatch_create();
    if (!dpp) { perror("dispatch_create"); return 1; }
    memset(&resource, 0, sizeof(resource));
    resource.nparts_max = 2;
    resource.msg_max_size = 2048;
    endpoint_handlers(&connect, &io);
    iofunc_attr_init(&attr, S_IFREG | 0444, NULL, NULL);
    attr.nbytes = nbt_body_length();
    id = resmgr_attach(dpp, &resource, path, _FTYPE_ANY, 0, &connect, &io, &attr);
    if (id < 0) { perror("resmgr_attach"); failed = 1; goto cleanup; }
    poll.tv_sec = 0;
    poll.tv_nsec = 100000000;
    if (dispatch_timeout(dpp, &poll) != 0) { perror("dispatch_timeout"); failed = 1; goto cleanup; }
    context = dispatch_context_alloc(dpp);
    if (!context) { perror("dispatch_context_alloc"); failed = 1; goto cleanup; }
    ready = 1;
    printf("READY pid=%ld path=%s bytes=%lu lease_ms=10000\n",
           (long)getpid(), path, (unsigned long)nbt_body_length());
    fflush(stdout);
    for (;;) {
        if (stopped) { reason = "signal"; break; }
        if (milliseconds(&now) != 0) { perror("clock"); failed = 1; break; }
        if (now >= deadline) { reason = "deadline"; break; }
        errno = 0;
        next = dispatch_block(context);
        receive_error = errno;
        if (next) context = next;
        action_result = nbt_body_dispatch_action(next != NULL,
                              next ? next->resmgr_context.rcvid : -1,
                              receive_error);
        if (action_result == NBT_DISPATCH_RETRY) continue;
        if (action_result == NBT_DISPATCH_FAIL) {
            errno = receive_error ? receive_error : EIO;
            perror("dispatch_block/receive"); failed = 1; break;
        }
        errno = 0;
        if (dispatch_handler(context) < 0) {
            if (!errno) errno = EIO;
            perror("dispatch_handler"); failed = 1; break;
        }
    }

cleanup:
    if (id >= 0 && resmgr_detach(dpp, id, _RESMGR_DETACH_ALL) != 0) {
        perror("resmgr_detach"); failed = 1;
    }
    if (context) dispatch_context_free(context);
    if (dpp && dispatch_destroy(dpp) != 0) { perror("dispatch_destroy"); failed = 1; }
    if (milliseconds(&now) == 0) elapsed = now - started;
    nbt_trace_dump(elapsed);
    if (failed || !ready) return 1;
    printf("DETACHED reason=%s; endpoint server exiting\n", reason);
    fflush(stdout);
    return stopped ? 2 : 0;
}
#endif
