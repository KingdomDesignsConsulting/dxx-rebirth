# PERSIST1-S: D2 secret companion pair transactions

Date: October 19, 2026 (America/Los_Angeles)

## Status

**PASS for the final two absence-recovery regressions; broader coverage limits remain.**

The canonical implementation includes the final `restore_absent_file()` correction and persistent recovery handling for the two no-original-file rollback-deletion failures found by the second validation. Work subsequently validated the two outstanding regressions against matching source from commit `6557eac20a5d`. This closes those regressions, not every failure mode or release-readiness criterion.

This publication synchronizes `similar/main/state.cpp` from the live canonical Google Drive source and adds this document. It does not introduce a further implementation cycle, run fault injection, or modify real user saves. DGSS save formats and versions are unchanged. The previously published PERSIST1 state serialization checks remain intact; `ai.cpp` and `fireball.cpp` are unchanged by this commit.

## Architecture and implementation

A normal D2 single-player slot consists of the main save and its numbered secret-level companion. The running game also uses `secret.sgc`. Updating either companion independently can leave a valid individual file paired with the wrong main save or current game.

`copy_file()` stages the destination at `<destination>.tmp`, checks read and write counts (including positive short writes), checks close, verifies the staged size, and publishes by rename. It returns failure to the caller rather than treating expected I/O failures as fatal. This protects an individual destination; the callers coordinate the logical pair.

For ordinary D2 slot saves, `state_save_all()` refuses to overwrite an unresolved `<main>.pairbak`. If an old main exists, it first copies it to that recovery backup. After the checked main save commits, it copies the live companion to the numbered companion, or removes the numbered companion when the live companion is absent. Companion failure rolls the main back by renaming its backup, or restores original absence when no main existed. Failure returns without a success message. Successful operations remove the old backup; cleanup failure warns and leaves a recovery guard.

For ordinary slot restores, confirmation occurs before live companion mutation. A preflight checks that the selected main opens and has DGSS magic; it does not validate the entire save. Existing `secret.sgc.pairbak` blocks another transaction. The caller backs up an existing live companion, installs or removes the selected companion, then calls main restoration. A failed main restoration rolls the live companion back, including restoration of original absence. Successful restoration cleans the backup.

`restore_backup_file()` renames a recovery backup over its active destination and retains the backup when rename fails. `restore_absent_file()` handles the distinct case where there were no original bytes to back up: it first tries deletion of the newly created active file. If deletion fails, it tries quarantining that file under the recovery name. If both fail, it attempts to create an empty persistent recovery marker. Existing recovery records are never deliberately overwritten. Callers report critical failures; subsequent transactions detect recovery records across application relaunch. A quarantine record or empty marker represents unresolved original absence, not an old valid save.

The pair uses multiple filesystem operations. This provides checked recovery for ordinary failures, not an atomic two-file commit across process termination or power loss.

## Validation history and evidence

Sources:

