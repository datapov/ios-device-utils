#!/usr/bin/env python3
"""Parser test using the iPhone sample Diwakar pasted on 2026-10-26.
Builds a plist with the same shape/values as idevicediagnostics output,
monkeys the run() helper to return it, and checks the extracted fields.
"""
import plistlib
import sys
sys.path.insert(0, ".")
import battery_health as bh

sample = {
    "IORegistry": {
        "CurrentCapacity": 88,
        "CycleCount": 379,
        "Voltage": 4291,
        "IsCharging": True,
        "FullyCharged": False,
        "BatteryData": {
            "DesignCapacity": 5015,
            "FullChargeCapacity": 4447,
            "NominalChargeCapacity": 4523,
            "AppleRawMaxCapacity": 4447,
            "AppleRawCurrentCapacity": 3800,
            "CurrentCapacity": 88,
        },
    }
}
plist_bytes = plistlib.dumps(sample)

orig_run = bh.run
def fake_run(cmd):
    if "idevicediagnostics" in cmd[0]:
        return plist_bytes
    if "-q" in cmd:
        return b"BatteryCurrentCapacity: 89\nBatteryIsCharging: true\nFullyCharged: false\n"
    return b"DeviceName: Test iPhone\nProductType: iPhone16,2\nProductVersion: 17.0\n"
bh.run = fake_run
try:
    d = bh.get_battery_for_udid("TESTUDID")
finally:
    bh.run = orig_run

assert d["cycle_count"] == 379, d
assert d["full_charge_capacity_mah"] == 4447, d
assert d["design_capacity_mah"] == 5015, d
assert d["nominal_capacity_mah"] == 4523, d
assert d["health_vs_design_pct"] == 88.7, d
assert d["health_vs_nominal_pct"] == 98.3, d
print("PASS: cycle=379 FCC=4447 design=5015 nominal=4523 health_vs_design=88.7% health_vs_nominal=98.3%")
bh.print_table([d])
