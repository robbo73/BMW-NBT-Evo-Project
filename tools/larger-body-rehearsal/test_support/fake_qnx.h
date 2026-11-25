/* Host loop-contract stubs only. Not QNX headers, an ABI model or an emulator. */
#ifndef NBT_LARGE_FAKE_QNX_H
#define NBT_LARGE_FAKE_QNX_H
#include <stddef.h>
#include <sys/stat.h>
#include <time.h>

typedef struct { int unused; } dispatch_t;
typedef struct { void *base; size_t length; } nbt_fake_iov;
typedef struct { int rcvid, status; nbt_fake_iov iov[2]; } resmgr_context_t;
typedef union { resmgr_context_t resmgr_context; } dispatch_context_t;
typedef struct { struct { unsigned ioflag; } connect; } io_open_t;
typedef struct { struct { int nbytes; unsigned xtype; } i; } io_read_t;
typedef struct { int unused; } io_write_t;
typedef union { struct { short whence; unsigned long long offset; } i; unsigned long long o; } io_lseek_t;
typedef struct { unsigned flags; long long nbytes; mode_t mode; } iofunc_attr_t;
typedef struct { iofunc_attr_t *attr; long long offset; } iofunc_ocb_t;
typedef struct {
    int (*open)(resmgr_context_t *, io_open_t *, iofunc_attr_t *, void *);
    void *unlink, *rename, *mknod, *link, *mount;
} resmgr_connect_funcs_t;
typedef struct {
    int (*read)(resmgr_context_t *, io_read_t *, iofunc_ocb_t *);
    int (*lseek)(resmgr_context_t *, io_lseek_t *, iofunc_ocb_t *);
    int (*write)(resmgr_context_t *, io_write_t *, iofunc_ocb_t *);
    void *chmod, *chown, *utime, *space, *mmap, *msg, *shutdown, *power, *sync;
} resmgr_io_funcs_t;
typedef struct { unsigned nparts_max, msg_max_size; } resmgr_attr_t;
#define _IO_FLAG_WR 2
#define _IO_XTYPE_NONE 0
#define IOFUNC_ATTR_ATIME 2
#define _RESMGR_CONNECT_NFUNCS 8
#define _RESMGR_IO_NFUNCS 26
#define _FTYPE_ANY 0
#define _RESMGR_DETACH_ALL 0
#define _IO_SET_READ_NBYTES(c,n) ((c)->status = (n))
#define _RESMGR_NPARTS(n) (-(n))
#define _RESMGR_PTR(c,p,n) ((c)->iov[0].base = (void *)(p), (c)->iov[0].length = (n), -1)

dispatch_t *dispatch_create(void);
int dispatch_destroy(dispatch_t *);
dispatch_context_t *dispatch_context_alloc(dispatch_t *);
void dispatch_context_free(dispatch_context_t *);
dispatch_context_t *dispatch_block(dispatch_context_t *);
int dispatch_handler(dispatch_context_t *);
int dispatch_timeout(dispatch_t *, struct timespec *);
void iofunc_func_init(unsigned, resmgr_connect_funcs_t *, unsigned, resmgr_io_funcs_t *);
void iofunc_attr_init(iofunc_attr_t *, mode_t, iofunc_attr_t *, void *);
int iofunc_open_default(resmgr_context_t *, io_open_t *, iofunc_attr_t *, void *);
int iofunc_read_verify(resmgr_context_t *, io_read_t *, iofunc_ocb_t *, int *);
int iofunc_lseek_default(resmgr_context_t *, io_lseek_t *, iofunc_ocb_t *);
extern int nbt_fake_verify_error, nbt_fake_seek_rc, nbt_fake_seek_calls;
extern long long nbt_fake_seek_after;
int resmgr_attach(dispatch_t *, resmgr_attr_t *, const char *, int, unsigned,
                  const resmgr_connect_funcs_t *, const resmgr_io_funcs_t *, iofunc_attr_t *);
int resmgr_detach(dispatch_t *, int, unsigned);
#endif
