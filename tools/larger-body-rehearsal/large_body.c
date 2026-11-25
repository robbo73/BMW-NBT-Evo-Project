/* Inert position-dependent binary data, deliberately containing NUL bytes. */
#include "large_body.h"
#include <errno.h>

static unsigned char body[NBT_BODY_LENGTH];

unsigned char nbt_body_expected(size_t index)
{
    static const char hex[] = "0123456789abcdef";
    unsigned position = (unsigned)(index % 16u);
    unsigned block = (unsigned)(index / 16u);
    if (position < 8u) return (unsigned char)hex[((block * 16u) >> ((7u-position)*4u)) & 15u];
    if (position == 8u) return ':';
    if (position == 9u) return 0;
    if (position == 15u) return '\n';
    return (unsigned char)('A' + (block + position) % 26u);
}

void nbt_body_init(void)
{
    size_t i;
    for (i = 0; i < sizeof(body); ++i) body[i] = nbt_body_expected(i);
}
const unsigned char *nbt_body_data(void) { return body; }
size_t nbt_body_length(void) { return sizeof(body); }

int nbt_body_slice(long long offset, long long requested, size_t *start, size_t *count)
{
    size_t remaining;
    if (!start || !count) return EINVAL;
    *start = 0; *count = 0;
    if (offset < 0 || requested < 0) return EINVAL;
    if (offset >= (long long)nbt_body_length()) {
        *start = nbt_body_length(); return 0;
    }
    *start = (size_t)offset;
    remaining = nbt_body_length() - *start;
    *count = requested < (long long)remaining ? (size_t)requested : remaining;
    return 0;
}
int nbt_body_open_allowed(unsigned flags, unsigned write_mask, unsigned change_mask)
{
    return (flags & (write_mask | change_mask)) == 0;
}
enum nbt_dispatch_action nbt_body_dispatch_action(int has_context, int rcvid, int error)
{
    if (has_context && rcvid >= 0) return NBT_DISPATCH_MESSAGE;
    if (error == EINTR || error == ETIMEDOUT) return NBT_DISPATCH_RETRY;
    return NBT_DISPATCH_FAIL;
}
