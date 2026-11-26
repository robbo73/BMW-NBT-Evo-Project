/* Linux-only injected observations. Never part of a QNX build. */
#include <errno.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static int reads, seeks, interrupted;
static int fault(const char *n) { const char *v=getenv("NBT_RAW_FAULT"); return v && strcmp(v,n)==0; }
ssize_t __real_read(int, void *, size_t);
ssize_t __real___read_chk(int, void *, size_t, size_t);
ssize_t __real_write(int, const void *, size_t);
off_t __real_lseek(int, off_t, int);
int __real_close(int);
int __real_sigwaitinfo(const sigset_t *, siginfo_t *);
static int injected_read(ssize_t *r) {
    ++reads;
    if (reads==1) { if (fault("control_read")) { errno=EIO; *r=-1; return 1; } return 0; }
    if (fault("read_hang")) for (;;) pause();
    if (fault("zero")) { *r=0; return 1; }
    if (fault("partial")) { *r=7; return 1; }
    if (fault("read_success")) return 0;
    errno=reads==2?EBADF:EIO; *r=-1; return 1;
}
ssize_t __wrap_read(int fd, void *b, size_t n) { ssize_t r; return injected_read(&r)?r:__real_read(fd,b,n); }
ssize_t __wrap___read_chk(int fd, void *b, size_t n, size_t c) { ssize_t r; return injected_read(&r)?r:__real___read_chk(fd,b,n,c); }
off_t __wrap_lseek(int fd, off_t o, int w) {
    if (++seeks==1) return fault("control_seek")?99:__real_lseek(fd,o,w);
    if (fault("seek_hang")) for (;;) pause();
    if (fault("seek_success")) return __real_lseek(fd,o,w);
    errno=EIO; return (off_t)-1;
}
int __wrap_close(int fd) {
    int r;
    if (fault("close_hang")) for (;;) pause();
    r=__real_close(fd);
    if (fault("close_failure")) { errno=EBADF; return -1; }
    return r;
}
ssize_t __wrap_write(int fd, const void *b, size_t n) {
    ssize_t r;
    if (fault("output_eintr") && !interrupted++) { errno=EINTR; return -1; }
    if (fault("output_zero")) return 0;
    if (fault("output_hang")) for (;;) pause();
    if (fault("partial_output") && n>3) n=3;
    r=__real_write(fd,b,n);
    if (n>=5 && memcmp(b,"HELD ",5)==0 && fault("pending_release")) {
        struct timespec delay={0,150000000}; nanosleep(&delay,NULL);
    }
    return r;
}
int __wrap_sigwaitinfo(const sigset_t *s, siginfo_t *i) {
    int r=__real_sigwaitinfo(s,i);
    if (r>0 && fault("wrong_sender")) i->si_pid=getpid();
    return r;
}
