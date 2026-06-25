#pragma once

#include <string>

namespace teststand {

enum class MachineState {
    Offline,
    Idle,
    Connecting,
    Connected,
    Homing,
    Homed,
    Ready,
    Running,
    Paused,
    Fault,
    Complete,
    Aborted
};

inline std::string toString(MachineState state) {
    switch (state) {
        case MachineState::Offline: return "OFFLINE";
        case MachineState::Idle: return "IDLE";
        case MachineState::Connecting: return "CONNECTING";
        case MachineState::Connected: return "CONNECTED";
        case MachineState::Homing: return "HOMING";
        case MachineState::Homed: return "HOMED";
        case MachineState::Ready: return "READY";
        case MachineState::Running: return "RUNNING";
        case MachineState::Paused: return "PAUSED";
        case MachineState::Fault: return "FAULT";
        case MachineState::Complete: return "COMPLETE";
        case MachineState::Aborted: return "ABORTED";
        default: return "UNKNOWN";
    }
}

} // namespace teststand
