"""Does a screenshot of the TV show one pose of the dog? Used by deploy_pose.sh.

    python3 -I dev/pose_on_tv.py POSE shots/NAME.png "YYYY-MM-DD HH:MM:SS"

POSE is a name of dog.poses, or `door` (house.pose: the dog in the doghouse's doorway; the cells that the layer
house_front covers are left out). The screenshot is 1920 x 1080: four screen pixels to one art pixel. Every opaque
cell of the pose's parts that no move touches must have the colour the Python renderer gives it at that time (the lighting state follows the clock;
the weather is tried as clear, cloudy and rain, and the best counts). The same cells are compared with the render
of the pose `stand` as well, which shows that the comparison can fail. Writes shots/NAME-480.png (the art pixels).
Exit status 0 when at least 99 % of the cells are equal and every 4 x 4 block of the screenshot is one colour.
"""
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
ADDON = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON / 'tools'))
import scene  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene_on_tv  # noqa: E402


def main():
    pose_name, shot_path = sys.argv[1], sys.argv[2]
    when = datetime.strptime(sys.argv[3], '%Y-%m-%d %H:%M:%S')
    uniform, small = scene_on_tv.read_screenshot(shot_path)

    sc = scene.scene()
    pose = next(p for p in sc['dog']['poses'] + [sc['house']['pose']] if p['name'] == pose_name)
    xs_all, ys_all = [], []
    for part in pose['parts']:
        cells = np.asarray(Image.open(ADDON / 'art' / part['file']))
        moved = np.zeros(cells.shape, bool)
        for move in part.get('moves', []):
            for frame in move['frames']:
                for op in frame:
                    if op['op'] == 'recolour':
                        for x, y in op['cells']:
                            moved[y, x] = True
                    else:
                        x, y, w, h = op['rect']
                        moved[max(0, y - 2):y + h + 2, max(0, x - 2):x + w + 2] = True
        ys, xs = np.nonzero((cells > 0) & ~moved)
        at = part.get('at', [0, 0])
        xs_all.append(sc['dog']['x'] + at[0] + xs)
        ys_all.append(sc['dog']['y'] + at[1] + ys)
    X, Y = np.concatenate(xs_all), np.concatenate(ys_all)
    seen = (X >= 0) & (X < 480) & (Y >= 0) & (Y < 270)                       # the door pose reaches past the left edge
    X, Y = X[seen], Y[seen]
    if pose_name == sc['house']['pose']['name']:
        front = scene.layer('house_front.png')[Y, X] == 0                    # the wall in front of him hides the rest
        X, Y = X[front], Y[front]
    print(f'screenshot: {uniform:.4f} of the 4 x 4 blocks are one colour; pose {pose_name}: {len(X)} cells outside '
          f'every move')
    best = 0
    for weather in ('clear', 'cloudy', 'rain'):
        counts = []
        for name in (pose_name, 'stand'):
            raw = np.asarray(scene.render(when, weather, 24, None, name).convert('RGB'))
            mask = np.zeros(raw.shape[:2], bool)
            mask[Y, X] = True
            counts.append(scene_on_tv.best_brightness(scene, when, raw, small, mask)[0])
        print(f'   {weather:7s}: equal to the render of {pose_name}: {counts[0]} of {len(X)}; equal to the render of '
              f'stand: {counts[1]}')
        best = max(best, counts[0])
    ok = uniform == 1.0 and best >= 0.99 * len(X)
    print('RESULT: the TV shows the pose' if ok else 'RESULT: NOT CONFIRMED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
