/* Invoke actual static callbacks in a host-only translation unit. */
#define main nbt_large_endpoint_main
#include "../nbt_large_endpoint.c"
#undef main
int probe_read(long long offset, int requested, unsigned xtype, int verify_error, long long *out)
{
    resmgr_context_t c; io_read_t msg; iofunc_attr_t attr; iofunc_ocb_t ocb; int rc;
    memset(&c, 0, sizeof(c)); memset(&msg, 0, sizeof(msg));
    memset(&attr, 0, sizeof(attr)); memset(&ocb, 0, sizeof(ocb));
    nbt_body_init(); c.status = 1234; c.iov[0].length = 777;
    msg.i.nbytes = requested; msg.i.xtype = xtype;
    attr.nbytes = nbt_body_length(); ocb.attr = &attr; ocb.offset = offset;
    nbt_fake_verify_error = verify_error;
    rc = endpoint_read(&c, &msg, &ocb);
    out[0] = c.status; out[1] = ocb.offset; out[2] = c.iov[0].length;
    out[3] = c.iov[0].base ? (const unsigned char *)c.iov[0].base - nbt_body_data() : -1;
    out[4] = attr.flags; return rc;
}
int probe_seek(long long before, unsigned long long bits, int whence,
               int default_rc, long long after, long long *out)
{
    resmgr_context_t c; io_lseek_t msg; iofunc_ocb_t ocb; int rc;
    memset(&c, 0, sizeof(c)); memset(&msg, 0, sizeof(msg)); memset(&ocb, 0, sizeof(ocb));
    msg.i.offset = bits; msg.i.whence = (short)whence; ocb.offset = before;
    nbt_fake_seek_calls = 0; nbt_fake_seek_rc = default_rc; nbt_fake_seek_after = after;
    rc = endpoint_lseek(&c, &msg, &ocb);
    out[0] = c.status; out[1] = ocb.offset; out[2] = c.iov[0].length;
    out[3] = c.iov[0].base == &msg; out[4] = nbt_fake_seek_calls; return rc;
}
int probe_handlers(void)
{
    resmgr_connect_funcs_t connect; resmgr_io_funcs_t io;
    endpoint_handlers(&connect, &io);
    return connect.open == endpoint_open && io.read == endpoint_read &&
           io.write == endpoint_write && io.lseek == endpoint_lseek &&
           !connect.unlink && !connect.rename && !io.mmap;
}
