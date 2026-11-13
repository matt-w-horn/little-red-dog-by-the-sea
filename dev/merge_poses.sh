#!/bin/bash
# Put accepted poses into the add-on, through a staging copy, and stop before the deploy.
#
#   dev/merge_poses.sh [NAME=POSE_DIR ...]
#   example: dev/merge_poses.sh sit=/path/to/sit curl=/path/to/curl
#
# POSE_DIR holds pose.json (one pose in the format of scene.json dog.poses; its parts name files by absolute path).
# A part file named sprite.png becomes art/dog_NAME.png; any other part file keeps its name (towel.png, ball.png).
# With no argument it rebuilds what the add-on already holds (a check that nothing drifted).
#
# Steps, each of which must pass before the next:
#   1. out/stage/ = a fresh copy of tools/ and art/, plus the poses named
#   2. scene_build.py, scene_export.py; no lighting state over scene_build's colour limit in any month
#   3. frozen4_check.py: the stand, sit and sphinx sprites, the clock and the text render as in dev/baseline4/
#   4. loop_test.py (every loop and every pose change without a jump); quote_rule.py (a new quote every hour, a
#      new order on every pass)
#   5. the add-on's art/ and tools/poses/ become the staging copy's (rsync by checksum, with deletes)
#   6. Gradle: unit tests, lint, release build; prints the test counts and the APK's size and hash; apk_check.py:
#      the APK holds the art folder as it is now
# JAVA_HOME and ANDROID_HOME keep a value from the environment; otherwise Homebrew's paths are used.
# If quotes.private.txt exists at the root (a link to a longer quote list), the gate ends with a second build: the
# same tools and art with that list, in out/stage-private/, tested and packaged as the last APK.
# With STAGE_ONLY=1 in the environment it stops after step 4, runs the Java tests on the staging art, and changes
# nothing in the add-on (a rehearsal).
# The add-on is not touched before step 5. The TV is not touched at all: deploy with the add-on's build-and-install.sh.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ADDON="$REPO"
STAGE="$REPO/out/stage"
cd "$REPO"

echo "== 1. staging copy"
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp -Rp "$ADDON/tools" "$ADDON/art" "$STAGE/"
rm -rf "$STAGE/tools/__pycache__"; mkdir -p "$STAGE/tools/poses"
for arg in "$@"; do
  name="${arg%%=*}"; dir="${arg#*=}"
  python3 -I - "$name" "$dir" "$STAGE" <<'EOF'
import json, shutil, sys
from pathlib import Path
name, folder, stage = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
pose = json.loads((folder / 'pose.json').read_text())
assert pose['name'] == name, f'{folder}/pose.json holds the pose {pose["name"]!r}, not {name!r}'
for part in pose['parts']:
    src = Path(part['file'])
    assert src.is_absolute() and src.exists(), f'{src}: a part file must be an existing absolute path'
    part['file'] = f'dog_{name}.png' if src.name == 'sprite.png' else src.name
    shutil.copyfile(src, stage / 'art' / part['file'])
    print(f'   {name}: {src} -> art/{part["file"]}')
(stage / 'tools' / 'poses' / f'{name}.json').write_text(json.dumps(pose, indent=1) + '\n')
EOF
done

echo "== 2. build, export, colours"
(cd "$STAGE" && python3 -I tools/scene_build.py | tail -3 && python3 -I tools/scene_export.py | tail -2)
counts="$(cd "$STAGE" && python3 -I tools/scene_build.py count | grep -E '^(dawn|day|dusk|night|cloudy|rain):')"
echo "$counts" | tr '\n' ' '; echo
if echo "$counts" | grep "OVER" > /dev/null; then echo "over the colour limit"; exit 1; fi
test "$(echo "$counts" | wc -l | tr -d ' ')" = 6 || { echo "the colour count did not print six states"; exit 1; }

echo "== 3. frozen"
python3 -I dev/frozen4_check.py "$STAGE" | tail -3 | tee /dev/stderr | grep "RESULT: the frozen things render as before" > /dev/null

echo "== 4. loops and pose changes"
python3 -I dev/loop_test.py --tools "$STAGE/tools" 2>&1 | tail -3 | tee /dev/stderr | grep "RESULT: every check passed" > /dev/null
python3 -I -B dev/quote_rule.py "$STAGE/tools" | tail -1 | sed 's/^/   quotes: /' | tee /dev/stderr | grep "RESULT: every check passed" > /dev/null

