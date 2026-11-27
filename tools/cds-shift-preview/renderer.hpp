// Host wrapper around three unchanged MIT ShiftDeck methods; see LICENSE.
#ifndef CDS_SHIFT_PREVIEW_RENDERER_HPP
#define CDS_SHIFT_PREVIEW_RENDERER_HPP
#if defined(__QNX__) || defined(__QNXNTO__)
#error Host model sink only. No BMW SDK, object layout or dispatcher is implemented.
#endif
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "shift_assets.h"

// Token for a HOST fake only: not a declaration of the real BMW ImageID ABI.
namespace bmw { struct ImageID { unsigned value; explicit ImageID(unsigned v) : value(v) {} }; }
struct drive_frame { uint64_t sampled_ms; int32_t rpm, kph; };
enum { DRIVE_STALE_MS = 750 }; // Pinned upstream baseline, NOT a chosen CDS lifetime.
struct ImageSink { virtual ~ImageSink() {} virtual void image(unsigned, unsigned) = 0; };

class Renderer {
    ImageSink& sink_;
    bool visible_;
    unsigned target_;
    drive_frame frame_;
    unsigned bar_, lights_;
    int rpm_, kph_;
    bool shift_, metric_;
    double rpm_from_;
    uint64_t rpm_started_;
    enum { kSweepSteps = 128, kSweepBase = 56400, kSweepAlert = 56529, kEaseMs = 50 };
    void updateModel(unsigned model, bmw::ImageID image) { sink_.image(model, image.value); }
#include "renderer_methods.inc"
public:
    explicit Renderer(ImageSink& sink) : sink_(sink), visible_(true), target_(kDefaultTarget),
        bar_(0), lights_(static_cast<unsigned>(-1)), rpm_(-2), kph_(-2),
        shift_(false), metric_(false), rpm_from_(0), rpm_started_(0) {
        clear();
    }
    void clear() { frame_.sampled_ms = 0; frame_.rpm = frame_.kph = -1; rpm_started_ = 0; }
    void visible(bool value) { visible_ = value; clear(); }
    bool accept(const drive_frame& next, uint64_t now) {
        if (!visible_ || !next.sampled_ms || next.sampled_ms < frame_.sampled_ms ||
            next.sampled_ms > now || next.rpm < -1 || next.rpm > 16383 ||
            next.kph < -1 || next.kph > 255) return false;
        if (next.rpm != frame_.rpm) {
            bool continuous = next.rpm >= 0 && frame_.rpm >= 0 && frame_.sampled_ms &&
                              now - frame_.sampled_ms < DRIVE_STALE_MS;
            rpm_from_ = continuous ? animatedRpm(now) : next.rpm;
            rpm_started_ = continuous ? now : 0;
        }
        frame_ = next;
        return true;
    }
    void tick(uint64_t now) { draw(now); }
};
#endif
