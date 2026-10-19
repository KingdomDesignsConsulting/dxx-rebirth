# PERSIST1: staged save replacement validation (2026-10-18)

Status: **PASS for tested D1/D2 save replacement and failure-preservation scenarios**, not an assertion of universal crash/power-loss durability.

## Implemented
- `similar/main/state.cpp`: stage saves in a sibling temporary file; check direct serialization results, nested serializer failures, expected versus physical temp-file length, close, and rename before success; clean temp on failures; fix shadowed `write_failed` so serializer errors block commit.
- `similar/main/ai.cpp`: detect positive short byte writes and throw to abort the save transaction.
- `similar/main/fireball.cpp`: detect short writes of exploding-wall records and count header.

Existing DGSS save format unchanged (D1 v7, D2 v22).

## Evidence
Work report (2026-10-18): https://drive.google.com/file/d/1l1AYow02jrH_aWFn3Hy-qg4VTtP_q8Cw/view

- All six builds passed: D1/D2 on macOS, iOS Simulator, tvOS Simulator.
- D1 and D2 at RLIMIT_FSIZE=65536, SIGXFSZ ignored: save rejected; previous file SHA-256 and size unchanged; temp removed; previous save loaded without crash.
- D2 failure thresholds 0, 1024, 16384, 32768, 65536, 98304, 131072 all passed. D1 thresholds passed in the preceding validation, with 65536 repeated after the latest fix.
- Normal D1/D2 save, occupied-slot overwrite, quit/relaunch, and restore passed using disposable profiles. Source/harness checks verified nested failure propagation.
- No production user saves modified.

## Remaining scope
- D2 secret-level companion-file copy is **not** covered: preemptive deletion and direct replacement may destroy an old companion on failed copy. Track separately as PERSIST1-S.
- Fixed .tmp names can race with concurrent writers. No file/directory fsync guarantees sudden-power-loss persistence. Catch-path cleanup return values and exceptional runtime paths are not fully tested.
- PERSIST2 configuration/pilot and PERSIST3 corrupt-load safety remain separate work.

Commit this tested correction separately from any future PERSIST1-S implementation.
