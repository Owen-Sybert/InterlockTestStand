# runTestServer

Initial C++ runtime skeleton for TestStand motion control.

## Commands

```bash
./runTestServer --scan
./runTestServer --home --node 0
```

## Intended first hardware test

```bash
mkdir -p build
cd build
cmake ..
cmake --build .
./runTestServer --scan
./runTestServer --home --node 0
```

## Notes

- Homing must be configured in ClearView first.
- This is not yet connected to the PyQt dashboard.
- This is not yet a gRPC server.
- This is the first real runtime subsystem foundation.
