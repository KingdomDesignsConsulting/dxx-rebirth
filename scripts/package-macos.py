#!/usr/bin/env python3
"""Add licensed game data and music to locally built Mac app bundles.

The source data remains outside Git.  Run after the SCons Mac build.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parent.parent


def package_game(game: str, data_root: Path, install_dir: Path | None) -> None:
    app = ROOT / "build" / f"{game}X-Rebirth.app"
    resources = app / "Contents" / "Resources"
    source_data = data_root / game
    if not resources.is_dir() or not source_data.is_dir():
        raise RuntimeError(f"Missing app or licensed data for {game}")

    required = ("descent.hog", "descent.pig") if game == "D1" else (
        "DESCENT2.HOG", "DESCENT2.HAM", "groupa.pig")
    available = {path.name.casefold() for path in source_data.iterdir() if path.is_file()}
    missing = [name for name in required if name.casefold() not in available]
    if missing:
        raise RuntimeError(f"Missing {game} data: {', '.join(missing)}")

    for path in source_data.iterdir():
        if path.is_file() and not path.name.startswith("."):
            shutil.copy2(path, resources / path.name)

    music = resources / "Music"
    if music.exists():
        shutil.rmtree(music)
    tracks = sorted((data_root / "Music" / game).glob("*.mp3"))
    if tracks:
        levels = music / "Levels"
        levels.mkdir(parents=True)
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

    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app)], check=True)
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
    parser.add_argument("--data-root", type=Path, default=ROOT.parent / "Descent-Mobile")
    parser.add_argument("--install-dir", type=Path)
    args = parser.parse_args()
    for game in ("D1", "D2"):
        package_game(game, args.data_root.resolve(), args.install_dir)


if __name__ == "__main__":
    main()
