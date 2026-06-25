# InterlockTestStand

Initial subsystem layout for the TestStand platform.

```text
InterlockTestStand/
├── TestStandGUI/          # Existing PyQt6 dashboard/application controller
├── runTestServer/         # C++ runtime server / motion control subsystem
├── shared/                # Schemas, protocol files, shared definitions
├── docs/                  # Architecture and implementation notes
├── hardware/              # Future wiring notes, pin maps, calibration docs
└── tools/                 # Future developer/operator utility scripts
```

This package contains the first-pass `runTestServer` scaffold only. Copy the
`runTestServer/`, `shared/`, and `docs/` folders beside your existing
`TestStandGUI/` folder.
