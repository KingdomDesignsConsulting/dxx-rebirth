#!/usr/bin/env python3
"""Build D1X and D2X iOS app bundles from the shared Rebirth source tree.

Requires Xcode, CMake, SCons, pkg-config, and the user's licensed game data.
The pinned third-party sources and compiled dependencies stay in a cache
outside this repository. No licensed assets are added to Git.
"""

import argparse
import hashlib
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tarfile
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
VERSIONS = {
    "SDL2": ("2.32.10", "https://github.com/libsdl-org/SDL/releases/download/release-2.32.10/SDL2-2.32.10.tar.gz"),
    "SDL2_image": ("2.8.12", "https://github.com/libsdl-org/SDL_image/releases/download/release-2.8.12/SDL2_image-2.8.12.tar.gz"),
    "SDL2_mixer": ("2.8.1", "https://github.com/libsdl-org/SDL_mixer/releases/download/release-2.8.1/SDL2_mixer-2.8.1.tar.gz"),
    "physfs": ("3.2.0", "https://github.com/icculus/physfs/archive/refs/tags/release-3.2.0.tar.gz"),
}
SHA256 = {
    "SDL2": "5f5993c530f084535c65a6879e9b26ad441169b3e25d789d83287040a9ca5165",
    "SDL2_image": "393f5efb50536ec13ca4f4affb69cc9966d3c3f969e6c5e701faddf9f9785381",
    "SDL2_mixer": "cb760211b056bfe44f4a1e180cc7cb201137e4d1572f2002cc1be728efd22660",
    "physfs": "1991500eaeb8d5325e3a8361847ff3bf8e03ec89252b7915e1f25b3f8ab5d560",
}


def run(*args, env=None):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=ROOT, env=env, check=True)


