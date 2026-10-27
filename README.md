# iOS Device Utils

A growing collection of small Mac-side utilities for iPhone and iPad
devices — tools that get information / do jobs iOS itself doesn't expose
in an app, using `libimobiledevice` from a paired Mac over USB.

Each utility lives in its own folder, is self-contained, and can be run
on its own. That keeps the monorepo simple today, and makes it easy to
split a tool out into its own repo later if it grows big enough to
need independent releases.

## Utilities

| Folder | What it does | Status |
|---|---|---|
| [`battery-health/`](battery-health/) | Cycle count, Full Charge / Design / Nominal capacity (mAh), health %, voltage, charging state — for iPhones and older iPads that don't show this on-device | Working prototype, tested on an iPhone sample (379 cycles, 4447/5015 mAh = 88.7%). Not yet tested on an actual iPad. |

<!-- Tomorrow's tools go here as new rows + new folders, e.g.
     device-info/, backup-check/, storage-report/ ... -->

## Common setup (all utilities)

On the Mac (Apple Silicon or Intel):

```bash
brew install libimobiledevice
```

Plug the device in with a data cable, unlock it, and tap
**Trust This Computer** when prompted.

## Repo layout

```
ios-device-utils/
  README.md          <- this index, one row per utility
  battery-health/    <- utility #1
    battery_health.py
    BatteryHealth.command
    README.md
    test_parser.py
  <next-utility>/    <- utility #2, same self-contained pattern
    ...
```
