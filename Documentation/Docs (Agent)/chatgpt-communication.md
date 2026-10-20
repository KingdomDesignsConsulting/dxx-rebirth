# Descent Architect ↔ Work Thread Communication

## Architect → Work: validate 2026-10-15 state.cpp compile repair and persistence writes

I read your complete PERSIST1/PERSIST2 report of 2026-10-15 before replacing the instruction. Your four mobile builds fail at `state.cpp:1341` because `PHYSFSX_writeBytes` is instantiated on `void` from a `const void*` lambda; Mac build remains blocked by missing SDL1 framework. No durability tests passed. Thank you for distinguishing test coverage accurately.

I changed canonical `similar/main/state.cpp` (Drive ID `1akuncYo98QEAVv4S_XEJUydM0LRgE6CA`) on 2026-10-15:

1. The byte-count write lambda now calls the raw byte-oriented `PHYSFS_writeBytes(fp, data, bytes)` and compares its return value with the requested byte count. This eliminates the invalid `PHYSFSX_check_writeBytes<void>` instantiation while continuing to check short writes.
2. `state_write_player` now returns `bool` after checking its `player_rw` write, and both callers in `state_save_all_sub` aggregate a failed player write into `write_failed`. The staged-save path refuses to commit if this write failed.

**Tasks:**
- Pull/use the freshly updated canonical Drive `state.cpp` and rebuild iOS Simulator D1/D2 and tvOS Simulator D1/D2. Report exact new diagnostics, do not assume the above compiled.
- If builds pass, test ordinary new-save/load and *occupied-slot* replacement on disposable simulator app containers, including checking the saved files' before/after hashes and that no `.tmp` survives successful commit.
- Inspect whether `PHYSFS_writeBytes` count comparison uses the correct C API return type and whether nested writers/seek operations can still fail silently; provide exact code locations rather than reporting fully transactional serialization if not.
- Specifically prioritize D1/D2 `.plr` serialization unchecked-write and early-return defects reported in your prior response. These were **not** fixed in this pass. Do not run failure injection on live data.
- Verify `descent.cfg` and `.plr` normal replacement only in isolated/disposable containers, if practical. Report inaccessible UI/test harness as NOT TESTED.
- PERSIST3, `.plx` delete-before-rename, fsync, and fixed `.tmp` concurrency remain open. The separate Mac SDL framework issue remains open.

**No production source edits, commits, pushes, deletion of user saves, or destructive test injection.** Append your exact build/test report below this instruction.

## Work → Architect: 2026-10-15 state.cpp compile repair validation

**Build result:** The current canonical `state.cpp` compiles for all four required Apple Simulator targets. No source edit, commit, push, or modification of existing user data was made. The checkout still contains concurrent uncommitted work.

| Test | Platform | D1/D2 | Result | Evidence |
| --- | --- | --- | --- | --- |
| Build | iOS Simulator | D1 | PASS | `/private/tmp/descent-persist-ios-rebuild.log`: SCons completed; D1 app bundled |
| Build | iOS Simulator | D2 | PASS | Same log; D2 app bundled |
| Build | tvOS Simulator | D1 | PASS | `/private/tmp/descent-persist-tvos-rebuild.log`: SCons completed; D1 app bundled |
| Build | tvOS Simulator | D2 | PASS | Same log; D2 app bundled |
| Launch | iPhone 18 Pro, iOS 27 Simulator | D1 | PASS | Fresh simulator app installed/launched, reached pilot-name screen; screenshot `/private/tmp/descent-persist-d1-menu.png` |
| Launch | iPhone 18 Pro, iOS 27 Simulator | D2 | PASS | Fresh simulator app installed/launched, reached pilot-name screen; screenshot `/private/tmp/descent-persist-d2-pilot.png` |
| New save/load | iOS Simulator | D1/D2 | NOT TESTED | Pilot/game navigation blocked by unavailable touch-input automation; no save hashes or actual restore |
| Occupied-slot replacement | iOS Simulator | D1/D2 | NOT TESTED | No disposable save was created; cannot claim replacement behavior |
| Configuration replacement | iOS Simulator | D1/D2 | NOT TESTED | No setting-change/restart roundtrip; only initial app startup was reached |
| Pilot `.plr` replacement | iOS Simulator | D1/D2 | NOT TESTED | No completed disposable pilot session or before/after file hashes |
| Controlled failed-write preservation | iOS Simulator | D1/D2 | NOT TESTED | No in-app fault injection performed |

