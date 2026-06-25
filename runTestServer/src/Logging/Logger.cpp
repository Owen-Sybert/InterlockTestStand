#include "runTestServer/Logging/Logger.h"

#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <sstream>

namespace teststand {

Logger::Logger(const std::string& filePath) {
    open(filePath);
}

bool Logger::open(const std::string& filePath) {
    std::lock_guard<std::mutex> lock(mutex_);
    file_.open(filePath, std::ios::app);
    return file_.is_open();
}

void Logger::info(const std::string& message) {
    log(LogLevel::Info, message);
}

void Logger::warn(const std::string& message) {
    log(LogLevel::Warn, message);
}

void Logger::error(const std::string& message) {
    log(LogLevel::Error, message);
}

void Logger::fault(const std::string& message) {
    log(LogLevel::Fault, message);
}

void Logger::log(LogLevel level, const std::string& message) {
    std::lock_guard<std::mutex> lock(mutex_);
    const auto line = "[" + timestamp() + "] " + levelText(level) + ": " + message;
    std::cout << line << std::endl;
    if (file_.is_open()) {
        file_ << line << std::endl;
    }
}

std::string Logger::timestamp() const {
    const auto now = std::chrono::system_clock::now();
    const auto time = std::chrono::system_clock::to_time_t(now);
    std::tm tm{};

#if defined(_WIN32)
    localtime_s(&tm, &time);
#else
    localtime_r(&time, &tm);
#endif

    std::ostringstream out;
    out << std::put_time(&tm, "%b %d, %Y %I:%M:%S %p");
    return out.str();
}

std::string Logger::levelText(LogLevel level) const {
    switch (level) {
        case LogLevel::Info: return "INFO";
        case LogLevel::Warn: return "WARN";
        case LogLevel::Error: return "ERROR";
        case LogLevel::Fault: return "FAULT";
        default: return "INFO";
    }
}

} // namespace teststand
