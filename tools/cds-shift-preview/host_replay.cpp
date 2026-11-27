#define __STDC_FORMAT_MACROS
#include <inttypes.h>
#include <pthread.h>
#include <stdlib.h>
#include <vector>
#include "rpm_latch.hpp"
#include "renderer.hpp"

struct Update { unsigned model, image; Update(unsigned m, unsigned i) : model(m), image(i) {} };
class CaptureSink : public ImageSink {
    pthread_t owner_;
public:
    std::vector<Update> updates;
    CaptureSink() : owner_(pthread_self()) {}
    void image(unsigned model, unsigned image) {
        if (!pthread_equal(owner_, pthread_self())) abort();
        updates.push_back(Update(model, image));
    }
};

struct Stress { RpmLatch* latch; bool ok; };
static void* producer(void* data) {
    Stress* s = static_cast<Stress*>(data);
    for (unsigned i = 1; i <= 20000; ++i)
        if (!s->latch->publish(i % 9001, i)) s->ok = false;
    return 0;
}
static bool stress() {
    RpmLatch latch;
    if (!latch.ready()) return false;
    Stress s = { &latch, true };
    pthread_t writer;
    if (pthread_create(&writer, 0, producer, &s) != 0) return false;
    bool consistent = true;
    for (unsigned i = 0; i < 30000; ++i) {
        RpmReceipt r;
        if (!latch.copy(r) || (r.present && (r.rpm != r.received_ms % 9001 ||
                                           r.sequence != r.received_ms))) consistent = false;
    }
    if (pthread_join(writer, 0) != 0) abort(); // never destroy a live writer's latch
    RpmReceipt r;
    consistent = consistent && latch.copy(r) && r.sequence == 20000;
    latch.stop();
    return consistent && s.ok && !latch.publish(700, 20001);
}

int main() {
    RpmLatch latch;
    if (!latch.ready()) return 2;
    CaptureSink sink;
    Renderer renderer(sink);
    char op[24];
    while (scanf("%23s", op) == 1) {
        uint64_t ms;
        if (!strcmp(op, "sample")) {
            double rpm;
            if (scanf("%" SCNu64 " %lf", &ms, &rpm) != 2) return 2;
            printf("{\"accepted\":%s}\n", latch.publish(rpm, ms) ? "true" : "false");
        } else if (!strcmp(op, "discard")) {
            puts("{\"accepted\":false}");
        } else if (!strcmp(op, "stop")) {
            latch.stop(); renderer.clear(); puts("{\"stopped\":true}");
        } else if (!strcmp(op, "stress")) {
            if (!stress()) return 3;
            puts("{\"stress\":true,\"writes\":20000}");
        } else if (!strcmp(op, "poll") || !strcmp(op, "show") || !strcmp(op, "hide")) {
            if (scanf("%" SCNu64, &ms) != 1) return 2;
            if (!strcmp(op, "show")) renderer.visible(true);
            if (!strcmp(op, "hide")) renderer.visible(false);
            RpmReceipt r;
            if (!latch.copy(r)) return 3;
            bool recent = r.present && r.received_ms <= ms && ms - r.received_ms < DRIVE_STALE_MS;
            drive_frame f = { r.received_ms, static_cast<int32_t>(r.rpm + .5), -1 };
            if (recent) renderer.accept(f, ms); else renderer.clear();
            sink.updates.clear(); renderer.tick(ms);
            printf("{\"received_ms\":%" PRIu64 ",\"sequence\":%" PRIu64
                   ",\"recent_arrival\":%s,\"producer_freshness_verified\":false,\"models\":[",
                   r.received_ms, r.sequence, recent ? "true" : "false");
            for (size_t i = 0; i < sink.updates.size(); ++i)
                printf("%s[%u,%u]", i ? "," : "", sink.updates[i].model, sink.updates[i].image);
            puts("]}");
        } else return 2;
    }
    return ferror(stdin) ? 2 : 0;
}
