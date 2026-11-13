# dev/: the gate, the checks, the TV scripts and the review sheets

The app does not package this folder. It holds what changing the art or the tools needs besides the app itself. Run
every script from the repository root. Everything a script writes goes under `out/` (review sheets, the gate's staging
copy) or `shots/` (TV screenshots); git ignores both.

## What is here

| File | What it does |
|---|---|
| `merge_poses.sh` | The gate. Copies `tools/` and `art/` to `out/stage/`, rebuilds and re-exports there, checks the colour limit per lighting state, runs `frozen4_check.py`, `loop_test.py` and `quote_rule.py`, copies the staging art into `art/`, then runs the Gradle tests, lint and the release build and `apk_check.py`. `STAGE_ONLY=1` stops before `art/` is changed. Poses given as `NAME=DIR` (a folder with `pose.json`) are merged in. |
| `apk_check.py` | The built APK holds every file of an art folder (but `reference/`) with the same bytes, and nothing else. |
| `frozen4_check.py`, `baseline4/` | The stand, sit and sphinx sprites, the clock and the text render as in the frozen copy in `baseline4/`. `--selftest` must fail on seven constructed faults. The copy's renderer shows the checked folder's quotes. |
| `loop_test.py` | Every animation loop and every change of pose without a jump. |
| `quote_rule.py` | A new quote every hour, each pass in its own order. |
| `fs_check.py` | The sky, the sea and the sand are baked Floyd-Steinberg gradients. `--selftest` builds a banded copy that must fail. |
| `check_dates.py` | The date rules of the holidays against the system's calendar. |
| `tv.sh` | Sourced by the TV scripts and `build-and-install.sh`: `tv`, `tv_install` and `tv_screenshot`, with the stock `adb` or the ADB client of cleanyourtv. |
| `deploy_scene.sh`, `scene_on_tv.py` | Install what the gate built and compare a screenshot's still pixels with the render of that minute. |
| `deploy_pose.sh`, `pose_wait.py`, `pose_on_tv.py` | Wait until the screensaver shows one pose (its schedule, and the doghouse; `door` is the dog in the doorway) and compare its cells with the render. `CONFIRM_ONLY=1` installs nothing; `WAIT_MAX` is the longest wait in seconds. |
| `demo.sh` | Shows one surprise on the TV without waiting for its day (`NAME`, `tour`, `off`). `surprises_table.py` prints the names and their timetable. |
| `shot.py`, `look.py`, `holidays.py`, `surprises.py`, `plants.py`, `house_look.py` | Review sheets, written to `out/`. `look.py` puts a trial copy of the tools beside the current ones. |
| `make_latest.py` | `out/latest.png`: every pose in every lighting state. |
| `make_gifs.py` | `docs/day.gif` and `docs/poses.gif`, the two animations of the README, drawn by the reference renderer. |
| `walk/` | Measured dog gait (`GAIT.md`), what a walk sheet must pass, and two strips of a public domain plate by Muybridge. A walk was tried and is not in the renderers. |

## dev/local.env

The TV scripts read `dev/local.env` (git ignores it): lines `NAME=value`, and a value already set in the environment
wins. `TV_HOST` is the TV's address, with or without a port (5555 is added); it is required. `CLEANYOURTV` is
optional: the path of a checkout of cleanyourtv with `tools/venv`, whose ADB client is then used in place of `adb`.

```
TV_HOST=192.168.1.50
CLEANYOURTV=$HOME/cleanyourtv
```

## Commands

Put a change of `tools/` or `art/` through the gate (it never touches the TV):

```sh
bash dev/merge_poses.sh
```

Install what the gate built and compare a screenshot with the render (the TV must be showing the screensaver):

```sh
dev/deploy_scene.sh NAME
```

Confirm one pose when the screensaver shows it, without installing:

```sh
CONFIRM_ONLY=1 WAIT_MAX=3600 dev/deploy_pose.sh sit NAME
```

Try a change in a copy first, then look at it beside the current tools:

```sh
rm -rf out/trial && mkdir -p out/trial && cp -Rp tools art out/trial/ && (cd out/trial && python3 -I -B tools/scene_build.py | tail -1) && python3 -I -B dev/look.py NAME out/trial/tools
```

## A longer quote list

To build with a longer quote list without changing a tracked file, link it as `quotes.private.txt` at the root (git
ignores that name). The gate then builds a second APK in `out/stage-private/` with that list, tests it, prints how many
quotes it holds and leaves it as the APK that `deploy_scene.sh` installs.
