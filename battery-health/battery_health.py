#!/usr/bin/env python3
"""
Battery Health for iPhone / iPad (including older iPads)
Mac companion tool using libimobiledevice.

Why a Mac app and not an on-iPad app?
  iOS gives apps no public API for cycle count, Full Charge Capacity,
  Design Capacity or Nominal Capacity. Those values live in IORegistry /
  diagnostics, which are only reachable from a paired Mac over USB
  via libimobiledevice (ideviceinfo / idevicediagnostics).

Requires:
  brew install libimobiledevice
  python3 (macOS system python3 3.9+ is fine)

Usage:
  python3 battery_health.py            # scan all connected devices, print table
  python3 battery_health.py --gui      # simple window
  python3 battery_health.py --json     # machine-readable
  python3 battery_health.py --csv out.csv
  python3 battery_health.py -u <UDID>  # only one device
"""
import argparse
import csv
import json
import plistlib
import subprocess
import sys


def run(cmd):
    """Run a command, return stdout bytes or None."""
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return out
    except subprocess.CalledProcessError as e:
        return e.output or b""
    except FileNotFoundError:
        return None


def check_tools():
    missing = []
    for tool in ("idevice_id", "ideviceinfo", "idevicediagnostics"):
        out = run(["which", tool])
        if not out:
            # which via shell builtin fallback: try running --help style probe
            probe = run([tool])
            if probe is None:
                missing.append(tool)
    if missing:
        print("Missing tools: " + ", ".join(missing), file=sys.stderr)
        print("Install them with:  brew install libimobiledevice", file=sys.stderr)
        sys.exit(2)


def list_devices():
    out = run(["idevice_id", "-l"])
    if not out:
        return []
    text = out.decode("utf-8", "ignore")
    return [line.strip() for line in text.splitlines() if line.strip()]


def parse_key_value_output(raw_bytes):
    result = {}
    if not raw_bytes:
        return result
    text = raw_bytes.decode("utf-8", "ignore")
    for line in text.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            result[k.strip()] = v.strip()
        elif ":" in line:
            k, v = line.split(":", 1)
            result[k.strip()] = v.strip()
    return result


