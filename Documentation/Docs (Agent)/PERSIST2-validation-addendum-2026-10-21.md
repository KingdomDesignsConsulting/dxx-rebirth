## PERSIST2 validation addendum — 2026-10-21

The final configuration-write guard revision was retested by the Persistence Validation Engineer.

- **D1/D2 macOS builds: PASS** before and after one correction.
- **13 final checks: PASS**, including first-pilot creation, alternate interactive pilot selection, failed creation, repeated recovered cold starts, and repeated refused cold starts.
- **14 harness game processes exited 0** (13 final checks plus the retained initial reproduction); the focused retest did not re-execute every previous fault-injection case.
- The confirmed omission was the first-pilot creation path: `RegisterPlayer` called `MakeNewPlayerFile` without traversing the selection-listbox callback, so successful creation failed to lift the suppression of final configuration writes. The corrected `menu.cpp` verifies the new pilot with `read_player_file()`, refreshes configuration, and calls `persist2_resume_config_writes_after_pilot_load()` only on successful read.
- A failed first-pilot creation remains guarded and does not create `descent.cfg` during the tested normal exit.
- **Remaining**: a failed first-pilot creation may still proceed to the main menu because `RegisterPlayer` ignores `MakeNewPlayerFile`'s result; physical power-loss durability, cross-process locking, automatic repair of invalid markers, and iOS/tvOS validation are not established.
- PERSIST2 is **OPEN**, not globally certified or complete.

Report: https://drive.google.com/file/d/1IQH6hNHnwfKm1Tu3Ql_LFEqD8UwFb_or/view

Corrected canonical Drive `similar/main/menu.cpp`: 106256 bytes, SHA-256 `8fe6d4de84825f6538c50b38b3f27d33b39bac195cb60812956f3476b5018190`.
