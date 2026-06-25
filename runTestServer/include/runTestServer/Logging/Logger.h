#pragma once

#include <fstream>
#include <mutex>
#include <string>

namespace teststand {

enum class LogLevel {
    Info,
    Warn,
    Error,
    Fault
};

class Logger {
public:
    Logger() = default;
    explicit Logger(const std::string& filePath);

    bool open(const std::string& filePath);
    void info(const std::string& message);
    void warn(const std::string& message);
    void error(const std::string& message);
    void fault(const std::string& message);
    void log(LogLevel level, const std::string& message);

private:
    std::string timestamp() const;
    std::string levelText(LogLevel level) const;

    mutable std::mutex mutex_;
    std::ofstream file_;
};

} // namespace teststand
