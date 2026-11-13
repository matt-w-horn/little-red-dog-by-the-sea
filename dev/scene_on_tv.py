"""Does a screenshot of the TV show the scene that the add-on's files describe? Used by deploy_scene.sh.

    python3 -I dev/scene_on_tv.py shots/NAME.png "YYYY-MM-DD HH:MM:SS"

The screenshot is 1920 x 1080: four screen pixels to one art pixel. It is compared with the Python renderer's frame
for that minute (the weather and the lighting state follow the date and the clock, as on the TV) at the pixels that
stand still (the render is taken as the television shows it: the warmth, and the brightness among those the screen
can have at that moment, as it depends on how long the screensaver has run, best_brightness): those that have one colour in 24 frames spread over the animation (so no wave, cloud, glint or rain),
outside the box the dog can be in and outside the clock's and the quote's boxes. The same pixels are compared with
the frame of the frozen baseline (baseline4/ beside this file: a frozen copy from before the doghouse), which shows that the comparison can fail.
Writes shots/NAME-480.png (the art pixels). Exit status 0 when at least 99 % of the still pixels are equal and
every 4 x 4 block of the screenshot is one colour.
"""
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
DOG_BOX = (130, 150, 350, 262)
TEXT_BOXES = [(0, 0, 130, 56), (300, 0, 480, 56)]


def load(folder, name):
    spec = importlib.util.spec_from_file_location(name, folder / 'tools' / 'scene.py')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(folder / 'tools'))
    spec.loader.exec_module(module)
    sys.path.pop(0)
    return module


def screen_factors(scene, when):
    """Every (red, green, blue) factor the screen can have at this moment: the brightness depends on how long the
    screensaver has run (scene.evening_factors), which a screenshot does not say. One entry for an older scene.py."""
    if 'hold_minutes' not in scene.scene().get('evening', {}):
        return None
    e = scene.scene()['evening']
    span = 60_000 * (e['hold_minutes'] + e['fade_minutes'])
    return sorted({scene.evening_factors(when, d) for d in range(0, span + 1, 250)} | {scene.evening_factors(when)})


def best_brightness(scene, when, raw, small, still):
    """(equal pixels, factors) for the factors that make the most still pixels of raw equal to the screenshot."""
    best = (-1, None)
    for f in screen_factors(scene, when):
        shown = (raw[still].astype(np.int32) * np.array(f, np.int32) + 500) // 1000
        best = max(best, (int((small[still] == shown).all(axis=1).sum()), f))
    return best


def frames(scene, when, ticks):
    weather = scene.weather_name(when)
    shown = getattr(scene, 'on_screen', lambda rgb, time: np.asarray(rgb))     # the evening's dimming and warmth
    if screen_factors(scene, when) is not None:
        shown = lambda rgb, time: np.asarray(rgb)                               # matched later: best_brightness
    return weather, scene.choose_state(when, weather), [shown(np.asarray(scene.render(when, weather, t, None, 'stand')), when)
                                                         for t in ticks]


def main():
    shot_path = sys.argv[1]
    when = datetime.strptime(sys.argv[2], '%Y-%m-%d %H:%M:%S')
    shot = np.asarray(Image.open(shot_path).convert('RGB'))
    if shot.shape != (1080, 1920, 3):
        raise SystemExit(f'{shot_path}: {shot.shape[1]} x {shot.shape[0]}, not 1920 x 1080')
    blocks = shot.reshape(270, 4, 480, 4, 3)
    uniform = (blocks.max(axis=(1, 3)) == blocks.min(axis=(1, 3))).all(axis=2).mean()
    small = shot[2::4, 2::4]
    Image.fromarray(small).save(shot_path[:-4] + '-480.png')
    ticks = [1000 + 997 * k for k in range(24)]
    new = load(ROOT, 'scene_now')
    weather, state, now = frames(new, when, ticks)
    still = np.all([(f == now[0]).all(axis=2) for f in now], axis=0)
    still[DOG_BOX[1]:DOG_BOX[3], DOG_BOX[0]:DOG_BOX[2]] = False
    for x0, y0, x1, y1 in TEXT_BOXES:
        still[y0:y1, x0:x1] = False
    sc = new.scene()                          # the dog in the doghouse's doorway: where he is depends on the real tick
    for part in sc.get('house', {}).get('pose', {}).get('parts', []):
        w, h = Image.open(ROOT / 'art' / part['file']).size
        x0, y0 = sc['dog']['x'] + part['at'][0], sc['dog']['y'] + part['at'][1]
        still[max(0, y0):y0 + h, max(0, x0):x0 + w] = False
    n = int(still.sum())
    same, factors = best_brightness(new, when, now[0], small, still)
    old = load(Path(__file__).resolve().parent / 'baseline4', 'scene_before')
    old.quotes = new.quotes                   # the baseline holds no quotes file
    _, _, before = frames(old, when, ticks[:1])
    same_before = best_brightness(old, when, before[0], small, still)[0]      # the same comparison, the older art
    print(f'screenshot: {uniform:.4f} of the 4 x 4 blocks are one colour; {when:%Y-%m-%d %H:%M}: weather {weather}, state {state}')
    print(f'   still pixels compared: {n} of {480 * 270}; equal to the render of the add-on: {same} '
          f'(brightness {factors[0] / 10:.1f} %, factors {factors}); '
          f'equal to the render of the baseline: {same_before}')
    ok = uniform == 1.0 and n > 20000 and same >= 0.99 * n
    print('RESULT: the TV shows the scene' if ok else 'RESULT: NOT CONFIRMED')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