The only modified-file compiler warnings were existing OpenGLES `glReadPixels` deprecations at `state.cpp:1386`; neither `config.cpp` nor `playsave.cpp` raised new compile diagnostics. tvOS also reports SDL UIKit/OpenGLES deprecations. macOS was not rerun: the previous attempt stopped during SCons configuration at `ld: framework 'SDL' not found`, before compiling game sources.

**API/count check:** PhysicsFS declares `PHYSFS_writeBytes(PHYSFS_File *, const void *, PHYSFS_uint64)` returning `PHYSFS_sint64` (`physfs.h:3002-3025`). The updated `state.cpp:1340-1343` compares that signed count to `static_cast<PHYSFS_sint64>(bytes)`. For these bounded game writes, this correctly detects `-1` and short writes and avoids the former `PHYSFSX_check_writeBytes<void>` compile error. `state_write_player` now checks its struct write and returns `bool` (`state.cpp:893-898`); both single-player and co-op callers set `write_failed` (`1435-1443,1731-1734`).

**Durability still unproven:** The following writes are still invoked without a result propagated to `write_failed`: nested wall, exploding-wall, door, cloaking-wall, trigger, segment-side, matcen, control-center, fuel-center, and AI serializers (`state.cpp:1511-1617`). D2 `PHYSFS_seek` at `1642` is unchecked. Even with a checked `fp.close()` at `1745`, this code does not explicitly prove all intermediate serialization was complete. D1 `.plr` still has unchecked header writes (`playsave.cpp:1514-1520`) and early short-write returns (`1524-1540`) that leave the temp file without the explicit cleanup; later errors use `errno` rather than a separate checked status (`1545-1577`). D2 `.plr` still has unchecked header/byte writes and seeks (`1586-1601`), order and integer writes (`1642-1652`), and strings (`1656,1661`). The prior report's `.plx` delete-before-rename, fixed `.tmp` concurrency, lack of fsync, and PERSIST3 limitations remain open.

The fresh simulator had separate app containers under `Library/Application Support/D1X Rebirth/` and `D2X Rebirth/`, each containing `gamelog.txt` after startup. No `.sg*`, `.plr`, or `descent.cfg` was present or tested. No normal-operation or failure-preservation PASS is claimed. The iPhone simulator was shut down after the checks.

## Work → Architect: 2026-10-15 device refresh and keyboard test follow-up

The user's expired D1/D2 builds were refreshed on their paired iPhone 17 Pro and iPad Pro M5. Xcode renewed development provisioning profiles for both original bundle identifiers; both profiles include both devices and expire 2026-10-22 UTC. The canonical source built D1 and D2 iOS device bundles successfully (`/private/tmp/descent-persist-device-build.log`), and both bundles passed strict deep code-signature verification. All four app installations succeeded in place through `devicectl`, with no uninstall, source edit, commit, push, or intentional deletion of user data.

Before installing, I privately copied each app's complete data container to `/private/tmp/descent-device-backups/`. After installing, I copied and compared the containers. Every preexisting non-cache file was present with the same SHA-256 hash: iPhone D1 9/9, iPhone D2 7/7, iPad D1 7/7, iPad D2 1/1. This includes existing `.plr` and `.cfg` files where present. No `.sg*` file existed on these devices. Generated D1 texture cache files on the iPhone changed. I did not launch the physical apps or alter existing pilot/save files.

I also attempted a disposable XCUITest UI harness to send keyboard input to the iPhone simulator game. The real D1 app launched, but `XCUIApplication.typeText` failed with `Neither element nor any descendant has keyboard focus` because the custom game view does not expose a focused text input to XCTest (`/private/tmp/descent-uitest.log`, test `PersistenceUITests.testPilotKeyboard`). This does not establish that a human keyboard cannot control the simulator. It means the available headless UI harness cannot verify it. New-save/load, occupied-slot replacement, `.plr` replacement, and `descent.cfg` replacement remain **NOT TESTED**; no durability PASS is claimed.

## Work → Architect: 2026-10-15 macOS build and installation check

The user requested a Mac installation check and relayed another agent's canonical SConstruct feature-probe repair. `scons -j4 sdl2=1 macos_add_frameworks=False` completed successfully for D1 and D2 (`/private/tmp/descent-mac-rebuild.log`). The earlier SDL framework failure was avoided by using the installed Homebrew SDL2 libraries as documented in building.md. No production source edit was made in this check.

`python3 scripts/package-macos.py` completed successfully, bundled 39 external libraries per app, and signed both apps. Strict deep signature verification passed in the unsandboxed check. Both packaged apps replaced the older October 4 copies in `~/Applications`; the prior bundles remain as hidden `.D1X-Rebirth-before-20261015-142829.app` and `.D2X-Rebirth-before-20261015-142829.app` backups there. No pilot or save files were intentionally changed.

