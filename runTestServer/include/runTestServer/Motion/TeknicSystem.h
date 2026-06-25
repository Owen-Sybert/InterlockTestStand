#pragma once

#include "runTestServer/Logging/Logger.h"
#include "runTestServer/Motion/IMotionModule.h"
#include "runTestServer/Motion/TeknicAxis.h"
#include "pubSysCls.h"

#include <memory>
#include <string>
#include <vector>

namespace teststand {

class TeknicSystem : public IMotionModule {
public:
    explicit TeknicSystem(Logger* logger);
    ~TeknicSystem() override;

    bool connect() override;
    void disconnect() override;

    std::vector<AxisInfo> scanAxes() override;
    bool enableAxis(int nodeIndex) override;
    bool disableAxis(int nodeIndex) override;
    bool homeAxis(const MotionConfig& config) override;
    AxisStatus axisStatus(int nodeIndex) override;

private:
    TeknicAxis* axis(int nodeIndex);
    void rebuildAxisList();

    Logger* logger_;
    sFnd::SysManager* manager_ = nullptr;
    bool connected_ = false;
    std::vector<std::string> hubPorts_;
    std::vector<std::unique_ptr<TeknicAxis>> axes_;
};

} // namespace teststand
