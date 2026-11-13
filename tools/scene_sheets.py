"""Review pictures of the scene, made with scene.render:

    python3 -I tools/scene_sheets.py [--out DIR] [--only poses]

Writes to out/ (or DIR):
- states.png (the six lighting states and two full-moon nights at x2, two columns) and x8/<state>.png (each of the
  six states at 3840x2160);
- for each animation, <name>.png, a contact sheet of labelled frames (x2; the dog x4; the fades x1, whole frames),
  and <name>.gif, scaled by 8 at eight frames a second (one frame per tick): waves, dog, night, rain, clouds,
  fade_dawn_day, fade_clear_rain. dog.png and dog.gif show the first pose of scene.json (stand), forced;
- for the poses of scene.json (the only pictures written with --only poses):
  - poses.png: every pose (one row each) in the six lighting states (the night on the full moon of 24 November),
    whole frames at x1, each at the pose's still tick (the first from 20 on where none of its moves is active);
    poses_dog.png: the same grid, each tile the box POSE_BOX at x3;
  - pose_<name>.png and pose_<name>.gif for every pose, as dog.png and dog.gif, with the box POSE_BOX;
  - with more than one pose, pose_change.png and pose_change.gif: the first change of pose after tick 14000000000,
    every tick from 2 before its fade to 2 after it, by the schedule; the sheet whole frames at x1 labelled with the
    tick and pose_at's answer, the GIF the box POSE_BOX at x4;
- loops.txt, the length of every loop in ticks and seconds, and the numbers of the pose schedule (also with --only);
- weather.txt, the weather of each day of November 2026 and the times of its showers.
The GIFs keep every colour exactly: a frame with more than 256 colours is reported, not dithered. A GIF counts time
in hundredths of a second, so its frames alternate 120 and 130 ms: 125 ms a tick on average.
"""
import argparse
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import scene  # noqa: E402
from scene import render  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / 'out'
TICK = 20
DAY = datetime(2026, 11, 9, 13, 0)
SHOTS = [('dawn', datetime(2026, 11, 9, 6, 52), 'clear'), ('day', DAY, 'clear'),
         ('dusk', datetime(2026, 11, 9, 18, 0), 'clear'), ('night', datetime(2026, 11, 9, 23, 0), 'clear'),
         ('cloudy', datetime(2026, 11, 9, 14, 0), 'cloudy'), ('rain', datetime(2026, 11, 9, 8, 23), 'rain')]
MOON_NIGHT = datetime(2026, 11, 24, 23, 0)
DOG_BOX = (175, 155, 350, 258)
POSE_BOX = (130, 150, 350, 262)   # wider than DOG_BOX: a part may sit left of the dog's corner (a tail, the towel)
CHANGE_AFTER = 14_000_000_000


def scaled(img, k):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)


def label(text, width):
    """A strip 11 pixels high with the text in the scene's own pixel font, on black."""
    t = scene.scene()['text']
    font = scene.layer(t['font'])
    cw = t['cell'][0]
    rgb = scene.month_palette('day', 1)[0]            # the text's colours are the same in every month
    strip = np.zeros((11, width), np.uint8)
    for k, c in enumerate(text.upper()):
        i = t['chars'].find(c)
        x = 1 + k * t['advance']
        if i >= 0 and x + cw <= width:
            cell = font[:, i * cw:(i + 1) * cw]
            strip[1:10, x:x + cw][cell != 0] = cell[cell != 0]
    return Image.fromarray(rgb[strip])


