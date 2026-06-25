#include "runTestServer/Motion/TeknicSystem.h"

#include <sstream>

namespace teststand {

TeknicSystem::TeknicSystem(Logger* logger)
    : logger_(logger), manager_(sFnd::SysManager::Instance()) {}

TeknicSystem::~TeknicSystem() {
    disconnect();
}

bool TeknicSystem::connect() {
    if (connected_) {
        return true;
    }

    logger_->info("Searching for SC hubs...");
    sFnd::SysManager::FindComHubPorts(hubPorts_);

    if (hubPorts_.empty()) {
        logger_->error("No SC hubs found. Check USB connection and 24V hub power.");
        return false;
    }

    logger_->info("Found " + std::to_string(hubPorts_.size()) + " SC hub port(s).");
    for (size_t i = 0; i < hubPorts_.size(); ++i) {
        logger_->info("  Hub[" + std::to_string(i) + "]: " + hubPorts_[i]);
    }

    manager_->ComHubPort(0, hubPorts_[0].c_str());
    manager_->PortsOpen(1);

    sFnd::IPort& port = manager_->Ports(0);
    logger_->info(
        "Opened port. Net=" + std::to_string(port.NetNumber()) +
        " State=" + std::to_string(port.OpenState()) +
        " Nodes=" + std::to_string(port.NodeCount())
    );

    connected_ = true;
    rebuildAxisList();
    return true;
}

void TeknicSystem::disconnect() {
    if (!manager_) {
        return;
    }

    for (auto& axisPtr : axes_) {
        if (axisPtr) {
            axisPtr->disable();
        }
    }

    if (connected_) {
        logger_->info("Closing Teknic ports.");
        manager_->PortsClose();
        connected_ = false;
    }
}

void TeknicSystem::rebuildAxisList() {
    axes_.clear();

    sFnd::IPort& port = manager_->Ports(0);
    const int nodeCount = port.NodeCount();

    for (int i = 0; i < nodeCount; ++i) {
        axes_.push_back(std::make_unique<TeknicAxis>(manager_, &port.Nodes(i), logger_));
    }
}

std::vector<AxisInfo> TeknicSystem::scanAxes() {
    std::vector<AxisInfo> result;

    if (!connected_ && !connect()) {
        return result;
    }

    for (auto& axisPtr : axes_) {
        if (axisPtr) {
            result.push_back(axisPtr->info());
        }
    }

    return result;
}

bool TeknicSystem::enableAxis(int nodeIndex) {
    auto* a = axis(nodeIndex);
    return a && a->enable(10000);
}

bool TeknicSystem::disableAxis(int nodeIndex) {
    auto* a = axis(nodeIndex);
    return a && a->disable();
}

bool TeknicSystem::homeAxis(const MotionConfig& config) {
    auto* a = axis(config.nodeIndex);
    if (!a) {
        logger_->error("Requested node does not exist: " + std::to_string(config.nodeIndex));
        return false;
    }

    if (!a->enable(config.enableTimeoutMs)) {
        return false;
    }

    const bool ok = a->home(config.homingTimeoutMs);
    a->disable();
    return ok;
}

AxisStatus TeknicSystem::axisStatus(int nodeIndex) {
    auto* a = axis(nodeIndex);
    if (!a) {
        AxisStatus status;
        status.nodeIndex = nodeIndex;
        status.alertPresent = true;
        return status;
    }
    return a->status();
}

TeknicAxis* TeknicSystem::axis(int nodeIndex) {
    if (nodeIndex < 0 || nodeIndex >= static_cast<int>(axes_.size())) {
        return nullptr;
    }
    return axes_[nodeIndex].get();
}

} // namespace teststand
