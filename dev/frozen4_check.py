"""The frozen things render as before: the stand, sit and sphinx sprites, the clock, the text.

    python3 -I dev/frozen4_check.py [DIR]         DIR holds tools/ and art/ (default: the add-on)
    python3 -I dev/frozen4_check.py --selftest    the check must fail on seven constructed faults

The baseline is baseline4/ beside this file: a frozen copy of the tools and art from before the doghouse, without
art/reference/ and without art/quotes.txt. The baseline's renderer shows the checked folder's quotes: the words may
change, and the font, the wrapping and the places of the text are still the baseline tools'.
The author froze the stand, sit and sphinx poses (they stay byte-identical, with their places and moves):
1. the bytes of art/dog.png, art/dog_sit.png and art/dog_sphinx.png;
2. where those three poses stand and how they move: scene.json dog.x, dog.y and the entries of the poses `stand`,
   `sit` and `sphinx` (file, at, ground, moves);
3. the dog's colours: with each of the three poses, in each lighting state, on the 15th of every month and on four
   days on which one month fades into the next, at three ticks (one still, two with moves), every pixel of the frame
   that the dog covers has the baseline's colour. Rain and text are left out of these frames (they are drawn over him);
4. the clock and the text: in each lighting state, at eight times spread over the year and the day, the pieces that
   text_pieces places (positions, shapes, and which pixels are ink and which are edge) equal the baseline's, and
   every pixel they cover has the baseline's colour in the finished frame (in every state).
What it cannot see: the dog's shadow, the background behind the dog and the text, and whether the television's panel
shows the same.
"""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent / 'baseline4'
FROZEN_FILES = ['dog.png', 'dog_sit.png', 'dog_sphinx.png']
FROZEN_POSES = ['stand', 'sit', 'sphinx']
TEXT_RECOLOURED = ()             # states whose text colours are not compared: none against this baseline
STATES = ['dawn', 'day', 'dusk', 'night', 'cloudy', 'rain']
WEATHER = {'cloudy': 'cloudy', 'rain': 'rain'}
DATES = [(m, 15) for m in range(1, 13)] + [(1, 28), (4, 30), (7, 1), (10, 27)]
TICKS = [20, 2, 1196]            # 20: a still tick of the standing dog; 2: a breath of stand and sit; 1196: the sphinx's tail
TIMES = [datetime(2026, 1, 15, 0, 38), datetime(2026, 2, 28, 9, 5), datetime(2026, 4, 30, 12, 0),
         datetime(2026, 6, 15, 15, 47), datetime(2026, 7, 1, 19, 59), datetime(2026, 9, 15, 21, 10),
         datetime(2026, 11, 9, 13, 0), datetime(2026, 12, 25, 6, 23)]


def load(folder, name):
    spec = importlib.util.spec_from_file_location(name, folder / 'tools' / 'scene.py')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(folder / 'tools'))
    spec.loader.exec_module(module)
    sys.path.pop(0)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(folder):
    bad = []
    old, new = load(BASE, 'scene_baseline3'), load(folder, 'scene_checked')
    old.quotes = new.quotes                   # the words are not frozen; how they are set is
    # 1. files
    for f in FROZEN_FILES:
        if sha(BASE / 'art' / f) != sha(folder / 'art' / f):
            bad.append(f'art/{f} is not the baseline file')
    # 2. places and moves
    a, b = old.scene()['dog'], new.scene()['dog']
    if (a['x'], a['y']) != (b['x'], b['y']):
        bad.append(f'the dog stands at {(b["x"], b["y"])}, baseline {(a["x"], a["y"])}')
    for name in FROZEN_POSES:
        pa = next((p for p in a['poses'] if p['name'] == name), None)
        pb = next((p for p in b['poses'] if p['name'] == name), None)
        if pa != pb:
            bad.append(f'scene.json: the pose {name} (file, at, ground or moves) differs from the baseline')
    # 3. the dog's colours in finished frames
    skip = ('rain_far', 'rain_near', 'text')
    frames = pixels = 0
    for name in FROZEN_POSES:
        pose = next(p for p in old.poses() if p['name'] == name)
        for state in STATES:
            weather = WEATHER.get(state, 'clear')
            for tick in TICKS:
                when = datetime(2026, 11, 9, 13, 0)
                want = old.finished(when, weather, tick, state, skip, name)
                mask = np.zeros(want.shape[:2], bool)
                for part in pose['parts']:
                    if part['flat']:
                        continue
                    img = old.dog_frame(part['image'], tick, part['moves']) != 0
                    x, y = a['x'] + part['at'][0], a['y'] + part['at'][1]
                    mask[y:y + img.shape[0], x:x + img.shape[1]] |= img
                for month, day in DATES:
                    got = new.finished(datetime(2026, month, day, 13, 0), weather, tick, state, skip, name)
                    differ = int((got[mask] != want[mask]).any(axis=1).sum())
                    frames += 1
                    pixels += int(mask.sum())
                    if differ:
                        bad.append(f'{name}, {state}, {month:02d}-{day:02d}, tick {tick}: {differ} of {int(mask.sum())} '
                                   f'pixels of the dog differ from the baseline')
    print(f'dog: {frames} frames, {pixels} pixels of the dog compared')
    # 4. the clock and the text
    frames = pixels = 0
    for when in TIMES:
        date = f'{old.DAYS[when.isoweekday() % 7]} {when.day} {old.MONTHS[when.month - 1]}'
        pa = old.text_pieces(when.hour, when.minute, date, old.quote_of(when))
        pb = new.text_pieces(when.hour, when.minute, date, new.quote_of(when))
        ink_a, ink_b = old.role('TEXT'), new.role('TEXT')        # a role's index may move; its pixels may not
        same = len(pa) == len(pb) and all(
            x0 == x1 and y0 == y1 and np.array_equal(i0 != 0, i1 != 0) and np.array_equal(i0 == ink_a, i1 == ink_b)
            for (i0, x0, y0), (i1, x1, y1) in zip(pa, pb))
        if not same:
            bad.append(f'{when}: the pieces of the clock and the text differ from the baseline (image or position)')
            continue
        mask = np.zeros((old.H, old.W), bool)
        for img, x, y in pa:
            h, w = img.shape
            x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, old.W), min(y + h, old.H)
            mask[y0:y1, x0:x1] |= img[y0 - y:y1 - y, x0 - x:x1 - x] != 0
        for state in STATES:
            if state in TEXT_RECOLOURED:
                continue
            weather = WEATHER.get(state, 'clear')
            want = old.finished(when, weather, 20, state, (), 'stand')
            got = new.finished(when, weather, 20, state, (), 'stand')
            differ = int((got[mask] != want[mask]).any(axis=1).sum())
            frames += 1
            pixels += int(mask.sum())
            if differ:
                bad.append(f'{when}, {state}: {differ} of {int(mask.sum())} pixels of the clock and the text differ')
    print(f'text: {frames} frames, {pixels} pixels of the clock and the text compared')
    for line in bad[:12]:
        print('FAIL:', line)
    if len(bad) > 12:
        print(f'FAIL: and {len(bad) - 12} more')
    print('RESULT:', 'the frozen things render as before' if not bad else f'NOT as before ({len(bad)} faults)')
    return not bad


