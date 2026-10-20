# Repository integration — October 19, 2026

Role: **Repository Integration Engineer**.

## Initial state and preservation

Local HEAD `da434d493e199a54664052132e26b10603e315db`. Before fetch, origin tracked `82e19171f`; the fetched branch was `6557eac20a5d308ca22309a9b2f1a9e8404995ce`. Local HEAD was its ancestor, five commits behind. Those five commits published persistence validation, state/AI/fireball write checks and pair recovery; they were retained without duplication or history rewriting.

Initial index had no staged changes. There were **36 modified tracked files, zero staged additions, zero tracked deletions, and 203 untracked individual files** (seven collapsed status entries). Of the untracked files, 199 were generated files under build-macos-persist (3), build-tvos-simulator (128) and build-tvos-device (68); four were a packet validator header, sanitizer runner, packet test and older duplicate packager. Every path is inventoried in the private local audit manifest. No licensed game data, generated app, library, provisioning profile or user save is included in these commits.

Before changing the index, captured initial status, branch/remotes/log/diffs, tracked binary patches, hashes of all changed/untracked files, and a recoverable archive of modified/untracked non-build source. Generated outputs remain in place; their initial hashes and sizes are inventoried. Recovery evidence is outside the repository at `/Users/knagel/Documents/Codex/Descent-integration-2026-10-19`. App data backups remain in the separate device-install evidence directory. No reset, clean, force-push or deletion of unexplained work was used.

No competing active Descent writer was shown in the app task inventory; repeated source hashes were stable during review. This is an observation, not a filesystem lock. Hash checks and an expected-old-HEAD ref update protect publication from unnoticed changes. A separate index constructs explicit reviewed groups on the fetched remote parent; adopting that history updates the branch/index without checking out over working source. Two documentation files introduced only on the remote are materialized additively, preserving that history rather than treating their initial absence as deletions.

## Integration commits

