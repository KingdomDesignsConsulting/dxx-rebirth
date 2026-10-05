# Descent architect handoff

Updated October 5, 2026. This is a working map for the architecture and programming thread. Check the live source and Git state before relying on any status stated here. Read `GITHUB_WORKFLOW.md`, `scripts/README-ios.md`, `README.md`, and `COPYING.txt` alongside this file.

## Mission and division of work

The user wants Descent 1 and Descent 2 to play properly and as consistently as practical on macOS, iPhone, and iPad. This fork of DXX-Rebirth is the sole active source tree. The separate Descent-Mobile tree has been retired. The architect thread owns architectural analysis, design decisions, programming plans, and source changes it agrees to undertake with the user. This existing Codex thread remains the build, installation, and hands-on testing agent. Coordinate before changing shared build scripts or asking for device tests; both threads may see the same working tree.

The architect thread has already picked up controller and tvOS discussion. Treat those as ongoing design work, not as implemented features. Do not assume tvOS builds exist. The user explicitly excludes Android builds unless they later request them. For proposed features, identify concrete code locations, platform behavior, migration steps, and the tests needed on Mac, iPhone, and iPad. Keep D1 and D2 behavior aligned where shared code permits.

## Source and runtime map

- Canonical checkout: `/Users/knagel/My Drive/dxx-rebirth`. `/Users/Shared/Main Hard Drive/My Projects/Projects In Progress/Applications/Games to make/Descent` is a symlink to it. The former nested `Descent/dxx-rebirth` path is obsolete.
- `SConstruct` is the main SCons build definition. `d1x-rebirth/` and `d2x-rebirth/` contain game-specific source and resources; `similar/` and `common/` hold substantial shared code. Inspect compile guards and game-specific call sites before changing shared behavior.
- `common/arch/sdl/event.cpp` processes mobile input and motion, coordinates the touch overlay, and exposes the mobile control functions declared in `common/include/event.h`. `common/arch/sdl/mobile_touch.h` lays out and handles touch controls. `common/include/mobile_safe_area.h` provides screen insets.
- `similar/main/kconfig.cpp` converts the current gyroscope rates into pitch, heading, and bank controls when mobile “Use Mouse” is enabled. The touch mode and intro skip are connected in `similar/main/game.cpp` and `similar/main/gameseq.cpp`.
- `similar/main/newmenu.cpp` and `similar/main/menu.cpp` are central to game menus and mobile hit testing. Inspect both coordinate conversions and menu layout before changing taps, keyboard behavior, Back/Go buttons, or dismissing a menu by touching outside it.
- `similar/arch/ogl/ogl.cpp` draws the touch overlay. `similar/main/gauges.cpp` applies mobile safe insets to in-game HUD text. These paths matter for Dynamic Island and other display cutouts.
- `scripts/build-ios.py` builds and packages both iOS apps; `scripts/package-macos.py` packages Mac apps. Both derive the repo root from their own resolved file path, so they already work from the canonical checkout or its symlink. Build guidance is in `scripts/README-ios.md`.

## Build and assets

The iOS port uses SDL2, PhysicsFS, SDL2_image, SDL2_mixer, and OpenGL ES 1.1. The Mac build uses the regular SCons path. iOS simulator and device outputs go under `build-ios-simulator/` and `build-ios-device/`; Mac outputs go under `build/`. Device installation uses the user's existing development signing setup. Do not infer that a successful compile proves device input, motion, audio, or graphics work.

The Git-ignored `private assets/` directory has licensed D1/D2 game data, music, and app icons. It must remain local; never stage, commit, push, quote, or attach its contents. Recovery patches from the old mobile tree are in `private assets/Legacy source recovery`. A fresh clone lacks these assets. Scripts accept `--data-root` when assets are elsewhere. The Mac bundles can use `D1-Data` and `D2-Data` next to their `.app` bundles.

## Known interaction and testing expectations

The user provides direct observations, often with iPhone screenshots. Treat a correction or bug report as a request to fix the behavior, then verify the precise menu/game state and both game variants where relevant. Explain changes in plain language with the practical effect, what was tested, and what still needs device verification. Give short progress updates during longer work; avoid repeated permission questions for work already authorized.

Prior device testing uncovered keyboard overlap on pilot naming, menu tap scaling, missing touch actions in dialogs, gameplay control layout, safe-area clipping, and gyro axis/continuity problems. Several fixes have been made, but the current implementation must be inspected and re-tested rather than assumed correct. The user previously permitted launching the games for testing; coordinate GPU-intensive runs with the build/testing thread, since the user may run other GPU tests. The user does not want Android work.

For iPhone/iPad UI, account for keyboard appearance only when text entry is needed, safe areas, screen size, orientation, and equivalent D1/D2 flow. For controller or tvOS design, assess SDL support, focus/navigation, gamepad mapping, platform graphics and audio availability, signing, packaging, and actual test hardware before promising a scope or schedule. Record decisions and any unresolved assumptions.

## GitHub and collaboration workflow

Our public fork is `https://github.com/KingdomDesignsConsulting/dxx-rebirth`; `origin` points there. `upstream` points to `https://github.com/dxx-rebirth/dxx-rebirth`. Work is on `codex/ios-port`, tracking `origin/codex/ios-port`. The fork retains original DXX-Rebirth attribution and license. `GITHUB_WORKFLOW.md` is the detailed Git and credential handoff; follow it.

At the start of each work session, inspect the current branch, status, remotes, and recent commits. The repository may have user-owned untracked files (currently `Documentation/Docs (Agent)/`), so stage only intended files and inspect the staged list. Do not use broad staging. Preserve the configured user author identity. Commit coherent changes and push to the fork when appropriate. Do not push to upstream or force-push shared history without the user's authorization. Never commit licensed data, generated apps, signing material, or credentials.

When the architect and build/testing thread work concurrently, avoid overlapping edits. Provide the builder with the commit hash, changed behavior, target platforms, exact test scenario, and expected result. The builder should report actual build, install, and device results separately from architectural claims. Reconcile failures back into the source rather than treating a build as final proof.
