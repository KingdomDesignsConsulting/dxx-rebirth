# GitHub handoff for the Descent Mac and iOS port

This file is for anyone continuing this project in another Codex thread. Read it alongside `README.md`, `COPYING.txt`, and `scripts/README-ios.md`. Check the live Git state before acting; branch names, authentication, and device availability can change.

## Repositories and checkout

- **Our public fork:** <https://github.com/KingdomDesignsConsulting/dxx-rebirth>
- **Original project:** <https://github.com/dxx-rebirth/dxx-rebirth>
- **Local source checkout:** `/Users/Shared/Main Hard Drive/My Projects/Projects In Progress/Applications/Games to make/Descent/dxx-rebirth`
- **Our port branch:** `codex/ios-port`. This is currently the fork's default branch and tracks `origin/codex/ios-port`.
- **`origin`:** our fork. Push project work here.
- **`upstream`:** the original DXX-Rebirth repository. Fetch updates from here; do not push our port directly to it.
- **`master`:** a local branch following `upstream/master`. It is not the port branch.

The fork was created on October 5, 2026. Existing Mac/iOS port commits were pushed to `origin/codex/ios-port`; the last code commit before this document was `ec7b21705` (Mac game-data search). The fork description explicitly credits DXX-Rebirth. There is no upstream pull request for the port as a whole.

For a fresh checkout, clone `https://github.com/KingdomDesignsConsulting/dxx-rebirth.git`. That gives the fork the name `origin`; then add the original project with `git remote add upstream https://github.com/dxx-rebirth/dxx-rebirth.git`. The fork's default branch currently checks out the port. Do not expect a fresh clone to include licensed game data.

## What has been done

The existing DXX-Rebirth code now builds D1 and D2 for macOS and iOS. The port includes touch controls, menu input and keyboard handling, signed development builds for iPhone/iPad, app icons, music packaging, and Mac app packaging. Recent Mac builds search for `D1-Data` or `D2-Data` beside the respective `.app`, then the app's own `Contents/Resources` folder. See the Git history for exact changes and `scripts/README-ios.md` for iOS build details.

The Mac app bundles are built under `build/` and installed to `/Users/knagel/Applications/`. The signed iOS device bundles are built under `build-ios-device/`. These are generated outputs, not Git source.

## Licensed data must stay local

Retail game data, ripped music, and private icon assets belong to the user and must **not** be committed or pushed. The build source is the Git-ignored `private assets` directory in this checkout: `D1`, `D2`, `Music/D1`, `Music/D2`, `Icons/D1/Assets.xcassets`, and `Icons/D2/Assets.xcassets`. `scripts/build-ios.py` and `scripts/package-macos.py` use this directory by default; both accept `--data-root` if the assets are relocated. The user also placed `D1-Data` and `D2-Data` beside the Mac apps under `build/`. The `/build` and `/build-ios-*` directories are ignored by Git. A fresh clone does not include private assets, so keep a separate backup. Before committing, inspect `git status` and the staged filenames; do not use a broad `git add .` if it could include assets. Keep the existing `COPYING.txt` and upstream attribution intact.

The former mobile source tree is preserved at `../Descent-Mobile-retired` because its own Git checkout has uncommitted changes. Rebirth builds do not use it. Do not delete that legacy checkout as part of ordinary port work.

## GitHub authentication and attribution

The Mac's GitHub CLI (`gh`) was authenticated to the user's `KingdomDesignsConsulting` account through its keyring when the fork was created. No GitHub token, password, or credential is stored in this repository. Check access with `gh auth status`. In a restricted tool environment, a GitHub command may fail because network or keyring access is sandboxed; use the normal tool approval/escalation path if available. If authentication has genuinely expired, ask the user to sign in with `gh auth login -h github.com`. Never print, copy into a file, or commit a token.

Git commits in this checkout were authored as `Kevin Nagel <95175704+KingdomDesignsConsulting@users.noreply.github.com>`, which is tied to the user's GitHub account. Check `git config user.name` and `git config user.email` before committing; preserve the user's chosen identity. A fork does not erase or replace the original contributors' credit.

## Routine workflow for a future thread

1. Confirm the checkout and branch with `pwd`, `git status --short --branch`, `git remote -v`, and `git branch -vv`. If the thread uses a different checkout or worktree, inspect its remotes rather than assuming they match this file.
2. Make the requested source changes. Build or test the affected platform as requested. Do not perform Android builds unless the user asks.
3. Review `git diff`, run `git diff --check`, and inspect every staged filename for licensed assets or generated bundles.
4. Commit coherent changes on the port branch with the user's Git author identity, then push to `origin`. A typical push is `git push origin codex/ios-port`; use the actual working branch if it differs.
5. Bring in original Rebirth updates deliberately: `git fetch upstream`, review `upstream/master`, then merge or rebase with conflict review and rebuilds. Do not overwrite port changes or force-push shared history without a clear reason and the user's authorization.
6. If a generic fix would help the original project, propose a separate, focused pull request to `dxx-rebirth/dxx-rebirth`. A pull request to upstream is not required for ordinary work on our fork.

GitHub fork and default-branch settings were established for this project already. Do not create another fork merely because a new Codex thread starts.
