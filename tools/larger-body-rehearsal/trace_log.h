#ifndef NBT_LARGE_TRACE_H
#define NBT_LARGE_TRACE_H
#ifndef NBT_LARGE_TYPES_ONLY
#include <stddef.h>
#endif
#define NBT_TRACE_CAP 64
struct nbt_trace_event {
    int kind, result, whence;
    unsigned long xtype;
    long long before, after, read_requested;
    unsigned long long seek_offset_bits;
    size_t count;
};
void nbt_trace_reset(void);
void nbt_trace_read(long long before, long long requested, unsigned long xtype,
                    size_t count, long long after, int result);
void nbt_trace_seek(long long before, unsigned long long bits, int whence,
                    long long after, int result);
size_t nbt_trace_count(void);
unsigned long nbt_trace_dropped(void);
const struct nbt_trace_event *nbt_trace_at(size_t index);
void nbt_trace_dump(long long elapsed_ms);
#endif
