/* Only bounded memory updates in callbacks; formatting happens after detach. */
#include "trace_log.h"
#include <limits.h>
#include <stdio.h>
#include <string.h>
static struct nbt_trace_event events[NBT_TRACE_CAP];
static size_t used;
static unsigned long dropped;

void nbt_trace_reset(void) { used = 0; dropped = 0; }
static struct nbt_trace_event *reserve(void)
{
    struct nbt_trace_event *event;
    if (used == NBT_TRACE_CAP) {
        if (dropped != ULONG_MAX) ++dropped;
        return NULL;
    }
    event = &events[used++];
    memset(event, 0, sizeof(*event));
    return event;
}
void nbt_trace_read(long long before, long long requested, unsigned long xtype,
                    size_t count, long long after, int result)
{
    struct nbt_trace_event *e = reserve();
    if (!e) return;
    e->kind = 1; e->before = before; e->read_requested = requested;
    e->xtype = xtype; e->count = count; e->after = after; e->result = result;
}
void nbt_trace_seek(long long before, unsigned long long bits, int whence,
                    long long after, int result)
{
    struct nbt_trace_event *e = reserve();
    if (!e) return;
    e->kind = 2; e->before = before; e->seek_offset_bits = bits;
    e->whence = whence; e->after = after; e->result = result;
}
size_t nbt_trace_count(void) { return used; }
unsigned long nbt_trace_dropped(void) { return dropped; }
const struct nbt_trace_event *nbt_trace_at(size_t index)
{ return index < used ? &events[index] : NULL; }
void nbt_trace_dump(long long elapsed_ms)
{
    size_t i;
    printf("TRACE_SUMMARY events=%lu dropped=%lu overflow=%u elapsed_ms=%lld\n",
           (unsigned long)used, dropped, (unsigned)(dropped != 0), elapsed_ms);
    for (i = 0; i < used; ++i) {
        const struct nbt_trace_event *e = &events[i];
        if (e->kind == 1)
            printf("TRACE_READ index=%lu before=%lld requested=%lld xtype=%lu count=%lu after=%lld rc=%d\n",
                   (unsigned long)i, e->before, e->read_requested, e->xtype,
                   (unsigned long)e->count, e->after, e->result);
        else
            printf("TRACE_SEEK index=%lu before=%lld offset_bits=%016llx whence=%d after=%lld rc=%d\n",
                   (unsigned long)i, e->before, e->seek_offset_bits, e->whence,
                   e->after, e->result);
    }
    fflush(stdout);
}