def source(cache, name):
    version, url = VERSIONS[name]
    dirname = f"physfs-release-{version}" if name == "physfs" else f"{name}-{version}"
    src = cache / dirname
    if src.exists():
        return src
    archive = cache / f"{name}-{version}.tar.gz"
    if not archive.exists():
        print(f"Downloading {name} {version}", flush=True)
        urllib.request.urlretrieve(url, archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != SHA256[name]:
        raise RuntimeError(f"Checksum mismatch for {archive}: {digest}")
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            target = (cache / member.name).resolve()
            if not target.is_relative_to(cache.resolve()):
                raise RuntimeError(f"Unsafe archive path: {member.name}")
        tf.extractall(cache)
    if not src.exists():
        raise RuntimeError(f"Missing extracted source: {src}")
    return src


def configure_and_build(src, out, *options):
    run("cmake", "-S", src, "-B", out, *options)
    run("cmake", "--build", out, "--parallel", "4")


def write_pc(path, name, version, include, library_dir, libs):
    path.write_text(
        f"Name: {name}\nDescription: iOS static {name}\nVersion: {version}\n"
        f"Cflags: -I{include}\nLibs: -L{library_dir} {libs}\n"
    )


def build_dependencies(cache, platform):
    suffix = "simulator" if platform == "simulator" else "device"
    sdk = "iphonesimulator" if platform == "simulator" else "iphoneos"
    common = (
        "-DCMAKE_SYSTEM_NAME=iOS", f"-DCMAKE_OSX_SYSROOT={sdk}",
        "-DCMAKE_OSX_ARCHITECTURES=arm64", "-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0",
    )
    sdl = source(cache, "SDL2")
    physfs = source(cache, "physfs")
    image = source(cache, "SDL2_image")
    mixer = source(cache, "SDL2_mixer")
    sdl_out = cache / f"sdl2-{suffix}"
    physfs_out = cache / f"physfs-{suffix}"
    image_out = cache / f"image-{suffix}"
    mixer_out = cache / f"mixer-{suffix}"
    configure_and_build(sdl, sdl_out, *common, "-DSDL_STATIC=ON", "-DSDL_SHARED=OFF", "-DSDL_TEST=OFF")
    configure_and_build(physfs, physfs_out, *common,
                        "-DCMAKE_POLICY_VERSION_MINIMUM=3.5", "-DPHYSFS_BUILD_STATIC=ON",
                        "-DPHYSFS_BUILD_SHARED=OFF", "-DPHYSFS_BUILD_TEST=OFF", "-DPHYSFS_BUILD_DOCS=OFF")
    sdl_lib = f"-DSDL2_LIBRARY={sdl_out / 'libSDL2.a'}"
    sdl_headers = f"-DSDL2_INCLUDE_DIR={sdl / 'include'}"
    no_host_sdl = "-DSDL2_DIR=SDL2_DIR-NOTFOUND"
    configure_and_build(image, image_out, *common, sdl_lib, sdl_headers, no_host_sdl,
                        "-DBUILD_SHARED_LIBS=OFF", "-DSDL2IMAGE_SAMPLES=OFF",
                        "-DSDL2IMAGE_AVIF=OFF", "-DSDL2IMAGE_TIF=OFF",
                        "-DSDL2IMAGE_WEBP=OFF", "-DSDL2IMAGE_JXL=OFF",
                        "-DSDL2IMAGE_DEPS_SHARED=OFF", "-DSDL2IMAGE_VENDORED=OFF")
    configure_and_build(mixer, mixer_out, *common, sdl_lib, sdl_headers, no_host_sdl,
                        "-DBUILD_SHARED_LIBS=OFF", "-DSDL2MIXER_SAMPLES=OFF",
                        "-DSDL2MIXER_VENDORED=OFF", "-DSDL2MIXER_DEPS_SHARED=OFF",
                        "-DSDL2MIXER_MOD=OFF", "-DSDL2MIXER_OPUS=OFF",
                        "-DSDL2MIXER_WAVPACK=OFF", "-DSDL2MIXER_MIDI_FLUIDSYNTH=OFF",
                        "-DSDL2MIXER_MIDI_NATIVE=OFF")
    pc = cache / f"pkgconfig-{suffix}"
    pc.mkdir(exist_ok=True)
    write_pc(pc / "sdl2.pc", "sdl2", VERSIONS["SDL2"][0], sdl / "include", sdl_out, "-lSDL2 -lSDL2main")
    write_pc(pc / "physfs.pc", "physfs", VERSIONS["physfs"][0], physfs / "src", physfs_out, "-lphysfs -lz")
    write_pc(pc / "SDL2_image.pc", "SDL2_image", VERSIONS["SDL2_image"][0], image / "include", image_out, "-lSDL2_image")
    write_pc(pc / "SDL2_mixer.pc", "SDL2_mixer", VERSIONS["SDL2_mixer"][0], mixer / "include", mixer_out, "-lSDL2_mixer")
    return pc, sdk


def bundle_game(build, game, data_root, platform, signing_identity, provisioning_profile):
    short = game.lower()
    binary = build / f"{short}x-rebirth" / f"{short}x-rebirth"
    app = build / f"{game}X-Rebirth.app"
    app.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, app / binary.name)
    source_data = data_root / game
    if not source_data.is_dir():
        raise RuntimeError(f"Licensed game data folder is missing: {source_data}")
    required = ("descent.hog", "descent.pig") if game == "D1" else ("DESCENT2.HOG", "DESCENT2.HAM", "groupa.pig")
    available = {path.name.casefold() for path in source_data.iterdir() if path.is_file()}
    missing = [name for name in required if name.casefold() not in available]
    if missing:
        raise RuntimeError(f"Missing {game} game data: {', '.join(missing)}")
    for path in source_data.iterdir():
        if path.is_file() and not path.name.startswith("."):
            shutil.copy2(path, app / path.name)
    tracks = sorted((data_root / "Music" / game).glob("*.mp3"))
    if tracks:
        music = app / "Music"
        levels = music / "Levels"
        levels.mkdir(parents=True, exist_ok=True)
        playlist = []
        for path in tracks:
            if path.name.startswith("02 "):
                shutil.copy2(path, music / "title.mp3")
            elif path.name.startswith("03 "):
                shutil.copy2(path, music / "briefing.mp3")
            elif path.name[:2].isdigit() and int(path.name[:2]) >= 4:
                track_name = f"{path.name[:2]}.mp3"
                shutil.copy2(path, levels / track_name)
                playlist.append(f"Music/Levels/{track_name}")
        if playlist:
            (music / "Levels.m3u").write_text("\n".join(playlist) + "\n")
    info = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": f"Descent {game[-1]}",
        "CFBundleExecutable": binary.name,
        "CFBundleIdentifier": f"org.dxx-rebirth.{short}x-ios",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": f"{game}X-Rebirth",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.61.0",
        "CFBundleVersion": "1",
        "LSRequiresIPhoneOS": True,
        "MinimumOSVersion": "15.0",
        "UIDeviceFamily": [1, 2],
        "UIRequiresFullScreen": True,
        "UISupportedInterfaceOrientations": ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"],
        "UISupportedInterfaceOrientations~ipad": ["UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"],
        "UILaunchScreen": {},
    }
    icon_source = data_root / "Icons" / game / "Assets.xcassets"
    if not (icon_source / "AppIcon.appiconset").is_dir():
        raise RuntimeError(f"Missing {game} app icon catalog: {icon_source}")
    icon_info = build / f"{short}x-icon-info.plist"
    run("xcrun", "actool", "--compile", app,
        "--platform", "iphonesimulator" if platform == "simulator" else "iphoneos",
        "--minimum-deployment-target", "15.0", "--target-device", "iphone",
        "--target-device", "ipad", "--app-icon", "AppIcon",
        "--output-partial-info-plist", icon_info, icon_source)
    info.update(plistlib.loads(icon_info.read_bytes()))
    with (app / "Info.plist").open("wb") as f:
        plistlib.dump(info, f)
    if provisioning_profile:
        shutil.copy2(provisioning_profile, app / "embedded.mobileprovision")
    if signing_identity:
        profile = subprocess.run(
            ["openssl", "cms", "-verify", "-inform", "DER", "-noverify", "-in", str(provisioning_profile)],
            check=True, capture_output=True,
        )
        profile_data = plistlib.loads(profile.stdout)
        entitlements = profile_data["Entitlements"]
        if not entitlements["application-identifier"].endswith("." + info["CFBundleIdentifier"]):
            raise RuntimeError(f"Provisioning profile does not match {info['CFBundleIdentifier']}")
        entitlements_path = build / f"{short}x-entitlements.plist"
        with entitlements_path.open("wb") as f:
            plistlib.dump(entitlements, f)
        run("codesign", "--force", "--sign", signing_identity,
            "--entitlements", entitlements_path, "--timestamp=none", app)
    print(f"Built {app} ({platform})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("simulator", "device"), default="simulator")
    parser.add_argument("--data-root", type=Path, default=ROOT / "private assets")
    parser.add_argument("--cache", type=Path, default=Path("/private/tmp/rebirth-ios-deps"))
    parser.add_argument("--signing-identity", help="Apple Development certificate for device installation")
    parser.add_argument("--provisioning-profile-d1", type=Path, help="matching Descent 1 development provisioning profile")
    parser.add_argument("--provisioning-profile-d2", type=Path, help="matching Descent 2 development provisioning profile")
    args = parser.parse_args()
    profiles = {"D1": args.provisioning_profile_d1, "D2": args.provisioning_profile_d2}
    if args.platform == "device" and (args.signing_identity or any(profiles.values())) and not (args.signing_identity and all(profiles.values())):
        parser.error("device signing requires --signing-identity and both game provisioning profiles")
    if args.platform == "simulator" and (args.signing_identity or any(profiles.values())):
        parser.error("simulator bundles do not need device signing")
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    pc, sdk = build_dependencies(cache, args.platform)
    target = "arm64-apple-ios15.0-simulator" if args.platform == "simulator" else "arm64-apple-ios15.0"
    wrapper = cache / f"clangxx-{args.platform}"
    wrapper.write_text(f'#!/bin/sh\nexec /usr/bin/clang++ -target {target} -isysroot "$(xcrun --sdk {sdk} --show-sdk-path)" "$@" -Wno-error=unused-result\n')
    wrapper.chmod(0o755)
    env = os.environ.copy()
    env["PKG_CONFIG_PATH"] = ""
    env["PKG_CONFIG_LIBDIR"] = str(pc)
    build = ROOT / f"build-ios-{args.platform}"
    run("scons", "-j4", "host_platform=ios", f"builddir={build.name}", f"CXX={wrapper}",
        "sdlimage=1", "sdlmixer=1", "screenshot=none", "lto=0", "git_status=0",
        "macos_add_frameworks=0", "macos_bundle_libs=0", env=env)
    for game in ("D1", "D2"):
        bundle_game(build, game, args.data_root.resolve(), args.platform,
                    args.signing_identity, profiles[game])


if __name__ == "__main__":
    main()
