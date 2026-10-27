import plistlib, sys
sys.path.insert(0, ".")
import battery_health as bh
# iPad-shaped sample built from a real iPad dump (2026-10-26):
# NO FullChargeCapacity anywhere; FCC equivalent is AppleRawMaxCapacity (top)
# and BatteryData FccComp1/2. NominalChargeCapacity is TOP level only.
sample = {"IORegistry": {
    "CurrentCapacity": 69, "CycleCount": 185, "Voltage": 4089,
    "IsCharging": True, "FullyCharged": False,
    "DesignCapacity": 7544, "NominalChargeCapacity": 6637,
    "AppleRawMaxCapacity": 6371, "AppleRawCurrentCapacity": 4321,
    "Temperature": 2589,
    "BatteryData": {
        "CycleCount": 185, "DesignCapacity": 7544,
        "FccComp1": 6371, "FccComp2": 6371,
        "StateOfCharge": 68, "Qmax": [7499],
        # deliberately NO FullChargeCapacity, NO NominalChargeCapacity here
    }}}
plist_bytes = plistlib.dumps(sample)
orig = bh.run
def fake(cmd):
    if "idevicediagnostics" in cmd[0]: return plist_bytes
    if "-q" in cmd: return b"BatteryCurrentCapacity: 69\nBatteryIsCharging: true\nFullyCharged: false\n"
    return b"DeviceName: Test iPad\nProductType: iPad14,1\nProductVersion: 17.0\n"
bh.run = fake
try: d = bh.get_battery_for_udid("IPADTEST")
finally: bh.run = orig
assert d["cycle_count"] == 185, d
assert d["full_charge_capacity_mah"] == 6371, d
assert d["design_capacity_mah"] == 7544, d
assert d["nominal_capacity_mah"] == 6637, d
assert d["health_vs_design_pct"] == 84.5, d
assert d["health_vs_nominal_pct"] == 96.0, d
print("PASS iPad shape: cycles=185 FCC(via AppleRawMax)=6371 design=7544 nominal=6637 health=84.5%/96.0%")
