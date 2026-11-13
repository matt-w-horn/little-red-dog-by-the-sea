"""How many seconds from now until the screensaver shows a pose alone (no fade) for at least 10 seconds.

    python3 -I dev/pose_wait.py POSE LIMIT_SECONDS

POSE is a name of dog.poses, or `door` (house.pose: the dog in the doghouse's doorway). Prints the number of seconds
(0 when it shows now; 3 more than the start otherwise), or -1 when the pose does not show within the limit. What
shows is the add-on's scene.chosen_poses(None, tick, time): the schedule (pose_at) and the doghouse, which takes the
schedule's pose away in rain and at night. The tick and the time are the wall clock's, as in the app.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import scene  # noqa: E402


def main():
    sc = scene.scene()
    names = [p['name'] for p in sc['dog']['poses']] + [sc['house']['pose']['name']]
    want, limit = sys.argv[1], int(sys.argv[2])
    if want not in names:
        raise SystemExit(f'{want} is no pose: {" ".join(names)}')
    now_ms = int(time.time() * 1000)
    alone = 0                                         # seconds for which the pose has been alone so far
    for second in range(limit + 11):
        ms = now_ms + second * 1000
        old, new, _ = scene.chosen_poses(None, scene.tick_at(ms), datetime.fromtimestamp(ms / 1000))
        alone = alone + 1 if old is None and new['name'] == want else 0
        if alone == 11:                               # alone at this second and the ten before it
            start = second - 10
            print(start + 3 if start else 0)
            return
    print(-1)


if __name__ == '__main__':
    main()
