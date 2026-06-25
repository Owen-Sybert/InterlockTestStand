cmake_minimum_required(VERSION 3.16)

project(runTestServer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---------------------------------------------------------------------------
# Teknic sFoundation SDK location
#
# Recommended:
#   set environment variable TEKNIC_SDK_DIR to the folder containing:
#       inc/pubSysCls.h
#       sFoundation Source/
#
# Example Linux/Pi:
#   export TEKNIC_SDK_DIR=$HOME/Desktop/Linux_Software/sFoundation
#
# Example Windows PowerShell:
#   $env:TEKNIC_SDK_DIR="C:\\path\\to\\sFoundation"
# ---------------------------------------------------------------------------
if(NOT DEFINED TEKNIC_SDK_DIR)
    if(DEFINED ENV{TEKNIC_SDK_DIR})
        set(TEKNIC_SDK_DIR $ENV{TEKNIC_SDK_DIR})
    else()
        message(WARNING "TEKNIC_SDK_DIR is not set. Configure it before building against real hardware.")
        set(TEKNIC_SDK_DIR "")
    endif()
endif()

add_executable(runTestServer
    src/main.cpp
    src/State/StateMachine.cpp
    src/Logging/Logger.cpp
    src/Safety/SafetyModule.cpp
    src/Motion/TeknicSystem.cpp
    src/Motion/TeknicAxis.cpp
)

target_include_directories(runTestServer PRIVATE
    include
)

if(TEKNIC_SDK_DIR)
    target_include_directories(runTestServer PRIVATE
        "${TEKNIC_SDK_DIR}/inc"
    )

    # The exact library path/name may differ between the Windows beta examples
    # and your Raspberry Pi/Linux sFoundation install. Adjust this block once
    # the Pi SDK path is confirmed.
    find_library(SFOUNDATION_LIB
        NAMES sFoundation20 sFoundation
        PATHS
            "${TEKNIC_SDK_DIR}"
            "${TEKNIC_SDK_DIR}/lib"
            "${TEKNIC_SDK_DIR}/sFoundation Source"
            "${TEKNIC_SDK_DIR}/sFoundation Source/lib"
        NO_DEFAULT_PATH
    )

    if(SFOUNDATION_LIB)
        target_link_libraries(runTestServer PRIVATE "${SFOUNDATION_LIB}")
    else()
        message(WARNING "Could not locate sFoundation library. Header parsing may work, final link may fail.")
    endif()
endif()

if(UNIX)
    target_link_libraries(runTestServer PRIVATE pthread)
endif()
