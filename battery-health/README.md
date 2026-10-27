# iPhone / iPad Battery Health — Mac companion app

Gets the details iOS does **not** show for older iPads (and hides on iPhones):

- Current charge %
- Cycle Count
- Full Charge Capacity (mAh)
- Design Capacity (mAh)
- Nominal Capacity (mAh)
- Remaining Capacity (mAh), Voltage, Is Charging
- Health = Full Charge / Design, and Full Charge / Nominal

## Why it has to run on the Mac

There is no public iOS API for cycle count / full-charge / design capacity,
and an app running *on* the iPad is sandboxed away from IORegistry.
Those values are only reachable from a paired Mac over USB via
`libimobiledevice` — the same commands you just used on your M4 Air:
`ideviceinfo` + `idevicediagnostics ioregentry AppleSmartBattery`.

## Setup on the M4 Air (one time)

```bash
brew install libimobiledevice
```

System python3 (3.9+) is enough — no pip installs needed.

## Run

Plug the iPad in with a data cable, unlock it, tap **Trust This Computer**.

Terminal / CLI (prints a clean table for *all* connected devices):

```bash
python3 battery_health.py
python3 battery_health.py --json
python3 battery_health.py --csv ipads.csv
python3 battery_health.py -u <UDID>     # one specific device
```

Window / GUI:

```bash
python3 battery_health.py --gui
```

Or double-click `BatteryHealth.command` in Finder
(first time: right-click → Open, and `chmod +x BatteryHealth.command battery_health.py`).

## Older iPads — what to expect

- **Most iPads with Lightning / USB-C** return `AppleSmartBattery` and
  give all fields above. Parser searches recursively, so fields that
  moved between iOS versions (BatteryData vs top-level) are still found.
- **Very old models / very old iOS** (e.g. early iOS 9 and earlier,
  30-pin era) may only return the simple `com.apple.mobile.battery`
  domain: charge %, charging, fully-charged — no cycle/FCC/design.
  The app detects that, labels the source, and doesn't invent numbers.
- If a device shows nothing at all: re-plug, unlock, Trust, then check
  `idevice_id -l` and `ideviceinfo` work for that UDID first.
- Multiple iPads plugged in at once (via a hub) are scanned in one run,
  which is the intended use for checking a batch of older iPads.

## Files

- `battery_health.py` — the app (CLI + GUI in one file, stdlib only)
- `BatteryHealth.command` — double-click launcher for the GUI
- `test_parser.py` — parser test using the iPhone sample from Oct 26
  (4447 / 5015 mAh = 88.7%, 379 cycles)
