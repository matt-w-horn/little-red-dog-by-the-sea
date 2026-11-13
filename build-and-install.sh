#!/usr/bin/env bash
# Build Little Red Dog by the Sea, install it on the TV and make it the TV's screensaver.
#
# The TV is reached with the stock adb (TV_HOST, port 5555 unless given), or with the ADB client of cleanyourtv
# when CLEANYOURTV points at a checkout of it. Settings may be written into dev/local.env; see dev/tv.sh.
#
# Usage: TV_HOST=192.168.1.50 ./build-and-install.sh
#        TV_HOST=192.168.1.50 START=1 ./build-and-install.sh       # and show it now
#        TV_HOST=192.168.1.50 SKIP_BUILD=1 ./build-and-install.sh  # install the APK already built
#        TV_HOST=192.168.1.50 NO_SCREENSAVER=1 ./build-and-install.sh  # install, leave the screensaver alone
#        TV_HOST=192.168.1.50 ./build-and-install.sh --uninstall   # previous screensaver back, app removed
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/dev/tv.sh"
PKG=io.matthorn.littlereddog
DREAM=$PKG/.DogDream
APK="$HERE/app/build/outputs/apk/release/app-release.apk"
# The screensaver the TV had before the first run, so --uninstall can put it back.
BEFORE=/data/local/tmp/littlereddog-before

if [ "${1:-}" = --uninstall ]; then
  tv "if [ -f $BEFORE ]; then { read c; read e; } < $BEFORE; if [ \"\$c\" = null ]; then settings delete secure screensaver_components >/dev/null; else settings put secure screensaver_components \"\$c\"; fi; settings put secure screensaver_enabled \"\$e\"; rm -f $BEFORE; fi; pm uninstall $PKG"
  exit 0
fi

if [ "${SKIP_BUILD:-}" != 1 ]; then
  (cd "$HERE" && ./gradlew assembleRelease -q) || { echo "build failed (JDK 17 and Android SDK 34 needed)" >&2; exit 1; }
fi
[ -f "$APK" ] || { echo "ERROR: no $APK; build it first." >&2; exit 1; }
tv_install "$APK"
if [ -z "${NO_SCREENSAVER:-}" ]; then
  tv "[ -f $BEFORE ] || { settings get secure screensaver_components; settings get secure screensaver_enabled; } > $BEFORE; settings put secure screensaver_components $DREAM; settings put secure screensaver_enabled 1"
  echo "Installed: Little Red Dog by the Sea is the screensaver. Undo with: ./build-and-install.sh --uninstall"
else
  echo "Installed: Little Red Dog by the Sea has a tile; the screensaver is unchanged."
fi
[ -z "${START:-}" ] || tv "am start -n com.android.systemui/.Somnambulator >/dev/null; sleep 3; dumpsys dreams | grep mCurrentDreamName"
