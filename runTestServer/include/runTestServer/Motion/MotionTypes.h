#pragma once

#include <string>
#include <vector>

namespace teststand {

struct AxisInfo {
    int nodeIndex = -1;
    int nodeType = 0;
    std::string userId;
    std::string firmwareVersion;
    int serialNumber = 0;
    std::string model;
};

struct AxisStatus {
    int nodeIndex = -1;
    bool ready = false;
    bool homed = false;
    bool alertPresent = false;
    bool moveCanceled = false;
    double measuredPositionCounts = 0.0;
};

struct MotionConfig {
    int nodeIndex = 0;
    int enableTimeoutMs = 10000;
    int homingTimeoutMs = 30000;
};

} // namespace teststand
