# PERSIST2 — pilot and configuration persistence (2026-10-20)

Status: **implemented in source; partial validation; not a power-loss atomicity guarantee**.

## Scope

- Staged and checked serialization for D1 and D2 pilot options (`.plx`) and player records (`.plr`); staged global configuration (`descent.cfg`).
- Coordinated `.cfg`/`.plx`/`.plr` backup, absent-original, completion, rollback, and recovery handling, including `.p2bak`, `.p2absent`, and `.p2complete` recovery records.
- Startup recovery gate: avoid loading a pilot if rollback/recovery cannot safely complete; reload configuration after recovery before further configuration writes.
- Command-line `-pilot` respects failed reads and clears a refused selection.
- GUI pilot-selection path refreshes the restored configuration before writing last-player settings.
- Checked staged writes for network profile (`.ngp`) and D1 effectiveness (`.eff`).
- Latest shutdown guard revision: a failed command-line pilot load suppresses unsafe final configuration writes until a successful interactive pilot load clears the guard.

## Files

- `similar/main/playsave.cpp`: PERSIST2 serialization, transaction recovery, NGP and EFF writer protections.
- `similar/main/config.cpp`: checked staged global configuration replacement.
- `similar/main/inferno.cpp`: command-line pilot startup recovery/guard logic.
- `similar/main/menu.cpp`: successful interactive pilot load re-enables final config saving.

## Evidence and validation chronology

1. Initial PLX fault matrix: **FAIL**; unchecked writes published incomplete files.
   Report: https://drive.google.com/file/d/1AYjfRHzzU0UJlaMkbccO9LNG4GqNyK7A/view
2. Coordinated transaction matrix: D1/D2 macOS builds **PASS**; ordinary failures and retained-record guards **PASS**, forced rollback limitations documented.
   Report: https://drive.google.com/file/d/1ibbnn7DhDfP50FxR7xDDCpuoJVkjl76y/view
3. Recovery and profile writers: **244 scenarios** (including 56 deliberate process terminations); NGP/EFF tested preservation **PASS**, but startup configuration replacement and ignored `-pilot` refusal **FAIL**.
   Report: https://drive.google.com/file/d/1FaX8dU_ph1DdWhQ95IaRc3YvBu4gsk2X/view
4. Targeted startup retest: D1/D2 builds **PASS**, both startup regressions **PASS** across **34 test processes** including repeated cold starts and interactive selection. Identified a session-wide final configuration-save suppression after refused `-pilot`.
   Report: https://drive.google.com/file/d/10Iu4VnqZl9OfIXjTwEXdOBbUT3HFUs5n/view
5. Subsequent guard-scope adjustment in `inferno.cpp` and `menu.cpp` installed in canonical Drive on 2026-10-20. **Not yet compiled or fault-injection tested**. No acceptance claim for this last revision.

## Known limitations and follow-up

- If a `-pilot` load is refused and no later successful interactive pilot load occurs, the final configuration write stays suppressed. Unrelated settings changed in that session may not persist. The latest revision restores normal saving *after* successful pilot selection, but does not solve the no-successful-pilot case.
- Invalid/empty completion records may require manual intervention. Recovery refuses unsafe operations rather than silently assuming data is valid.
- Process termination was tested; **physical power loss, fsync/directory durability and concurrent-process exclusion were not established**.
- Targeted failures and specific original-presence masks were tested; no exhaustive claim for all I/O failure points or platforms. iOS/tvOS builds and runtime tests are outside these macOS validation reports.
- Some writer APIs log failures without propagating an error to a UI modal.

## Release gates

Before calling PERSIST2 complete, build D1/D2 using these exact committed source blobs, retest both refusal/recovery paths and the new guard transition, and verify profile hashes and recovery-record preservation. Keep PERSIST1/PERSIST1-S regression evidence and do not conflate it with PERSIST2 acceptance.

These commits record source and documentation, **not final PERSIST2 acceptance**.
