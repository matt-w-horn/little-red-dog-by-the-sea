#!/bin/bash
# Install the add-on's built APK on the TV (the existing procedure) and confirm that the screensaver shows the scene.
#
#   dev/deploy_scene.sh SHOT
#
# Run dev/merge_poses.sh first: this script installs what that built (SKIP_BUILD=1).
#   1. The TV must be dreaming (the screensaver is up, nobody is using the TV). If not, stop: nothing is installed.
#   2. SKIP_BUILD=1 START=1 ./build-and-install.sh
#   3. After 25 s: the screensaver must be the window in front; take shots/SHOT.png.
#   4. scene_on_tv.py: the still pixels of the screenshot against the Python render of that minute.
# With CONFIRM_ONLY=1 steps 1 and 2 are left out. An ADB screenshot is not proof of what the panel shows.
set -euo pipefail
SHOT="$1"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
. "$REPO/dev/tv.sh"
tv() { tv_run "$@" 2>&1 | grep -v "Broken pipe" || true; }
if [ "${CONFIRM_ONLY:-}" != 1 ]; then
  echo "== 1. state of the TV"
  state="$(tv "dumpsys power | grep mWakefulness=")"; echo "$state"
  echo "$state" | grep "mWakefulness=Dreaming" > /dev/null || { echo "The TV is not dreaming: not installed."; exit 1; }
  echo "== 2. install"
  SKIP_BUILD=1 START=1 ./build-and-install.sh 2>&1 | tail -3
  sleep 25
  tv "dumpsys package io.matthorn.littlereddog | grep -m1 lastUpdateTime"
fi
echo "== 3. screenshot"
state="$(tv "dumpsys power | grep mWakefulness=; dumpsys window | grep mCurrentFocus")"; echo "$state"
echo "$state" | grep "DreamActivity" > /dev/null || { echo "The screensaver is not in front. Not confirmed."; exit 1; }
shot_time="$(date '+%Y-%m-%d %H:%M:%S')"
tv_screenshot "shots/$SHOT.png" 2>&1 | grep -v "Broken pipe" | tail -1
echo "== 4. compare with the Python render ($shot_time)"
python3 -I dev/scene_on_tv.py "shots/$SHOT.png" "$shot_time"
