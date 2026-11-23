#include "endpoint_policy.h"
#include <errno.h>

static const char text[] = "nbt-endpoint-rehearsal\n";

const char *nbt_endpoint_text(void) { return text; }
size_t nbt_endpoint_length(void) { return sizeof(text) - 1; }

int nbt_endpoint_slice(long long offset, long long requested,
                       size_t *start, size_t *count)
{
    size_t remaining;
    if (!start || !count) return EINVAL;
    *start = 0;
    *count = 0;
    if (offset < 0 || requested < 0) return EINVAL;
    if (offset >= (long long)nbt_endpoint_length()) {
        *start = nbt_endpoint_length();
        return 0;
    }
    *start = (size_t)offset;
    remaining = nbt_endpoint_length() - *start;
    *count = requested < (long long)remaining ? (size_t)requested : remaining;
    return 0;
}

int nbt_endpoint_open_allowed(unsigned flags, unsigned write_mask,
                              unsigned change_mask)
{
    return (flags & (write_mask | change_mask)) == 0;
}

enum nbt_dispatch_action nbt_endpoint_dispatch_action(int has_context,
                                                     int rcvid, int error)
{
    /* A real request/pulse is valid even if an API left errno unchanged.
     * QNX receive timeout can return a context with rcvid == -1. */
    if (has_context && rcvid >= 0) return NBT_DISPATCH_MESSAGE;
    if (error == EINTR || error == ETIMEDOUT) return NBT_DISPATCH_RETRY;
    return NBT_DISPATCH_FAIL;
}
