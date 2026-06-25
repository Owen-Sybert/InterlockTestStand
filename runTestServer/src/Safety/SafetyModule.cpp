#include "runTestServer/Safety/SafetyModule.h"

namespace teststand {

void SafetyModule::update() {
    // Future: poll ESTOP GPIO, door switches, load cells, thermocouples, Teknic faults.
}

bool SafetyModule::safeToMove() const {
    return !softwareEstopActive_;
}

bool SafetyModule::hasFault() const {
    return softwareEstopActive_;
}

std::vector<std::string> SafetyModule::activeFaults() const {
    if (softwareEstopActive_) {
        return {"SOFTWARE ESTOP ACTIVE"};
    }
    return {};
}

void SafetyModule::setSoftwareEstop(bool active) {
    softwareEstopActive_ = active;
}

} // namespace teststand
