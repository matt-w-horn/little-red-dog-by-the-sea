"""The two animations of the README, drawn by the reference renderer.

    python3 -I -B dev/make_gifs.py [day] [poses]        (both without an argument)

docs/day.gif    one day in about 25 seconds: the clock runs fast (a mark in the corner says so), slower through dawn
                and dusk so that the change of light shows. The waves and the dog move at their real pace. No
                surprise shows in it.
docs/poses.gif  each pose for three seconds at a moment it moves, one surprise, and the night with the dog in the
                doghouse's doorway.
Both are the scene's own 480x270 pixels enlarged twice with no filtering, eight pictures a second.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import scene  # noqa: E402

OUT = ROOT / 'docs'
DAY = datetime(2026, 5, 12, 4, 40)                 # a day with no holiday; the clip starts before dawn
NO_SURPRISE = ('surprises_sky', 'surprises_back', 'surprises_front')
SURPRISE = 'tall_ship'
SCALE, MS = 2, 125


def mark(rgb):
    """Two small triangles in the lower left corner: this clip runs fast."""
    for x0 in (10, 17):
        for dy in range(-4, 5):
            for dx in range(5 - abs(dy)):
                rgb[258 + dy, x0 + dx] = (255, 244, 214)
    return rgb


def save(frames, name):
    OUT.mkdir(exist_ok=True)
    big = [Image.fromarray(f).resize((480 * SCALE, 270 * SCALE), Image.NEAREST) for f in frames]
    first = big[0].quantize(colors=255, dither=Image.Dither.NONE)
    rest = [b.quantize(colors=255, dither=Image.Dither.NONE) for b in big[1:]]
    first.save(OUT / name, save_all=True, append_images=rest, duration=MS, loop=0, optimize=True)
    print(f'wrote {OUT / name}: {len(big)} pictures, {len(big) * MS / 1000:.0f} s, {(OUT / name).stat().st_size / 1e6:.1f} MB')


def day():
    times, t = [], DAY
    while t < DAY + timedelta(hours=24):
        times.append(t)
        near = any(scene.state_fade(t + timedelta(minutes=m), 'clear') for m in (-8, 0, 8))
        t += timedelta(minutes=1 if near else 12)
    frames = []
    for tick, t in enumerate(times):
        night = scene.choose_state(t, 'clear') == 'night'
        frames.append(mark(np.array(scene.frame(t, 'clear', tick, None, NO_SURPRISE, 'door' if night else 'sit'))))
    save(frames, 'day.gif')


def lively(pose, length):
    """The first tick of the stretch of `length` ticks in which the pose moves the most."""
    parts = scene.house_pose()['parts'] if pose == 'door' else scene.poses()[scene.pose_index(pose)]['parts']
    moves = [m for p in parts for m in p.get('moves', [])]
    busy = np.array([sum(scene.move_frame(m, t) is not None for m in moves) for t in range(6000)])
    sums = np.convolve(busy > 0, np.ones(length, int), 'valid')
    return int(sums.argmax())


def poses():
    noon, frames = datetime(2026, 5, 12, 13, 0), []
    for pose in [p['name'] for p in scene.scene()['dog']['poses']]:
        start = lively(pose, 24)
        frames += [np.array(scene.frame(noon, 'clear', start + k, None, NO_SURPRISE, pose)) for k in range(24)]
    item = next(i for i in scene.scene()['specials']['items'] if i['name'] == SURPRISE)
    when, weather, state, tick = scene.special_moment(item)
    frames += [np.array(scene.frame(when, weather, tick - 24 + k, state, (), 'stand')) for k in range(48)]
    night, start = datetime(2026, 5, 12, 22, 30), lively('door', 32)
    frames += [np.array(scene.frame(night, 'clear', start + k, None, NO_SURPRISE, 'door')) for k in range(32)]
    save(frames, 'poses.gif')


if __name__ == '__main__':
    todo = sys.argv[1:] or ['day', 'poses']
    for name in todo:
        {'day': day, 'poses': poses}[name]()
