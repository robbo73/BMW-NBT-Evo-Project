#ifndef NBT_LARGE_BODY_H
#define NBT_LARGE_BODY_H
#ifndef NBT_LARGE_TYPES_ONLY
#include <stddef.h>
#endif
#ifndef NBT_BODY_LENGTH
#define NBT_BODY_LENGTH 586
#endif
#define NBT_BODY_CAP 16384
#if NBT_BODY_LENGTH < 1 || NBT_BODY_LENGTH > NBT_BODY_CAP
#error NBT_BODY_LENGTH must be between 1 and 16384
#endif
void nbt_body_init(void);
const unsigned char *nbt_body_data(void);
size_t nbt_body_length(void);
unsigned char nbt_body_expected(size_t index);
int nbt_body_slice(long long offset, long long requested, size_t *start, size_t *count);
int nbt_body_open_allowed(unsigned flags, unsigned write_mask, unsigned change_mask);
enum nbt_dispatch_action {
    NBT_DISPATCH_FAIL = -1, NBT_DISPATCH_RETRY = 0, NBT_DISPATCH_MESSAGE = 1
};
enum nbt_dispatch_action nbt_body_dispatch_action(int has_context, int rcvid, int error);
#endif
