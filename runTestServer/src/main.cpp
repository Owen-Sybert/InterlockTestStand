#include "runTestServer/Logging/Logger.h"
#include "runTestServer/Motion/TeknicSystem.h"
#include "runTestServer/State/StateMachine.h"

#include "pubSysCls.h"

#include <cstdlib>
#include <iostream>
#include <string>

using namespace teststand;

namespace {

struct Args {
    bool scan = false;
    bool home = false;
    int nodeIndex = 0;
};

void printUsage() {
    std::cout
        << "runTestServer v1 terminal runtime\n\n"
        << "Usage:\n"
        << "  runTestServer --scan\n"
        << "  runTestServer --home --node 0\n\n";
}

Args parseArgs(int argc, char* argv[]) {
    Args args;

    for (int i = 1; i < argc; ++i) {
        std::string token = argv[i];

        if (token == "--scan") {
            args.scan = true;
        } else if (token == "--home") {
            args.home = true;
        } else if (token == "--node" && i + 1 < argc) {
            args.nodeIndex = std::atoi(argv[++i]);
        } else if (token == "--help" || token == "-h") {
            printUsage();
            std::exit(0);
        }
    }

    return args;
}

void printAxis(const AxisInfo& axis) {
    std::cout
        << "Node[" << axis.nodeIndex << "]\n"
        << "  Type: " << axis.nodeType << "\n"
        << "  User ID: " << axis.userId << "\n"
        << "  Firmware: " << axis.firmwareVersion << "\n"
        << "  Serial: " << axis.serialNumber << "\n"
        << "  Model: " << axis.model << "\n";
}

} // namespace

int main(int argc, char* argv[]) {
    Args args = parseArgs(argc, argv);

    if (!args.scan && !args.home) {
        printUsage();
        return 1;
    }

    Logger logger;
    StateMachine sm;
    TeknicSystem motion(&logger);

    try {
        sm.transitionTo(MachineState::Connecting, "operator command");
        logger.info("State: " + toString(sm.state()));

        if (!motion.connect()) {
            sm.transitionTo(MachineState::Fault, "Teknic connect failed");
            logger.fault("State: " + toString(sm.state()));
            return 1;
        }

        sm.transitionTo(MachineState::Connected, "Teknic connected");
        logger.info("State: " + toString(sm.state()));

        if (args.scan) {
            const auto axes = motion.scanAxes();
            logger.info("Detected " + std::to_string(axes.size()) + " node(s).");
            for (const auto& axis : axes) {
                printAxis(axis);
            }
        }

        if (args.home) {
            MotionConfig config;
            config.nodeIndex = args.nodeIndex;
            config.enableTimeoutMs = 10000;
            config.homingTimeoutMs = 30000;

            sm.transitionTo(MachineState::Homing, "operator home command");
            logger.info("State: " + toString(sm.state()));

            const bool homed = motion.homeAxis(config);
            if (!homed) {
                sm.transitionTo(MachineState::Fault, "homing failed");
                logger.fault("State: " + toString(sm.state()));
                return 1;
            }

            sm.transitionTo(MachineState::Homed, "homing complete");
            logger.info("State: " + toString(sm.state()));

            sm.transitionTo(MachineState::Ready, "axis ready");
            logger.info("State: " + toString(sm.state()));
        }

        motion.disconnect();
        return 0;
    }
    catch (sFnd::mnErr& err) {
        logger.error(
            "Teknic mnErr caught. addr=" + std::to_string(err.TheAddr) +
            " err=0x" + std::to_string(err.ErrorCode) +
            " msg=" + std::string(err.ErrorMsg)
        );

        motion.disconnect();
        return 1;
    }
    catch (const std::exception& exc) {
        logger.error(std::string("Exception: ") + exc.what());
        motion.disconnect();
        return 1;
    }
}