- [`b63050459085`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/b630504590855746aa2f0c377b03f337376f5f21) build(apple): integrate tvOS and self-contained app packaging
- [`da2827ce9e2a`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/da2827ce9e2afe3187dcc07254a6c40c80a5dbc3) fix(input): integrate mobile controls and lifecycle handling
- [`e7003f9710f5`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/e7003f9710f5a1ddc5e0ebb29e47fb254807f9fb) fix(render): restore OpenGL state and pixel alignment
- [`1ce6af57f5b3`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/1ce6af57f5b39c1c1de1bfa00453ce59917d27e4) fix(engine): validate network packets and bound mission scans
- [`e9bbd5234812`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/e9bbd52348124c3912a8cd08c3957c3dd4a3db7b) fix(media): handle optional movies and pointer dismissal
- [`39887f6b709a`](https://github.com/KingdomDesignsConsulting/dxx-rebirth/commit/39887f6b709a038eff9f9ce20d42b58e361f8bcd) fix(persistence): retain existing staged config and pilot writes

### b63050459085 — build(apple): integrate tvOS and self-contained app packaging

- `.gitignore`
- `SConstruct`
- `scripts/build-ios.py`
- `scripts/package-macos.py`
- `common/include/3d.h`
- `common/include/d_gl.h`
- `common/include/ogl_extensions.h`
- `common/include/mobile_safe_area.h`
- `common/main/newmenu.h`
- `similar/main/newmenu.cpp`
- `similar/misc/physfsx.cpp`
- `similar/main/config.cpp`
- `similar/arch/ogl/gr.cpp`
- `similar/arch/ogl/ogl.cpp`

### da2827ce9e2a — fix(input): integrate mobile controls and lifecycle handling

- `common/arch/sdl/event.cpp`
- `common/arch/sdl/mobile_touch.h`
- `common/arch/sdl/timer.cpp`
- `common/include/event.h`
- `common/include/timer.h`
- `common/main/kconfig.h`
- `similar/main/kconfig.cpp`
- `similar/main/game.cpp`
- `similar/main/gauges.cpp`
- `similar/main/menu.cpp`
- `contrib/gamecontrollerdb.txt`
- `common/arch/sdl/gamecontroller.cpp`

### e7003f9710f5 — fix(render): restore OpenGL state and pixel alignment

- `similar/arch/ogl/gr.cpp`
- `similar/arch/ogl/ogl.cpp`

### 1ce6af57f5b3 — fix(engine): validate network packets and bound mission scans

- `common/include/net_udp_packet_validate.h`
- `similar/main/net_udp.cpp`
- `similar/main/multi.cpp`
- `similar/main/mission.cpp`
- `tests/net_udp_packet_safety_test.cpp`
- `scripts/test-net-udp-sanitizers.sh`

### e9bbd5234812 — fix(media): handle optional movies and pointer dismissal

- `d1x-rebirth/main/movie.cpp`
- `d2x-rebirth/main/movie.cpp`
- `similar/main/titles.cpp`

### 39887f6b709a — fix(persistence): retain existing staged config and pilot writes

- `similar/main/config.cpp`
- `similar/main/playsave.cpp`

## Review and provenance

Build/platform changes add tvOS SDK support, target-specific pinned SDL scene/text patches, minimized signing entitlements, bundled soundtrack/controller mappings, device icon handling, safe areas and data-home migration. Mac packaging includes recursive dylib bundling, SDL2-compat's runtime-loaded SDL3 and its executable-relative lookup, minimum-OS normalization and signature verification. These are the same existing workspace changes used for the recent Apple builds and Mac SDL startup repair, not an SDL API migration.

Input changes preserve direct touch actions, centered/integrated gyro controls, neutral/recenter behavior, background input release/timer reset and mobile menu handling. Renderer changes restore GL client state and pixel alignment and apply VSync after context creation. Engine changes validate datagram shape/sender and player/object bounds, terminate marker text and bound recursive mission scanning. The standalone validator and randomized sanitizer test were reviewed and included. Media changes permit pointer dismissal and suppress expected missing optional movies.

The controller database search fix is selectively included. Temporary per-button event watching and verbose GUID/mapping diagnostics stay in the working file, uncommitted. The duplicate `scripts/package-macos.py.new` predates the final SDL3 fix and stays untracked. Neither is deleted. Existing local coordination-artifact ignoring is retained; explicit reviewed generated Apple TV/persistence-build directories are now ignored. Selected documentation is tracked explicitly despite the coordination-directory rule. Ignoring was applied only after inventory/classification, not to conceal unknown files.

Existing config/pilot staged-write changes are retained in their own commit. These were present in the workspace and earlier Architect assignments. Integration does not implement additional PERSIST2/PERSIST3 behavior or assert their durability.

## Build verification

| Target | D1 | D2 | Evidence |
| --- | --- | --- | --- |
| macOS arm64 | PASS | PASS | Reuse recent full main builds; final SDL3 packaging/signature checks and visual menu launches; staged controller compiled and both games freshly relinked |
| iOS simulator arm64 | PASS | PASS | Reuse successful full main build; staged controller compiled and both games freshly relinked |
| iOS device arm64 | PASS | PASS | Reuse successful full signed main builds and four successful iPhone/iPad updates; staged controller compiled and both games freshly relinked |
| tvOS simulator arm64 | PASS | PASS | Reuse successful full main build; staged controller compiled and both games freshly relinked |
| tvOS device arm64 | PASS | PASS | Reuse successful full main build; staged controller compiled and both games freshly relinked; physical-device provisioning remains unavailable |

Full build evidence: [workspace build report](https://drive.google.com/file/d/18VND6Xb9vic5Jyn109ob6YvY88ffZKLy/view). It established successful compilation and packaging, not successful Mac launch. The subsequent [Mac SDL runtime repair](https://drive.google.com/file/d/1OwABUkVGIFAN2ck8Nn057UAjoJCTyNnZ/view) fixes the missing dlopen-only SDL3 dependency and verifies both main menus and normal exit. Mac and signed iOS bundles passed strict deep signature checks. All ten bundles contain game data and the expected arm64/platform metadata. iOS profiles expire October 22, 2026 UTC.

Published code matches the tested workspace except removal of temporary controller logging, one trailing-whitespace cleanup, and the sanitizer runner compatibility fix. The exact staged controller was freshly compiled for all five target configurations and linked into both games using existing main-checkout objects/recorded commands; all ten candidate links passed. These validation binaries are separate evidence outputs; existing user app bundles were not replaced by this audit. Other compilation inputs match the recent source manifest; the latest Mac packager matches the successful repair capture. Git version text in preexisting bundles can still describe the old dirty HEAD; source manifests, not that old label, establish provenance.

The sanitizer test initially aborted because Apple's ASan lacks LeakSanitizer. The runner now disables only leak detection on Darwin, preserving address/undefined-behavior checks. The existing deterministic cases and 250,000 randomized malformed inputs pass. No multiplayer gameplay, mobile UI, power-loss or destructive save test was repeated during integration. All commit diffs pass whitespace checks. Reviewed source contains no binary files or recognized credential/private-key patterns.

Normal outputs remain `build/D1X-Rebirth.app`, `build/D2X-Rebirth.app` and corresponding pairs in `build-ios-simulator/`, `build-ios-device/`, `build-tvos-simulator/`, `build-tvos-device/`. Mac packaging uses `scons -j8 sdl2=1` then `python3 scripts/package-macos.py`; mobile commands are in `scripts/README-ios.md`. Licensed data must be supplied privately. The persistent local dependency cache used for this build is outside /tmp.

## Persistence and outstanding work

PERSIST1 and PERSIST1-S state.cpp/ai.cpp/fireball.cpp remain byte-for-byte equal to validated remote `6557eac20a5d`; no persistence implementation is duplicated or reverted. [Final two PERSIST1-S regressions](https://drive.google.com/file/d/130s5lvVV7PS_odzl5g7vXR89_N9YIijP/view) passed against matching state source. Earlier forced rollback failures with an original file can still leave inconsistent active pairs while preserving recovery backups. Original-absence quarantine works in the two final tests; tertiary marker creation after both delete and rename fail remains untested. This is not universal transaction atomicity or release certification.

PERSIST2 remains open: existing config/pilot replacement compiles but its complete write/error/cleanup/restart guarantees are unvalidated. PERSIST3 remains open: header preflight does not guarantee deep corrupted restoration leaves world state intact. Exceptions, concurrency, fsync/power-loss, internal secret/co-op and mobile runtime coverage remain limited.

## Remaining local work and final branch state

Expected remaining status: ` M common/arch/sdl/gamecontroller.cpp` (preserved temporary diagnostics), `?? scripts/package-macos.py.new` (preserved older duplicate). Reviewed generated outputs/private assets remain ignored and present. No other source is intentionally omitted.

The integrated code checkpoint above is followed by this audit/documentation commit. The exact final branch SHA and post-push status are recorded in the final Work report and local `final-verification.json`; the remote push uses the normal fast-forward path to origin/codex/ios-port. No upstream push, force-push, validated-history rewrite, private assets or application binaries are included.
