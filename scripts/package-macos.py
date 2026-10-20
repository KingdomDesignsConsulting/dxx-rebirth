#!/usr/bin/env python3
"""Add licensed game data and music to locally built Mac app bundles.

The source data remains outside Git.  Run after the SCons Mac build.
"""

from __future__ import annotations

import argparse
import hashlib
import plistlib
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent.parent



def package_music(resource_root: Path, data_root: Path, game: str, *, keep_original_names: bool = False) -> None:
    music = resource_root / "Music"
    if music.exists():
        shutil.rmtree(music)
    tracks = sorted((data_root / "Music" / game).glob("*.mp3"))
    if not tracks:
        return

    numbered: dict[int, Path] = {}
    for path in tracks:
        prefix = path.name.split(" ", 1)[0]
        if prefix.isdigit():
            numbered[int(prefix)] = path

    music.mkdir(parents=True, exist_ok=True)
    if keep_original_names:
        for path in tracks:
            shutil.copy2(path, music / path.name)

    roles: dict[str, int] = {}
    level_numbers: list[int] = []
    if game == "D1":
        # D1 Redbook semantics: 2 title, 3 briefing, 4 end-level,
        # 5 credits, 6..N-1 levels, final track endgame.
        roles = {"title": 2, "briefing": 3, "endlevel": 4, "credits": 5}
        if numbered:
            last_track = max(numbered)
            roles["endgame"] = last_track
            level_numbers = [n for n in sorted(numbered) if 6 <= n < last_track]
    else:
        # D2 Redbook semantics: 2 title, 3 credits, 4+ level tracks.
        roles = {"title": 2, "credits": 3}
        level_numbers = [n for n in sorted(numbered) if n >= 4]

    for role, number in roles.items():
        if path := numbered.get(number):
            shutil.copy2(path, music / f"{role}.mp3")

    if level_numbers:
        levels = music / "Levels"
        levels.mkdir(parents=True, exist_ok=True)
        playlist = []
        for number in level_numbers:
            path = numbered[number]
            track_name = f"{number:02d}.mp3"
            shutil.copy2(path, levels / track_name)
            playlist.append(f"Music/Levels/{track_name}")
        (music / "Levels.m3u").write_text("\n".join(playlist) + "\n")



def _dylib_references(binary: Path) -> list[str]:
    """Return the dependency names recorded in a Mach-O file."""
    proc = subprocess.run(["otool", "-L", str(binary)], check=True, capture_output=True, text=True)
    return [line.strip().split(" (", 1)[0] for line in proc.stdout.splitlines()[1:]]


def _external_dylibs(binary: Path) -> list[str]:
    return [dep for dep in _dylib_references(binary) if dep.startswith("/") and
            not dep.startswith(("/System/Library/", "/usr/lib/"))]


def _bundle_external_dylibs(app: Path) -> None:
    executable_dir = app / "Contents" / "MacOS"
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    executables = [executable_dir / info["CFBundleExecutable"]]
    if not executables:
        raise RuntimeError(f"No executable found in {executable_dir}")
    binary = executables[0]
    # Packaging must be repeatable after install_name_tool has modified an
    # earlier bundle.  Start from SCons' unmodified executable each time.
    built_binary = ROOT / "build" / binary.name / binary.name
    if not built_binary.is_file():
        raise RuntimeError(f"Missing unmodified build executable: {built_binary}")
    shutil.copy2(built_binary, binary)
    frameworks = app / "Contents" / "Frameworks"
    if frameworks.exists():
        shutil.rmtree(frameworks)
    frameworks.mkdir(parents=True, exist_ok=True)
    copied: dict[Path, Path] = {}
    source_for: dict[Path, Path] = {binary: binary}
    pending = [binary]
    visited: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        original = source_for[current]
        for dependency in _dylib_references(current):
            if dependency == f"@rpath/{current.name}":
                continue  # The dylib's own install name is not a dependency.
            if dependency.startswith(("/System/Library/", "/usr/lib/")):
                continue
            if dependency.startswith("@rpath/"):
                source = original.parent / dependency.removeprefix("@rpath/")
            elif dependency.startswith("@loader_path/"):
                source = original.parent / dependency.removeprefix("@loader_path/")
            elif dependency.startswith("/"):
                source = Path(dependency)
            else:
                raise RuntimeError(f"Unsupported library reference in {current}: {dependency}")
            if not source.is_file():
                raise RuntimeError(f"Missing external library: {dependency}")
            canonical = source.resolve()
            if canonical not in copied:
                # A dependency chain can contain different libraries with the
                # same basename (SDL2 and SDL2-compat, for example).
                digest = hashlib.sha256(str(canonical).encode()).hexdigest()[:12]
                destination = frameworks / f"{digest}-{source.name}"
                shutil.copy2(source, destination)
                destination.chmod(destination.stat().st_mode | 0o200)
                copied[canonical] = destination
                source_for[destination] = source
                subprocess.run(["install_name_tool", "-id", f"@rpath/{destination.name}",
                                str(destination)], check=True)
                pending.append(destination)
                # Homebrew SDL2 may be sdl2-compat.  SDL3 is loaded with
                # dlopen, so otool cannot discover this runtime dependency.
                # Its lookup includes libSDL3.dylib beside the compat library.
                if "libSDL2" in source.name and b"SDL2COMPAT_DEBUG_LOGGING" in source.read_bytes():
                    sdl3_dir = subprocess.check_output(
                        ["pkg-config", "--variable=libdir", "sdl3"], text=True).strip()
                    sdl3_source = Path(sdl3_dir) / "libSDL3.dylib"
                    if not sdl3_dir or not sdl3_source.is_file():
                        raise RuntimeError("sdl2-compat requires an installed SDL3 runtime")
                    sdl3_canonical = sdl3_source.resolve()
                    if sdl3_canonical not in copied:
                        sdl3_destination = frameworks / "libSDL3.dylib"
                        shutil.copy2(sdl3_source, sdl3_destination)
                        sdl3_destination.chmod(sdl3_destination.stat().st_mode | 0o200)
                        copied[sdl3_canonical] = sdl3_destination
                        source_for[sdl3_destination] = sdl3_source
                        subprocess.run(["install_name_tool", "-id", "@rpath/libSDL3.dylib",
                                        str(sdl3_destination)], check=True)
                        pending.append(sdl3_destination)
                    # dlopen's @loader_path lookup can resolve relative to
                    # the main executable.  Provide its documented fallback.
                    runtime_link = executable_dir / "libSDL3.dylib"
                    if runtime_link.is_symlink():
                        runtime_link.unlink()
                    if not runtime_link.exists():
                        runtime_link.symlink_to("../Frameworks/libSDL3.dylib")
            destination = copied[canonical]
            loader_ref = (f"@loader_path/{destination.name}" if current != binary else
                          f"@loader_path/../Frameworks/{destination.name}")
            subprocess.run(["install_name_tool", "-change", dependency, loader_ref,
                            str(current)], check=True)

    for current in (binary, *copied.values()):
        remaining = [dep for dep in _dylib_references(current)
                     if dep.startswith("@rpath/") and dep != f"@rpath/{current.name}"]
        remaining.extend(_external_dylibs(current))
        for dependency in _dylib_references(current):
            if dependency.startswith("@loader_path/") and not (
                    current.parent / dependency.removeprefix("@loader_path/")).resolve().is_file():
                remaining.append(dependency)
        if remaining:
            raise RuntimeError(f"Unresolved dylib dependencies remain in {current}: {remaining}")
    print(f"Bundled {len(copied)} external libraries in {app.name}")


