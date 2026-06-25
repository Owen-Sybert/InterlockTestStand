#pragma once

#include "runTestServer/Logging/Logger.h"
#include "runTestServer/Motion/MotionTypes.h"
#include "pubSysCls.h"

namespace teststand {

class TeknicAxis {
public:
    TeknicAxis(sFnd::SysManager* manager, sFnd::INode* node, Logger* logger);

    AxisInfo info() const;
    AxisStatus status();
    bool clearStopsAndAlerts();
    bool enable(int timeoutMs);
    bool disable();
    bool home(int homingTimeoutMs);

private:
    sFnd::SysManager* manager_;
    sFnd::INode* node_;
    Logger* logger_;
};

} // namespace teststand
