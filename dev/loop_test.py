"""Loop test of the Python scene renderer: every animation repeats, and no wrap makes a visible jump.
python3 -I dev/loop_test.py [--tools DIR]
    prints the result and writes out/loop_test.txt. With --tools, the test imports DIR/scene.py
    (which reads DIR/../art) and writes DIR/../loop_test.txt instead.

What it checks, and what each check cannot see:
1. The periodic part of the frame (waves, glints, light paths, beam, rain ripples, rain tiles) repeats after
   L = 54720 ticks in every lighting state. Clouds, star twinkle and the dog's movements are left out here: clouds
   have their own longer periods (check 2) and twinkle and three dog movements follow a hash, not a period.
   The pose is forced to the first of scene.json (stand): the pose schedule has no period, and check 5 tests it.
   Without rain the shorter loop of 18240 ticks must hold too. Negative controls: the frame one tick later must
   differ everywhere, and in rain the frame 18240 ticks later must differ (the rain tiles need three times that).
   (A first control, "N + 152 differs", was wrong: 152 ticks move the glints by 25 steps of their 5, so by day the
   frame can repeat after 152 ticks. The control was at fault, not the renderer.)
2. Each cloud is off the screen on both sides of its wrap, in both sizes, and its position repeats after its period.
   Negative control: a made-up track with a span of 400 must be reported as visible.
3. The wave strip's step from its last frame to its first changes no more pixels than its other steps do.
   The same for the ripple strip and the beam strip. It counts changed pixels; it does not judge the motion.
4. The dog, for every part of every pose of scene.json, one block per pose: at every tick where none of the part's
   movements is active the part is its still image; and no pixel of the part steps more than STEP_LIMIT (2) pixels
   from one tick to the next while a movement plays (move_step follows every opaque pixel through the movement's
   shifts and shears, from the still image to the first frame, from frame to frame as they play, and back to the
   still image). 2 is the largest step of the movements accepted before this check existed (the standing dog's tail,
   the sphinx's tail as it drops). The area that changes, the movements' starts and the largest change in one tick
   are reported, not limited. The step check sees one movement at a time: two movements that move the same pixels
   in one tick are not added up. Negative control: a made-up movement that lifts a block 3 pixels in one tick must
   be reported.
5. The changes of pose (skipped with one pose): for the first 40 changes that start after tick 0 and the first 40
   after tick 14000000000, at every tick from 3 before the start to 3 after the fade (day, clear):
   - pose_at names only the old pose before the start, (old, new, (tick - start) * steps // fade_ticks) during the
     fade and only the new pose after it; the start is computed here from the formula of ENGINE_SPEC.md section 6;
   - the frame is the old pose's forced frame before the start, the new pose's after the fade, and during it
     blend(old, new, step) computed here from the two forced frames;
   - the jump bound, per pixel and channel: between two neighbouring ticks the frame changes by at most
     ceil(|new - old| / fade_ticks) + the larger change of the two forced poses on their own in one tick + 1
     (the three terms are each the largest over the change's ticks, at that pixel). A correct fade with the step
     rising by steps / fade_ticks a tick stays inside it. The largest change between neighbouring ticks of the whole
     frame, and of the old pose alone, are reported beside it. The bound fits only a fade whose ticks divide its
     steps (16 into 32): with another setting a correct fade can pass the bound, so the check then fails and says
     that the bound, not the fade, must be changed.
   Negative control: a made-up change with no fade (the old pose up to the start, the new pose from it) must break
   the jump bound in every change.
"""
import argparse
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.dont_write_bytecode = True
scene = None   # imported in main(), from TOOLS or from --tools

OUT = ROOT / 'out' / 'loop_test.txt'
DAY = datetime(2026, 11, 9, 13, 0)
CHANGES = 40
CHANGE_FROM = [0, 14_000_000_000]
AROUND = 3
SKIP = ('clouds', 'twinkle', 'dog_moves', 'surprises_sky', 'surprises_back', 'surprises_front')   # surprises follow a hash, not a period
STEP_LIMIT = 2
SHOTS = [('dawn', datetime(2026, 11, 9, 6, 52), 'clear'), ('day', datetime(2026, 11, 9, 13, 0), 'clear'),
         ('dusk', datetime(2026, 11, 9, 18, 0), 'clear'), ('night', datetime(2026, 11, 24, 23, 0), 'clear'),
         ('cloudy', datetime(2026, 11, 9, 14, 0), 'cloudy'), ('rain', datetime(2026, 11, 9, 8, 23), 'rain'),
         ('night', datetime(2026, 11, 24, 23, 0), 'rain')]