if [ "${STAGE_ONLY:-}" = 1 ]; then
  echo "== STAGE_ONLY: Java tests on the staging art; the add-on is not changed"
  cd "$ADDON"
  export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}" ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
  rm -rf app/build/test-results/testReleaseUnitTest
  set +e
  ./gradlew --no-daemon -q testReleaseUnitTest "-PartDir=$STAGE/art" 2>&1 | grep -v "SDK XML" | tail -8
  gradle_status="${PIPESTATUS[0]}"
  set -e
  grep -o 'tests="[0-9]*" skipped="[0-9]*" failures="[0-9]*" errors="[0-9]*"' app/build/test-results/testReleaseUnitTest/*.xml | sed 's/^/   /'
  rm -rf app/build/test-results/testReleaseUnitTest   # they describe the staging art, not the add-on's
  test "$gradle_status" = 0 || { echo "Gradle failed with status $gradle_status"; exit 1; }
  echo "REHEARSED at $(date '+%H:%M:%S'). Nothing merged, nothing deployed."
  exit 0
fi

echo "== 5. into the add-on"
mkdir -p "$ADDON/tools/poses"
rsync -a --checksum --delete "$STAGE/tools/poses/" "$ADDON/tools/poses/"
rsync -a --checksum --delete "$STAGE/art/" "$ADDON/art/"
diff -rq "$STAGE/art" "$ADDON/art" && diff -rq -x __pycache__ "$STAGE/tools" "$ADDON/tools"
echo "   the add-on equals the staging copy; poses: $(ls "$ADDON/tools/poses" | tr '\n' ' ')"

echo "== 6. Gradle"
cd "$ADDON"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}" ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
rm -rf app/build/test-results/testReleaseUnitTest      # so that Gradle runs the tests again and their result is this run's
set +e
./gradlew --no-daemon -q testReleaseUnitTest lintRelease assembleRelease 2>&1 | grep -v "SDK XML" | tail -8
gradle_status="${PIPESTATUS[0]}"
set -e
test "$gradle_status" = 0 || { echo "Gradle failed with status $gradle_status"; exit 1; }
python3 -I - <<'EOF'
import glob, hashlib, os, re, sys, time
bad = False
for f in sorted(glob.glob('app/build/test-results/testReleaseUnitTest/*.xml')):
    tests, skipped, failures, errors, stamp = re.search(
        r'tests="(\d+)" skipped="(\d+)" failures="(\d+)" errors="(\d+)" timestamp="([^"]+)"', open(f).read(400)).groups()
    print(f'   {os.path.basename(f)}: tests {tests}, skipped {skipped}, failures {failures}, errors {errors}, at {stamp} UTC')
    bad |= failures != '0' or errors != '0'
    bad |= time.time() - os.path.getmtime(f) > 600          # a result older than this run is no result
apk = 'app/build/outputs/apk/release/app-release.apk'
print(f'   {apk}: {os.path.getsize(apk)} bytes, sha256 {hashlib.sha256(open(apk, "rb").read()).hexdigest()[:16]}, '
      f'built {time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(apk)))}')
sys.exit('tests failed, or their results are not from this run' if bad else 0)
EOF
python3 -I "$REPO/dev/apk_check.py" app/build/outputs/apk/release/app-release.apk art
echo "   lint: $(tail -1 app/build/reports/lint-results-release.txt)"
unzip -l app/build/outputs/apk/release/app-release.apk | grep -E "assets/art/(dog|towel|ball)" | sed 's/^/   /'
echo "MERGED at $(date '+%H:%M:%S'). Not deployed."

if [ -e "$REPO/quotes.private.txt" ]; then
  echo "== 7. private build: the same tools and art with the list in quotes.private.txt"
  PRIV="$REPO/out/stage-private"
  rm -rf "$PRIV"; mkdir -p "$PRIV"
  cp -Rp "$ADDON/tools" "$ADDON/art" "$PRIV/"
  rm -rf "$PRIV/tools/__pycache__"
  cp "$REPO/quotes.private.txt" "$PRIV/art/quotes.txt"
  (cd "$PRIV" && python3 -I tools/scene_export.py | tail -2)
  python3 -I -B dev/quote_rule.py "$PRIV/tools" | tail -1 | sed 's/^/   quotes: /' | tee /dev/stderr | grep "RESULT: every check passed" > /dev/null
  rm -rf app/build/test-results/testReleaseUnitTest
  set +e
  ./gradlew --no-daemon -q testReleaseUnitTest assembleRelease "-PartDir=$PRIV/art" 2>&1 | grep -v "SDK XML" | tail -8
  gradle_status="${PIPESTATUS[0]}"
  set -e
  test "$gradle_status" = 0 || { echo "Gradle failed with status $gradle_status"; exit 1; }
  grep -o 'tests="[0-9]*" skipped="[0-9]*" failures="[0-9]*" errors="[0-9]*"' app/build/test-results/testReleaseUnitTest/*.xml | sed 's/^/   /'
  python3 -I "$REPO/dev/apk_check.py" app/build/outputs/apk/release/app-release.apk "$PRIV/art"
  echo "PRIVATE BUILD: the APK holds $(unzip -p app/build/outputs/apk/release/app-release.apk assets/art/quotes.txt | grep -c .) quotes"
fi