- [Live canonical state.cpp](https://drive.google.com/file/d/1akuncYo98QEAVv4S_XEJUydM0LRgE6CA/view), 109,805 bytes at publication capture.
- [First PERSIST1-S validation](https://drive.google.com/file/d/1ypUiG17MxrY-3Yt9SeyJcRgW153fQJaO/view), tested source SHA-256 `285ad7697b218a2ed3f23988241899167501e4f60104cf822b6b0a337a52b2e7`.
- [Pair-aware transaction validation](https://drive.google.com/file/d/12VtLoLSM016x5LhQPIoA2yXnhOVYes3_/view), tested source SHA-256 `a7554f05c226f471aef1e036663f700b4d6dbf04eab08ebdde763bd87225533f`.

Both reports used disposable fixtures and processes; their runtime results are macOS D2 results. They do not establish iOS or tvOS runtime behavior.

| Revision | Build coverage | Runtime outcome |
| --- | --- | --- |
| First staged-companion implementation | PASS: D1/D2 on macOS, iOS Simulator, tvOS Simulator | Individual companion-copy failures preserved the destination. Overall FAIL: companion failures after main commit left mixed pairs; canceled restores and later main-open failures changed the live companion prematurely. |
| Pair-aware transaction revision | PASS: all six builds, each compiling state.cpp | Previous ordinary pair-preservation regressions PASS; canceled restore and failed main-open protection PASS. Existing-backup recovery guard after D2 relaunch PASS. Two additional no-original-file rollback-deletion cases FAIL. |
| Final absence-recovery correction published here | Not independently rebuilt or tested in this assignment | **IMPLEMENTED — VALIDATION PENDING**. Earlier results must not be attributed to this final revision. |

The second report records 28 isolated runtime cases, all exiting without a crash or surviving `.tmp`. It confirms ordinary rollback for companion short writes, staged-open failures, commit-rename failures, main-save failure, cancellation, and selected early/late main-open failures. Deliberately failed rollback with an original file retained the exact original bytes in `.pairbak`, logged a critical failure, and blocked later operations where exercised, but could leave the active pair inconsistent.

The two additional failures were `save-nomain-rollbackdeletefail` and `restore-nolive-rollbackdeletefail`. With no original main or live companion, failure to delete the newly installed file left inconsistent active state without a persistent recovery record; a subsequent save could accept that state as its baseline. The Architect subsequently added `restore_absent_file()` and persistent recovery handling. The reports predate that correction.

## Remaining defects, concerns, and coverage limits

- Power-loss durability is unproven: there is no file/directory fsync guarantee, and separate main/companion operations are not crash-atomic.
- When rollback and every fallback recovery mechanism fail, active state can remain inconsistent and even marker creation can fail. Critical logging does not itself recover the pair.
- Fixed `.tmp` and `.pairbak` names are vulnerable to concurrent access; no simultaneous-writer validation is claimed.
- PERSIST3 remains open: preflight checks only open and magic. A deeper restore failure may partially mutate game state; companion rollback cannot undo those mutations.
- Allocation/path exceptions and exceptions during main restoration are not coordinated by the ordinary return-value rollback paths. Some cleanup close/delete results remain unchecked.
- Some backup cleanup failures can retain recovery state and block future operations. Restore backup creation/cleanup failures and allocation failures need additional coverage.
- Internal secret-level entry/exit callers, co-op paths, PERSIST2, full corrupted-save handling, and mobile runtime were outside the second report's coverage.

## Next required tests

Independently capture and hash the final canonical revision, then rebuild D1/D2 for macOS, iOS Simulator, and tvOS Simulator. In disposable data only, rerun both no-original-file rollback-deletion regressions and verify original absence, quarantine/marker contents, accurate diagnostics, and transaction blocking after application relaunch. Exercise deletion failure with successful quarantine, deletion plus quarantine failure with successful marker creation, and failure of all recovery mechanisms; preserve evidence of the resulting active and recovery states.

Rerun the ordinary pair-preservation, cancellation, main-open, backup-retention, cleanup, and restart-guard matrix against that exact final revision. Record before/after hashes and surviving artifacts. Separately validate deeper restoration failures under PERSIST3, exception paths, mobile runtime, concurrent access, and interruption/power-loss behavior. These are required future tests, not tests performed by this publication assignment.

## Repository Integration Engineer update — October 19, 2026

[Final two regression report](https://drive.google.com/file/d/130s5lvVV7PS_odzl5g7vXR89_N9YIijP/view): `save-nomain-rollbackdeletefail` and `restore-nolive-rollbackdeletefail` PASS against state.cpp SHA-256 `341c2ea04738284e54a90ebeea59cede3dfa4cc11d69aa7198c6a494fe45e6fa`, matching the published checkpoint. Original absence was restored through quarantine, companion/main hashes preserved where applicable, repeat operations blocked, both processes exited 0. The later complete workspace build passed D1/D2 macOS, iOS simulator/device and tvOS simulator/device compilation. Earlier pending statements and proposed test matrices above describe the historical publication state; they must be read with this update.

Tertiary marker creation after both delete and quarantine rename fail was not runtime tested. Restart guarding was previously tested with an existing backup; restart with the new quarantine records was not separately retested. PERSIST2 and PERSIST3, deeper world-state mutation, exceptions, concurrency and power-loss limits remain open. No further persistence implementation was introduced during integration.