STARTS = [20, 1234, 14354064000]

lines, failed = [], []


def say(s=''):
    lines.append(s)
    print(s)


def need(ok, what):
    if not ok:
        failed.append(what)
    return 'ok' if ok else 'FAIL'


def core_loop():
    sc = scene.scene()
    listed = math.lcm(sc['foam']['frames'] * sc['foam']['ticks_per_frame'],
                      sc['glints']['ticks_per_step'] * len(sc['glints']['roles']),
                      sc['paths']['ticks_per_step'] * sc['paths']['frames'],
                      sc['beam']['ticks_per_frame'] * sc['beam']['frames'],
                      sc['ripples']['ticks_per_frame'] * sc['ripples']['frames'])
    tw, th = sc['rain']['tile']
    lean = sc['rain']['lean']
    rain = [math.lcm(th // math.gcd(th, r['speed']), tw * lean // math.gcd(tw * lean, r['speed']))
            for r in sc['rain']['layers'].values()]
    L = math.lcm(listed, *rain)
    first = sc['dog']['poses'][0]['name'] if sc['dog']['poses'] else None
    say(f'1. Periodic part, skip={SKIP}, pose {first}. L = {L} ticks ({L / 8 / 60:.0f} min); '
        f'without the rain tiles {listed}.')
    for state, time, weather in SHOTS:
        for n in STARTS:
            a = scene.finished(time, weather, n, state, SKIP, first)
            same = np.array_equal(a, scene.finished(time, weather, n + L, state, SKIP, first))
            next_differs = not np.array_equal(a, scene.finished(time, weather, n + 1, state, SKIP, first))
            short = np.array_equal(a, scene.finished(time, weather, n + listed, state, SKIP, first))
            want = weather != 'rain'  # the rain tiles do not repeat after the shorter loop
            say(f'   {state:6} {weather:6} N={n:<12} N+L equal: {need(same, f"core {state} {n}")}; '
                f'N+1 differs: {need(next_differs, f"control N+1 {state} {n}")}; '
                f'N+{listed} {"equal" if want else "differs"}: {need(short == want, f"short loop {state} {weather} {n}")}')


def cloud_box(c, track, size, tick):
    x = (track['start_x'] + tick // track['ticks_per_px']) % c['span'] + c['left']
    _, _, w, _ = track[size]['sheet']
    return x + track[size]['dx'], x + track[size]['dx'] + w - 1


def cloud_wrap_visible(c, track, size):
    """True when the cloud shows on the screen right before or right after its wrap."""
    last = (c['span'] - 1 - track['start_x']) % c['span'] * track['ticks_per_px']  # first tick with x = left + span - 1
    before, after = cloud_box(c, track, size, last), cloud_box(c, track, size, last + track['ticks_per_px'])
    assert before[0] - track[size]['dx'] == c['left'] + c['span'] - 1 and after[0] - track[size]['dx'] == c['left']
    on = lambda box: box[1] >= 0 and box[0] < scene.W
    return on(before) or on(after), before, after


def clouds():
    c = scene.scene()['clouds']
    say('2. Clouds: columns covered right before and right after the wrap (the screen is 0..479).')
    for k, track in enumerate(c['tracks']):
        period = c['span'] * track['ticks_per_px']
        for size in ('normal', 'grown'):
            visible, before, after = cloud_wrap_visible(c, track, size)
            repeats = all(cloud_box(c, track, size, n) == cloud_box(c, track, size, n + period) for n in STARTS)
            say(f'   cloud {k} {size:6} period {period:5} ticks: before {before}, after {after}: '
                f'{need(not visible, f"cloud {k} {size} wrap")}; repeats: {need(repeats, f"cloud {k} period")}')
    bad = dict(c, span=400)
    visible, before, after = cloud_wrap_visible(bad, c['tracks'][0], 'normal')
    say(f'   control, span 400: before {before}, after {after}: reported visible: {need(visible, "cloud control")}')


def strip_steps(name, frames, height):
    """Changed pixels between consecutive frames of a strip of full-width frames stacked top to bottom."""
    img = scene.layer(name)
    fr = [img[k * height:(k + 1) * height] for k in range(frames)]
    inner = [int((fr[k] != fr[k + 1]).sum()) for k in range(frames - 1)]
    return inner, int((fr[-1] != fr[0]).sum())


def strips():
    sc = scene.scene()
    say('3. Strips: pixels that change from one frame to the next; the wrap is the step from the last frame to the first.')
    for key in ('foam', 'ripples'):
        f = sc[key]
        inner, wrap = strip_steps(f['file'], f['frames'], f['frame_height'])
        ok = min(inner) <= wrap <= max(inner)
        say(f'   {key:8} {f["frames"]} frames: other steps {min(inner)}..{max(inner)} (median {int(np.median(inner))}), '
            f'wrap {wrap}: {need(ok, f"{key} wrap")}')
    b = sc['beam']
    img, w = scene.layer(b['file']), b['size'][0]
    fr = [img[:, k * w:(k + 1) * w] for k in range(b['frames'])]
    inner = [int((fr[k] != fr[k + 1]).sum()) for k in range(b['frames'] - 1)]
    wrap = int((fr[-1] != fr[0]).sum())
    say(f'   beam     {b["frames"]} frames: other steps {min(inner)}..{max(inner)}, wrap {wrap}: '
        f'{need(min(inner) <= wrap <= max(inner), "beam wrap")}')


def move_step(sprite, move):
    """The largest whole-pixel step (in x or in y) that any opaque pixel of the sprite takes from one tick to the next
    while the move plays. Each pixel carries its own number through the move's shifts and shears (a recolour moves
    nothing); a pixel that a frame covers or pushes out of the image is not counted in that step."""
    h, w = sprite.shape
    ids = np.where(sprite != 0, np.arange(1, h * w + 1).reshape(h, w), 0)

    def places(frame):
        img = ids.copy()
        for op in frame:
            if op['op'] == 'shift':
                scene.move_pixels(img, op['rect'], op['dx'], op['dy'], 0)
            elif op['op'] == 'shear':
                x, y, rw, _ = op['rect']
                for k, dx in enumerate(op['dx']):
                    scene.move_pixels(img, [x, y + k, rw, 1], dx, 0, 0)
        ys, xs = np.nonzero(img)
        at = np.full((h * w + 1, 2), -10 ** 6)
        at[img[ys, xs]] = np.stack([ys, xs], 1)
        return at

    played = [(t // move['ticks_per_frame']) % len(move['frames']) for t in range(move['timetable']['length'])]
    frames = {k: places(move['frames'][k]) for k in set(played)}
    still = places([])
    run, worst = [still] + [frames[k] for k in played] + [still], 0
    for a, b in zip(run, run[1:]):
        both = (a[:, 0] >= 0) & (b[:, 0] >= 0)
        if both.any():
            worst = max(worst, int(np.abs(a[both] - b[both]).max()))
    return worst


def dog(limit=40000, poses=None):
    """Check 4 for every part of every pose (default: the poses of scene.json)."""
    poses = scene.poses() if poses is None else poses
    files = {e['name']: [Path(p['file']).name for p in e['parts']] for e in scene.scene()['dog']['poses']}
    say(f'4. Dog, every part of every pose, ticks 0..{limit - 1} ({limit / 8 / 60:.0f} min).')
    for pose in poses:
        say(f'   pose {pose["name"]}:')
        for k, part in enumerate(pose['parts']):
            name = files.get(pose['name'], [])[k:k + 1]
            dog_part(f'{pose["name"]} part {k}', f'part {k}{" " + name[0] if name else ""}', part, limit)
    block = np.zeros((12, 12), np.uint8)
    block[6:9, 2:8] = 2
    jump = dict(name='made-up', ticks_per_frame=1, timetable=dict(period=40, length=4), frames=[
        [dict(op='shift', rect=[2, 6, 6, 3], dx=0, dy=-3, fill=None)]])
    seen = move_step(block, jump)
    say(f'   negative control, a made-up movement that lifts a block 3 pixels in one tick: step {seen} px, '
        f'{"reported" if seen > STEP_LIMIT else "NOT SEEN"}: {need(seen > STEP_LIMIT, "step control")}')


def dog_part(key, title, part, limit):
    sprite, moves = part['image'], part['moves']
    h, w = sprite.shape
    title = f'     {title} ({w} x {h}{", flat" if part["flat"] else ""})'
    if not moves:
        say(f'{title}: no movements, so nothing here applies')
        return
    say(f'{title}:')
    still_ok, worst, worst_at, prev = True, 0, None, scene.dog_frame(sprite, 0, moves)
    area = np.zeros(sprite.shape, bool)
    counts = {m['name']: 0 for m in moves}
    was = {m['name']: False for m in moves}
    for t in range(limit):
        active = [m['name'] for m in moves if scene.move_frame(m, t) is not None]
        for m in moves:
            on = m['name'] in active
            counts[m['name']] += on and not was[m['name']]
            was[m['name']] = on
        cur = scene.dog_frame(sprite, t, moves)
        if not active and not np.array_equal(cur, sprite):
            still_ok = False
        changed = cur != prev
        area |= changed
        if int(changed.sum()) > worst:
            worst, worst_at = int(changed.sum()), t
        prev = cur
    say(f'       still image whenever no movement is active: {need(still_ok, f"dog still, {key}")}')
    say(f'       movements started: {counts}')
    if area.any():
        ys, xs = np.nonzero(area)
        say(f'       largest change in one tick: {worst} pixels (tick {worst_at}); every changed pixel lies in '
            f'columns {xs.min()}..{xs.max()}, rows {ys.min()}..{ys.max()} of the {w} x {h} image')
    else:
        say('       no pixel changed in any tick')
    # how far a pixel moves in one tick: the shear rows move by the listed dx, the shifts by their dx, dy
    used = {}
    for m in moves:
        steps = used.setdefault(m['name'], set())
        for frame in m['frames']:
            for op in frame:
                if op['op'] == 'shift':
                    steps.add(max(abs(op['dx']), abs(op['dy'])))
                elif op['op'] == 'shear':
                    steps.update(abs(d) for d in op['dx'])
    say(f'       whole-pixel displacements used by the movements: '
        f'{sorted(set().union(*used.values()))} ({", ".join(f"{n} {sorted(s)}" for n, s in used.items())})')
    steps = {m['name']: move_step(sprite, m) for m in moves}
    say(f'       largest step of a pixel from one tick to the next, per movement: {steps}; none above {STEP_LIMIT}: '
        f'{need(max(steps.values()) <= STEP_LIMIT, f"step, {key}")}')


def spec_start(s, p):
    """ENGINE_SPEC.md section 6: start = s * hold + hash(s, 1, salt) mod jitter, on the low 32 bits of s."""
    return s * p['hold'] + scene.beach_hash(s & 0xFFFFFFFF, 1, p['salt']) % p['jitter']


def mix(old, new, step, steps):
    """The fade's blend, written out here: (old * (steps - step) + new * step + steps // 2) // steps per channel."""
    return (old * (steps - step) + new * step + steps // 2) // steps


def changes():
    entries = scene.scene()['dog']['poses']
    names = [e['name'] for e in entries]
    if len(names) < 2:
        say(f'5. Changes of pose: skipped, scene.json has {len(names)} pose ({" ".join(names)}), so the pose never changes.')
        return
    p, steps = scene.scene()['dog']['pose_change'], scene.scene()['fade']['steps']
    say(f'5. Changes of pose: {len(names)} poses ({" ".join(names)}); hold {p["hold"]}, jitter {p["jitter"]}, '
        f'fade {p["fade_ticks"]} ticks, {steps} steps. Day, clear; ticks start-{AROUND} .. start+fade+{AROUND - 1}.')
    say(f'   the jump bound fits this fade (its ticks divide its steps): '
        f'{need(steps % p["fade_ticks"] == 0, "check 5: the bound does not fit a fade whose ticks do not divide its steps; change the bound")}')
    say('   columns: slot, start, old -> new; pose_at; frames; largest change between neighbouring ticks of the whole '
        'frame (of the old pose alone); jump bound (largest excess over it, <= 0 passes); the no-fade control')
    total, caught = 0, 0
    for after in CHANGE_FROM:
        say(f'   the first {CHANGES} changes that start after tick {after}:')
        s, found = after // p['hold'], 0
        while found < CHANGES:
            start = spec_start(s, p)
            if start > after:
                caught += one_change(s, start, p, steps, names)
                total += 1
                found += 1
            s += 1
    say(f'   {total} changes checked; the no-fade control was reported as a jump in {caught} of them: '
        f'{need(caught == total, "no-fade control")}')


def one_change(s, start, p, steps, names):
    """Checks one change; returns 1 when its no-fade control breaks the jump bound."""
    fade = p['fade_ticks']
    ticks = range(start - AROUND, start + fade + AROUND)
    said = {t: scene.pose_at(t) for t in ticks}
    old, new = said[start - 1][1], said[start + fade][1]
    want = {t: (None, old, None) if t < start else (None, new, None) if t >= start + fade
            else (old, new, (t - start) * steps // fade) for t in ticks}
    asked = all(said[t] == want[t] for t in ticks) and old != new
    shot = lambda t, pose: np.asarray(scene.render(DAY, 'clear', t, 'day', pose), np.int32)
    real = [shot(t, None) for t in ticks]
    a = [shot(t, names[old]) for t in ticks]
    b = [shot(t, names[new]) for t in ticks]
    expect = [x if t < start else y if t >= start + fade else mix(x, y, (t - start) * steps // fade, steps)
              for t, x, y in zip(ticks, a, b)]
    frames = all(np.array_equal(r, e) for r, e in zip(real, expect))
    step_of = lambda run: np.max([np.abs(y - x) for x, y in zip(run, run[1:])], axis=0)
    apart = np.max([np.abs(y - x) for x, y in zip(a, b)], axis=0)
    allowed = (apart + fade - 1) // fade + np.maximum(step_of(a), step_of(b)) + 1
    over = step_of(real) - allowed
    # passes when nothing is over; the margin shown is the closest approach where the poses differ (elsewhere it is
    # at most -1 by construction, which would hide how near the fade comes)
    excess = int(over.max()) if over.max() > 0 else int(over[apart > 0].max()) if (apart > 0).any() else int(over.max())
    cut = [x if t < start else y for t, x, y in zip(ticks, a, b)]
    control = int((step_of(cut) - allowed).max())
    key = f'slot {s} start {start}'
    say(f'     {key:28} {names[old]:>6} -> {names[new]:6}; pose_at {need(asked, f"pose_at, {key}")}; '
        f'frames {need(frames, f"frames, {key}")}; largest change {int(step_of(real).max())} '
        f'(old alone {int(step_of(a).max())}); jump bound {need(excess <= 0, f"jump, {key}")} ({excess:+d}); '
        f'no fade: {"jump" if control > 0 else "NOT SEEN"} ({control:+d})')
    return int(control > 0)


def main():
    global scene, OUT
    ap = argparse.ArgumentParser(description='Loop test of the Python scene renderer.')
    ap.add_argument('--tools', type=Path, help=f'the tools folder whose scene.py to test (default {TOOLS}); '
                    'the output then goes to DIR/../loop_test.txt')
    args = ap.parse_args()
    tools = (args.tools or TOOLS).resolve()
    if args.tools:
        OUT = tools.parent / 'loop_test.txt'
    sys.path.insert(0, str(tools))
    import scene  # noqa: F811
    say(f'scene.py: {Path(scene.__file__).resolve()}; art: {scene.ART}')
    say()
    core_loop()
    say()
    clouds()
    say()
    strips()
    say()
    dog()
    say()
    changes()
    say()
    say('RESULT: ' + ('every check passed' if not failed else f'{len(failed)} FAILED: {failed}'))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(lines) + '\n')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
