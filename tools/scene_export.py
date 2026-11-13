"""Reference frames for the Java port, made with scene.render and scene.render_now:

    python3 -I tools/scene_export.py

Writes the frames (480x270 RGB PNGs) to out/reference_frames/ and art/reference/manifest.json. Each entry holds every input of the call
that drew it, and the SHA-256 of the frame's raw RGB bytes (row by row, three bytes a pixel, no header):
- via "render": date, time (HH:MM:SS.ffffff), weather (a name, or [old, new, step]), frame_number, state (null, or the
  state passed to override the one the time gives), pose (a pose name, or null for the schedule, scene.pose_at);
- via "render_now": date, time, epoch_ms (the same instant in the time zone named); the pose follows the schedule.
The other fields (drawn_state, derived_weather, derived_tick) are for reading only. The Java renderer passes when it
gives the same bytes for the same inputs. Every other PNG directly in out/reference_frames/ is deleted. The frames are
not tracked: only their hashes in the manifest are tested.

For every pose in scene.json: pose_<name>_<state> (the six SHOTS, at the first tick from 20 on where none of its moves
is active) and pose_<name>_<move>_alone_tick<t>. With more than one pose: pose_fade_step<k>, three ticks of the first
pose change after tick 0 (schedule), and art/reference/pose_schedule.txt: 'poses <name> ...', then
'tick<TAB>old<TAB>new<TAB>step' (names, '-' for none) at start - 1, start, start + fade_ticks - 1 and
start + fade_ticks of the change in slots 0..9 and S..S+199, S = 14000000000 // hold.

Also writes art/reference/quotes_wrapped.txt: the wrap width, then for every hour of QUOTE_SPANS the quote of that
hour as scene.wrap breaks it, 'YYYY-MM-DD HH<TAB>line|line'. The Java renderer must give the same lines for every hour.
The export stops, naming the hours, if a quote shows twice inside one pass of those hours (so a whole pass shows every
quote once) or if two hours in a row show the same quote; and if the quote of quote_four_lines does not wrap to four
lines.

For the months: month_<mm>_noon, the 15th of each month of 2026 at 12:30 drawn from the clock alone (the month's
palette, weather, sun times and shadow), and mix_<mmdd>, five days on which one month's palette is mixed with the
next's. art/reference/day_states.txt holds, for 24 times of every day of 2026 and of February and March 2028,
'YYYY-MM-DD HH:MM<TAB>weather<TAB>state' as scene.weather_name and scene.choose_state give them: sunrise and sunset by
month, summer time, the weather's odds and the morning cloud. art/reference/layer_counts.txt holds the size of
layers/clouds.png and how many pixels it has of each index, as Pillow reads it (for the Java PNG reader).
art/reference/evening.txt holds scene.evening_factors for every tenth minute of six days, settled and at five moments
after the screensaver starts: how far the app dims and warms the finished frame.

For what shows only on some dates (scene.json, specials): special_<name>, a frame on each holiday of 2026 and in the
months of the boats, the fog, the smoke and the driftwood, with the flag and December's lamps in their second frame,
the fireworks at three ticks, an evening hour before they start, three days that come two before a holiday, and the
whale's flukes. art/reference/specials_days.txt holds, for every day of 2026 to 2035,
'YYYY-MM-DD<TAB>name name ...' (- for none): the items whose date rule holds, as scene.special_on gives them.

For the surprises (tools/scene_surprises.py): surprise_<name>, a frame at a moment each one shows
(scene.special_moment), and one while it fades in for those that fade; surprise_windows.txt (timetables),
surprise_days.txt (day lotteries) and meteors.txt (the shooting star by the millisecond).
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scene  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / 'art' / 'reference'
FRAMES = Path(__file__).resolve().parent.parent / 'out' / 'reference_frames'
D = datetime(2026, 11, 9)
ZONE = 'America/Los_Angeles'
SHOTS = [('dawn', D.replace(hour=6, minute=52), 'clear'), ('day', D.replace(hour=13), 'clear'),
         ('dusk', D.replace(hour=17), 'clear'), ('night', D.replace(hour=23), 'clear'),
         ('cloudy', D.replace(hour=14), 'cloudy'), ('rain', D.replace(hour=8, minute=23), 'rain')]
BIG_TICK = 14_000_000_020


def four_lines():
    """The first hour of the first pass (n hours from 1 January of the epoch year) whose quote wraps to four lines."""
    epoch, n = scene.scene()['text']['quote_epoch_year'], len(scene.quotes())
    width = scene.scene()['text']['quote_chars']
    for k in range(n):
        t = datetime(epoch, 1, 1) + timedelta(hours=k)
        if len(scene.wrap(scene.quote_of(t), width)) == 4:
            return t
    raise SystemExit(f'no quote of art/quotes.txt wraps to four lines at width {width}: add one (the export draws '
                     f'the case quote_four_lines at an hour that shows it)')


def quote_spans():
    """(first hour, number of hours) for quotes_wrapped.txt: the last day before the epoch, the first three passes from
    1 January of the epoch year (3 n hours), and 28 February to 1 March 2028 (a leap day)."""
    epoch, n = scene.scene()['text']['quote_epoch_year'], len(scene.quotes())
    return [(datetime(epoch - 1, 12, 31), 24), (datetime(epoch, 1, 1), 3 * n), (datetime(2028, 2, 28), 72)]


def drawn(name, time, weather, tick, state=None, pose='stand'):
    if pose == 'stand' and pose not in pose_names():
        pose = None                     # art/dog.png is missing: there is no dog to draw
    return dict(file=name, via='render', time=time, weather=weather, frame_number=tick, state=state, pose=pose)


def now(name, time):
    return dict(file=name, via='render_now', time=time, epoch_ms=int(time.replace(tzinfo=ZoneInfo(ZONE)).timestamp() * 1000))


def light_changes():
    """(state before, state after, the moment the change of light begins) for each of D's four in clear weather; the
    build stops when scene.state_fade does not say the same of that change's first and last tick."""
    span, steps = scene.scene()['fade']['light']['minutes'], scene.scene()['fade']['light']['steps']
    out = []
    for m in range(1, 1440):
        t = D.replace(hour=m // 60, minute=m % 60)
        before, after = scene.choose_state(t - timedelta(minutes=1), 'clear'), scene.choose_state(t, 'clear')
        if before != after:
            start = t - timedelta(minutes=span) if after in ('dawn', 'dusk') else t
            end = start + timedelta(minutes=span)
            got = [scene.state_fade(x, 'clear') for x in (start - timedelta(milliseconds=1), start, end - timedelta(milliseconds=1), end)]
            want = [None, (before, after, 0, steps), (before, after, steps - 1, steps), None]
            if got != want:
                raise SystemExit(f'the change of light {before} to {after} from {start:%H:%M}: state_fade gives {got}, not {want}')
            out.append((before, after, start))
    if len(out) != 4:
        raise SystemExit(f'{len(out)} changes of light on {D:%Y-%m-%d}, not 4')
    return out


def cases():
    for s, t, w in SHOTS:       # a shot's name is the state its time gives: at 18:00 the 'dusk' shot was a second night
        if scene.choose_state(t, w) != s or scene.state_fade(t, w):
            raise SystemExit(f'SHOTS: {t:%H:%M} in {w} weather draws {scene.choose_state(t, w)}, not {s}')
    out = [drawn(f'state_{s}', t, w, 20) for s, t, w in SHOTS]
    out += [drawn(f'state_{s}_big_tick', t, w, BIG_TICK, s) for s, t, w in SHOTS]
    if scene.house_pose():              # the dog in the doghouse's doorway, in every state
        out += [drawn(f'house_door_{s}', t, w, 20, pose=scene.house_pose()['name']) for s, t, w in SHOTS]
    out += [drawn(f'waves_tick{t:03d}', D.replace(hour=13), 'clear', t) for t in range(0, 32, 4)]
    for name, t in alone_ticks('stand'):
        out.append(drawn(f'dog_{name}_alone_tick{t}', D.replace(hour=13), 'clear', t))
    out += [drawn(f'beam_tick{t:02d}', D.replace(hour=23), 'clear', t) for t in (0, 3, 4, 8, 13, 61)]
    out += [drawn(f'rain_tick{t}', D.replace(hour=8, minute=23), 'rain', t) for t in (40, 41)]
    out += [drawn(f'twinkle_tick{t}', D.replace(hour=23), 'clear', t) for t in (9, 21, 33, 14_000_000_011)]   # stars mid-fade
    for before, after, start in light_changes():     # each change of light of the day, early, half way and at its end
        out += [drawn(f'light_{before}_{after}_{k}s', start + timedelta(seconds=k), 'clear', 1000 + 8 * k) for k in (2, 150, 299)]
    out += [drawn('fade_clear_rain_step12', D.replace(hour=13), ('clear', 'rain', 12), 1024)]
    full_moon = datetime(2026, 11, 24, 23, 0)
    out += [drawn(f'moon_full_{w}', full_moon, w, 20) for w in ('clear', 'rain', 'cloudy')]
    out += [drawn('leap_day_noon', datetime(2028, 2, 29, 12, 0), 'clear', 20),
            drawn('quote_four_lines', four_lines(), 'clear', 20)]
    out += [drawn(f'clock_{h:02d}{m:02d}', D.replace(hour=h, minute=m), 'clear', tick)
            for h, m, tick in ((0, 5, 20), (12, 30, 3), (10, 10, 20), (23, 59, 3))]
    out += [now('now_new_year', datetime(2027, 1, 1, 0, 0, 3))]
    out += [now(name, t) for name, t in now_cases()]
    for pose in pose_names():
        still = next(t for t in range(20, 20000) if all(scene.move_frame(m, t) is None for m in moves_of(pose)))
        out += [drawn(f'pose_{pose}_{s}', t, w, still, pose=pose) for s, t, w in SHOTS]
        out += [drawn(f'pose_{pose}_{name}_alone_tick{t}', D.replace(hour=13), 'clear', t, pose=pose)
                for name, t in alone_ticks(pose)]
    if len(pose_names()) > 1:
        out += [drawn(f'pose_fade_step{scene.pose_at(t)[2]}', D.replace(hour=13), 'clear', t, pose=None)
                for t in fade_ticks()]
    out += [now(f'month_{m:02d}_noon', datetime(2026, m, 15, 12, 30)) for m in range(1, 13)]
    out += [drawn(f'mix_{m:02d}{d:02d}', datetime(2026, m, d, 13, 0), 'clear', 20, 'day')
            for m, d in ((1, 25), (4, 30), (7, 26), (10, 27), (12, 31))]
    out += [drawn(f'special_{name}', datetime(2026, m, d, hour, minute), 'clear', tick)
            for name, m, d, hour, minute, tick in SPECIAL_SHOTS]
    sp = scene.scene()['specials']
    dated = [i for i in sp['items'] if i['slot'].startswith('specials')]        # the holidays, December, the plants
    for _, m, d, hour, _, _ in SPECIAL_SHOTS:
        t = datetime(2026, m, d, hour)
        state = scene.choose_state(t, 'clear')
        dated = [i for i in dated if not scene.gates_open(i, state, 'clear', t)]
    while dated:                               # what no line of SPECIAL_SHOTS shows gets a frame at a moment it shows
        time, weather, state, tick = scene.special_moment(dated[0])
        out.append(drawn(f'special_{dated[0]["name"]}', time, weather, tick, state))
        dated = [i for i in dated if not scene.gates_open(i, state, weather, time)]
    for item in [i for i in sp['items'] if i['slot'].startswith('surprises')] + sp['tints']:
        time, weather, state, tick = scene.special_moment(item)         # a moment at which the surprise shows
        out.append(drawn(f'surprise_{item["name"]}', time, weather, tick, state))
        if item.get('fade'):                                            # and one while it fades in
            out.append(drawn(f'surprise_{item["name"]}_fading', time, weather, tick - item['every'][2] // 2 + item['fade'] // 3, state))
    return out


# name, month, day, hour, minute, tick. An item of the specials that none of these shows gets a frame of its own (cases)
SPECIAL_SHOTS = [
    ('new_year', 1, 1, 13, 0, 20), ('january', 1, 15, 13, 0, 20), ('mlk', 1, 19, 13, 0, 20),
    ('valentine', 2, 14, 13, 0, 20), ('presidents', 2, 16, 13, 0, 20), ('easter', 4, 5, 13, 0, 20),
    ('memorial', 5, 25, 13, 0, 20), ('juneteenth', 6, 19, 13, 0, 20), ('pride', 6, 28, 13, 0, 20),
    ('july4', 7, 4, 13, 0, 20), ('july4_flag_frame_b', 7, 4, 13, 0, 26), ('july4_night_tick18', 7, 4, 21, 30, 18),
    ('july4_night_tick40', 7, 4, 21, 30, 40), ('july4_night_tick14000000100', 7, 4, 23, 59, 14_000_000_100),
    ('july', 7, 15, 13, 0, 20), ('labor', 9, 7, 13, 0, 20), ('columbus', 10, 12, 13, 0, 20),
    ('halloween', 10, 31, 13, 0, 20), ('halloween_night', 10, 31, 20, 0, 20), ('veterans', 11, 11, 13, 0, 20),
    ('thanksgiving', 11, 26, 13, 0, 20), ('december_dusk', 12, 10, 17, 0, 20), ('christmas', 12, 25, 13, 0, 20),
    ('christmas_night', 12, 25, 21, 0, 20), ('new_year_eve_before_20', 12, 31, 19, 0, 18),
    ('new_year_eve_night', 12, 31, 22, 0, 18),
    # one thing two days before its holiday; the whale's flukes; December's lamps in their second frame
    ('valentine_lead', 2, 12, 13, 0, 20), ('easter_lead', 4, 3, 13, 0, 20), ('labor_lead', 9, 5, 13, 0, 20),
    ('whale_flukes', 1, 15, 13, 0, 84), ('december_19_night_frame_b', 12, 19, 21, 0, 36),
]


def surprise_windows_text():
    """'name<TAB>slot number<TAB>start tick or -' for the first 300 slots of each surprise's timetable and 300 from
    tick 14000000000 on (scene.window_start)."""
    lines = []
    for item in scene.scene()['specials']['items']:
        if item['every']:
            first = 14_000_000_000 // item['every'][0]
            for s in list(range(300)) + list(range(first, first + 300)):
                start = scene.window_start(item['every'], s)
                lines.append(f'{item["name"]}\t{s}\t{"-" if start is None else start}')
    return '\n'.join(lines) + '\n'


def surprise_days_text():
    """'name<TAB>YYYY-MM-DD<TAB>HH<TAB>0 or 1' for every surprise and tint with a day lottery, at 01:00 and 13:00 of
    every day of 2026 and 2027: whether the lottery lets it show (scene.day_key and the hash)."""
    sp = scene.scene()['specials']
    lines = []
    for item in sp['items'] + sp['tints']:
        days = item.get('days')
        if days:
            day = datetime(2026, 1, 1)
            while day.year <= 2027:
                for hour in (1, 13):
                    hit = scene.beach_hash(scene.day_key(days, day.replace(hour=hour)), 0, days[1]) % days[0] == 0
                    lines.append(f'{item["name"]}\t{day:%Y-%m-%d}\t{hour:02d}\t{int(hit)}')
                day += timedelta(days=1)
    return '\n'.join(lines) + '\n'


def meteors_text():
    """'millisecond<TAB>one_in<TAB>x,y,level x,y,level ...' (- for none): the shooting star of the first four slots
    that have one from 2026-11-11 06:00 UTC on, with the usual odds and with a shower's, every 23 ms from 23 ms
    before its start to 46 ms after its end (scene.meteor_pixels)."""
    m = scene.scene()['specials']['meteors']
    lines = []
    for one_in in (m['one_in'], min(sh[4] for sh in m['showers'])):
        s, found = 1_794_376_800_000 // m['slot_ms'], 0
        while found < 4:
            if scene.beach_hash(s, 1, m['salt']) % one_in == 0:
                found += 1
                start = s * m['slot_ms'] + scene.beach_hash(s, 2, m['salt']) % (m['slot_ms'] - m['life_ms'] + 1)
                for ms in range(start - 23, start + m['life_ms'] + 47, 23):
                    px = scene.meteor_pixels(m, ms, one_in)
                    lines.append(f'{ms}\t{one_in}\t' + (' '.join(f'{x},{y},{level}' for x, y, level in px) or '-'))
            s += 1
    return '\n'.join(lines) + '\n'


def specials_days_text():
    """One line for every day of 2026 to 2035: the specials whose date rule holds."""
    items = scene.scene()['specials']['items']
    lines, day = [], datetime(2026, 1, 1)
    while day.year <= 2035:
        names = [i['name'] for i in items if i['when'] is not None and scene.special_on(i['when'], day.year, day.month, day.day)]
        lines.append(f'{day:%Y-%m-%d}\t{" ".join(names) or "-"}')
        day += timedelta(days=1)
    return '\n'.join(lines) + '\n'


DAY_TIMES = [(0, 30), (1, 30), (2, 30), (4, 20), (5, 0), (5, 40), (6, 20), (7, 0), (7, 40), (8, 20), (9, 30), (10, 40),
             (11, 50), (13, 0), (15, 50), (16, 30), (17, 10), (17, 50), (18, 30), (19, 10), (19, 50), (20, 30), (21, 10),
             (22, 0)]


def day_states_text():
    """One line for each of DAY_TIMES of every day of 2026 and of February and March 2028."""
    days = [datetime(2026, 1, 1) + timedelta(days=k) for k in range(365)]
    days += [datetime(2028, 2, 1) + timedelta(days=k) for k in range(60)]
    lines = []
    for day in days:
        for hour, minute in DAY_TIMES:
            t = day.replace(hour=hour, minute=minute)
            w = scene.weather_name(t)
            lines.append(f'{t:%Y-%m-%d %H:%M}\t{w}\t{scene.choose_state(t, w)}')
    return '\n'.join(lines) + '\n'


def evening_text():
    """'YYYY-MM-DD HH:MM:SS<TAB>D<TAB>red green blue' (scene.evening_factors) for every tenth minute of six days of 2026,
    37 seconds in, settled (D '-') and D milliseconds after the screensaver started: before, inside and after the fade."""
    lines = []
    for month, day in ((1, 15), (3, 8), (6, 21), (9, 30), (11, 1), (12, 25)):
        for minute in range(0, 1440, 10):
            t = datetime(2026, month, day, minute // 60, minute % 60, 37)
            for dreaming in (None, 0, 299_999, 400_000, 777_777, 900_000):
                lines.append(f'{t:%Y-%m-%d %H:%M:%S}\t{"-" if dreaming is None else dreaming}\t'
                             + ' '.join(map(str, scene.evening_factors(t, dreaming))))
    # Every edge, to the second: one second before, on and after each point where a ramp starts or ends, on days
    # with the earliest and the latest sunset, both changes of summer time and the days before them; and the hold
    # and the fade, one millisecond before, on and after their ends.
    e = scene.scene()['evening']
    hold, fade = 60_000 * e['hold_minutes'], 60_000 * e['fade_minutes']
    edges_ms = (None, -1, 0, hold - 1, hold, hold + 1, hold + fade // 2, hold + fade - 1, hold + fade, hold + fade + 1)
    for month, day in ((1, 1), (3, 7), (3, 8), (6, 21), (6, 27), (10, 31), (11, 1), (12, 7), (12, 31)):
        rise, set_ = scene.sun_times(datetime(2026, month, day, 12))
        points = (60 * (rise - e['dawn_ramp']), 60 * rise, 60 * set_, 60 * (set_ + e['warm_after_sunset']),
                  60 * e['night_from'], 60 * (e['night_from'] + e['night_ramp']), 0, 86399)
        for point in points:
            for second in (point - 1, point, point + 1):
                if not 0 <= second < 86400:
                    continue
                t = datetime(2026, month, day, second // 3600, second // 60 % 60, second % 60)
                for dreaming in edges_ms:
                    lines.append(f'{t:%Y-%m-%d %H:%M:%S}\t{"-" if dreaming is None else dreaming}\t'
                                 + ' '.join(map(str, scene.evening_factors(t, dreaming))))
    return '\n'.join(lines) + '\n'


def layer_counts_text():
    import numpy as np
    from PIL import Image
    img = np.array(Image.open(scene.ART / 'layers' / 'clouds.png'))
    values, counts = np.unique(img, return_counts=True)
    return f'clouds.png {img.shape[1]} {img.shape[0]}\n' + ''.join(f'{v} {c}\n' for v, c in zip(values.tolist(), counts.tolist()))


def pose_names():
    return [p['name'] for p in scene.scene()['dog']['poses']]


def moves_of(pose):
    return [m for part in scene.poses()[scene.pose_index(pose)]['parts'] for m in part['moves']]


def alone_ticks(pose):
    """(move name, tick) for each move of the pose (all its parts): the first tick where it is active and the pose's
    other moves are not. Moves that share a name and a timetable are one move here (a move whose rect crosses two
    parts is written once for each part, and neither half is ever active without the other). [] for a pose that is
    not in scene.json; the build stops, naming the move, when a move is never alone in 20000 ticks."""
    if pose not in pose_names():
        return []
    moves, out = moves_of(pose), []
    for m in moves:
        if any(o['name'] == m['name'] and o['timetable'] == m['timetable'] for o in moves[:moves.index(m)]):
            continue
        others = [o for o in moves if (o['name'], o['timetable']) != (m['name'], m['timetable'])]
        tick = next((t for t in range(20000) if scene.move_frame(m, t) is not None and
                     all(scene.move_frame(o, t) is None for o in others)), None)
        if tick is None:
            raise SystemExit(f'pose {pose}: the move {m["name"]!r} is never active alone in 20000 ticks')
        out.append((m['name'], tick))
    return out


def fade_ticks():
    """Three ticks of the pose change in slot 1: its second tick, its middle and its last."""
    start, n = scene.change_start(1), scene.scene()['dog']['pose_change']['fade_ticks']
    return [start + 1, start + n // 2, start + n - 1]


def schedule_text():
    p = scene.scene()['dog']['pose_change']
    names = pose_names()
    lines = ['poses ' + ' '.join(names)]
    first = 14_000_000_000 // p['hold']
    for s in list(range(10)) + list(range(first, first + 200)):
        start = scene.change_start(s)
        for t in (start - 1, start, start + p['fade_ticks'] - 1, start + p['fade_ticks']):
            old, new, step = scene.pose_at(t)
            lines.append('\t'.join([str(t), '-' if old is None else names[old], names[new],
                                    '-' if step is None else str(step)]))
    return '\n'.join(lines) + '\n'


PLACE_DAYS = [(2026, 3, 8), (2026, 6, 21), (2026, 11, 9), (2026, 12, 31)]     # and the first day of D's month with a shower


def places_text():
    """dog_places.txt, or None when the dog never goes into the doghouse: 'places <the doorway pose's name>', then
    epoch milliseconds, old, new, step (pose names, - for none) from scene.chosen_poses with the time, as the
    television draws: for every pose slot of five days (a day the clocks change, midsummer, D, a day with a shower,
    New Year's Eve) at the slot's first tick, and at the tick before its change, the change's first, its middle and
    the tick after its last. Every other line is taken 124 ms into its tick."""
    door = scene.house_pose()
    if door is None:
        return None
    p, tps = scene.scene()['dog']['pose_change'], scene.scene()['ticks_per_second']
    wet = next(D.replace(day=d) for d in range(1, 31) if scene.day_weather(D.replace(day=d)) == 'rain')
    lines, zone = [f'places {door["name"]}'], ZoneInfo(ZONE)
    for y, mo, d in PLACE_DAYS + [(wet.year, wet.month, wet.day)]:
        first = scene.tick_at(int(datetime(y, mo, d, tzinfo=zone).timestamp() * 1000)) // p['hold']
        for s in range(first, first + 86400 * tps // p['hold']):
            start = scene.change_start(s)
            for t in (s * p['hold'], start - 1, start, start + p['fade_ticks'] // 2, start + p['fade_ticks']):
                ms = t * 1000 // tps + (124 if len(lines) % 2 else 0)
                when = datetime.fromtimestamp(ms / 1000, zone).replace(tzinfo=None)
                old, new, step = scene.chosen_poses(None, scene.tick_at(ms), when)
                lines.append('\t'.join([str(ms), '-' if old is None else old['name'], new['name'],
                                        '-' if step is None else str(step)]))
    return '\n'.join(lines) + '\n'


def now_cases():
    """(file name, local time) for frames drawn the way the television draws them, from the clock alone: a clear
    afternoon, a shower in progress, a night, and the first minute of a shower 3 seconds in (a weather fade)."""
    day = next(D.replace(day=d, hour=13) for d in range(1, 31) if scene.day_weather(D.replace(day=d)) == 'clear')
    wet = next(D.replace(day=d) for d in range(1, 31) if scene.day_weather(D.replace(day=d)) == 'rain'
               and 480 <= scene.shower(D.replace(day=d))[0] <= 900)
    start = scene.shower(wet)[0]
    begins = wet.replace(hour=start // 60, minute=start % 60)
    return [('now_clear_day', day), ('now_shower', begins + timedelta(minutes=30)), ('now_night', D.replace(hour=23)),
            ('now_shower_fade_in', begins + timedelta(seconds=3))]


def quotes_text():
    width = scene.scene()['text']['quote_chars']
    hours = {}                          # quote_hour -> (time, quote)
    for first, count in quote_spans():
        for k in range(count):
            t = first + timedelta(hours=k)
            hours[scene.quote_hour(t)] = (t, scene.quote_of(t))
    check_quotes(hours)
    four_lines()
    lines = [f'width {width}']
    for h in sorted(hours):
        t, quote = hours[h]
        if '|' in quote:
            raise SystemExit(f'a quote holds the separator |: {quote}')
        lines.append(f'{t:%Y-%m-%d %H}\t' + '|'.join(scene.wrap(quote, width)))
    return '\n'.join(lines) + '\n'


def check_quotes(hours):
    """Stops, naming the hours, if a quote shows twice in one pass (n hours without a repeat are every quote once) or
    if two neighbouring hours show the same quote. hours: quote_hour -> (time, quote)."""
    n = len(scene.quotes())
    passes = {}
    for h, (t, quote) in sorted(hours.items()):
        seen = passes.setdefault(h // n, {})
        if quote in seen:
            raise SystemExit(f'the same quote twice in pass {h // n}: {seen[quote]:%Y-%m-%d %H}:00 and {t:%Y-%m-%d %H}:00: '
                             f'{quote}')
        seen[quote] = t
        if h - 1 in hours and hours[h - 1][1] == quote:
            raise SystemExit(f'the same quote two hours in a row: {hours[h - 1][0]:%Y-%m-%d %H}:00 and '
                             f'{t:%Y-%m-%d %H}:00: {quote}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FRAMES.mkdir(parents=True, exist_ok=True)
    (OUT / 'quotes_wrapped.txt').write_text(quotes_text(), encoding='utf-8')
    (OUT / 'day_states.txt').write_text(day_states_text())
    (OUT / 'layer_counts.txt').write_text(layer_counts_text())
    (OUT / 'evening.txt').write_text(evening_text())
    (OUT / 'specials_days.txt').write_text(specials_days_text())
    (OUT / 'surprise_windows.txt').write_text(surprise_windows_text())
    (OUT / 'surprise_days.txt').write_text(surprise_days_text())
    (OUT / 'meteors.txt').write_text(meteors_text())
    manifest = []
    for c in cases():
        t = c['time']
        entry = {'file': c['file'] + '.png', 'via': c['via'], 'date': f'{t:%Y-%m-%d}', 'time': f'{t:%H:%M:%S.%f}'}
        if c['via'] == 'render':
            img = scene.render(t, c['weather'], c['frame_number'], c['state'], c['pose'])
            w = c['weather']
            entry.update(weather=list(w) if isinstance(w, tuple) else w, frame_number=c['frame_number'], state=c['state'],
                         pose=c['pose'])
            names = w[:2] if isinstance(w, tuple) else (w,)
        else:
            img = scene.render_now(t, c['epoch_ms'])
            w = scene.weather_at(t)
            entry.update(timezone=ZONE, epoch_ms=c['epoch_ms'], derived_weather=list(w) if isinstance(w, tuple) else w,
                         derived_tick=scene.tick_at(c['epoch_ms']))
            names = w[:2] if isinstance(w, tuple) else (w,)
        entry['drawn_state'] = c.get('state') or [scene.choose_state(t, n) for n in names]
        entry['sha256'] = hashlib.sha256(img.tobytes()).hexdigest()
        img.save(FRAMES / entry['file'])
        manifest.append(entry)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    schedule = OUT / 'pose_schedule.txt'
    if len(pose_names()) > 1:
        schedule.write_text(schedule_text())
    elif schedule.exists():
        schedule.unlink()               # one pose: no schedule, and a file left from more poses would be wrong
    places = places_text()
    if places:
        (OUT / 'dog_places.txt').write_text(places)
    elif (OUT / 'dog_places.txt').exists():
        (OUT / 'dog_places.txt').unlink()
    listed = {e['file'] for e in manifest}
    stale = sorted(p.name for p in FRAMES.glob('*.png') if p.is_file() and p.name not in listed)
    for name in stale:                  # frames of a case that is gone (a pose left, a move was renamed or retimed)
        (FRAMES / name).unlink()
    if stale:
        print(f'deleted {len(stale)} reference frames the manifest no longer lists: {" ".join(stale)}')
    print(f'wrote {len(manifest)} frames to {FRAMES}, manifest.json and quotes_wrapped.txt to {OUT}; poses: '
          f'{" ".join(pose_names()) or "none"}{", pose_schedule.txt" if len(pose_names()) > 1 else ""}')
    if 'stand' not in pose_names():
        print('art/dog.png is missing: no dog frames; run this again once it exists')


if __name__ == '__main__':
    main()