def find_first(obj, key):
    """Recursively search dicts/lists for a key. Return its value or None."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        # Prefer BatteryData first if present
        if "BatteryData" in obj and isinstance(obj["BatteryData"], dict):
            val = find_first(obj["BatteryData"], key)
            if val is not None:
                return val
        for v in obj.values():
            val = find_first(v, key)
            if val is not None:
                return val
    elif isinstance(obj, list):
        for item in obj:
            val = find_first(item, key)
            if val is not None:
                return val
    return None


def get_battery_for_udid(udid):
    info = parse_key_value_output(run(["ideviceinfo", "-u", udid]))
    batt_domain = parse_key_value_output(
        run(["ideviceinfo", "-u", udid, "-q", "com.apple.mobile.battery"])
    )

    data = {
        "udid": udid,
        "device_name": info.get("DeviceName"),
        "product_type": info.get("ProductType"),      # e.g. iPad5,3
        "product_version": info.get("ProductVersion"),  # iOS version
        "current_capacity_pct": None,
        "is_charging": None,
        "fully_charged": None,
        "cycle_count": None,
        "full_charge_capacity_mah": None,
        "design_capacity_mah": None,
        "nominal_capacity_mah": None,
        "raw_max_capacity_mah": None,
        "remaining_capacity_mah": None,
        "voltage_mv": None,
        "health_vs_design_pct": None,
        "health_vs_nominal_pct": None,
        "source": None,
        "notes": [],
    }

    # Fallback values from the simple battery domain
    if batt_domain.get("BatteryCurrentCapacity"):
        try:
            data["current_capacity_pct"] = int(batt_domain["BatteryCurrentCapacity"])
        except ValueError:
            pass
    if "BatteryIsCharging" in batt_domain:
        data["is_charging"] = batt_domain["BatteryIsCharging"] == "true"
    if "FullyCharged" in batt_domain:
        data["fully_charged"] = batt_domain["FullyCharged"] == "true"

    # Main source: IORegistry AppleSmartBattery (works on iPhones and
    # most iPads, including many older models)
    raw = run(["idevicediagnostics", "-u", udid, "ioregentry", "AppleSmartBattery"])
    parsed = None
    if raw:
        try:
            parsed = plistlib.loads(raw)
        except Exception:
            # Some very old iOS versions return a slightly different
            # payload; try the generic diagnostics routes as fallback
            parsed = None

    if parsed is not None:
        data["source"] = "ioregentry AppleSmartBattery"
        ioreg = parsed.get("IORegistry", parsed) if isinstance(parsed, dict) else {}

        def grab(key):
            # Look in BatteryData / IORegistry first, then anywhere
            if isinstance(ioreg, dict) and isinstance(ioreg.get("BatteryData"), dict):
                if key in ioreg["BatteryData"]:
                    return ioreg["BatteryData"][key]
            if isinstance(ioreg, dict) and key in ioreg:
                return ioreg[key]
            return find_first(parsed, key)

        data["cycle_count"] = grab("CycleCount")
        data["full_charge_capacity_mah"] = grab("FullChargeCapacity")
        data["design_capacity_mah"] = grab("DesignCapacity")
        data["nominal_capacity_mah"] = grab("NominalChargeCapacity")
        data["raw_max_capacity_mah"] = grab("AppleRawMaxCapacity")
        data["remaining_capacity_mah"] = grab("AppleRawCurrentCapacity")
        if data["remaining_capacity_mah"] is None:
            data["remaining_capacity_mah"] = grab("RemainingCapacity")
        data["voltage_mv"] = grab("Voltage")
        cc = grab("CurrentCapacity")
        if cc is not None:
            data["current_capacity_pct"] = cc
        charging = grab("IsCharging")
        if charging is not None:
            data["is_charging"] = bool(charging)
        fully = grab("FullyCharged")
        if fully is not None:
            # In IORegistry FullyCharged can be 0/1 or bool
            data["fully_charged"] = bool(fully)
    else:
        data["source"] = "com.apple.mobile.battery only"
        data["notes"].append(
            "AppleSmartBattery not returned by this device/iOS version - "
            "health capacities unavailable, showing live charge only."
        )

    # Prefer AppleRawMaxCapacity if FullChargeCapacity was missing
    if data["full_charge_capacity_mah"] is None and data["raw_max_capacity_mah"] is not None:
        data["full_charge_capacity_mah"] = data["raw_max_capacity_mah"]

    fcc = data["full_charge_capacity_mah"]
    design = data["design_capacity_mah"]
    nominal = data["nominal_capacity_mah"]
    if isinstance(fcc, (int, float)) and isinstance(design, (int, float)) and design:
        data["health_vs_design_pct"] = round(fcc / design * 100.0, 1)
    if isinstance(fcc, (int, float)) and isinstance(nominal, (int, float)) and nominal:
        data["health_vs_nominal_pct"] = round(fcc / nominal * 100.0, 1)

    return data


def fmt(v, suffix=""):
    if v is None:
        return "-"
    return str(v) + suffix


def print_table(rows):
    if not rows:
        print("No iPhone/iPad found. Plug one in, unlock it, and tap Trust.")
        return
    for d in rows:
        print("=" * 62)
        name = d["device_name"] or "Unknown device"
        ptype = d["product_type"] or "-"
        iosv = d["product_version"] or "-"
        print(name + "  (" + ptype + ", iOS " + iosv + ")")
        print("-" * 62)
        print("Current Capacity:       " + fmt(d["current_capacity_pct"], "%"))
        print("Cycle Count:            " + fmt(d["cycle_count"]))
        print("Full Charge Capacity:   " + fmt(d["full_charge_capacity_mah"], " mAh"))
        print("Design Capacity:        " + fmt(d["design_capacity_mah"], " mAh"))
        print("Nominal Capacity:       " + fmt(d["nominal_capacity_mah"], " mAh"))
        print("Remaining Capacity:     " + fmt(d["remaining_capacity_mah"], " mAh"))
        if d["health_vs_design_pct"] is not None:
            print("Health (FCC / Design):  " + str(d["health_vs_design_pct"]) + "%")
        if d["health_vs_nominal_pct"] is not None:
            print("Health (FCC / Nominal): " + str(d["health_vs_nominal_pct"]) + "%")
        print("Voltage:                " + fmt(d["voltage_mv"], " mV"))
        print("Is Charging:            " + fmt(d["is_charging"]))
        print("Fully Charged:          " + fmt(d["fully_charged"]))
        print("Source:                 " + fmt(d["source"]))
        for note in d["notes"]:
            print("Note: " + note)
    print("=" * 62)


def run_gui(rows_provider):
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError:
        print("Tkinter not available in this python3 - use the CLI output instead.", file=sys.stderr)
        print_table(rows_provider())
        return

    root = tk.Tk()
    root.title("iPhone / iPad Battery Health")
    root.geometry("760x420")

    cols = ("device", "ios", "charge", "cycles", "fcc", "design", "nominal", "health")
    tree = ttk.Treeview(root, columns=cols, show="headings")
    headings = {
        "device": "Device", "ios": "iOS", "charge": "Charge %",
        "cycles": "Cycles", "fcc": "Full Charge", "design": "Design",
        "nominal": "Nominal", "health": "Health vs Design",
    }
    for c in cols:
        tree.heading(c, text=headings[c])
        tree.column(c, width=95)
    tree.column("device", width=160)
    tree.pack(fill="both", expand=True, padx=8, pady=8)

    status = tk.Label(root, text="Plug in a device, unlock + Trust, then Refresh.")
    status.pack(pady=4)

    def refresh():
        for item in tree.get_children():
            tree.delete(item)
        rows = rows_provider()
        if not rows:
            status.config(text="No device found.")
            return
        for d in rows:
            device_label = (d["device_name"] or d["product_type"] or "Device")
            health = "-"
            if d["health_vs_design_pct"] is not None:
                health = str(d["health_vs_design_pct"]) + "%"
            tree.insert("", "end", values=(
                device_label, d["product_version"] or "-",
                fmt(d["current_capacity_pct"], "%"), fmt(d["cycle_count"]),
                fmt(d["full_charge_capacity_mah"]), fmt(d["design_capacity_mah"]),
                fmt(d["nominal_capacity_mah"]), health,
            ))
        status.config(text="Done - " + str(len(rows)) + " device(s). Values in mAh.")

    btn = tk.Button(root, text="Refresh", command=refresh)
    btn.pack(pady=6)
    refresh()
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description="iPhone/iPad battery health via libimobiledevice")
    ap.add_argument("--gui", action="store_true", help="open a simple window")
    ap.add_argument("--json", action="store_true", help="print JSON")
    ap.add_argument("--csv", metavar="FILE", help="also write CSV to FILE")
    ap.add_argument("-u", "--udid", help="only check this UDID")
    args = ap.parse_args()

    check_tools()

    def collect():
        udids = [args.udid] if args.udid else list_devices()
        return [get_battery_for_udid(u) for u in udids]

    if args.gui:
        run_gui(collect)
        return

    rows = collect()

    if args.csv:
        fields = list(rows[0].keys()) if rows else [
            "udid", "device_name", "product_type", "product_version",
            "current_capacity_pct", "cycle_count", "full_charge_capacity_mah",
            "design_capacity_mah", "nominal_capacity_mah", "health_vs_design_pct",
        ]
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print("Wrote " + args.csv)

    if args.json:
        print(json.dumps(rows, indent=2, default=str))
    else:
        print_table(rows)


if __name__ == "__main__":
    main()