def sheet(images, columns, labels=None, gap=4):
    """Lays the pictures out left to right, top to bottom, each with its label under it and a black gap after."""
    w, h = images[0].size
    lh = 11 if labels else 0
    rows = (len(images) + columns - 1) // columns
    out = Image.new('RGB', (columns * (w + gap), rows * (h + lh + gap)))
    for k, img in enumerate(images):
        x, y = (k % columns) * (w + gap), (k // columns) * (h + lh + gap)
        out.paste(img, (x, y))
        if labels:
            out.paste(label(labels[k], w), (x, y + h))
    return out


def change_sheet(name, before, after, box, caption):
    """out/change_<name>.png: the same crop of two day frames, before and after a change, at x3,
    side by side, each captioned, with the caption of the change above them."""
    a, b = (scaled(f.crop(box), 3) for f in (before, after))
    pair = sheet([a, b], 2, ['before', 'after'])
    out = Image.new('RGB', (pair.width, pair.height + 13))
    out.paste(label(caption, pair.width), (0, 0))
    out.paste(pair, (0, 13))
    out.save(OUT / f'change_{name}.png')


def to_p(img):
    """An exact P-mode copy of an RGB picture, or None when it has more than 256 colours."""
    a = np.array(img).reshape(-1, 3)
    colours, inverse = np.unique(a, axis=0, return_inverse=True)
    if len(colours) > 256:
        return None
    p = Image.frombytes('P', img.size, inverse.astype(np.uint8).reshape(-1).tobytes())
    p.putpalette(colours.astype(np.uint8).reshape(-1).tolist())
    return p


def gif(name, frames, scale=8, out=None):
    """frames: RGB pictures at 1x, one per tick. Writes <name>.gif at x scale into out (default OUT), eight frames a
    second, and reads it back to check that every frame came out with exactly the colours it went in with."""
    p = [to_p(f) for f in frames]
    over = [k for k, f in enumerate(p) if f is None]
    if over:
        print(f'  {name}.gif: frames {over} have more than 256 colours; they are quantised without dithering')
        p = [f if f is not None else b.quantize(256, dither=Image.Dither.NONE) for f, b in zip(p, frames)]
    p = [scaled(f, scale) for f in p]
    path = (out or OUT) / f'{name}.gif'
    # A GIF counts time in hundredths of a second, so ticks alternate 120 and 130 ms: every two ticks take 250 ms.
    p[0].save(path, save_all=True, append_images=p[1:], duration=[120 + 10 * (t % 2) for t in range(len(p))],
              loop=0, disposal=1)
    back = Image.open(path)
    stored, exact, ms = back.n_frames, True, 0
    for i in range(stored):
        back.seek(i)
        k = (ms + 62) // 125
        want = np.repeat(np.repeat(np.array(frames[k]), scale, axis=0), scale, axis=1)
        exact &= np.array_equal(np.array(back.convert('RGB')), want) or k in over
        ms += back.info['duration']
    k = (ms + 62) // 125
    print(f'  {name}.gif: {path.stat().st_size / 1e6:.1f} MB, {len(frames)} ticks, {stored} stored frames, '
          f'{"colours exact" if exact else "COLOURS CHANGED"}{f" except {len(over)} quantised frames" if over else ""}, '
          f'ends on tick {k}')


def pose_moves(pose):
    """Every move of every part of a loaded pose."""
    return [m for part in pose['parts'] for m in part['moves']]


def stand_moves():
    """The moves of the first pose (stand), every part's."""
    return [m for pose in scene.poses()[:1] for m in pose_moves(pose)]


def still_tick(moves):
    """The first tick from 20 on where none of the moves is active (as scene_export.py picks it)."""
    return next(t for t in range(20, 20000) if all(scene.move_frame(m, t) is None for m in moves))


def first_ticks(moves, limit):
    """For each dog movement, the first tick it shows each of its frames while no other movement is happening."""
    found = {}
    for t in range(limit):
        active = [(m['name'], scene.move_frame(m, t)) for m in moves if scene.move_frame(m, t) is not None]
        if len(active) == 1 and active[0] not in found:
            found[active[0]] = t
    return found


def dog_window(moves, length):
    """The first tick (a multiple of 8) from which every movement happens within `length` ticks; 0 if none does."""
    wanted = {m['name'] for m in moves}
    for start in range(0, 20000, 8):
        names = {m['name'] for t in range(start, start + length) for m in moves if scene.move_frame(m, t) is not None}
        if wanted <= names:
            return start
    return 0


def dog_pictures(name, pose, box):
    """<name>.png: the box at x4 at the still tick and at the first tick each frame of each movement shows alone;
    <name>.gif: 240 ticks at x8 from dog_window. The pose is forced, by day."""
    moves = pose_moves(pose)
    found = first_ticks(moves, 4000)
    still = next(t for t in range(4000) if all(scene.move_frame(m, t) is None for m in moves))
    shots = [('still', still)] + sorted(((f'{n} frame {k}', t) for (n, k), t in found.items()), key=lambda s: s[1])
    sheet([scaled(render(DAY, 'clear', t, 'day', pose['name']).crop(box), 4) for _, t in shots], 3,
          [f'{n} alone, tick {t}' for n, t in shots]).save(OUT / f'{name}.png')
    start = dog_window(moves, 240)
    gif(name, [render(DAY, 'clear', t, 'day', pose['name']).crop(box) for t in range(start, start + 240)])
    print(f'  {name}.gif runs from tick {start}' + ('' if moves else f' (pose {pose["name"]} has no moves)'))


def pose_shots():
    """SHOTS with the night on the full moon of 24 November, so that the moon and its shadow show."""
    return [(s, MOON_NIGHT if s == 'night' else t, w) for s, t, w in SHOTS]


def pose_pictures():
    """poses.png, poses_dog.png, pose_<name>.png/.gif and, with more than one pose, pose_change.png/.gif."""
    poses = scene.poses()
    if not poses:
        print('  poses: scene.json has no pose, so there are no pose pictures')
        return
    frames, names = [], []
    for pose in poses:
        tick = still_tick(pose_moves(pose))
        for state, time, weather in pose_shots():
            frames.append(render(time, weather, tick, state, pose['name']))
            names.append(f'{pose["name"]} {state} tick {tick}')
    sheet(frames, len(SHOTS), names).save(OUT / 'poses.png')
    sheet([scaled(f.crop(POSE_BOX), 3) for f in frames], len(SHOTS), names).save(OUT / 'poses_dog.png')
    print(f'poses.png and poses_dog.png: {len(poses)} pose{"s" * (len(poses) > 1)} '
          f'({" ".join(p["name"] for p in poses)}) x {len(SHOTS)} states')
    for pose in poses:
        dog_pictures(f'pose_{pose["name"]}', pose, POSE_BOX)
    if len(poses) < 2:
        print('  pose_change: one pose in scene.json, so no change of pose to show')
        return
    p = scene.scene()['dog']['pose_change']
    s = CHANGE_AFTER // p['hold']
    while scene.change_start(s) <= CHANGE_AFTER:
        s += 1
    start = scene.change_start(s)
    ticks = range(start - 2, start + p['fade_ticks'] + 2)
    run = [render(DAY, 'clear', t, 'day') for t in ticks]

    def said(t):
        old, new, step = scene.pose_at(t)
        new = poses[new]['name']
        return f'tick {t}: {new}' if old is None else f'tick {t}: {poses[old]["name"]}/{new} step {step}'
    sheet(run, 4, [said(t) for t in ticks]).save(OUT / 'pose_change.png')
    gif('pose_change', [f.crop(POSE_BOX) for f in run], scale=4)
    print(f'  pose_change: slot {s}, fade starts at tick {start}; ticks {ticks[0]}..{ticks[-1]}')


def weather_text():
    """weather.txt: each day of November 2026, its weather, and for rain days the shower's start and end."""
    lines = []
    for d in range(1, 31):
        day = datetime(2026, 11, d)
        w = scene.day_weather(day)
        if w == 'rain':
            start, end = scene.shower(day)
            w += f'  shower {start // 60:02d}:{start % 60:02d} to {end // 60:02d}:{end % 60:02d}'
        lines.append(f'{day:%Y-%m-%d %a}  {w}')
    return '\n'.join(lines) + '\n'


def loops_text():
    sc = scene.scene()
    rows = [('waves', sc['foam']['frames'] * sc['foam']['ticks_per_frame']),
            ('glints', sc['glints']['ticks_per_step'] * len(sc['glints']['roles'])),
            ('light paths', sc['paths']['ticks_per_step'] * sc['paths']['frames']),
            ('lighthouse beam', sc['beam']['ticks_per_frame'] * sc['beam']['frames']),
            ('rain ripples', sc['ripples']['ticks_per_frame'] * sc['ripples']['frames'])]
    listed = math.lcm(*(n for _, n in rows))
    tw, th = sc['rain']['tile']
    for name, r in sc['rain']['layers'].items():
        lean = sc['rain']['lean']
        rows.append((name, math.lcm(th // math.gcd(th, r['speed']), tw * lean // math.gcd(tw * lean, r['speed']))))
    for k, t in enumerate(sc['clouds']['tracks']):
        rows.append((f'cloud {k}', sc['clouds']['span'] * t['ticks_per_px']))
    for m in stand_moves():
        t = m['timetable']
        rows.append((f'dog {m["name"]} ({"regular" if "period" in t else "irregular, slot"})',
                     t.get('period') or t['slot']))
    rows.append(('star twinkle (irregular, slot)', sc['twinkle']['slot']))
    rows.append(('fade', sc['fade']['ticks']))
    lines = [f'{name:34} {n:7d} ticks {n / 8:9.3f} s' for name, n in rows]
    rain = math.lcm(listed, *(n for name, n in rows if name.startswith('rain_')))
    lines += ['', f'{"L (waves, glints, paths, beam, ripples)":34} {listed:7d} ticks {listed / 8:9.3f} s',
              f'{"L with the rain tiles":34} {rain:7d} ticks {rain / 8:9.3f} s']
    return '\n'.join(lines + [''] + schedule_lines()) + '\n'


def schedule_lines(slots=3000):
    """The pose schedule: hold, jitter and fade ticks, and the shortest and longest time between the starts of two
    neighbouring changes of pose over slots 0..slots-1."""
    p, names = scene.scene()['dog']['pose_change'], [e['name'] for e in scene.scene()['dog']['poses']]
    rows = [('pose hold', p['hold']), ('pose jitter', p['jitter']), ('pose fade', p['fade_ticks'])]
    head = f'pose schedule: {len(names)} pose{"s" * (len(names) > 1)} ({" ".join(names)})'
    if len(names) < 2:
        return [head + '; with one pose there is no change, and these numbers are unused'] + \
            [f'{name:34} {n:7d} ticks {n / 8:9.3f} s' for name, n in rows]
    starts = [scene.change_start(s) for s in range(slots)]
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    rows += [(f'pose change gap, min ({slots} slots)', min(gaps)), (f'pose change gap, max ({slots} slots)', max(gaps))]
    return [head] + [f'{name:34} {n:7d} ticks {n / 8:9.3f} s' for name, n in rows]


def main():
    global OUT
    ap = argparse.ArgumentParser(description='Review pictures of the scene.')
    ap.add_argument('--out', type=Path, default=OUT, help=f'where to write (default {OUT})')
    ap.add_argument('--only', choices=['poses'], help='write only the pose pictures and loops.txt')
    args = ap.parse_args()
    OUT = args.out.resolve()
    if args.only == 'poses':
        OUT.mkdir(parents=True, exist_ok=True)
        pose_pictures()
        text = loops_text()
        (OUT / 'loops.txt').write_text(text)
        print(text)
        return
    (OUT / 'x8').mkdir(parents=True, exist_ok=True)
    frames = []
    for state, time, weather in SHOTS:
        frame = render(time, weather, TICK, state)
        scaled(frame, 8).save(OUT / 'x8' / f'{state}.png')
        frames.append(scaled(frame, 2))
    names = [f'{s} {t:%H:%M} {w} tick {TICK}' for s, t, w in SHOTS]
    # 9 November 2026 is a new moon, so the night above has no moon. Two more nights, on the full moon of 24 November:
    # clear (the moon and its path on the water) and in rain (no stars, no moon).
    for weather in ('clear', 'rain'):
        frames.append(scaled(render(MOON_NIGHT, weather, TICK, 'night'), 2))
        names.append(f'night {MOON_NIGHT:%d %b %H:%M} {weather} tick {TICK}')
    sheet(frames, 2, names).save(OUT / 'states.png')
    print('states.png and x8/')

    # Waves: one whole wave in the day, the bay.
    bay = (150, 110, 390, 270)
    run = [render(DAY, 'clear', t, 'day').crop(bay) for t in range(152)]
    sheet([scaled(run[t], 2) for t in range(0, 152, 10)], 4, [f'tick {t}' for t in range(0, 152, 10)]).save(OUT / 'waves.png')
    gif('waves', run)

    # The dog in the day, and its shadow: the first pose (stand), forced.
    if not scene.poses():
        print('  dog: art/dog.png is missing, so there is no dog sheet or GIF')
    else:
        dog_pictures('dog', scene.poses()[0], DOG_BOX)

    # Night: the beam's turn and the stars, on the point and the sky.
    night = SHOTS[3][1]
    point = (150, 0, 480, 130)
    sheet([scaled(render(night, 'clear', t, 'night').crop(point), 2) for t in range(0, 64, 4)], 4,
          [f'tick {t}' for t in range(0, 64, 4)]).save(OUT / 'night.png')
    gif('night', [render(night, 'clear', t, 'night').crop(point) for t in range(128)])

    # Rain: the streaks and the rings.
    rain_t, box = SHOTS[5][1], (200, 40, 440, 200)
    sheet([scaled(render(rain_t, 'rain', t, 'rain').crop(box), 2) for t in range(40, 48)], 4,
          [f'tick {t}' for t in range(40, 48)]).save(OUT / 'rain.png')
    gif('rain', [render(rain_t, 'rain', t, 'rain').crop(box) for t in range(48)])

    # Clouds: a cloudy afternoon, the sky; they move a pixel every 18 to 24 ticks.
    cloudy, sky = SHOTS[4][1], (0, 0, 480, 100)
    sheet([scaled(render(cloudy, 'cloudy', t, 'cloudy').crop(sky), 2) for t in range(0, 1280, 160)], 2,
          [f'tick {t}' for t in range(0, 1280, 160)]).save(OUT / 'clouds.png')
    gif('clouds', [render(cloudy, 'cloudy', t, 'cloudy').crop(sky) for t in range(320)])

    # Fades. Dawn to day: the boundary at sunrise + 60 (07:40 in autumn); the step comes from the time.
    edge = datetime(2026, 11, 9, 7, 40)
    at = [edge + timedelta(microseconds=125_000 * k) for k in range(-4, 72)]
    run = [render(t, 'clear', 1000 + k) for k, t in enumerate(at)]
    picks = list(range(0, 76, 8))
    sheet([run[k] for k in picks], 4, [f'{at[k]:%H:%M:%S}.{at[k].microsecond // 1000:03d}' for k in picks]
          ).save(OUT / 'fade_dawn_day.png')
    gif('fade_dawn_day', run)

    # Clear to rain at 13:00: the caller gives the step, one step every two ticks.
    run = [render(DAY, ('clear', 'rain', min(32, max(0, (t - 4) // 2))), 1000 + t) for t in range(76)]
    picks = list(range(0, 76, 8))
    sheet([run[t] for t in picks], 4, [f'step {min(32, max(0, (t - 4) // 2))}' for t in picks]
          ).save(OUT / 'fade_clear_rain.png')
    gif('fade_clear_rain', run)

    pose_pictures()

    text = loops_text()
    (OUT / 'loops.txt').write_text(text)
    (OUT / 'weather.txt').write_text(weather_text())
    print(text)


if __name__ == '__main__':
    main()
