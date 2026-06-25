# runTestServer v1 Notes

## Goal

This first runtime milestone is intentionally narrow:

1. Start from terminal.
2. Locate a Teknic SC hub.
3. Open the first detected hub port.
4. Detect connected nodes.
5. Clear node stops and alerts.
6. Enable one node.
7. Run the node's ClearView-configured homing routine.
8. Print basic status.
9. Disable the node and close ports safely.

No gRPC yet. No endurance cycling yet. No dashboard integration yet.

## Why terminal first?

The motion runtime must prove it can safely control hardware before the GUI
is allowed to command it. Once this standalone runtime is reliable, we will add
the gRPC layer around the same classes.

## Teknic assumptions

This code is based on the company-provided ClearPath SC C++ examples,
especially:

- `ProjectTemplate`
- `Homing`
- `NodeAlerts-Status`
- `SingleThreaded(Polling)`

The motor's homing routine must be configured in ClearView before
`runTestServer --home` is expected to work.

## Build expectation

The project uses CMake. Set `TEKNIC_SDK_DIR` to the folder containing:

```text
inc/pubSysCls.h
sFoundation Source/
```

or edit `runTestServer/CMakeLists.txt` to match your local SDK install.
