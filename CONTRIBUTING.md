# Contributing — adding a new utility

Internal pattern for keeping this monorepo consistent as new
iPhone/iPad utilities are added. Not needed to *use* the utilities —
see the main README for that.

1. Create a new top-level folder named for the tool.
2. Keep it self-contained (its own README + entry point) so it can
   be split out later if needed.
3. Reuse the device-listing / plist-parsing ideas from
   `battery-health/` first; only extract a shared `common/` library
   once a second tool actually duplicates the same code.
4. Add a row to the utilities table in the main README.
