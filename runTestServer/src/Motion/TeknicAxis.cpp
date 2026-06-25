#include "runTestServer/Motion/TeknicAxis.h"

#include <cstdio>
#include <sstream>

namespace teststand {

TeknicAxis::TeknicAxis(sFnd::SysManager* manager, sFnd::INode* node, Logger* logger)
    : manager_(manager), node_(node), logger_(logger) {}

AxisInfo TeknicAxis::info() const {
    AxisInfo axis;
    axis.nodeIndex = node_->Info.Ex.NodeIndex();
    axis.nodeType = node_->Info.NodeType();
    axis.userId = node_->Info.UserID.Value();
    axis.firmwareVersion = node_->Info.FirmwareVersion.Value();
    axis.serialNumber = node_->Info.SerialNumber.Value();
    axis.model = node_->Info.Model.Value();
    return axis;
}

AxisStatus TeknicAxis::status() {
    AxisStatus status;
    status.nodeIndex = node_->Info.Ex.NodeIndex();

    node_->Status.RT.Refresh();
    node_->Motion.PosnMeasured.Refresh();

    status.ready = node_->Motion.IsReady();
    status.homed = node_->Motion.Homing.WasHomed();
    status.alertPresent = node_->Status.RT.Value().cpm.AlertPresent;
    status.moveCanceled = node_->Status.RT.Value().cpm.MoveCanceled;
    status.measuredPositionCounts = node_->Motion.PosnMeasured.Value();
    return status;
}

bool TeknicAxis::clearStopsAndAlerts() {
    logger_->info("Clearing NodeStops and Alerts for node " + std::to_string(node_->Info.Ex.NodeIndex()));
    node_->Motion.NodeStopClear();
    node_->Status.AlertsClear();
    return true;
}

bool TeknicAxis::enable(int timeoutMs) {
    clearStopsAndAlerts();

    logger_->info("Enabling node " + std::to_string(node_->Info.Ex.NodeIndex()));
    node_->EnableReq(true);

    const double timeout = manager_->TimeStampMsec() + timeoutMs;
    while (!node_->Motion.IsReady()) {
        node_->Status.RT.Refresh();

        if (node_->Status.RT.Value().cpm.AlertPresent) {
            logger_->fault("Node alert present while enabling.");
            return false;
        }

        if (manager_->TimeStampMsec() > timeout) {
            logger_->error("Timed out waiting for node to enable.");
            return false;
        }
    }

    logger_->info("Node enabled successfully.");
    return true;
}

bool TeknicAxis::disable() {
    logger_->info("Disabling node " + std::to_string(node_->Info.Ex.NodeIndex()));
    node_->EnableReq(false);
    return true;
}

bool TeknicAxis::home(int homingTimeoutMs) {
    if (!node_->Motion.Homing.HomingValid()) {
        logger_->error("Homing is not configured for this node. Configure homing in ClearView first.");
        return false;
    }

    if (node_->Motion.Homing.WasHomed()) {
        node_->Motion.PosnMeasured.Refresh();
        logger_->info("Node was already homed at position " + std::to_string(node_->Motion.PosnMeasured.Value()) + ". Rehoming.");
    } else {
        logger_->info("Node has not been homed. Starting homing.");
    }

    node_->Motion.Homing.Initiate();

    const double timeout = manager_->TimeStampMsec() + homingTimeoutMs;
    while (!node_->Motion.Homing.WasHomed()) {
        node_->Status.RT.Refresh();

        if (node_->Status.RT.Value().cpm.AlertPresent) {
            logger_->fault("Node alert present during homing.");
            return false;
        }

        if (node_->Status.RT.Value().cpm.MoveCanceled) {
            logger_->fault("Homing move was canceled.");
            return false;
        }

        if (manager_->TimeStampMsec() > timeout) {
            logger_->fault("Homing timeout reached.");
            return false;
        }
    }

    node_->Motion.PosnMeasured.Refresh();
    logger_->info("Homing complete. Current position: " + std::to_string(node_->Motion.PosnMeasured.Value()));
    return true;
}

} // namespace teststand
