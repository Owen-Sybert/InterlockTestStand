# First-time setup

Place these two files at the root of your `InterlockTestStand` repository:

```text
InterlockTestStand/
├── setup.sh
├── environment.yml
├── TestStandGUI/
├── runTestServer/
└── Linux_Software/          optional, if storing Teknic SDK locally
```

Then run:

```bash
chmod +x setup.sh
./setup.sh
```

After setup finishes, reboot or log out/in so the `dialout` group change takes effect.
