"""One frame of the beach, from the files in art/.

    from scene import render
    image = render(datetime(2026, 11, 9, 13, 0), 'clear', 20)

render loads the layers and palettes (once), picks the lighting state, stacks the layers into one 480x270 array of
palette indexes and looks the indexes up in the palette of that state and of the date's month. Animation is whole
frames of a strip, whole-pixel moves, and roles hidden or recoloured for a tick. The only colour arithmetic is the
whole-frame fade between two finished frames (a change of pose, of state, of weather) and, on the last days of a
month, the mix of that month's palette with the next month's (month_mix). Every choice is integer arithmetic on the
date, the time, the weather and the tick. The dog shows one of several poses (scene.json dog.poses); pose_at picks it from the tick.

Integer division here is Python's floor division; the Java port must use Math.floorDiv and Math.floorMod wherever a
value can be negative (the dog's shadow, the dog's moves at a negative tick, and pose_at's slots and blocks, which
reach -1 and -2 near tick 0).

Java types: the tick is a long (tick_at gives about 1.4e10, past int). Everything divided from it (tick // 6 and the
like) stays a long until it is reduced by a modulus. A slot number handed to beach_hash may pass 2^31 (the twinkle's
tick // 6 does); Beach.hash takes ints, and its result depends only on the low 32 bits of each input, so the Java
port passes (int) slot and gets the same answer as this code, which masks every product to 32 bits.

Comments here and in scene_build.py name methods of the add-on's first version, which drew the scene in Java
(Beach.hash, PixelFont.wrap, Hud.draw). That code is gone; the names record where a
formula came from.
"""
import json
from datetime import datetime, timedelta
from functools import cache
from pathlib import Path

import numpy as np
from PIL import Image

ART = Path(__file__).resolve().parent.parent / 'art'
W, H = 480, 270
DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
M32, M64 = 2 ** 32 - 1, 2 ** 64 - 1


def beach_hash(x, y, seed):
    """Beach.hash, on non-negative ints, or elementwise on numpy arrays of them."""
    arrays = any(isinstance(v, np.ndarray) for v in (x, y, seed))
    if arrays:
        x, y, seed = (np.asarray(v).astype(np.uint64) for v in (x, y, seed))
    h = (x * 0x27D4EB2D + y * 0x165667B1 + (seed * 0x9E3779B9 & M32)) & M32
    h ^= h >> 15
    h = (h * 0x85EBCA6B) & M32
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & M32
    h = (h ^ (h >> 16)) & 0x7FFFFFFF
    return h.astype(np.int64) if arrays else h


# ------------------------------------------------------------------------------------------- files

@cache
def scene():
    return json.loads((ART / 'scene.json').read_text())


@cache
def layer(name):
    return np.array(Image.open(ART / 'layers' / name))


@cache
def month_palette(state, month):
    """One month's colours in a state (art/palettes/<mm>/<state>.json) as a 256 x 3 array, and which indexes it shows
    (not 0, not null)."""
    rgb = np.zeros((256, 3), np.uint8)
    shown = np.zeros(256, bool)
    for i, e in enumerate(json.loads((ART / 'palettes' / f'{month:02d}' / f'{state}.json').read_text())['colors']):
        if i > 0 and e['hex'] is not None:
            c = int(e['hex'], 16)
            rgb[i] = (c >> 16, (c >> 8) & 255, c & 255)
            shown[i] = True
    return rgb, shown


def days_in_month(year, month):
    if month == 2:
        return 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
    return 30 if month in (4, 6, 9, 11) else 31


def month_mix(year, month, day):
    """(month, next month, k, n): the date's palette is the month's, mixed k parts in n with the next month's. A month
    keeps its own palette until its last fade_days days; on those days k rises from 1 to fade_days, with
    n = fade_days + 1, so the first day of the next month is the first with that month's palette alone."""
    fade = scene()['months']['fade_days']
    k = day - (days_in_month(year, month) - fade)
    return month, month % 12 + 1, max(0, k), fade + 1


