#ifndef NBT_ENDPOINT_POLICY_H
#define NBT_ENDPOINT_POLICY_H
#ifndef NBT_ENDPOINT_TYPES_ONLY
#include <stddef.h>
#endif

const char *nbt_endpoint_text(void);
size_t nbt_endpoint_length(void);
int nbt_endpoint_slice(long long offset, long long requested,
                       size_t *start, size_t *count);
int nbt_endpoint_open_allowed(unsigned flags, unsigned write_mask,
                              unsigned change_mask);
#endif
