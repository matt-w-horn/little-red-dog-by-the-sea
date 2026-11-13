"""Are the sky, the sea and the sand Floyd-Steinberg dithered, at the scene's own size, and baked (the same in every
tick)?

    python3 -I -B dev/fs_check.py              the add-on
    python3 -I -B dev/fs_check.py --selftest   also a copy built with flat bands, which must FAIL

For each lighting state and each of sky, sea, sand it reads the baked layer that art/scene.json names (a picture
of palette indexes; the tones of one ramp are consecutive indexes) and checks:
  size     the layer is 480 x 270: dithered at the scene's own resolution, never scaled afterwards
  tones    it holds no more ramp tones than scene_dither.HOW gives the gradient
  mixed    among the pairs of side-by-side pixels of the gradient, at least MIX in 100 differ. Error diffusion mixes
           two neighbouring tones pixel by pixel; flat bands differ only along the bands' edges
  step     of the pairs that differ, at least STEP in 100 differ by one tone of the ramp: it dithers between
           neighbouring tones, it is not noise
  baked    scene.pieces returns the same picture for the layer at ticks 0, 1, 7 and 1000 and at two times of the
           day: nothing is dithered again while it runs, so it cannot shimmer
The limits MIX and STEP stand between what the add-on measures and what the banded copy measures; --selftest shows
that the banded copy fails `mixed`.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT
MIX, STEP = 12, 85


def measure(folder):
    """-> rows (state, name, file, size ok, tones, limit, mixed per 100, one-step per 100) for the art under folder."""
    sys.path.insert(0, str(folder / 'tools'))
    sys.modules.pop('scene_dither', None)
    import scene_dither
    how = dict(scene_dither.HOW)
    sys.path.pop(0)
    sc = json.loads((folder / 'art' / 'scene.json').read_text())
    rows = []
    for state, st in sc['states'].items():
        for name in ('sky', 'sea', 'sand'):
            a = np.asarray(Image.open(folder / 'art' / 'layers' / st[name])).astype(np.int64)
            vals = np.unique(a[a > 0])
            # the ramp: the longest run of consecutive indexes among those the layer uses
            runs, start = [], vals[0]
            for k in range(1, len(vals) + 1):
                if k == len(vals) or vals[k] != vals[k - 1] + 1:
                    runs.append((start, vals[k - 1]))
                    start = vals[k] if k < len(vals) else None
            lo, hi = max(runs, key=lambda r: r[1] - r[0])
            ramp = (a >= lo) & (a <= hi)
            both = ramp[:, 1:] & ramp[:, :-1]
            d = np.abs(a[:, 1:] - a[:, :-1])[both]
            differ = int((d > 0).sum())
            rows.append((state, name, st[name], a.shape == (270, 480), int(hi - lo + 1), how[name][1],
                         100 * differ / max(1, len(d)), 100 * int((d == 1).sum()) / max(1, differ)))
    return rows


def baked():
    """-> the layers that change with the tick or the time (none, if they are baked)."""
    sys.path.insert(0, str(ADDON / 'tools'))
    import scene
    bad = []
    for state in scene.scene()['states']:
        weather = state if state in ('cloudy', 'rain') else 'clear'
        for name in ('sky', 'sea', 'sand'):
            first = None
            for when in (datetime(2026, 11, 10, 12, 0), datetime(2026, 11, 10, 12, 0, 37)):
                for tick in (0, 1, 7, 1000):
                    got = scene.pieces(name, state, weather, when, tick)
                    key = [(np.asarray(im).tobytes(), x, y) for im, x, y in got]
                    first = key if first is None else first
                    if key != first or len(got) != 1:
                        bad.append((state, name, tick))
    return bad


def report(rows, label):
    ok = True
    print(label)
    for state, name, file, size, tones, limit, mixed, step in rows:
        good = size and tones <= limit and mixed >= MIX and step >= STEP
        ok &= good
        print(f'  {state:7s} {name:5s} {file:14s} size {"ok" if size else "WRONG"}; tones {tones:2d} of {limit:2d}; '
              f'mixed {mixed:5.1f} in 100 (at least {MIX}); one step {step:5.1f} in 100 (at least {STEP})'
              f'{"" if good else "   <-- FAILS"}')
    return ok


def main():
    ok = report(measure(ADDON), 'the add-on:')
    bad = baked()
    print('baked: every layer is the same picture at ticks 0, 1, 7, 1000 and at two times' if not bad else f'NOT baked: {bad}')
    ok &= not bad
    if '--selftest' in sys.argv:
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            copy = Path(tmp)
            shutil.copytree(ADDON / 'tools', copy / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ADDON / 'art', copy / 'art')
            env = dict(os.environ, DOG_GRADIENTS='sky=bands:48,sea=bands:16,sand=bands:16')
            subprocess.run([sys.executable, '-I', '-B', 'tools/scene_build.py'], cwd=copy, env=env, check=True,
                           stdout=subprocess.DEVNULL)
            control = report(measure(copy), 'the control, the same scene built with flat bands (it must fail):')
        print('selftest:', 'the banded control fails, as it must' if not control else 'THE CONTROL PASSED: the check proves nothing')
        ok &= not control
    print('RESULT: sky, sea and sand are baked Floyd-Steinberg' if ok else 'RESULT: FAILED')
    sys.exit(0 if ok else 1)


main()