@cache
def mixed_palette(state, a, b, k, n):
    """The palette of month a mixed k parts in n with month b's: per channel (a * (n - k) + b * k + n // 2) // n. A role
    that only one of the two months shows takes that month's colour, and shows from the middle of the fade
    (2 * k >= n) when it is the later month's, until the middle when it is the earlier month's."""
    rgb_a, shown_a = month_palette(state, a)
    if k == 0:
        return rgb_a, shown_a
    rgb_b, shown_b = month_palette(state, b)
    rgb = ((rgb_a.astype(np.int32) * (n - k) + rgb_b.astype(np.int32) * k + n // 2) // n).astype(np.uint8)
    late = 2 * k >= n
    rgb[shown_a & ~shown_b] = rgb_a[shown_a & ~shown_b]
    rgb[shown_b & ~shown_a] = rgb_b[shown_b & ~shown_a]
    shown = (shown_a & shown_b) | (shown_b if late else shown_a)
    return rgb, shown


def palette(state, time):
    """The colours of a state on the date of time, and which indexes they show."""
    return mixed_palette(state, *month_mix(time.year, time.month, time.day))


@cache
def role(name):
    names = [e['name'] for e in json.loads((ART / 'palettes' / 'day.json').read_text())['colors']]
    return names.index(name)


# ------------------------------------------------------------------------------------------- the day (Day.java)

def between_months(table, year, month, day):
    """The date's value from a table of twelve, one for the 15th of each month: from one 15th to the next the value
    changes by the same amount every day (rounded to a whole number)."""
    if day >= 15:
        a, b, n, k = month, month % 12 + 1, days_in_month(year, month), day - 15
    else:
        a = (month + 10) % 12 + 1
        n = days_in_month(year if month > 1 else year - 1, a)
        b, k = month, n - (15 - day)
    return (table[a - 1] * (n - k) + table[b - 1] * k + n // 2) // n


def us_summer_time(time):
    """True while the clocks of the United States are an hour ahead: from 03:00 on the second Sunday of March until
    01:00 on the first Sunday of November, read on the wall clock that time holds."""
    if time.month != 3 and time.month != 11:
        return 3 < time.month < 11
    first_sunday = 1 + (7 - (julian_day(time.year, time.month, 1) + 1) % 7) % 7     # (jd + 1) % 7 is 0 on a Sunday
    if time.month == 3:
        return time.day > first_sunday + 7 or (time.day == first_sunday + 7 and time.hour >= 3)
    return time.day < first_sunday or (time.day == first_sunday and time.hour < 1)


def sun_times(time):
    """(sunrise, sunset) of the date in minutes of the wall clock: the tables hold standard time on the 15th of each
    month, and an hour is added while summer time is on (day_parts.summer_time names the rule, or is null)."""
    parts = scene()['day_parts']
    ahead = 60 if parts['summer_time'] == 'us' and us_summer_time(time) else 0
    return (between_months(parts['sunrise'], time.year, time.month, time.day) + ahead,
            between_months(parts['sunset'], time.year, time.month, time.day) + ahead)


def settled_brightness(time):
    """The picture's brightness in thousandths once the screensaver has run for evening.fade_minutes: evening.day from
    sunrise to sunset; from sunset down to evening.evening over warm_after_sunset minutes; from night_from (a minute of
    the clock) down to evening.night over night_ramp minutes, held through the night; back up to evening.day over the
    dawn_ramp minutes before sunrise. To the second, so that a ramp has no steps."""
    e = scene()['evening']
    s = time.hour * 3600 + time.minute * 60 + time.second
    rise, set_ = (60 * m for m in sun_times(time))
    day, evening, night = 10 * e['day'], 10 * e['evening'], 10 * e['night']
    dawn, after = 60 * e['dawn_ramp'], 60 * e['warm_after_sunset']
    if s < rise - dawn:
        b = night
    elif s < rise:
        b = night + (day - night) * (s - (rise - dawn)) // dawn
    elif s < set_:
        b = day
    elif s < set_ + after:
        b = day + (evening - day) * (s - set_) // after
    else:
        b = evening
    if s >= 60 * e['night_from']:
        ramp = 60 * e['night_ramp']
        b = b + (night - b) * min(s - 60 * e['night_from'], ramp) // ramp
    return b


def brightness(time, dreaming_ms=None):
    """The picture's brightness in thousandths: full when the screensaver starts (or a key is pressed in the tile) and
    for evening.hold_minutes after, then down to settled_brightness over evening.fade_minutes. dreaming_ms: how long
    it has run; None for settled."""
    b = settled_brightness(time)
    if dreaming_ms is None:
        return b
    e = scene()['evening']
    fade = 60_000 * e['fade_minutes']
    return 1000 - (1000 - b) * min(max(dreaming_ms - 60_000 * e['hold_minutes'], 0), fade) // fade


def evening_factors(time, dreaming_ms=None):
    """(red, green, blue) in thousandths: how the television shows the finished frame at this moment. The brightness
    (brightness) times the warmth: after sunset green and blue fall to warm_green and warm_blue percent over
    warm_after_sunset minutes, stay through the night, and come back over the dawn_ramp minutes before sunrise.
    dreaming_ms as for brightness. render does not apply this: on_screen does."""
    e = scene()['evening']
    m = time.hour * 60 + time.minute
    rise, set_ = sun_times(time)
    warm = 0
    if m < rise - e['dawn_ramp']:
        warm = 1000
    elif m < rise:
        warm = 1000 - 1000 * (m - (rise - e['dawn_ramp'])) // e['dawn_ramp']
    elif m >= set_ + e['warm_after_sunset']:
        warm = 1000
    elif m >= set_:
        warm = 1000 * (m - set_) // e['warm_after_sunset']
    b = brightness(time, dreaming_ms)
    return (b, b * (1000 - (100 - e['warm_green']) * warm // 100) // 1000,
            b * (1000 - (100 - e['warm_blue']) * warm // 100) // 1000)


def on_screen(rgb, time, dreaming_ms=None):
    """An H x W x 3 frame as the television shows it at this moment: each channel (c * factor + 500) // 1000.
    dreaming_ms as for brightness; None: as it shows once settled."""
    f = np.array(evening_factors(time, dreaming_ms), np.int32)
    return ((np.asarray(rgb).astype(np.int32) * f + 500) // 1000).astype(np.uint8)


def choose_state(time, weather):
    """Night while it is dark; otherwise rain or cloudy by the weather; otherwise dawn, dusk or day by the clock."""
    parts = scene()['day_parts']
    minute = time.hour * 60 + time.minute
    rise, set_ = sun_times(time)
    if minute < rise + parts['dawn'][0] or minute >= set_ + parts['dusk'][1]:
        return 'night'
    if weather != 'clear':
        return weather
    if minute < rise + parts['dawn'][1]:
        return 'dawn'
    if minute >= set_ + parts['dusk'][0]:
        return 'dusk'
    return 'day'


def julian_day(year, month, day):
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def easter(year):
    """(month, day) of Easter Sunday of the western churches in a year of the Gregorian calendar (the Meeus, Jones
    and Butcher rule, in whole numbers)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 19 * m) // 433
    month = (h + m - 7 * n + 90) // 25
    return month, (h + m - 7 * n + 33 * month + 19) % 32


def special_on(when, year, month, day):
    """True on a date that one of the rules of `when` names (tools/scene_specials.py describes the rules). A rule
    with margins is counted in the date's own year: its days do not run over the year's end."""
    jd = julian_day(year, month, day)
    for rule in when:
        if rule[0] == 'range':
            first, last, here = rule[1] * 100 + rule[2], rule[3] * 100 + rule[4], month * 100 + day
            if (first <= here <= last) if first <= last else (here >= first or here <= last):
                return True
            continue
        if rule[0] == 'nth':
            _, m, weekday, n, before, after = rule
            if n > 0:               # julian_day % 7 is 0 on a Monday
                target = julian_day(year, m, 1)
                target += (weekday - target) % 7 + 7 * (n - 1)
            else:
                target = julian_day(year, m, days_in_month(year, m))
                target -= (target - weekday) % 7
        elif rule[0] == 'easter':
            (m, d), before, after = easter(year), rule[1], rule[2]
            target = julian_day(year, m, d)
        else:
            raise ValueError(f'a rule scene.py does not know: {rule}')
        if target - before <= jd <= target + after:
            return True
    return False


BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def day_key(days, time):
    """The number of the day (or block of days) that an item's lottery draws for: days = [one_in, salt, block, noon];
    with noon the day turns at 12:00, so that a night is one day."""
    return (julian_day(time.year, time.month, time.day) - (1 if days[3] and time.hour < 12 else 0)) // days[2]


def gates_open(item, state, weather, time):
    """True while an item's (or a tint's) states, weather, hours, date rules and day lottery all let it show."""
    days = item.get('days')
    return not ((item['states'] and state not in item['states']) or (item.get('clear') and weather != 'clear')
                or (item.get('hours') and not item['hours'][0] <= time.hour < item['hours'][1])
                or (item['when'] is not None and not special_on(item['when'], time.year, time.month, time.day))
                or (days and beach_hash(day_key(days, time), 0, days[1]) % days[0]))


def window_start(every, s):
    """The tick at which slot s of a timetable [slot, one_in, length, salt] shows its item, or None for a slot
    that shows nothing."""
    slot, one_in, length, salt = every
    if beach_hash(s, 1, salt) % one_in:
        return None
    return s * slot + beach_hash(s, 2, salt) % (slot - length + 1)


def special_piece(item, sheet, state, weather, time, tick):
    """(image, x, y) of an item of scene.json's specials at this moment, or None while it does not show
    (tools/scene_specials.py and scene_surprises.py describe the fields)."""
    if not gates_open(item, state, weather, time):
        return None
    t, key = tick, day_key(item['days'], time) if item['days'] else 0
    if item['every']:
        key = tick // item['every'][0]
        start = window_start(item['every'], key)
        if start is None or not 0 <= tick - start < item['every'][2]:
            return None
        t = tick - start
    x, y, w, h = item['sheet']
    k = (t + item['ahead']) // item['ticks_per_frame']
    k = min(k, item['frames'] - 1) if item['once'] else k % item['frames']
    img = sheet[y:y + h, x + k * w:x + (k + 1) * w]
    ax, ay = item['at']
    if item['jitter']:
        jx, jy, salt = item['jitter']
        ax, ay = ax + beach_hash(key, 3, salt) % (jx + 1), ay + beach_hash(key, 4, salt) % (jy + 1)
    if item['move']:
        dx, px, dy, py = item['move']
        ax, ay = ax + t * dx // px, ay + t * dy // py
    if item['fade']:                         # through a dither: 16 levels, by the pixel's place on the screen
        level = min(16, 16 * (t + 1) // item['fade'], 16 * (item['every'][2] - t) // item['fade'])
        yy, xx = np.mgrid[ay:ay + h, ax:ax + w]
        img = np.where(BAYER[yy & 3, xx & 3] < level, img, 0).astype(np.uint8)
    return img, ax, ay


STATE_HOUR = {'day': 13, 'cloudy': 14, 'dusk': 18, 'night': 22, 'dawn': 6, 'rain': 9}


def special_moment(item, year=2026):
    """A moment at which an item shows, for the reference frames and the review sheets: (time, weather, state,
    tick). The first of its states in the order of STATE_HOUR, at that state's hour (or the first of its hours); the
    first date of the year that its rules and its lottery allow; the middle of its timetable's first window."""
    state = next(s for s in STATE_HOUR if not item['states'] or s in item['states'])
    hours = item.get('hours')
    hour = STATE_HOUR[state] if not hours or hours[0] <= STATE_HOUR[state] < hours[1] else hours[0]
    weather = state if state in ('cloudy', 'rain') else 'clear'
    time = datetime(year, 1, 1, hour)
    while not gates_open(item, state, weather, time):
        time += timedelta(days=1)
        if time.year > year + 3:
            raise ValueError(f'{item["name"]} shows on no day of {year} to {year + 3}')
    if not item.get('every'):
        return time, weather, state, 20
    s = next(s for s in range(100000) if window_start(item['every'], s) is not None)
    return time, weather, state, window_start(item['every'], s) + item['every'][2] // 2


def meteor(time, epoch_ms, state, weather):
    """The shooting star at this millisecond: [(x, y, level)] with level 0 for its head, 1 for the three pixels
    behind it and 2 for the rest of its tail (specials.meteors.levels names their roles); [] while there is none.
    Only on a clear night. The television draws these over the finished frame on every refresh, on sky pixels."""
    m = scene()['specials']['meteors']
    if state != 'night' or weather != 'clear':
        return []
    one_in = m['one_in']
    for m1, d1, m2, d2, n in m['showers']:
        if special_on([['range', m1, d1, m2, d2]], time.year, time.month, time.day):
            one_in = n
    return meteor_pixels(m, epoch_ms, one_in)


def meteor_pixels(m, epoch_ms, one_in):
    slot, life, salt = m['slot_ms'], m['life_ms'], m['salt']
    s = epoch_ms // slot
    if beach_hash(s, 1, salt) % one_in:
        return []
    u = epoch_ms - s * slot - beach_hash(s, 2, salt) % (slot - life + 1)
    if not 0 <= u < life:
        return []
    x0, y0, x1, y1 = m['box']
    hx, hy = x0 + beach_hash(s, 3, salt) % (x1 - x0 + 1), y0 + beach_hash(s, 4, salt) % (y1 - y0 + 1)
    way = 1 if beach_hash(s, 5, salt) % 2 else -1
    speed = m['speed'][0] + beach_hash(s, 6, salt) % (m['speed'][1] - m['speed'][0] + 1)
    slope = m['slope'][0] + beach_hash(s, 7, salt) % (m['slope'][1] - m['slope'][0] + 1)
    gone, left = u * speed // 1000, life - u
    tail = min(gone, m['tail'])
    if left < m['fade_ms']:
        tail = tail * left // m['fade_ms']
    out = []
    for k in range(tail + 1):
        d = gone - k
        x, y = hx + way * d, hy + d * slope // 100
        if 0 <= x < W and 0 <= y < H:
            out.append((x, y, 0 if k == 0 and left >= m['fade_ms'] else 1 if k <= 3 else 2))
    return out


def moon_frame(time):
    """Which of the eight moon sprites tonight is, 0 for new: Day.moonPhase rounded to eighths, in whole numbers."""
    m = scene()['moon']
    since = (julian_day(time.year, time.month, time.day) * 10 ** 9 - m['epoch_jd_e9']) % m['month_e9']
    return (since * 16 + m['month_e9']) // (2 * m['month_e9']) % 8


def mix64(z):
    """Day.mix, on 64 bits (Java long, >>> as the shift)."""
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return z ^ (z >> 31)


def pick(time, question, bound):
    """Day.pick: a number in [0, bound) that depends on the date and the question (Long.remainderUnsigned)."""
    seed = mix64(time.year * 10000 + time.month * 100 + time.day)
    return mix64((seed + question * 0x9E3779B97F4A7C15) & M64) % bound


def day_weather(time):
    """Day.weather: 'clear', 'cloudy' or 'rain' for the date: the first name whose odds number for the month is above
    the day's roll."""
    w = scene()['weather']
    roll = pick(time, w['roll_question'], w['roll_bound'])
    return next(n for n, odds in zip(w['names'], w['odds'][time.month - 1]) if roll < odds)


def gloom_end(time):
    """The minute at which the date's morning cloud clears, or None on a day without it. A clear day has morning cloud
    when pick(date, question, 100) is below the month's number in weather.gloom.odds; it clears at
    until + pick(date, until_question, until_range)."""
    g = scene()['weather']['gloom']
    if pick(time, g['question'], 100) >= g['odds'][time.month - 1]:
        return None
    return g['until'] + pick(time, g['until_question'], g['until_range'])


def shower(time):
    """(start, end) minutes of the date's shower, end cut at midnight (1440). Only rain days use it."""
    s = scene()['weather']['shower']
    start = s['start'] + pick(time, s['start_question'], s['start_range'])
    return start, min(1440, start + s['length'] + pick(time, s['length_question'], s['length_range']))


def weather_name(time):
    """The weather for this minute: a rain day rains during its shower and is cloudy the rest of the day; a clear day
    with morning cloud (gloom_end) is cloudy until that clears."""
    day = day_weather(time)
    if day == 'clear':
        end = gloom_end(time)
        return 'cloudy' if end is not None and time.hour * 60 + time.minute < end else 'clear'
    if day != 'rain':
        return day
    start, end = shower(time)
    return 'rain' if start <= time.hour * 60 + time.minute < end else 'cloudy'


def weather_at(time):
    """The weather name, or (old, new, step) during the first fade of a minute whose weather differs from the minute
    before (the minute before 00:00 is 23:59 of the day before); the step comes from the seconds, as the state fade's."""
    now, before = weather_name(time), weather_name(time - timedelta(minutes=1))
    f = scene()['fade']
    ticks = (time.second * 1_000_000 + time.microsecond) * scene()['ticks_per_second'] // 1_000_000
    if now == before or ticks >= f['ticks']:
        return now
    return before, now, ticks * f['steps'] // f['ticks']


def tick_at(epoch_ms):
    """The tick from the system clock, milliseconds since 1970 UTC (Java long): it never jumps at midnight or when the
    clocks change."""
    return epoch_ms * scene()['ticks_per_second'] // 1000


# ------------------------------------------------------------------------------------------- the words (quotes, PixelFont)

@cache
def quotes():
    """The quotes, one per non-empty line of quotes.txt, surrounding spaces removed."""
    text = (ART / scene()['text']['quotes']).read_text(encoding='utf-8')
    return [q.strip() for q in text.splitlines() if q.strip()]


def quote_hour(time):
    """The hour the quote belongs to: whole days from 1 January of quote_epoch_year to the date (every calendar day
    counts, 29 February too), times 24, plus the hour of the local wall clock. Negative before the epoch."""
    epoch = time.replace(year=scene()['text']['quote_epoch_year'], month=1, day=1)
    return (time.toordinal() - epoch.toordinal()) * 24 + time.hour


@cache
def pass_order(p, n, salt):
    """Pass p's order of the n quotes (n >= 3): shuffled(p) (the same shuffle as the poses', with the quote salt), with
    its first two places swapped when its first quote is the last of pass p - 1, so no quote shows two hours in a row.
    With n >= 3 the swap never moves a pass's last place, so the rule holds from pass to pass."""
    order = shuffled(p, n, salt)
    if order[0] == shuffled(p - 1, n, salt)[n - 1]:
        order[0], order[1] = order[1], order[0]
    return tuple(order)


def quote_of(time):
    """The quote for the date and hour (minutes do not matter). A pass is n hours, in which every quote shows once for
    an hour; each pass has its own order (pass_order). H = quote_hour(time); the quote is pass_order(H div n)[H mod n]
    (floor division, so dates before the epoch work too). With two quotes they alternate, H mod 2; with one, it shows."""
    q = quotes()
    n = len(q)
    if n == 1:
        return q[0]
    h = quote_hour(time)
    if n == 2:
        return q[h % 2]
    return q[pass_order(h // n, n, scene()['text']['quote_salt'])[h % n]]


def wrap(text, width):
    """Lines of at most width characters, broken at spaces, and balanced: the text is filled at the narrowest width
    that still gives the same number of lines, so the last line is not left holding one short word.
    (Filled at 24: "Tidy the house tonight / for whoever wakes up in / it."; balanced: "Tidy the house /
    tonight for whoever / wakes up in it.") A word longer than width is cut, and then the lines stay as filled."""
    lines = fill(text, width)
    longest = max((len(word) for word in text.split()), default=0)
    for narrow in range(max(1, min(longest, width)), width):
        fewer = fill(text, narrow)
        if len(fewer) == len(lines):
            return fewer
    return lines


def fill(text, width):
    """PixelFont.wrap: each line takes as many words as fit in width characters; a longer word is cut."""
    lines, line = [], ''
    for word in text.split():
        while len(word) > width:
            if line:
                lines.append(line)
                line = ''
            lines.append(word[:width])
            word = word[width:]
        if not word:
            continue
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = ''
        line = f'{line} {word}' if line else word
    if line:
        lines.append(line)
    return lines


def text_pieces(hour, minute, date, quote):
    """Hud.draw's layout: the clock, AM or PM and the date on the left; on the right the quote, its first line at the
    top margin and each further line one font line and one pixel lower, right-aligned.
    The clock's colon is always lit: it does not blink.
    Each glyph is placed twice: first its whole cell as edge, then its ink, so no edge covers the ink of a neighbour."""
    t = scene()['text']
    font, digits = layer(t['font']), layer(t['digits'])
    cw, ch = t['cell']
    cells = []

    def figure(d, x, y):
        cx, cy, w, h = t['digit_cells'][d]
        cells.append((digits[cy:cy + h, cx:cx + w], x - 1, y - 1))
        return x + (6 if d in '1:' else 14)

    def words(s, x, y):
        for k, c in enumerate(s):
            i = t['chars'].find(c.upper())
            if i >= 0:
                cells.append((font[:, i * cw:(i + 1) * cw], x + k * t['advance'] - 1, y - 1))

    def width(s):
        return len(s) * t['advance'] - 1 if s else 0

    x, y = t['margin_x'], t['margin_y']
    h12 = hour % 12 or 12
    if h12 >= 10:
        x = figure('1', x, y)
    x = figure(str(h12 % 10), x, y)
    figure(':', x, y)
    x += 6
    x = figure(str(minute // 10), x, y)
    x = figure(str(minute % 10), x, y)
    words('AM' if hour < 12 else 'PM', x + 1, y + 12)
    words(date, t['margin_x'], y + 26)
    right = W - t['margin_x']
    for k, line in enumerate(wrap(quote, t['quote_chars'])[:t['quote_lines']]):
        words(line, right - width(line), y + k * (t['line'] + 1))
    edge, ink = role('TEXT_EDGE'), role('TEXT')
    return ([(np.where(img != 0, edge, 0).astype(np.uint8), x, y) for img, x, y in cells]
            + [(np.where(img == ink, ink, 0).astype(np.uint8), x, y) for img, x, y in cells])


# ------------------------------------------------------------------------------------------- what moves

def frame_colours(state, tick, time, skip=()):
    """The palette of the state and the date for one tick: glint groups and path roles out of phase are hidden, and a
    bright star group that is twinkling is on its way to the dim stars' colour or back. skip may hold 'twinkle'."""
    sc = scene()
    rgb, shown = palette(state, time)
    rgb, shown = rgb.copy(), shown.copy()
    for tint in sc['specials']['tints']:                 # roles in another colour on some days (the surf that glows)
        if gates_open(tint, state, 'clear', time):
            for name, colour in tint['roles'].items():
                rgb[role(name)] = [int(colour[k:k + 2], 16) for k in (0, 2, 4)]
    g = sc['glints']
    phase = tick // g['ticks_per_step'] % len(g['roles'])
    for k, name in enumerate(g['roles']):
        if (k - phase) % len(g['roles']) >= g['shown']:
            shown[role(name)] = False
    p = sc['paths']
    phase = str(tick // p['ticks_per_step'] % p['frames'])
    for prefix in p['prefixes']:
        for name in path_roles(prefix):
            if phase not in name[len(prefix):]:
                shown[role(name)] = False
    t = sc['twinkle']
    if 'twinkle' not in skip:
        # A group that twinkles in its slot fades to the dim stars' colour and back, evenly over the slot: at tick
        # `at` of the slot it is a = half - |at - half| parts in half of the way there (half = slot // 2). Group k's
        # slots are k * (slot // groups) ticks ahead of group 0's, so no two groups start together.
        half, stride = t['slot'] // 2, t['slot'] // len(t['roles'])
        dim = rgb[role(t['dim_to'])].astype(np.int32)
        for k, name in enumerate(t['roles']):
            slot, at = divmod(tick + k * stride, t['slot'])
            if beach_hash(k, slot, t['salt']) % t['one_in'] == 0:
                a = half - abs(at - half)
                bright = rgb[role(name)].astype(np.int32)
                rgb[role(name)] = (bright * (half - a) + dim * a + half // 2) // half
    return rgb, shown


@cache
def path_roles(prefix):
    names = [e['name'] for e in json.loads((ART / 'palettes' / 'day.json').read_text())['colors']]
    return [n for n in names if n.startswith(prefix) and n[len(prefix):].isdigit()]


def move_frame(move, tick):
    """Which frame of a dog movement shows at this tick, or None while it is not happening."""
    t = move['timetable']
    if 'period' in t:
        start, at = 0, tick % t['period']
    else:
        slot, at = divmod(tick, t['slot'])
        a, b = t['chance']
        if beach_hash(slot, 0, t['salt']) % b >= a:
            return None
        start = beach_hash(slot, 1, t['salt']) % t['spread']
    if not start <= at < start + t['length']:
        return None
    return (at - start) // move['ticks_per_frame'] % len(move['frames'])


def move_pixels(sprite, rect, dx, dy, fill):
    """The opaque pixels inside rect move by (dx, dy); where they were becomes fill; where they land is replaced."""
    x, y, w, h = rect
    part = sprite[y:y + h, x:x + w].copy()
    ys, xs = np.nonzero(part)
    sprite[y + ys, x + xs] = fill
    ny, nx = y + ys + dy, x + xs + dx
    inside = (ny >= 0) & (ny < sprite.shape[0]) & (nx >= 0) & (nx < sprite.shape[1])
    sprite[ny[inside], nx[inside]] = part[ys[inside], xs[inside]]


def apply(sprite, op):
    """One operation of a dog movement on the sprite's indexes: recolour, shift or shear."""
    if op['op'] == 'recolour':
        for x, y in op['cells']:
            sprite[y, x] = role(op['to'])
    elif op['op'] == 'shift':
        move_pixels(sprite, op['rect'], op['dx'], op['dy'], role(op['fill']) if op['fill'] else 0)
    elif op['op'] == 'shear':
        x, y, w, h = op['rect']
        for k, dx in enumerate(op['dx']):
            move_pixels(sprite, [x, y + k, w, 1], dx, 0, 0)
    else:
        raise ValueError(f'unknown dog operation {op["op"]}')


def dog_frame(sprite, tick, moves):
    """A part of the dog at this tick: its image with every movement that is happening applied, in order."""
    out = sprite.copy()
    for move in moves:
        k = move_frame(move, tick)
        if k is not None:
            for op in move['frames'][k]:
                apply(out, op)
    return out


@cache
def sand_roles():
    """The roles of the sand: every index in the sand layer of any state."""
    marks = np.zeros(256, bool)
    for s in scene()['states'].values():
        marks[np.unique(layer(s['sand']))] = True
    marks[0] = False
    return marks


def moon_shows(state, weather, time):
    """True while the moon is drawn: a state that has one, not the new moon's frame, and no cloud or rain over a night."""
    sc = scene()
    hidden = state == 'night' and weather != 'clear' and 'moon' in sc['clear_night_only']
    return state in sc['moon']['states'] and moon_frame(time) != 0 and not hidden


def shadow_key(state, weather, time):
    """Which entry of the dog's shadow table applies: the state's, or 'no_moon' in a state that has a moon while none
    is drawn (nothing casts a shadow then)."""
    return 'no_moon' if state in scene()['moon']['states'] and not moon_shows(state, weather, time) else state


def shadow_target(idx):
    """What a shadow makes of each frame pixel, decided before any shadow is laid (so the shadow cannot extend itself):
    DOG_SHADOW on a sand role, the value of dog.shadow_onto on one of its keys, 0 (no change) anywhere else."""
    lut = np.zeros(256, np.uint8)
    lut[sand_roles()] = role('DOG_SHADOW')
    for k, v in scene()['dog']['shadow_onto'].items():
        lut[role(k)] = role(v)
    return lut[idx]


def shadow_lean(key, time):
    """[ax, bx, ay, by] for a shadow key: dog.shadow[key], or by day the month's entry of dog.shadow_day (the sun
    stands lower in winter, so the shadow is longer)."""
    d = scene()['dog']
    return d['shadow_day'][time.month - 1] if key == 'day' else d['shadow'][key]


def cast_shadow(idx, target, image, ground, x, y, key, lean):
    """One part's shadow, the part's top-left at (x, y): each opaque pixel (px, py) at h = max(0, ground[px] - py)
    casts onto column x + px + h * ax // bx, rows top .. top + thick - 1 with top = y + ground[px] + h * ay // by
    (floor division; [ax, bx, ay, by] = lean, from shadow_lean; thick = shadow_thick[key]). A frame pixel it lands on
    takes its target (shadow_target) unless that is 0. A pixel in a column without ground (-1) casts nothing."""
    d = scene()['dog']
    ax, bx, ay, by = lean
    ys, xs = np.nonzero(image)
    g = ground[xs]
    has = g >= 0
    ys, xs, g = ys[has], xs[has], g[has]
    h = np.maximum(0, g - ys)
    sx = x + xs + (h * ax) // bx
    top = y + g + (h * ay) // by
    for k in range(d['shadow_thick'][key]):
        sy = top + k
        inside = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
        cx, cy = sx[inside], sy[inside]
        t = target[cy, cx]
        hit = t != 0
        idx[cy[hit], cx[hit]] = t[hit]


# ------------------------------------------------------------------------------------------- the poses

def ground_rows(image, ground):
    """A part's ground row for each of its columns: the one row given, or for 'outline' the lowest opaque row of the
    column in the image as loaded, -1 (no ground) in a column with no opaque pixel."""
    if ground != 'outline':
        return np.full(image.shape[1], ground, np.int64)
    opaque = image != 0
    lowest = image.shape[0] - 1 - np.argmax(opaque[::-1], axis=0)
    return np.where(opaque.any(axis=0), lowest, -1).astype(np.int64)


def load_part(entry, image=None):
    """One part of a pose (an entry of a pose's parts in scene.json) with its image loaded: from art/, or from the path
    itself when it is absolute; or the image given. Flat parts have no ground."""
    if image is None:
        path = Path(entry['file'])
        image = np.array(Image.open(path if path.is_absolute() else ART / path))
    flat = bool(entry.get('flat'))
    return dict(image=image, at=tuple(entry.get('at', (0, 0))), flat=flat,
                ground=None if flat else ground_rows(image, entry['ground']), moves=entry.get('moves', []))


def load_pose(entry):
    return dict(name=entry['name'], parts=[load_part(p) for p in entry['parts']])


@cache
def poses():
    """The poses of scene.json, each part with its image, ground and moves loaded (once)."""
    return [load_pose(e) for e in scene()['dog']['poses']]


def pose_index(name):
    names = [p['name'] for p in scene()['dog']['poses']]
    if name not in names:
        raise ValueError(f'scene.json has no pose {name}; it has {" ".join(names)}')
    return names.index(name)


def shuffled(b, n, salt):
    """Block b's order of the n poses, before the fix at its start: for i from n-1 down to 1, swap places i and
    hash(i, b, salt) % (i + 1). b may be negative: the hash takes its low 32 bits, as Java's (int) does."""
    order = list(range(n))
    for i in range(n - 1, 0, -1):
        j = beach_hash(i, b & M32, salt) % (i + 1)
        order[i], order[j] = order[j], order[i]
    return order


def pose_of_slot(s):
    """The pose of slot s: place s mod n of block s div n, whose first two places swap when its first pose is the last
    of the block before (no pose twice in a row). With two poses they alternate, s mod 2: there the swap would move
    the block's last place too, and the next block compares with the unswapped one."""
    n, salt = len(scene()['dog']['poses']), scene()['dog']['pose_change']['order_salt']
    if n == 2:
        return s % 2
    b, i = s // n, s % n
    order = shuffled(b, n, salt)
    if n > 1 and order[0] == shuffled(b - 1, n, salt)[n - 1]:
        order[0], order[1] = order[1], order[0]
    return order[i]


def change_start(s):
    """The tick at which the change of pose in slot s starts: s * hold + hash(s, 1, salt) % jitter."""
    p = scene()['dog']['pose_change']
    return s * p['hold'] + beach_hash(s & M32, 1, p['salt']) % p['jitter']


def pose_at(tick):
    """(old, new, step): the pose indexes for this tick; old and step are None unless a change is fading. In slot
    s = tick // hold, slot s - 1's pose shows until change_start(s); for fade_ticks ticks from there the step is
    (tick - start) * steps // fade_ticks. With one pose: (None, 0, None); with none, new is None too."""
    n = len(scene()['dog']['poses'])
    if n <= 1:
        return None, (0 if n else None), None
    p = scene()['dog']['pose_change']
    s = tick // p['hold']
    start = change_start(s)
    if tick < start:
        return None, pose_of_slot(s - 1), None
    if tick - start < p['fade_ticks']:
        return pose_of_slot(s - 1), pose_of_slot(s), (tick - start) * scene()['fade']['steps'] // p['fade_ticks']
    return None, pose_of_slot(s), None


def chosen_poses(pose, tick):
    """(old, new, step) as loaded poses for the pose argument of render: None follows pose_at; a name of scene.json or
    a dict in the format of one entry of its poses shows that pose, with no fade."""
    if pose is None:
        old, new, step = pose_at(tick)
        return (None if old is None else poses()[old]), (None if new is None else poses()[new]), step
    if isinstance(pose, str):
        return None, poses()[pose_index(pose)], None
    return None, load_pose(pose), None


# ------------------------------------------------------------------------------------------- the frame

def pieces(name, state, weather, time, tick):
    """The images that make up one layer in this frame, each with the x, y of its top-left corner."""
    sc = scene()
    if state == 'night' and weather != 'clear' and name in sc['clear_night_only']:
        return []
    if name in ('sky', 'sea', 'sand'):                    # baked for each lighting state
        return [(layer(sc['states'][state][name]), 0, 0)]
    if name == 'sun':
        at, (cx, cy) = sc['states'][state]['sun'], sc['sun']['centre']
        return [(layer(sc['sun']['file']), at[0] - cx, at[1] - cy)] if at else []
    if name in ('moon', 'path_moon'):
        m = sc['moon']
        k = moon_frame(time)
        if state not in m['states'] or k == 0:
            return []
        if name == 'path_moon':
            return [(layer(sc['full_layers'][name]), 0, 0)]
        n = m['size']
        return [(layer(m['file'])[:, k * n:(k + 1) * n], m['at'][0] - m['centre'][0], m['at'][1] - m['centre'][1])]
    if name in sc['full_layers']:
        return [(layer(sc['full_layers'][name]), 0, 0)]
    if name == 'clouds':
        c = sc['clouds']
        size = 'grown' if c['grown'][weather] else 'normal'
        sheet, out = layer(c['file']), []
        shown = c['shown_clear'][time.month - 1] if weather == 'clear' else c['shown'][weather]
        for track in c['tracks'][:shown]:
            x = (track['start_x'] + tick // track['ticks_per_px']) % c['span'] + c['left']
            sx, sy, w, h = track[size]['sheet']
            out.append((sheet[sy:sy + h, sx:sx + w], x + track[size]['dx'], track['row'] + track[size]['dy']))
        return out
    if name in ('foam', 'ripples'):
        f = sc[name]
        if name == 'ripples' and weather != f['weather']:
            return []
        k = tick // f['ticks_per_frame'] % f['frames']
        return [(layer(f['file'])[k * f['frame_height']:(k + 1) * f['frame_height']], 0, f['top'])]
    if name == 'beam':
        b = sc['beam']
        k = tick // b['ticks_per_frame'] % b['frames']
        w = b['size'][0]
        return [(layer(b['file'])[:, k * w:(k + 1) * w], b['at'][0], b['at'][1])]
    if name in ('rain_far', 'rain_near'):
        r = sc['rain']
        if weather != r['weather']:
            return []
        tile = layer(r['layers'][name]['file'])
        down = r['layers'][name]['speed'] * tick
        tile = np.roll(tile, (down % tile.shape[0], -(down // r['lean']) % tile.shape[1]), axis=(0, 1))
        return [(tile[:H, :W], 0, 0)]
    if name in ('specials_back', 'specials_front', 'surprises_sky', 'surprises_back', 'surprises_front'):
        sp, out = sc['specials'], []
        for item in sp['items']:
            if item['slot'] == name:
                piece = special_piece(item, layer(sp['file']), state, weather, time, tick)
                if piece:
                    out.append(piece)
        return out
    if name == 'text':
        date = f'{DAYS[time.isoweekday() % 7]} {time.day} {MONTHS[time.month - 1]}'
        return text_pieces(time.hour, time.minute, date, quote_of(time))
    raise ValueError(f'scene.json names a layer scene.py does not know: {name}')


def stamp(idx, img, x, y, shown):
    """Puts img with its top-left at (x, y): each pixel whose role is shown replaces what is under it."""
    h, w = img.shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    part = img[y0 - y:y1 - y, x0 - x:x1 - x]
    keep = shown[part]
    idx[y0:y1, x0:x1][keep] = part[keep]


def indexes(time, weather, frame_number, state=None, skip=(), pose=None):
    """The frame as palette indexes, its colours for this tick, and its state. skip names layers to leave out, and
    may also hold 'twinkle' and 'dog_moves' (every part of the dog, and its shadow, stays as its plain image).
    pose: as for render; with None, while a change fades, the new pose (one index frame cannot hold a fade; finished
    blends it)."""
    return pose_indexes(time, weather, frame_number, state, skip, chosen_poses(pose, frame_number)[1])


def pose_indexes(time, weather, frame_number, state, skip, pose):
    """indexes with the pose already loaded (None: no dog). At dog_shadow the flat parts are stamped, then every other
    part casts its shadow; at dog every other part is stamped; in the order of the pose's parts."""
    state = state or choose_state(time, weather)
    rgb, shown = frame_colours(state, frame_number, time, skip)
    parts = pose['parts'] if pose else []
    frames = [p['image'] if 'dog_moves' in skip else dog_frame(p['image'], frame_number, p['moves']) for p in parts]
    d = scene()['dog']
    idx = np.zeros((H, W), np.uint8)
    for name in scene()['order']:
        if name in skip:
            continue
        if name == 'dog_shadow':
            if parts:
                for p, f in zip(parts, frames):
                    if p['flat']:
                        stamp(idx, f, d['x'] + p['at'][0], d['y'] + p['at'][1], shown)
                target, key = shadow_target(idx), shadow_key(state, weather, time)
                for p, f in zip(parts, frames):
                    if not p['flat']:
                        cast_shadow(idx, target, f, p['ground'], d['x'] + p['at'][0], d['y'] + p['at'][1], key,
                                    shadow_lean(key, time))
        elif name == 'dog':
            for p, f in zip(parts, frames):
                if not p['flat']:
                    stamp(idx, f, d['x'] + p['at'][0], d['y'] + p['at'][1], shown)
        else:
            for img, x, y in pieces(name, state, weather, time, frame_number):
                stamp(idx, img, x, y, shown)
    return idx, rgb, state


def blend(old, new, step):
    """A whole-frame fade: each channel (old * (steps - step) + new * step + steps // 2) // steps."""
    n = scene()['fade']['steps']
    return ((old.astype(np.int32) * (n - step) + new.astype(np.int32) * step + n // 2) // n).astype(np.uint8)


def finished(time, weather, frame_number, state, skip=(), pose=None):
    """One state's frame as RGB; while a change of pose fades, the blend of the frames of the old and the new pose."""
    old, now, step = chosen_poses(pose, frame_number)
    new = coloured(time, weather, frame_number, state, skip, now)
    return new if old is None else blend(coloured(time, weather, frame_number, state, skip, old), new, step)


def coloured(time, weather, frame_number, state, skip, pose):
    """One pose's frame as RGB. In a state whose text is not solid (text.opacity, percent) every pixel that the clock
    and the words changed is mixed with what lies under it: (text * opacity + under * (100 - opacity) + 50) // 100
    for each channel."""
    idx, rgb, state = pose_indexes(time, weather, frame_number, state, skip, pose)
    out = rgb[idx]
    opacity = scene()['text']['opacity'][state]
    if opacity < 100 and 'text' not in skip:
        under, _, _ = pose_indexes(time, weather, frame_number, state, tuple(skip) + ('text',), pose)
        m = idx != under
        out[m] = (out[m].astype(np.int32) * opacity + rgb[under][m].astype(np.int32) * (100 - opacity) + 50) // 100
    return out


def state_fade(time, weather):
    """(previous state, step) while a state boundary passed less than a fade ago, else None. The step comes from the
    time since the boundary in whole ticks (boundaries fall on whole minutes): step = ticks * steps // fade ticks."""
    f = scene()['fade']
    ticks = (time.second * 1_000_000 + time.microsecond) * scene()['ticks_per_second'] // 1_000_000
    if ticks >= f['ticks']:
        return None
    before = choose_state(time - timedelta(minutes=1), weather)
    if before == choose_state(time, weather):
        return None
    return before, ticks * f['steps'] // f['ticks']


def frame(time, weather, frame_number, state=None, skip=(), pose=None):
    """One weather's frame as an H x W x 3 array, faded in from the previous state just after a boundary."""
    now = finished(time, weather, frame_number, state or choose_state(time, weather), skip, pose)
    fade = None if state else state_fade(time, weather)
    if fade:
        return blend(finished(time, weather, frame_number, fade[0], skip, pose), now, fade[1])
    return now


def render_now(time, epoch_ms, pose=None):
    """The frame the television shows: the local time, its weather by date, and the tick from the system clock."""
    return render(time, weather_at(time), tick_at(epoch_ms), pose=pose)


def render(time, weather, frame_number, state=None, pose=None):
    """One 480x270 RGB frame.
    time: a datetime (its seconds time the fade after a change of state);
    weather: 'clear', 'cloudy' or 'rain', or (old, new, step) with step 0..32 to fade from one weather to another;
    frame_number: the tick, eight a second;
    state: one of the six lighting states, to override the one the time and weather give (no state fade then);
    pose: None for the schedule (pose_at, with its fades), or a pose to show with no fade: a name in scene.json, or a
    dict in the format of one entry of its dog.poses (a file with an absolute path is read from there)."""
    if isinstance(weather, tuple):
        old, new, step = weather
        return Image.fromarray(blend(frame(time, old, frame_number, state, (), pose),
                                     frame(time, new, frame_number, state, (), pose), step))
    return Image.fromarray(frame(time, weather, frame_number, state, (), pose))