def poke_png(path, x, y, value):
    from PIL import Image
    im = Image.open(path)
    arr = np.array(im)
    arr[y, x] = value
    out = Image.fromarray(arr, 'P')
    out.putpalette(im.getpalette())
    out.save(path, transparency=0)


def selftest():
    """Seven faults, each in a fresh copy of the add-on; the check must fail on each and pass on the plain copy."""
    addon = ROOT

    def colour(d):
        for p in sorted((d / 'art' / 'palettes').rglob('*.json')):
            if 'night' in p.name:
                t = json.loads(p.read_text())
                for e in t['colors']:
                    if e['name'] == 'COAT':
                        e['hex'] = '46261B'              # one unit of red more
                p.write_text(json.dumps(t))

    def text_colour(d):
        for p in sorted((d / 'art' / 'palettes').rglob('*.json')):
            if 'cloudy' in p.name:
                t = json.loads(p.read_text())
                for e in t['colors']:
                    if e['name'] == 'TEXT_EDGE':
                        e['hex'] = '000001' if e['hex'] != '000001' else '000002'
                p.write_text(json.dumps(t))

    def margin(d):
        p = d / 'art' / 'scene.json'
        t = json.loads(p.read_text())
        t['text']['margin_y'] += 1
        p.write_text(json.dumps(t))

    def tail(d):
        p = d / 'art' / 'scene.json'
        t = json.loads(p.read_text())
        sphinx = next(q for q in t['dog']['poses'] if q['name'] == 'sphinx')
        sphinx['parts'][0]['at'][0] += 1
        p.write_text(json.dumps(t))

    def sit_place(d):
        p = d / 'art' / 'scene.json'
        t = json.loads(p.read_text())
        sit = next(q for q in t['dog']['poses'] if q['name'] == 'sit')
        sit['parts'][0]['at'][0] += 1
        p.write_text(json.dumps(t))

    faults = [('nothing changed', None, True),
              ('one cell of art/dog_sit.png', lambda d: poke_png(d / 'art' / 'dog_sit.png', 60, 50, 3), False),
              ('the sit one pixel to the right', sit_place, False),
              ('one cell of art/dog_sphinx.png', lambda d: poke_png(d / 'art' / 'dog_sphinx.png', 60, 50, 3), False),
              ('COAT at night one unit redder', colour, False),
              ('TEXT_EDGE in cloud another colour', text_colour, False),
              ('the text one pixel lower', margin, False),
              ('the sphinx one pixel to the right', tail, False)]
    ok = True
    for what, change, want in faults:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            shutil.copytree(addon / 'tools', d / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(addon / 'art', d / 'art')
            if change:
                change(d)
            r = subprocess.run([sys.executable, '-I', __file__, str(d)], capture_output=True, text=True)
            passed = r.returncode == 0
            last = (r.stdout.strip().splitlines() or r.stderr.strip().splitlines() or ['(no output)'])[-1]
            print(f'selftest, {what}: the check {"passed" if passed else "failed"} '
                  f'({"as it must" if passed == want else "WRONG"}): {last[:110]}')
            ok &= passed == want
    print('SELFTEST:', 'the check fails when it should' if ok else 'THE CHECK IS NOT TO BE TRUSTED')
    return ok


if __name__ == '__main__':
    if sys.argv[1:2] == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    sys.exit(0 if check(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT) else 1)