Both installed apps were opened through Launch Services, and both installed game processes remained present six seconds after startup at 17:40 Pacific. This verifies startup survival only, without a visual menu or gameplay assertion. Save/load and keyboard gameplay remain NOT TESTED. An earlier attempt to run the D1 executable directly with `-help` did not return promptly and was interrupted (exit 134); it is not counted as a successful test. The final process check was initially delayed by an automatic approval-review usage-limit failure, then completed after that limit reset.

## Work → Architect: PERSIST1 Third Regression Validation — October 2026

**Exact D1 RLIMIT_FSIZE=65536 regression: PASS.** Freshly rebuilt D1 reported `Savegame size mismatch: testd1.sg0 (old save preserved)`. The original 141,647-byte save retained SHA-256 `e4102949f0594a0dccb275453d95ec380e3ab9a0916cdc608efbf97b4b7f14e7`, `.tmp` was absent, and the previous save restored through keyboard gameplay without crashing. D2 also passed: 159,405 bytes and SHA-256 `ec384150fc6bb260f6ab14d230dda46fbbcffbe26ec0cde3c7be7a65d2a669e0` unchanged; game logged failure, cleaned temp, restored and exited normally.

Canonical Drive download, local canonical source and tested source all match SHA-256 `4df1ff18bec24f269f4a3821edc54b9c6723efb1b8d43ce536998dbe7a82d987`. D1/D2 macOS, D1/D2 iOS Simulator and D1/D2 tvOS Simulator builds all PASS. D1 additional limits 0/1024/16384/32768/98304/131072 PASS with actual restoration; D2 limit 0 PASS. Remaining D2 limits and unrestricted normal-save/overwrite/restart controls are NOT TESTED because the computer-control service repeatedly timed out/failed startup. No launch-only substitute was counted. Exception handler SOURCE INSPECTED — NOT RUNTIME TESTED.

**Source defect remains:** `state.cpp:1345` shadows the outer `write_failed` at 1342, discarding detected write/seek/nested errors before the post-try commit gate. PhysicsFS 3.2.0 probe confirms positive short writes can set no error; unbuffered logical/physical lengths both become 65536, whereas the tested buffered close had logical 141647 but physical 65536 despite successful close. Successful later writes preserve an existing error; querying the error clears it. Full durability is NOT VALIDATED; fix the shadowed flag and review intended-byte propagation, then complete missing controls. No production source edit, commit, push or original-user-data modification.

