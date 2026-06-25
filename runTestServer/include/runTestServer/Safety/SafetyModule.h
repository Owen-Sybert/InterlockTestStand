#pragma once

#include <string>
#include <vector>

namespace teststand {

class SafetyModule {
public:
    void update();
    bool safeToMove() const;
    bool hasFault() const;
    std::vector<std::string> activeFaults() const;

    // Temporary test hook until GPIO and sensor modules exist.
    void setSoftwareEstop(bool active);

private:
    bool softwareEstopActive_ = false;
};

} // namespace teststand
