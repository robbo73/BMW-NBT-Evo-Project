// New host-only adapter experiment. MIT; upstream renderer notices in LICENSE.
#ifndef CDS_SHIFT_PREVIEW_LATCH_HPP
#define CDS_SHIFT_PREVIEW_LATCH_HPP
#if defined(__QNX__) || defined(__QNXNTO__)
#error This experiment is host-only; it is not a native plugin or CDS binding.
#endif
#include <pthread.h>
#include <stdint.h>

struct RpmReceipt {
    double rpm;
    uint64_t received_ms;
    uint64_t sequence;
    bool present;
};

// This stores callback RECEIPTS, not proof of a new vehicle measurement.
// A same-value callback can be a new receipt; polling never re-stamps it.
// Owner must stop and join every writer before destroying the latch.
class RpmLatch {
    pthread_mutex_t mutex_;
    bool ready_, enabled_;
    RpmReceipt receipt_;
    RpmLatch(const RpmLatch&);
    RpmLatch& operator=(const RpmLatch&);
public:
    RpmLatch() : ready_(pthread_mutex_init(&mutex_, 0) == 0), enabled_(true) {
        receipt_.rpm = 0;
        receipt_.received_ms = receipt_.sequence = 0;
        receipt_.present = false;
    }
    ~RpmLatch() { if (ready_) pthread_mutex_destroy(&mutex_); }
    bool ready() const { return ready_; }
    bool publish(double rpm, uint64_t received_ms) {
        // Preserve the existing B58 parser's 0..9000 policy. JSON already is RPM.
        if (!(rpm >= 0 && rpm <= 9000) || !received_ms || !ready_ ||
            pthread_mutex_lock(&mutex_) != 0) return false;
        bool accepted = enabled_ && received_ms >= receipt_.received_ms &&
                        receipt_.sequence != ~static_cast<uint64_t>(0);
        if (accepted) {
            receipt_.rpm = rpm;
            receipt_.received_ms = received_ms;
            ++receipt_.sequence;
            receipt_.present = true;
        }
        pthread_mutex_unlock(&mutex_);
        return accepted;
    }
    bool copy(RpmReceipt& out) {
        if (!ready_ || pthread_mutex_lock(&mutex_) != 0) return false;
        out = receipt_;
        out.present = out.present && enabled_;
        pthread_mutex_unlock(&mutex_);
        return true;
    }
    void stop() {
        if (!ready_ || pthread_mutex_lock(&mutex_) != 0) return;
        enabled_ = false;
        receipt_.present = false;
        pthread_mutex_unlock(&mutex_);
    }
};
#endif