def _normalize_info_plist(app: Path) -> None:
    plist_path = app / "Contents" / "Info.plist"
    info = plistlib.loads(plist_path.read_bytes())
    info["CFBundleShortVersionString"] = "0.61.0"
    info["CFBundleVersion"] = "1"
    binaries = [p for p in (app / "Contents" / "MacOS").iterdir()
                if p.is_file() and p.stat().st_mode & 0o111]
    binaries.extend((app / "Contents" / "Frameworks").glob("*.dylib"))
    min_versions = []
    for binary in binaries:
        output = subprocess.run(["vtool", "-show-build", str(binary)], check=True,
                                capture_output=True, text=True).stdout
        match = re.search(r"\bminos (\d+(?:\.\d+)*)", output)
        if not match:
            raise RuntimeError(f"Cannot determine minimum macOS version for {binary}")
        min_versions.append(tuple(int(part) for part in match.group(1).split(".")))
    # Homebrew libraries can have a newer minimum than the game executable.
    # Advertise the true bundle minimum to Launch Services.
    info["LSMinimumSystemVersion"] = ".".join(map(str, max(min_versions)))
    with plist_path.open("wb") as f:
        plistlib.dump(info, f)

def package_game(game: str, data_root: Path, install_dir: Path | None, signing_identity: str) -> None:
    app = ROOT / "build" / f"{game}X-Rebirth.app"
    resources = app / "Contents" / "Resources"
    source_data = data_root / game
    if not resources.is_dir() or not source_data.is_dir():
        raise RuntimeError(f"Missing app or licensed data for {game}")

    required = ("descent.hog", "descent.pig") if game == "D1" else (
        "DESCENT2.HOG", "DESCENT2.HAM", "DESCENT2.S22", "groupa.pig",
        "alien1.pig", "alien2.pig", "fire.pig", "ice.pig", "water.pig", "hoard.ham")
    available = {path.name.casefold() for path in source_data.iterdir() if path.is_file()}
    missing = [name for name in required if name.casefold() not in available]
    if missing:
        raise RuntimeError(f"Missing {game} data: {', '.join(missing)}")

    d2_mission_stems = {path.stem.casefold() for path in source_data.iterdir()
                        if game == "D1" and path.is_file() and path.suffix.casefold() == ".mn2"}
    for path in source_data.iterdir():
        if not path.is_file() or path.name.startswith("."):
            continue
        if game == "D1" and (path.suffix.casefold() == ".mn2" or
                             (path.suffix.casefold() == ".hog" and path.stem.casefold() in d2_mission_stems)):
            continue
        shutil.copy2(path, resources / path.name)

    controller_db = ROOT / "contrib" / "gamecontrollerdb.txt"
    if not controller_db.is_file():
        raise RuntimeError(f"Missing SDL controller mapping database: {controller_db}")
    # PhysFS searches Resources, while SDL_GetBasePath() points at Contents/MacOS.
    # Install the same database in both locations so either loader path works.
    shutil.copy2(controller_db, resources / "gamecontrollerdb.txt")
    shutil.copy2(controller_db, app / "Contents" / "MacOS" / "gamecontrollerdb.txt")

    package_music(resources, data_root, game, keep_original_names=True)
    _bundle_external_dylibs(app)
    _normalize_info_plist(app)

    subprocess.run(["codesign", "--force", "--deep", "--sign", signing_identity, str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    if install_dir:
        install_dir.mkdir(parents=True, exist_ok=True)
        destination = install_dir / app.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(app, destination)
        print(f"Installed {destination}")
    else:
        print(f"Packaged {app}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "private assets")
    parser.add_argument("--install-dir", type=Path)
    parser.add_argument("--signing-identity", default="-", help="codesign identity; defaults to ad-hoc signing")
    args = parser.parse_args()
    for game in ("D1", "D2"):
        package_game(game, args.data_root.resolve(), args.install_dir, args.signing_identity)


if __name__ == "__main__":
    main()
