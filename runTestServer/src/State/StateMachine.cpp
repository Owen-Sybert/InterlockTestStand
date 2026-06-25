#include "runTestServer/State/StateMachine.h"

namespace teststand {

StateMachine::StateMachine()
    : state_(MachineState::Idle), lastReason_("startup") {}

MachineState StateMachine::state() const {
    return state_;
}

std::string StateMachine::lastTransitionReason() const {
    return lastReason_;
}

bool StateMachine::transitionTo(MachineState next, const std::string& reason) {
    if (!isAllowed(state_, next)) {
        return false;
    }

    state_ = next;
    lastReason_ = reason;
    return true;
}

bool StateMachine::isAllowed(MachineState from, MachineState to) const {
    if (to == MachineState::Fault || to == MachineState::Aborted) {
        return true;
    }

    switch (from) {
        case MachineState::Idle:
            return to == MachineState::Connecting;
        case MachineState::Connecting:
            return to == MachineState::Connected;
        case MachineState::Connected:
            return to == MachineState::Homing || to == MachineState::Ready;
        case MachineState::Homing:
            return to == MachineState::Homed;
        case MachineState::Homed:
            return to == MachineState::Ready;
        case MachineState::Ready:
            return to == MachineState::Running || to == MachineState::Idle;
        case MachineState::Running:
            return to == MachineState::Paused || to == MachineState::Complete;
        case MachineState::Paused:
            return to == MachineState::Running;
        case MachineState::Complete:
        case MachineState::Fault:
        case MachineState::Aborted:
            return to == MachineState::Idle;
        default:
            return false;
    }
}

} // namespace teststand
