# Apple mobile builds: iOS and tvOS

The shared source builds Descent 1 and Descent 2 for iPhone/iPad and Apple TV. Requirements: Xcode with the appropriate SDKs, Python 3, CMake, SCons and pkg-config. SDL2 2.32.10, PhysicsFS, SDL2_image and SDL2_mixer are pinned and built statically in a dependency cache. The script verifies archive hashes and patches target-specific SDL UIKit sources for scenes, orientation and tvOS text entry.

Licensed data stays in the Git-ignored `private assets` directory: `D1`, `D2`, `Music/D1`, `Music/D2`, and per-game icon catalogs under `Icons`. tvOS may use `Icons/D1/tvOS/Assets.xcassets` and its D2 counterpart, with `AppIcon.brandassets`. These private files are not available from GitHub. Use `--data-root` for another private location.

From the repository root:

```sh
python3 scripts/build-ios.py --target-os ios --platform simulator --cache "$HOME/Library/Caches/dxx-rebirth/apple-deps"
python3 scripts/build-ios.py --target-os tvos --platform simulator --cache "$HOME/Library/Caches/dxx-rebirth/apple-deps"
python3 scripts/build-ios.py --target-os ios --platform device --cache "$HOME/Library/Caches/dxx-rebirth/apple-deps"
python3 scripts/build-ios.py --target-os tvos --platform device --cache "$HOME/Library/Caches/dxx-rebirth/apple-deps"
```

Outputs are `build-ios-simulator/`, `build-ios-device/`, `build-tvos-simulator/` and `build-tvos-device/`, each containing `D1X-Rebirth.app` and `D2X-Rebirth.app`. A persistent cache avoids dependence on `/tmp` cleanup. A cache compiled at one path should be regenerated when moved because CMake records absolute paths.

Device builds need an Apple Development signing identity and matching platform/bundle-ID profiles to install:

```sh
python3 scripts/build-ios.py --target-os ios --platform device \
  --signing-identity "Apple Development: Your Name (TEAMID)" \
  --provisioning-profile-d1 /path/to/d1.mobileprovision \
  --provisioning-profile-d2 /path/to/d2.mobileprovision
```

Use `--target-os tvos` with tvOS profiles for Apple TV installation. An unsigned device bundle compiling successfully does not make it installable. Simulator bundles do not need device profiles.

Bundle IDs are `org.dxx-rebirth.d1x-ios`, `org.dxx-rebirth.d2x-ios`, and corresponding `-tvos` variants. Mobile profiles/configuration/saves live under each app's Application Support directory; legacy Preferences data is migrated when needed. The bundle contains controller mappings, a privacy manifest, game data and optional music. D1 Redbook roles use tracks 2 title, 3 briefing, 4 endlevel, 5 credits, 6 onward levels and the last track endgame. D2 uses track 2 title, 3 credits and 4 onward levels. Existing music settings remain configurable.

The renderer uses deprecated OpenGL ES 1.1. Successful compilation is not full gameplay validation. See `Documentation/Repository-Integration-2026-10-19.md` for build evidence, installation checks, validated persistence scope and remaining work.
