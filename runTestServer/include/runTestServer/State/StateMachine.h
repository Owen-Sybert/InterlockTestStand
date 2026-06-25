#pragma once

#include "runTestServer/State/MachineState.h"
#include <string>

namespace teststand {

class StateMachine {
public:
    StateMachine();

    MachineState state() const;
    bool transitionTo(MachineState next, const std::string& reason);
    std::string lastTransitionReason() const;

private:
    bool isAllowed(MachineState from, MachineState to) const;

    MachineState state_;
    std::string lastReason_;
};

} // namespace teststand