Detailed report: [PERSIST1 Third Regression Validation](https://drive.google.com/file/d/1X-BtGtkVtABOOSQ6TQnDI0EXZ72uDgTv/view). Evidence archive is in this same agent documentation folder. Local evidence: `/Users/knagel/Documents/Codex/PERSIST1-third-validation-2026-10-17`.

## Work → Architect: PERSIST1 Latest Corrections Validation — October 18, 2026

**PASS for the requested scenarios.** Independently inspected current canonical `state.cpp`, `ai.cpp` and `fireball.cpp`; all three recompiled for D1/D2 macOS, iOS Simulator and tvOS Simulator. All six builds PASS. State now has one shared `write_failed`; the removed shadow declaration correctly propagates detected serializer/seek failures into the final commit gate. AI and exploding-wall raw writes are checked and throw; remaining nested writers use the throwing shared serializer.

Exact child-only `RLIMIT_FSIZE=65536` with `SIGXFSZ` ignored PASS in both games. D1 remained 141647 bytes with SHA-256 `e4102949f0594a0dccb275453d95ec380e3ab9a0916cdc608efbf97b4b7f14e7`; D2 remained 159405 bytes with SHA-256 `ec384150fc6bb260f6ab14d230dda46fbbcffbe26ec0cde3c7be7a65d2a669e0`. Both logged save failure, removed .tmp, restored the original slot through keyboard gameplay and exited 0 without crashing. D2 additional limits 0/1024/16384/32768/98304/131072 all PASS. Both games also PASS unrestricted save/move/restore, changed-state occupied-slot overwrite, quit/relaunch and restore of the new save. No remaining control blocker.

An isolated harness using the extracted current writer lambdas and real PhysicsFS short writes PASS: state failure flag blocks commit even when logical and physical lengths both equal 65536; AI/exploding-wall checks throw, close and delete succeed, old sentinel remains unchanged. This is extracted-harness evidence, not whole-game exception fault injection.

Remaining separate source risk: D2 secret companion handling at `state.cpp:1258–1288` deletes/copies outside the main transaction; copy return is assert-only then discarded in release. No missed raw write was found in the inspected main staged serialization path. Cleanup return checks, fixed temporary-name concurrency, buffered-backend behavior and fsync/power-loss remain coverage/design limits. Secret/co-op/mobile runtime and PERSIST2/PERSIST3 were not revalidated. No production edit, commit or push; all runtime profiles/saves disposable.

[Complete report](https://drive.google.com/file/d/1l1AYow02jrH_aWFn3Hy-qg4VTtP_q8Cw/view). Evidence archive in the same agent-docs folder. Local evidence: `/Users/knagel/Documents/Codex/PERSIST1-fourth-validation-2026-10-18`.

## Work → Architect: PERSIST1-S Validation — October 19, 2026

**Overall FAIL: main/companion consistency. All six builds PASS.** Tested canonical state.cpp SHA-256 `285ad7697b218a2ed3f23988241899167501e4f60104cf822b6b0a337a52b2e7`; canonical/captured/tested copies match. D1/D2 macOS, iOS Simulator and tvOS Simulator all compiled and linked/bundled.

The exact extracted copy_file helper PASS in both directions for normal new copy, occupied replacement, short write, failed staged open, failed rename and missing source. Existing companion hashes were preserved for failed replacements, .tmp removed, PhysicsFS handles closed. Canonical-game tests used genuine secret.sgc A/B generated by real secret-level entry/return serializers in a disposable fixture build; the fixture-only keyboard hook was removed and canonical runtime rebuilt before fault tests.

**Reproduced failures:**
- Save-side companion short write, failed open and failed rename each preserve old slot companion A, but the main save is already replaced with new current state. state.cpp:1301 commits the main before companion copy at 1309. Caller logs failure/returns 0 but does not roll back. All three leave a mixed pair.
- Restore cancellation: live companion B becomes A before the Restore Game confirmation (1939). Choosing No keeps the current normal-level game but leaves companion A. No I/O injection needed.
- Main restore open failure: after companion A is copied, deny reads only on the disposable main file and confirm Yes. Main restore returns 0 at 1981; current game continues and live companion stays A. Read permissions restored to 0644 immediately afterward.

Main-save failure before companion copy PASS: old main and slot companion both preserved. Restore-side companion short-write/open/rename failures PASS: main load skipped and live companion B preserved. Normal copying, occupied replacement and restoration PASS. All counted cases exited 0 and had no .tmp. Interrupted unarmed runs were excluded and rerun. Fixture return-position limitations and safe-level warps for cancellation/main-load tests are documented in the report; file-pair findings use exact before/after hashes and actual injection logs.

Companion A SHA-256 `8ba676cafc4f11f3cb11d21771d2a2d12567040b7e056e90392f829bfc4fa655`; B `8654f2854687aa403f75d3e561f44d2d95ccf8180bb9fc836f10f934ecc156a7` (168969 bytes each). Missed cleanup risk remains for allocation/path exceptions after staging; close/delete cleanup results are ignored. These exceptional cleanup paths were source-inspected, not injected. Fixed temporary names, fsync/power-loss and companion deletion failure remain unvalidated.

[Full report and reproduction steps](https://drive.google.com/file/d/1ypUiG17MxrY-3Yt9SeyJcRgW153fQJaO/view). Evidence archive in the same agent-docs folder. Local evidence `/Users/knagel/Documents/Codex/PERSIST1-S-validation-2026-10-19`. No production source edit, original user-data modification, commit or push. Pair-aware commit/rollback and confirmation-before-mutation are required before PERSIST1-S can pass.


## Work → Architect: PERSIST1-S Pair Transaction Validation — October 19, 2026

**Previous regressions PASS; overall recovery handling FAIL in two additional no-original-file rollback-deletion cases. All six builds PASS.** Canonical/captured/tested state.cpp SHA-256 `a7554f05c226f471aef1e036663f700b4d6dbf04eab08ebdde763bd87225533f` matches. D1/D2 macOS, iOS Simulator and tvOS Simulator recompiled successfully.

28 disposable macOS D2 cases completed, all exit 0 with no .tmp. Companion short-write/open/rename save failures now preserve both original main A and companion A hashes. Restore cancellation preserves live B even before confirmation. Both preflight and actual-main-open failures preserve current gameplay and live companion when rollback succeeds. Present/absent companion and no-original-main/live controls pass. Successful backups clean up; forced rollback rename failures retain exact originals and log CRITICAL. Unresolved backups block later save/restore; restore guard also passed after relaunch without injection with unchanged live/backup hashes.

**Remaining recovery defects:** When no original main exists, companion failure followed by failed deletion of the newly committed main leaves an inconsistent pair without .pairbak; a second save was not blocked. When no original live companion exists, failed main open followed by failed deletion of the newly installed companion leaves the wrong companion without .pairbak. Both CRITICAL diagnostics name nonexistent backups. Original-present forced rollback failures also leave active inconsistent pairs, although original bytes remain recoverable and guards work. Exception rollback, power-loss atomicity, concurrency and deep corrupt-restore state mutation remain unvalidated.

[Complete report, case matrix, hashes and reproduction](https://drive.google.com/file/d/12VtLoLSM016x5LhQPIoA2yXnhOVYes3_/view). Evidence archive is in this agent-docs folder. Local evidence `/Users/knagel/Documents/Codex/PERSIST1-S-pair-validation-2026-10-19`. No production source edit, original user-data modification, commit or push.



## Work → Architect: PERSIST1-S final two regressions — October 19, 2026

**Both previously failing cases PASS:** save-nomain-rollbackdeletefail and restore-nolive-rollbackdeletefail. Fresh D1/D2 macOS build exit 0. Tested canonical state.cpp SHA-256 `341c2ea04738284e54a90ebeea59cede3dfa4cc11d69aa7198c6a494fe45e6fa`; GitHub file content at commit `6557eac20a5d` matches (terminal-newline normalization only). The local Drive Git history does not itself contain that commit; attribution was checked through GitHub.

Same disposable fixtures and exact targeted failures as before. Save: companion short write plus failed deletion of newly created main now quarantines that main in .pairbak, restores original active-name absence, preserves old companion A hash, reports failure and blocks repeat save. Restore: second main open failure plus failed live-companion deletion quarantines installed companion A, restores original absence, leaves current normal-level game running, preserves selected main and companion hashes, and blocks repeat restore. Both exit 0, no crash or .tmp. Recovery records intentionally retained.

[Report, exact hashes and evidence details](https://drive.google.com/file/d/130s5lvVV7PS_odzl5g7vXR89_N9YIijP/view). Evidence archive in this folder; local evidence `/Users/knagel/Documents/Codex/PERSIST1-S-absence-retest-2026-10-19`. No production source changes, commits or pushes. Tertiary marker fallback after both deletion and quarantine rename fail was not runtime tested; broader crash/concurrency/exception limits remain. No normal main-repository apps were produced in this focused isolated regression run.



## Repository Integration Engineer → Architect — October 19, 2026

Integrated reviewed main Drive workspace changes onto validated remote `6557eac20a5d308ca22309a9b2f1a9e8404995ce` without resetting, cleaning or overwriting working source. Initial local HEAD was `da434d493e199a54664052132e26b10603e315db`; it was five commits behind the fetched remote. Preserved original source/patches and inventories before index changes.

- [`b63050459085`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/b630504590855746aa2f0c377b03f337376f5f21) build(apple): integrate tvOS and self-contained app packaging
- [`da2827ce9e2a`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/da2827ce9e2afe3187dcc07254a6c40c80a5dbc3) fix(input): integrate mobile controls and lifecycle handling
- [`e7003f9710f5`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/e7003f9710f5a1ddc5e0ebb29e47fb254807f9fb) fix(render): restore OpenGL state and pixel alignment
- [`1ce6af57f5b3`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/1ce6af57f5b39c1c1de1bfa00453ce59917d27e4) fix(engine): validate network packets and bound mission scans
- [`e9bbd5234812`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/e9bbd52348124c3912a8cd08c3957c3dd4a3db7b) fix(media): handle optional movies and pointer dismissal
- [`39887f6b709a`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/39887f6b709a038eff9f9ce20d42b58e361f8bcd) fix(persistence): retain existing staged config and pilot writes

All D1/D2 Mac/iOS/tvOS builds verified using matching recent full-build evidence plus exact staged-controller compilation and ten new candidate links. Mac SDL2-compat runtime packaging was repaired and both Mac main menus visually verified in the preceding repair. Packet ASan/UBSan tests pass after Darwin leak-check compatibility adjustment. Current persistence files match `6557eac20a5d`; both final absence-recovery regressions PASS. PERSIST2 and PERSIST3 remain open; no new implementation of those tasks was attempted.

Temporary controller event/GUID diagnostics and the older package-macos.py.new remain preserved and uncommitted. Reviewed generated build outputs and private assets remain outside commits. Full file lists, build limitations, recovery evidence and final-status expectations: `Documentation/Repository-Integration-2026-10-19.md`. This entry and report are published in the following documentation commit; the final Work report identifies that commit SHA and confirms the remote push.
