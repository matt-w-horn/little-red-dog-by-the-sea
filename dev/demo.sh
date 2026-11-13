#!/bin/bash
# Shows one surprise on the TV over and over, without waiting for its day and hour, or ends that.
#
#   dev/demo.sh NAME      a name of surprises_table.py (it shows every surprise whose name
#                                                      begins with it: jet, monarch, aurora), or shooting_star
#   dev/demo.sh off       back to the real timetable
#   dev/demo.sh tour [SECONDS]   every surprise in turn, SECONDS each (default 20), then off
#
# It writes the global setting littlereddog_demo, which the screensaver reads every two seconds (SceneView). The setting is
# removed by `off` (and at the end of a tour); nothing else on the TV changes. A surprise shows in the light the TV
# has at that moment: a thing of the day looks dark at night.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
. "$REPO/dev/tv.sh"
tv() { tv_quiet "$@"; }
case "${1:?a name, off, or tour}" in
  off) tv "settings delete global littlereddog_demo"; echo "demo off" ;;
  tour)
    names="$(python3 -I - <<'PY'
import json
sp = json.load(open('art/scene.json'))['specials']
names = [i['name'] for i in sp['items'] if i['slot'].startswith('surprises') and i['name'] not in ('aurora_glints', 'monarch_1', 'monarch_2')]
names = ['monarch' if n == 'monarch_0' else n for n in names]      # a name shows every item that begins with it
print(' '.join(['shooting_star'] + names + [t['name'] for t in sp['tints']]))
PY
)"
    for name in $names; do
      echo "$(date '+%H:%M:%S') $name"
      tv "settings put global littlereddog_demo $name" > /dev/null
      sleep "${2:-20}"
    done
    tv "settings delete global littlereddog_demo"; echo "demo off" ;;
  *) tv "settings put global littlereddog_demo $1"; echo "demo: $1 (the screensaver picks it up within two seconds)" ;;
esac
