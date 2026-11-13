#!/bin/bash
# Install the add-on's built APK on the TV (the existing procedure) and confirm that the screensaver shows one pose.
#
#   dev/deploy_pose.sh POSE SHOT
#   example: dev/deploy_pose.sh side dog-goal-04-side
#
# Run dev/merge_poses.sh first: this script installs what that built (SKIP_BUILD=1).
# Steps:
#   1. The TV must be dreaming (the screensaver is up, nobody is using the TV). If not, stop: nothing is installed.
#   2. SKIP_BUILD=1 START=1 ./build-and-install.sh
#   3. Wait until the screensaver's own schedule shows the pose (scene.pose_at; at most WAIT_MAX seconds, 600 unless
#      set), check that the screensaver is the window in front, and take shots/SHOT.png. The tile cannot be used for
#      this: while the TV dreams, an activity started with "am start" stays behind the screensaver.
#      With CONFIRM_ONLY=1 in the environment, steps 1 and 2 are left out.
#   4. Compare: every opaque cell of the pose's parts that no move touches must have the colour the Python renderer
#      gives it now (the weather is tried as clear, cloudy and rain; the best counts). The same cells are also
#      compared with the render of the pose `stand`, to show that the check can fail.
# An ADB screenshot is not proof of what the panel shows; it is the evidence there is.
set -euo pipefail
POSE="$1"; SHOT="$2"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
. "$REPO/dev/tv.sh"
tv() { tv_quiet "$@"; }

if [ "${CONFIRM_ONLY:-}" != 1 ]; then
  echo "== 1. state of the TV"
  state="$(tv "dumpsys power | grep mWakefulness=")"; echo "$state"
  echo "$state" | grep "mWakefulness=Dreaming" > /dev/null || { echo "The TV is not dreaming: not installed."; exit 1; }

  echo "== 2. install"
  SKIP_BUILD=1 START=1 ./build-and-install.sh 2>&1 | tail -3
  sleep 4
  tv "dumpsys package io.matthorn.littlereddog | grep -m1 lastUpdateTime"
fi

echo "== 3. wait until the screensaver's own schedule shows the pose"
wait_s="$(python3 -I dev/pose_wait.py "$POSE" "${WAIT_MAX:-600}")"
if [ "$wait_s" = -1 ]; then
  echo "The schedule does not show $POSE in the next ${WAIT_MAX:-600} s. Not confirmed. Run again later with CONFIRM_ONLY=1."
  exit 2
fi
echo "   the screensaver shows $POSE in $wait_s s"
sleep "$wait_s"
state="$(tv "dumpsys power | grep mWakefulness=; dumpsys window | grep mCurrentFocus")"; echo "$state"
echo "$state" | grep "DreamActivity" > /dev/null || { echo "The screensaver is not in front. Not confirmed."; exit 1; }
shot_time="$(date '+%Y-%m-%d %H:%M:%S')"      # before the screenshot, as in deploy_scene.sh: taking it takes seconds
tv_shot "shots/$SHOT.png"

echo "== 4. compare with the Python render ($shot_time)"
python3 -I dev/pose_on_tv.py "$POSE" "shots/$SHOT.png" "$shot_time"
