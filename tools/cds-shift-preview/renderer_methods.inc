// Unmodified methods from ID6 Apps ShiftDeck, commit 8567abaadd1305965b3ad39e3222575cd49c507d.
// Copyright (c) 2026 ID6 Apps contributors. MIT; see LICENSE.
// Included only inside the host test Renderer; no real BMW object is constructed.

    double animatedRpm(uint64_t now) const {
        if (!rpm_started_ || now-rpm_started_>=kEaseMs) return frame_.rpm;
        const double remaining=1.-static_cast<double>(now-rpm_started_)/kEaseMs;
        return frame_.rpm+(rpm_from_-frame_.rpm)*remaining*remaining;
    }

    void digits(unsigned model, unsigned width, const char* text, unsigned base, bool center) {
        unsigned length=static_cast<unsigned>(strlen(text));
        unsigned offset=center && length<width ? (width-length)/2 : 0;
        for (unsigned i=0;i<width;++i) {
            char c=i>=offset && i-offset<length ? text[i-offset] : ' ';
            updateModel(model+i,bmw::ImageID(base+(c==' ' ? 11u : c=='-' ? 10u : c-'0')));
        }
    }

    void draw(uint64_t now) {
        bool live=visible_ && frame_.sampled_ms && frame_.sampled_ms<=now &&
                  now-frame_.sampled_ms<DRIVE_STALE_MS;
        int rpm=live ? frame_.rpm : -1;
        int kph=live ? frame_.kph : -1;
        int target=static_cast<int>(kShiftTargets[target_]);
        bool shift=rpm>=target;
        int displayed_rpm=rpm;
        if (rpm>=0) displayed_rpm=static_cast<int>(animatedRpm(now)+.5);
        unsigned bars=displayed_rpm>0 ? (displayed_rpm*kSweepSteps+4000)/8000 : 0;
        if (bars>kSweepSteps) bars=kSweepSteps;
        unsigned image=(shift ? kSweepAlert : kSweepBase)+bars;
        if (image!=bar_) {
            updateModel(54u,bmw::ImageID(image));
            bar_=image;
        }
        int approach=rpm-(target-2000);
        unsigned lights=shift ? 13u : approach>0 ? static_cast<unsigned>(approach)*12/2000 : 0u;
        if (lights!=lights_) {
            updateModel(55u,bmw::ImageID(kLightBase+lights));
            lights_=lights;
        }
        char text[48];
        if (displayed_rpm!=rpm_ || shift!=shift_) {
            if (displayed_rpm<0) strcpy(text,"--");
            else snprintf(text,sizeof text,"%d",displayed_rpm>9999 ? 9999 : displayed_rpm);
            digits(60u,4u,text,shift ? kDigitWarn : kDigitBase,true);
            rpm_=displayed_rpm;
        }
        if (kph!=kph_) {
            if (kph<0) strcpy(text,"--");
            else {
            int speed=(kph*621371+500000)/1000000;
            if (metric_) speed=kph;
            snprintf(text,sizeof text,"%d",speed);
        }
            digits(70u,3u,text,kDigitBase,false);
            kph_=kph;
        }
        if (shift!=shift_) {
            updateModel(57u,bmw::ImageID(shift ? kShiftOn : kShiftOff));
            shift_=shift;
        }
    }
