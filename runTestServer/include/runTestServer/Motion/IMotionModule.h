#pragma once

#include "runTestServer/Motion/MotionTypes.h"
#include <vector>

namespace teststand {

class IMotionModule {
public:
    virtual ~IMotionModule() = default;

    virtual bool connect() = 0;
    virtual void disconnect() = 0;

    virtual std::vector<AxisInfo> scanAxes() = 0;
    virtual bool enableAxis(int nodeIndex) = 0;
    virtual bool disableAxis(int nodeIndex) = 0;
    virtual bool homeAxis(const MotionConfig& config) = 0;
    virtual AxisStatus axisStatus(int nodeIndex) = 0;
};

} // namespace teststand
