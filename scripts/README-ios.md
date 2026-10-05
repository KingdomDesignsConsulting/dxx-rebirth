# iOS build

The Rebirth source tree builds both Descent 1 and Descent 2 for iPhone and iPad. This uses SDL2, PhysicsFS, SDL2_image, and SDL2_mixer as static iOS libraries. The build script downloads pinned releases into `/private/tmp/rebirth-ios-deps`; it does not add those dependencies or licensed game files to Git.

Requirements: Xcode with the iOS SDK, CMake, SCons, pkg-config, and licensed data in the sibling `Descent-Mobile/D1`, `Descent-Mobile/D2`, and `Descent-Mobile/Music/D1` and `D2` folders. Use `--data-root` to choose another data location.

From the repository root:

```sh
python3 scripts/build-ios.py --platform simulator
python3 scripts/build-ios.py --platform device
```

The results are `build-ios-simulator/D1X-Rebirth.app`, `build-ios-simulator/D2X-Rebirth.app`, and equivalent device bundles. The simulator bundles need no signing. Device bundles need a matching Apple Development certificate and provisioning profile for installation:

```sh
python3 scripts/build-ios.py --platform device \
  --signing-identity "Apple Development: Your Name (TEAMID)" \
  --provisioning-profile-d1 /path/to/d1.mobileprovision \
  --provisioning-profile-d2 /path/to/d2.mobileprovision
```

The two apps use separate bundle IDs and preferences. The build bundles the licensed `.hog`, `.pig`, `.ham`, and related files at the app root, and copies tracks 04 onward to `Music/Levels` with a numbered playlist. Track 02 is the title song; track 03 is the briefing song. Rebirth selects these tracks by default when the playlist is present. User music settings saved inside each app remain configurable.

The build compiles each game's existing `Assets.xcassets/AppIcon.appiconset` from the sibling Descent-Mobile source tree into its app bundle. These icon assets remain outside the Rebirth Git repository.

The macOS build continues to use the regular `scons` command. The iOS renderer currently uses OpenGL ES 1.1, which Apple marks as deprecated. Both games have reached the pilot-name screen on iPhone and iPad simulators. Gameplay graphics, touch controls, the software keyboard, and audio still need testing on a physical device.
