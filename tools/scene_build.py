"""Builds the beach scene's files.

The scene was first drawn by Java code. This generator began as a port of that code; the Java was removed, and the
files written here became the source of the picture. Comments below still name the Java methods a formula came from (Beach.buildLit, Beach.water,
Hud, and so on): that is a record of origin, not a file to look for.

    python3 -I tools/scene_build.py
    python3 -I tools/scene_build.py set STATE NAME=HEX ...              (sets only those roles in that state)
    python3 -I tools/scene_build.py count                               (distinct colours per state and month)

Writes art/layers/*.png (mode P, index 0 transparent), the palette files and art/scene.json. Every pixel in a layer
is a palette index, and an index is a role: what the pixel is, not its colour. A palette file gives each role a
colour, or null to hide it.

Palette files. art/palettes/<state>.json is the base design of a lighting state: six files. art/palettes/<mm>/
<state>.json is what month mm shows in that state: 72 files, and the only ones scene.py and the television read.
A role is either kept or computed (Roles.add):
- kept (the dog's, the props', the text's and every role not redesigned on 2026-11-10): the base file is the truth
  once it holds the role, so a hand edit survives a rebuild, and every month copies it;
- computed (the sky, the sea, the sand, the land): its colour comes from the tables here, in scene_dither.py and in
  scene_months.py on every build, for the base design and for each month. An edit of such a role in a file is lost.
The first 22 roles, the dog's 15 and the props' 7, keep their indexes; the scene's roles follow in the order the
layers register them, so a role no layer uses drops out and the rest are renumbered, with every layer rewritten in
the same run. A layer file that this run did not write is deleted.

The land is a port of Beach.java's painting, in 32-bit floats where Java uses float, so the shapes land on the same
pixels. Each layer has its own function below; change a layer by changing its function and running this again.
"""
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scene import W, H, beach_hash as jhash, wrap  # noqa: E402  (one port of Beach.hash and PixelFont.wrap, shared)


import scene_sand    # noqa: E402  (the sand's marks: layer_sand(roles, beach, sb); sb is this module, its tables and helpers)
import scene_foam    # noqa: E402  (the water's edge, its foam and wave lines: layer_foam(roles, beach, sb))
import scene_dither  # noqa: E402  (the sky, the sea and the sand: fields baked with Floyd-Steinberg dithering)
import scene_land    # noqa: E402  (the headland: wood, grass, cliff, houses)
import scene_months  # noqa: E402  (what each month changes: colours, sun times, weather)
import scene_house   # noqa: E402  (the doghouse at the left edge of the sand)
import scene_specials  # noqa: E402  (what shows only on some dates: holidays, the December lights, boats, fog)

ADDON = Path(__file__).resolve().parent.parent
ART = ADDON / 'art'
LAYERS = ART / 'layers'
PALETTES = ART / 'palettes'

HORIZON = 100
STATES = ['dawn', 'day', 'dusk', 'night', 'cloudy', 'rain']

# Beach.java's palette.
COLOURS = {
    'WHITE': 0xF4FAF8, 'PALE': 0xCFEDEF, 'SKY_LOW': 0x9AD6F7, 'SKY': 0x7AC8F9, 'AQUA': 0x81C6CE, 'TEAL': 0x4BAED1,
    'SEA': 0x3B8FC5, 'NAVY': 0x2B4A78, 'SAND_LIGHT': 0xF3D9B4, 'SAND': 0xECCA9D, 'SAND_SHADE': 0xD9AE8F,
    'MAUVE': 0xB58C80, 'BROWN': 0x7A5646, 'PLUM': 0x4A3540, 'LEAF_LIGHT': 0x8A9F38, 'LEAF': 0x5F7A2C,
    'LEAF_SHADE': 0x3A5A2E, 'RED': 0xB5544B,
}
COLOURS.update(scene_land.COLOURS)       # the headland's greens, browns, walls and roofs
NAME_OF = {v: k for k, v in COLOURS.items()}
assert len(NAME_OF) == len(COLOURS), 'two colour names share one colour: a land role is named by its colour'
globals().update(COLOURS)
WET_SAND = 0xC9A27E
LAMP = 0xFFD873

# The light in each state, from the brief: Beach.buildLit's light, glow and overcast, rain (the wet-sand mix) and the
# side the land is lit from. Dusk glow is Java's own value at 18:00, 1 - 10/60; the brief rounds it to 0.83.
LIGHT = {
    'dawn':   dict(light=0.65,  glow=0.8,         overcast=0.0,  rain=0, side='right'),
    'day':    dict(light=1.0,   glow=0.0,         overcast=0.0,  rain=0, side='left'),
    'dusk':   dict(light=0.625, glow=1 - 10 / 60, overcast=0.0,  rain=0, side='left'),
    'night':  dict(light=0.0,   glow=0.0,         overcast=0.0,  rain=0, side='right'),
    'cloudy': dict(light=1.0,   glow=0.0,         overcast=0.55, rain=0, side='left'),
    'rain':   dict(light=1.0,   glow=0.0,         overcast=0.9,  rain=1, side='left'),
}

# Sky gradient stops per state: (position, colour), position 0 = SKY_00 (top, or far from the glow), 1 = SKY_47.
SKY_STOPS = {
    'day':    [(0, 0x5CAEF0), (0.5, 0x7AC8F9), (0.85, 0x9AD6F7), (1, 0xC4E8F6)],
    'dawn':   [(0, 0x4E6FA8), (0.35, 0x7A6FA6), (0.6, 0xC07A98), (0.8, 0xF09A7C), (1, 0xFFC98A)],
    'dusk':   [(0, 0x3B4E86), (0.35, 0x6A5C96), (0.6, 0xB0688E), (0.8, 0xE88A72), (1, 0xFFBE7A)],
    'night':  [(0, 0x0A0F2A), (0.7, 0x16224A), (1, 0x22346A)],
    'cloudy': [(0, 0x8D99A8), (1, 0xB9C2CC)],
    'rain':   [(0, 0x747F8D), (1, 0xA3ADB8)],
}
GLOW_X = {'dawn': 400, 'dusk': 62}
# The sky's, the sea's and the sand's tones and fields are in scene_dither.py.

SUN_AT = {'dawn': [400, 87]}
MOON_AT = [404, 68]
PATH_SUN_X, PATH_MOON_X = 400, 404

TIDE_TICKS, FOAM_FRAMES = 152, 152     # one wave is 152 ticks; a frame for every tick (38 frames, 4 ticks each, looked jerky)
CLOUDS_SHOWN = {'clear': 2, 'cloudy': 8, 'rain': 10}    # in clear weather the month says how many: scene_months.CLOUDS_CLEAR
CLOUDS_GROWN = {'clear': False, 'cloudy': True, 'rain': True}
# Layers drawn at night only when the weather is clear.
CLEAR_NIGHT_ONLY = ['stars', 'moon', 'path_moon']

# The dog: the scene position of the top-left corner of every pose (POSES below places each part from there).
DOG = dict(x=189, y=165)
DOG_SHADOW_DAY = 0xC8A480
# The shadow's lean per state: a sprite pixel h rows above the ground row casts its shadow (h * ax) // bx pixels to
# the side and (h * ay) // by pixels down from the ground row. Floor division: negative values round down.
# By day the sun is high, so the shadow is short and joins the feet: with lean 1/3 and 1/6 and four pixels deep it was
# a slab that ran 20 pixels past the nose and read as a mat. Under cloud the
# light is soft but still comes from the left, as on the land: a smaller, thinner shadow that leans a little right.
# At night the moon casts the shadow, from the right. 'no_moon' is used in a night state while no moon is drawn (the
# new moon, or cloud or rain over it): nothing casts a shadow then, and only the dark patch right under him is left.
DOG_SHADOW_LEAN = {'day': [1, 6, 1, 10], 'dawn': [-3, 4, 1, 5], 'dusk': [3, 4, 1, 5], 'night': [-2, 5, 1, 6],
                   'cloudy': [1, 10, 1, 14], 'rain': [1, 10, 1, 14], 'no_moon': [0, 1, 1, 14]}
# How many pixels deep each shadow pixel is: it also covers the thick - 1 pixels right below it (on sand only).
DOG_SHADOW_THICK = {'day': 3, 'dawn': 2, 'dusk': 2, 'night': 2, 'cloudy': 2, 'rain': 2, 'no_moon': 2}


def _shear(sign):
    return [{'op': 'shear', 'rect': [4, 44, 12, 15], 'dx': [sign] * 7 + [2 * sign] * 8}]


# The dog's movements, applied in this order. Each is a list of frames; a frame is a list of operations on the
# sprite's indexes. A regular timetable is active for the first `length` ticks of every `period`. An irregular one,
# in each slot of `slot` ticks, happens when hash(slot number, 0, salt) % b < a (chance a/b) and starts at
# hash(slot number, 1, salt) % spread. While active, frame = (ticks since start // ticks_per_frame) % frames.
DOG_MOVES = [
    # breath: the belly between columns 43 and 60 drops one pixel; its shadow band (three rows) gets one row deeper
    dict(name='breath', timetable=dict(period=37, length=15), ticks_per_frame=1,
         frames=[[{'op': 'shift', 'rect': [43, 39, 18, 3], 'dx': 0, 'dy': 1, 'fill': 'COAT_UNDER'}]]),
    # blink: the eye (columns 110-111, rows 12-13) closes to its lower row
    dict(name='blink', timetable=dict(slot=29, length=2, spread=24, chance=[2, 3], salt=91), ticks_per_frame=1,
         frames=[[{'op': 'recolour', 'cells': [[110, 12], [111, 12]], 'to': 'COAT'}]]),
    # ear: its tip (row 12, columns 100-103) lifts one pixel
    dict(name='ear', timetable=dict(slot=83, length=6, spread=70, chance=[1, 2], salt=93), ticks_per_frame=1,
         frames=[[{'op': 'recolour', 'cells': [[100, 12], [101, 12], [102, 12], [103, 12]], 'to': 'COAT'}]]),
    dict(name='tail', timetable=dict(slot=131, length=40, spread=60, chance=[2, 3], salt=95), ticks_per_frame=5,
         frames=[_shear(1), [], _shear(-1), []]),
]

# The poses, `stand` first. A part is one PNG in art/, placed at (DOG x + at[0], DOG y + at[1]); it is either flat (a
# prop on the sand: stamped at dog_shadow, the shadow falls on it) or stands on `ground`: one row for every column, or
# 'outline', the lowest opaque row of each column of the file. Moves as DOG_MOVES, in the part's own pixels.
# `stand` is here; each pose of POSE_FILES comes from tools/poses/<name>.json when that file exists (one pose in the
# format of one entry of scene.json dog.poses; `file` is a name in art/), read and checked by pose_file.
# A pose goes into scene.json only when all its PNG files exist in art/.
POSES = [
    dict(name='stand', parts=[dict(file='dog.png', at=[0, 0], ground=75, moves=DOG_MOVES)]),
]
POSE_FILES = ['sit', 'sphinx', 'belly', 'side', 'curl']
POSES_DIR = Path(__file__).resolve().parent / 'poses'
# Which pose shows (scene.pose_at): slot s = tick // hold; each block of n slots shows every pose once, shuffled by
# order_salt; the change in slot s starts hash(s, 1, salt) % jitter ticks into it and fades over fade_ticks.
POSE_CHANGE = dict(hold=2400, jitter=1440, fade_ticks=16, salt=97, order_salt=98)
# What the dog's shadow turns a prop's role into (other than sand, which becomes DOG_SHADOW).
SHADOW_ONTO = {'TOWEL_A': 'TOWEL_A_SHADE', 'TOWEL_B': 'TOWEL_B_SHADE'}

# Loops, in ticks (eight a second).
GLINT_STEP, GLINT_GROUPS, GLINT_SHOWN = 6, 5, 3       # phase = (tick // 6) % 5; group g shows when (g - phase) % 5 < 3
PATH_STEP, PATH_FRAMES = 4, 3                         # phase = (tick // 4) % 3
# A bright group of stars fades to the faint stars' colour and back over a slot of 48 ticks (6 seconds), in one slot of
# five. (Until 2026-11-10 a group dropped to the faint colour at once for 6 ticks: that was too abrupt, so the fade is
# slower and more gradual.)
TWINKLE = dict(slot=48, groups=8, one_in=5, salt=41, dim_to='STAR_C')
BEAM_STEP, BEAM_ANGLES = 8, 32          # a position of the beam lasts 8 ticks; 32 positions: a turn takes 32 seconds
BEAM_LEVELS = [0.5, 0.33, 0.17]  # BEAM_0..2: how far each step is mixed from the night sky toward the beam colour
RIPPLE_STEP, RIPPLE_FRAMES = 3, 16
RAIN_TILE = [480, 288]
RAIN_LEAN = 4                   # rain moves (and streaks lean) one pixel left for every RAIN_LEAN down
RAIN_LAYERS = {'rain_far': dict(speed=4, streaks=100, length=3, salt=64),
               'rain_near': dict(speed=8, streaks=50, length=6, salt=65)}
FADE = dict(steps=32, ticks=64, light=dict(minutes=5, steps=300))

FONT_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?'-:&/()+\""
FONT_ROWS = [
    [14, 17, 17, 31, 17, 17, 17], [30, 17, 17, 30, 17, 17, 30], [14, 17, 16, 16, 16, 17, 14],
    [30, 17, 17, 17, 17, 17, 30], [31, 16, 16, 30, 16, 16, 31], [31, 16, 16, 30, 16, 16, 16],
    [14, 17, 16, 23, 17, 17, 15], [17, 17, 17, 31, 17, 17, 17], [14, 4, 4, 4, 4, 4, 14],
    [7, 2, 2, 2, 2, 18, 12], [17, 18, 20, 24, 20, 18, 17], [16, 16, 16, 16, 16, 16, 31],
    [17, 27, 21, 21, 17, 17, 17], [17, 25, 21, 19, 17, 17, 17], [14, 17, 17, 17, 17, 17, 14],
    [30, 17, 17, 30, 16, 16, 16], [14, 17, 17, 17, 21, 18, 13], [30, 17, 17, 30, 20, 18, 17],
    [15, 16, 16, 14, 1, 1, 30], [31, 4, 4, 4, 4, 4, 4], [17, 17, 17, 17, 17, 17, 14],
    [17, 17, 17, 17, 17, 10, 4], [17, 17, 17, 21, 21, 21, 10], [17, 17, 10, 4, 10, 17, 17],
    [17, 17, 10, 4, 4, 4, 4], [31, 1, 2, 4, 8, 16, 31],
    [14, 17, 19, 21, 25, 17, 14], [4, 12, 4, 4, 4, 4, 14], [14, 17, 1, 2, 4, 8, 31],
    [31, 2, 4, 2, 1, 17, 14], [2, 6, 10, 18, 31, 2, 2], [31, 16, 30, 1, 1, 17, 14],
    [6, 8, 16, 30, 17, 17, 14], [31, 1, 2, 4, 8, 8, 8], [14, 17, 17, 14, 17, 17, 14],
    [14, 17, 17, 15, 1, 2, 12],
    [0, 0, 0, 0, 0, 12, 12], [0, 0, 0, 0, 12, 4, 8], [4, 4, 4, 4, 4, 0, 4], [14, 17, 1, 2, 4, 0, 4],
    [4, 4, 8, 0, 0, 0, 0], [0, 0, 0, 31, 0, 0, 0], [0, 12, 12, 0, 12, 12, 0],
    [12, 18, 20, 8, 21, 18, 13], [1, 1, 2, 4, 8, 16, 16], [2, 4, 8, 8, 8, 4, 2],
    [8, 4, 2, 2, 2, 4, 8], [0, 4, 4, 31, 4, 4, 0], [10, 10, 20, 0, 0, 0, 0]]
# The quote of the hour, top right (replaces the idea and the TODAY line); each pass through the quotes has its own
# order. See scene.quote_of.
QUOTES = dict(quotes='quotes.txt', quote_chars=24, quote_lines=4, quote_salt=113,
              quote_epoch_year=2026)
# Where the words go (scene.text_pieces): the clock's top-left corner is the margin; a letter advances 6 px; a line of
# words is 9 px high.
TEXT = dict(cell=[7, 9], advance=6, line=9, margin_x=25, margin_y=15)
# How solid the clock and the words are in each lighting state, in percent: under 100 each of their pixels is mixed
# with what lies under it (scene.coloured). They were made less bright at night, with a slight
# transparency and a warmer colour. Their colour is
# the role TEXT of art/palettes/<state>.json, set by hand: at night a dimmer, warmer cream (D9B98C), at dawn and
# dusk a step toward it (EBCFA6), by day the cream it was (F3D9B4).
TEXT_OPACITY = {'dawn': 92, 'day': 100, 'dusk': 92, 'night': 80, 'cloudy': 100, 'rain': 100}
# No star within this many pixels of where words can be: beside the words a star read as a full stop ("MON 9 NOV .").
STAR_CLEAR = 4


def text_boxes():
    """(x0, y0, x1, y1), end not included, of everything the words can cover: the clock with AM or PM and the date
    (at most 10 letters) on the left; on the right the quote's quote_lines lines of quote_chars letters."""
    mx, my, adv, line = TEXT['margin_x'], TEXT['margin_y'], TEXT['advance'], TEXT['line']
    clock_right = mx - 1 + 6 + 14 + 6 + 14 + 14 + 1 + 2 * adv + 1   # 12:00, then AM or PM one pixel on
    date_right = mx - 1 + 10 * adv + 1
    left = (mx - 1, my - 1, max(clock_right, date_right), my + 26 - 1 + line)
    right = (W - mx - QUOTES['quote_chars'] * adv, my - 1,
             W - mx + 1, my - 1 + (QUOTES['quote_lines'] - 1) * (line + 1) + line)
    return [left, right]
# The weather by date (Day.java). roll = pick(date, roll_question, 100); the day's weather is the first name whose odds
# number for the season is above the roll. A rain day rains during one shower and is cloudy the rest of the day:
# start minute = start + pick(date, 4, start_range), length = length + pick(date, 5, length_range), cut at midnight.
WEATHER = dict(names=['clear', 'cloudy', 'rain'], roll_question=1, roll_bound=100,     # the odds: scene_months.py
               shower=dict(start=360, start_question=4, start_range=720, length=90, length_question=5, length_range=240))
TICKS_PER_SECOND = 8      # tick = epoch milliseconds * 8 // 1000
# The picture's brightness and warmth (scene.evening_factors; the app applies them to the finished frame, scene.render
# does not). Brightness, in percent: full when the screensaver starts and for hold_minutes after, then down over
# fade_minutes to the level of the hour: day from sunrise to sunset, down to evening over warm_after_sunset minutes
# after sunset, down to night over night_ramp minutes from night_from (a minute of the clock, 21:30), and back to day
# over the dawn_ramp minutes before sunrise (scene.settled_brightness). With the TV's own light-sensing
# dimming on, 35 % is the lowest and the day is 100 %, so the day and its start stay at 100 % and only the night dims,
# to 40 %. Below about 20 % the colours distort. Warmth: after sunset green and blue fall to warm_green and warm_blue percent over warm_after_sunset minutes. An app
# cannot set this television's backlight; a darker picture is what dims the panel.
EVENING = dict(day=100, evening=100, night=40, night_from=1290, night_ramp=10, hold_minutes=5, fade_minutes=10,
               dawn_ramp=30, warm_after_sunset=90, warm_green=93, warm_blue=74)
# Hud's seven-segment figures: which segments a..g each lights (bits 6..0), and where each segment sits in 11x19.
SEGMENTS = [0b1111110, 0b0110000, 0b1101101, 0b1111001, 0b0110011, 0b1011011, 0b1011111, 0b1110000, 0b1111111,
            0b1111011]
SEGMENT_AT = [(1, 0, 9, 3), (8, 1, 3, 8), (8, 10, 3, 8), (1, 16, 9, 3), (0, 10, 3, 8), (0, 1, 3, 8), (1, 8, 9, 3)]


# ------------------------------------------------------------------------------------------- Java arithmetic

f32 = np.float32
M32 = 0xFFFFFFFF


def jround(v):
    """Java's Math.round: halves go up."""
    return math.floor(float(v) + 0.5)


class JavaRandom:
    """java.util.Random, for the three seeded lists in Beach.java (sand marks, clouds, stars)."""

    def __init__(self, seed):
        self.seed = (seed ^ 0x5DEECE66D) & (2 ** 48 - 1)

    def next(self, bits):
        self.seed = (self.seed * 0x5DEECE66D + 0xB) & (2 ** 48 - 1)
        return self.seed >> (48 - bits)

    def next_int(self, bound):
        if bound & -bound == bound:
            return (bound * self.next(31)) >> 31
        while True:
            bits = self.next(31)
            val = bits % bound
            if bits - val + (bound - 1) < 2 ** 31:
                return val

    def next_float(self):
        return self.next(24) / float(1 << 24)


def mix(a, b, t):
    """Beach.mix: a to b by t, per channel, truncated."""
    t = f32(t)
    if t <= 0:
        return a
    if t >= 1:
        return b
    out = 0
    for shift in (16, 8, 0):
        ca, cb = (a >> shift) & 255, (b >> shift) & 255
        out |= int(f32(ca) + f32(cb - ca) * t) << shift
    return out


def mul(c, r, g, b):
    """Beach.mul: scale each channel, capped at 255."""
    return (min(255, int(f32((c >> 16) & 255) * f32(r))) << 16) | (min(255, int(f32((c >> 8) & 255) * f32(g))) << 8) \
        | min(255, int(f32(c & 255) * f32(b)))


def grade(c, state):
    """Beach.buildLit's colour grading for one state: dimmer and bluer at night, warmer at the glow, greyer overcast."""
    p = LIGHT[state]
    light, glow, overcast = f32(p['light']), f32(p['glow']), f32(p['overcast'])
    glow = glow * (f32(1) - overcast * f32(0.8))
    light_now = light * (f32(1) - f32(0.22) * overcast)
    n = (f32(0.36) + f32(0.64) * light_now, f32(0.33) + f32(0.67) * light_now, f32(0.47) + f32(0.53) * light_now)
    warm = (f32(1) + f32(0.08) * glow, f32(1) - f32(0.07) * glow, f32(1) - f32(0.20) * glow)
    grey = overcast * f32(0.35)
    toward = (150, 156, 164)
    out = 0
    for k, shift in enumerate((16, 8, 0)):
        v = (c >> shift) & 255
        g = (f32(v) * (f32(1) - grey) + f32(toward[k]) * grey) * n[k] * warm[k]
        out |= (0 if g < 0 else 255 if g > 255 else int(g)) << shift
    return out


def glow_of(state):
    p = LIGHT[state]
    return f32(p['glow']) * (f32(1) - f32(p['overcast']) * f32(0.8))


def lamps_on(state):
    """How far the lamps are lit, 0..1, or 0 by day (Beach.render)."""
    light = f32(LIGHT[state]['light'])
    return min(f32(1), (f32(0.45) - light) * f32(5)) if light < f32(0.45) else 0


def land_colour(left, right, state):
    """A land pixel's colour in one state, from its two daylight colours (lit from the left and from the right)."""
    p = LIGHT[state]
    if p['rain'] and left in (SAND, SAND_LIGHT, SAND_SHADE):
        left = right = mix(left, WET_SAND, f32(0.85) * f32(p['rain']))
    return grade(left if p['side'] == 'left' else right, state)


def each_state(fn):
    return {s: fn(s) for s in STATES}


MONTHS = range(1, 13)        # month 0 is the base design, before any month's change (art/palettes/<state>.json)


def lit(c, state, month, what='land'):
    """A day colour in one lighting state and month: the month's change first (scene_months.tint: what = 'sky', 'sea',
    'sand', 'land', 'leaf', 'grass', 'rock' ...; month 0 changes nothing), then the state's grading."""
    c = scene_months.tint(c, month, what) if month else scene_months.base(c, what)
    return grade(c, state)


def sky_tone(k, n, state, month):
    """Sky tone k of n: by day the table scene_dither.SKY_DAY, in the other states the state's stops; then the month."""
    c = scene_dither.tones(scene_dither.SKY_DAY, n)[k] if state == 'day' else sky_colour(state, k / (n - 1))
    return scene_months.tint(c, month, 'sky') if month else c


# ------------------------------------------------------------------------------------------- the shapes (Beach.java)

K_SKY, K_SEA, K_SOLID, K_SHORE = 0, 1, 2, 3
SHORE_BAND = 15
OWN_SAND, OWN_HILL, OWN_LH = 1, 2, 3

LAND_TOP = [(0, 70), (18, 66), (40, 68), (58, 74), (74, 70), (96, 64), (120, 66), (144, 74), (170, 84), (200, 92),
            (228, 100), (250, 106), (262, 114)]
LAND_FOOT = [(240, 121), (225, 119), (190, 118), (150, 120), (110, 123), (70, 126), (30, 130), (0, 133)]
SHORE = [(262, 114), (244, 120), (222, 126), (202, 134), (186, 143), (176, 153), (174, 163), (182, 172), (198, 180),
         (220, 189), (240, 200), (266, 208), (296, 220), (322, 232), (352, 240), (386, 251), (418, 262), (450, 272),
         (540, 300)]


def build_shore():
    """Beach.buildShore: each sea or sand pixel's distance from the waterline (sea > 0), the nearest point along it,
    and its kind. Returns (dist, along, kind) as H x W arrays."""
    p = [(f32(x), f32(y)) for x, y in SHORE]
    for _ in range(3):
        q = [p[0]]
        for k in range(len(p) - 1):
            q.append((p[k][0] * f32(0.75) + p[k + 1][0] * f32(0.25), p[k][1] * f32(0.75) + p[k + 1][1] * f32(0.25)))
            q.append((p[k][0] * f32(0.25) + p[k + 1][0] * f32(0.75), p[k][1] * f32(0.25) + p[k + 1][1] * f32(0.75)))
        q.append(p[-1])
        p = q
    sx, sy, tx, ty = [], [], [], []
    for s in range(len(p) - 1):
        dx, dy = p[s + 1][0] - p[s][0], p[s + 1][1] - p[s][1]
        steps = math.ceil(max(abs(dx), abs(dy)))
        for k in range(steps):
            sx.append(p[s][0] + dx * f32(k) / f32(steps))
            sy.append(p[s][1] + dy * f32(k) / f32(steps))
            tx.append(dx)
            ty.append(dy)
    sx, sy, tx, ty = (np.array(v, f32) for v in (sx, sy, tx, ty))

    dist = np.zeros((H, W), f32)
    along = np.zeros((H, W), np.int32)
    kind = np.full((H, W), K_SKY, np.int8)
    xs = np.arange(W)
    xf = xs.astype(f32)
    for y in range(HORIZON, H):
        scale = f32(0.30) + f32(0.70) * max(f32(0), f32(y - HORIZON) / f32(H - HORIZON))
        dx = xf[:, None] - sx[None, :]
        dy = f32(y) - sy
        d2 = dx * dx + (dy * dy)[None, :]
        at = np.argmin(d2, axis=1)
        best = d2[xs, at]
        cross = tx[at] * (f32(y) - sy[at]) - ty[at] * (xf - sx[at])
        d = np.sqrt(best) / scale
        behind = (y < 114) & (xs >= 228) & (f32(y) < f32(100) + ((xs - 228) * 14).astype(f32) / f32(34))
        sea = (cross < 0) | behind | ((xs >= 262) & (y < 114))
        d = np.where(behind, f32(300), d)
        dist[y] = np.where(sea, d, -d)
        along[y] = at
        kind[y] = np.where(sea, K_SEA, np.where(d < SHORE_BAND, K_SHORE, K_SOLID))

    # Out in the bay the distance is averaged over its neighbourhood (two passes of an 11-pixel box, added in Java's
    # order so the float sums round the same way).
    soft, row = dist.copy(), np.zeros((H, W), f32)
    clip_x = [np.clip(xs + k, 0, W - 1) for k in range(-11, 12)]
    clip_y = [np.clip(np.arange(HORIZON, H) + k, HORIZON, H - 1) for k in range(-11, 12)]
    for _ in range(2):
        total = np.zeros((H - HORIZON, W), f32)
        for cx in clip_x:
            total = total + soft[HORIZON:, cx]
        row[HORIZON:] = total / f32(23)
        total = np.zeros((H - HORIZON, W), f32)
        for cy in clip_y:
            total = total + row[cy, :]
        soft[HORIZON:] = total / f32(23)
    m = (dist > 10) & (dist < 250)
    dist[m] = dist[m] + (soft[m] - dist[m]) * np.minimum(f32(1), (dist[m] - f32(10)) / f32(18))
    return dist, along, kind


def foot_at(x):
    for k in range(len(LAND_FOOT) - 1, 0, -1):
        a, b = LAND_FOOT[k], LAND_FOOT[k - 1]
        if a[0] <= x <= b[0]:
            return jround(f32(a[1]) + f32((b[1] - a[1]) * (x - a[0])) / f32(b[0] - a[0])) + 1
    return H


class Painter:
    """Beach.java's land painting, lit from one side (direction 1 = from the left, -1 = from the right).
    Keeps the colour of every pixel, its kind, and which layer painted it last (sand, hill or lighthouse)."""

    def __init__(self, kind, direction):
        self.dir = direction
        self.kind = kind.copy()
        self.base = np.zeros((H, W), np.int32)
        self.owner = np.zeros((H, W), np.int8)
        self.layer = OWN_SAND
        self.lamps = []
        self.lantern = None
        self.paint_sand()
        self.paw_prints()
        self.sand_only = self.base.copy()
        self.paint_headland()

    def kind_at(self, x, y):
        return K_SKY if x < 0 or y < 0 or x >= W or y >= H else self.kind[y, x]

    def colour_at(self, x, y):
        return -1 if x < 0 or y < 0 or x >= W or y >= H or self.kind[y, x] == K_SEA else self.base[y, x]

    def solid(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.base[y, x] = c
            self.kind[y, x] = K_SOLID
            self.owner[y, x] = self.layer

    def poly(self, p, c):
        for y in range(min(v[1] for v in p), max(v[1] for v in p) + 1):
            sy = f32(y) + f32(0.01)
            xs = []
            for k in range(len(p)):
                a, b = p[k], p[(k + 1) % len(p)]
                if (a[1] <= sy) == (b[1] <= sy):
                    continue
                xs.append(f32(a[0]) + (sy - f32(a[1])) * f32(b[0] - a[0]) / f32(b[1] - a[1]))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(jround(xs[k]), jround(xs[k + 1]) + 1):
                    self.solid(x, y, c)

    def disc(self, cx, cy, r, c):
        for y in range(-r, r + 1):
            for x in range(-r, r + 1):
                if x * x + y * y <= r * r + r // 2:
                    self.solid(cx + x, cy + y, c)

    def paint_sand(self):
        sand = (self.kind != K_SEA) & (np.arange(H)[:, None] >= HORIZON)
        self.base[sand] = SAND          # the tones and the marks of the sand are laid by scene_dither and scene_sand
        self.owner[sand] = OWN_SAND

    def paint_headland(self):
        scene_land.paint_headland(self, sys.modules[__name__])

    def paw_prints(self):
        trail = [(18, 262), (40, 257), (62, 253), (84, 250), (106, 248), (128, 246), (150, 245), (172, 244), (194, 244)]
        for k, (x, y) in enumerate(trail):
            y += 0 if k % 2 == 0 else 3
            for ox, oy in ((0, 0), (1, 0), (0, 1), (1, 1), (8, 1), (9, 1), (8, 2), (9, 2)):
                self.solid(x + ox, y + oy, SAND_SHADE)

class Beach:
    """The fixed scene: the distance field and both paintings of the land."""

    def __init__(self):
        self.dist, self.along, bare = build_shore()
        self.bare = bare
        self.left = Painter(bare, 1)
        self.right = Painter(bare, -1)
        for name in ('kind', 'owner'):
            if not np.array_equal(getattr(self.left, name), getattr(self.right, name)):
                raise SystemExit(f'the two paintings disagree on {name}')
        if self.left.lamps != self.right.lamps or self.left.lantern != self.right.lantern:
            raise SystemExit('the two paintings disagree on the lamps')
        self.kind = self.right.kind      # Beach keeps the kind left by its second pass
        self.owner = self.left.owner
        self.water = (self.kind == K_SEA) | (self.kind == K_SHORE)   # Beach.seaAt: redrawn by water() each tick


# ------------------------------------------------------------------------------------------- roles

DOG_ROLES = 15   # the first entries of every palette are the dog's; their indexes never change
# The props' roles, at indexes 15..21 right after the dog's, also fixed: name, the role whose colour each state's palette
# file gives it when it is first added (after that the file is the truth), use.
PROP_ROLES = [('TOWEL_A', 'SEA_4', 'towel: dark stripe'), ('TOWEL_B', 'SEA_0', 'towel: pale stripe'),
              ('TOWEL_A_SHADE', 'SEA_7', "towel: dark stripe in the dog's shadow"),
              ('TOWEL_B_SHADE', 'SEA_2', "towel: pale stripe in the dog's shadow"),
              ('BALL', 'HILL_RED', 'ball'), ('BALL_SHADE', 'HILL_BROWN', 'ball: shaded side'),
              ('BALL_LIGHT', 'HILL_MAUVE', 'ball: lit spot')]


class Roles:
    """The role list. A role's index is its position: the dog's roles first, then every scene role in the order the
    layers register them, so a role no layer uses any more drops out and the rest are renumbered (every layer is
    rewritten in the same run). Each role carries the colour computed for it in every state, used only where a
    palette file lacks the role: colours already in a file are kept, matched by name."""

    def __init__(self, names):
        self.names = list(names)
        self.index = {n: i for i, n in enumerate(self.names)}
        self.colours, self.uses, self.computed = {}, {}, set()

    def add(self, name, colours, use, keep=True):
        """colours: {state: colour}, or a function (state, month) -> colour (None hides the role). keep=True: the
        palette file is the truth once it holds the role (a hand edit survives). keep=False: the colour is computed
        on every build, for the base design (month 0) and for each month."""
        if name not in self.index:
            self.index[name] = len(self.names)
            self.names.append(name)
        self.colours[name] = colours
        self.uses[name] = use
        if not keep:
            self.computed.add(name)
        return self.index[name]

    def colour(self, name, state, month):
        c = self.colours[name]
        return c(state, month) if callable(c) else c[state]


def pair_name(prefix, left, right):
    a, b = NAME_OF[left], NAME_OF[right]
    return f'{prefix}_{a}' if a == b else f'{prefix}_{a}__{b}'


def kind_of(colour):
    """What a land colour is, for the month's change: 'leaf', 'grass', 'rock' or 'land'."""
    name = NAME_OF[colour]
    if name in scene_months.BLOOM:
        return name
    return 'leaf' if name.startswith('LEAF_') else 'grass' if name.startswith('GRASS_') else \
        'rock' if name.startswith('ROCK_') else 'land'


def land_roles(roles, prefix, left, right, mask, what):
    """Gives each masked pixel the role of its two daylight colours (computed roles); returns the index array."""
    out = np.zeros((H, W), np.uint8)
    pairs = sorted(set(zip(left[mask].tolist(), right[mask].tolist())), key=lambda p: pair_name(prefix, *p))
    for a, b in pairs:
        name = pair_name(prefix, a, b)
        use = f'{what}: {NAME_OF[a]} lit from the left' + ('' if a == b else f', {NAME_OF[b]} from the right')

        def colour(s, m, a=a, b=b):
            c = a if LIGHT[s]['side'] == 'left' else b
            return lit(c, s, m, kind_of(c))
        i = roles.add(name, colour, use, keep=False)
        out[mask & (left == a) & (right == b)] = i
    return out


# ------------------------------------------------------------------------------------------- layers, back to front

def sky_colour(state, t, stops=None):
    """The colour at position t (0..1) of a ramp of (position, colour) stops; by default the state's sky stops."""
    stops = stops or SKY_STOPS[state]
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if t <= p1:
            u = (t - p0) / (p1 - p0)
            return sum(int(((c0 >> s) & 255) + (((c1 >> s) & 255) - ((c0 >> s) & 255)) * u + 0.5) << s
                       for s in (16, 8, 0))
    return stops[-1][1]


def sky_field(gx):
    """The sky's field s, 0 at the top (or far from the glow) to 1 at the horizon (or at the glow), rows 0..99.
    At dawn and dusk (gx = the glow's x) the field is pulled up round the glow on the horizon."""
    y, x = np.mgrid[0:HORIZON, 0:W]
    h = (HORIZON - y).astype(float)
    h_eff = h if gx is None else h / (1 + 1.5 * np.exp(-((x - gx) / 110) ** 2))
    return (HORIZON - h_eff) / HORIZON


def layer_sun(roles):
    """sun.png: Beach.sunDisc's two discs, radius 9 and 7, centre (9, 9). Coloured where the sun is low (dawn, dusk)."""
    def colour(a, b):
        return each_state(lambda s: mix(a, b, glow_of(s)) if s in ('dawn', 'dusk') else None)
    rim = roles.add('SUN_RIM', colour(0xFFE58A, 0xFF7A45), 'sun: outer ring')
    core = roles.add('SUN_CORE', colour(0xFFF7C8, 0xFF9A4F), 'sun: middle')
    img = np.zeros((19, 19), np.uint8)
    y, x = np.mgrid[-9:10, -9:10]
    img[x * x + y * y < 81] = rim       # "<", not "<=": with "<=" each disc had a one-pixel bump at its four compass points
    img[x * x + y * y < 49] = core
    return {'sun.png': img}


def layer_moon(roles):
    """moon.png: eight phases side by side, 17x17 each, new moon first (empty), full moon fifth (Beach.moon)."""
    lit = each_state(lambda s: WHITE if s == 'night' else None)
    edge = each_state(lambda s: PALE if s == 'night' else None)
    bright = roles.add('MOON', lit, 'moon: lit face')
    rim = roles.add('MOON_EDGE', edge, 'moon: lower right of the lit face')
    img = np.zeros((17, 17 * 8), np.uint8)
    for k in range(8):
        phase = k / 8
        turn = math.cos(2 * math.pi * phase)
        for y in range(-8, 9):
            for x in range(-8, 9):
                dx, dy = x / 7.5, y / 7.5
                if dx * dx + dy * dy > 1:
                    continue
                limb = math.sqrt(1 - dy * dy)
                if (dx > limb * turn) if phase < 0.5 else (dx < -limb * turn):
                    img[y + 8, k * 17 + x + 8] = rim if dx + dy > 0.7 else bright
    return {'moon.png': img}


def layer_stars(roles):
    """stars.png: Beach's 110 stars. Every fifth is bright, spread over eight groups STAR_T0..7 for twinkling;
    the rest are STAR_B (Java's 0.7) and STAR_C (0.45). Night only. A star that would fall where words can be, or
    within STAR_CLEAR pixels of there, is drawn again from a second sequence until it does not; the others stay
    where Beach put them."""
    sky_mid = sky_colour('night', 0.5)
    def colour(amount):
        return each_state(lambda s: mix(sky_mid, WHITE, amount) if s == 'night' else None)
    bright = [roles.add(f'STAR_T{g}', colour(1), f'star: bright, twinkle group {g}') for g in range(8)]
    mid = roles.add('STAR_B', colour(0.7), 'star: middle')
    dim = roles.add('STAR_C', colour(0.45), 'star: faint')
    img = np.zeros((H, W), np.uint8)
    r, again = JavaRandom(11), JavaRandom(12)
    keep_out = [(x0 - STAR_CLEAR, y0 - STAR_CLEAR, x1 + STAR_CLEAR, y1 + STAR_CLEAR) for x0, y0, x1, y1 in text_boxes()]
    for k in range(110):
        x = r.next_int(W)
        y = r.next_int(HORIZON - 4)
        while any(x0 <= x < x1 and y0 <= y < y1 for x0, y0, x1, y1 in keep_out):
            x, y = again.next_int(W), again.next_int(HORIZON - 4)
        img[y, x] = bright[(k // 5) % 8] if k % 5 == 0 else mid if k % 2 == 0 else dim
    return {'stars.png': img}


def cloud_shapes():
    """Beach.buildClouds: ten clouds, each a row of puffs (x, y, radius), with a start x, a row and a speed."""
    r = JavaRandom(23)
    clouds = []
    for k in range(10):
        puffs = 3 + r.next_int(3)
        shape, x = [], 0
        for p in range(puffs):
            mid = f32(1) - abs((f32(p) + f32(0.5)) / f32(puffs) - f32(0.5)) * f32(1.5)
            rad = jround(f32(3) + f32(5) * mid + f32(r.next_int(2)))
            shape.append((x, -jround(f32(rad) * f32(0.5)), rad))
            x += jround(f32(rad) * f32(1.3)) + r.next_int(3)
        start = r.next_int(W + 120)
        speed = f32(0.35) + f32(r.next_float()) * f32(0.5)
        clouds.append(dict(shape=shape, start=start, row=16 + (k * 23 % 44), speed=float(speed)))
    return clouds


def in_cloud(shape, x, y, grow):
    return y <= 0 and any((x - px) ** 2 + (y - py) ** 2 * 1.5 <= (r + grow) ** 2 for px, py, r in shape)


def layer_clouds(roles):
    """clouds.png: the ten clouds at their normal size (top row) and grown by 3 for overcast (bottom row). A pixel is
    the lit top, the middle or the shaded underside, by how much cloud lies under it on the side away from the light
    (four rows down: top; two: middle); which side that is depends on where the light comes from, as for the land."""
    def colours(s):
        glow, light, overcast = glow_of(s), f32(LIGHT[s]['light']), f32(LIGHT[s]['overcast'])
        dim = f32(0.25) + f32(0.75) * light
        top = mix(mix(WHITE, 0xFFD9C2, glow), 0x9AA4B2, overcast * f32(0.75))
        under = mix(mix(PALE, 0xE98FA0, glow), 0x6E7A8A, overcast * f32(0.8))
        blue = min(f32(1), dim + f32(0.14))
        return {'TOP': mul(top, dim, dim, blue), 'MID': mul(mix(top, under, f32(0.5)), dim, dim, blue),
                'UNDER': mul(under, dim, dim, blue)}
    by_state = each_state(colours)
    ids = {}

    def level(s, x, y, lee, grow):
        return 'TOP' if in_cloud(s, x + lee, y + 4, grow) else 'MID' if in_cloud(s, x + lee, y + 2, grow) else 'UNDER'
    for a in ('TOP', 'MID', 'UNDER'):
        for b in ('TOP', 'MID', 'UNDER'):
            name = f'CLOUD_{a}' if a == b else f'CLOUD_{a}__{b}'
            pick = each_state(lambda s, a=a, b=b: by_state[s][a if LIGHT[s]['side'] == 'left' else b])
            use = f'cloud: {a.lower()}' + ('' if a == b else f' lit from the left, {b.lower()} from the right')
            ids[a, b] = roles.add(name, pick, use)

    clouds = cloud_shapes()
    sprites = []
    for grow in (0, 3):
        for c in clouds:
            s = c['shape']
            width = s[-1][0] + s[-1][2] + grow
            cells = {}
            for y in range(-20, 1):
                for x in range(-14, width + 15):
                    if in_cloud(s, x, y, grow):
                        cells[x, y] = ids[level(s, x, y, 2, grow), level(s, x, y, -2, grow)]
            x0, y0 = min(x for x, _ in cells), min(y for _, y in cells)
            x1, y1 = max(x for x, _ in cells), max(y for _, y in cells)
            sprite = np.zeros((y1 - y0 + 1, x1 - x0 + 1), np.uint8)
            for (x, y), i in cells.items():
                sprite[y - y0, x - x0] = i
            sprites.append((sprite, x0, y0))
    sheet_w = max(sum(sp.shape[1] for sp, _, _ in sprites[:10]), sum(sp.shape[1] for sp, _, _ in sprites[10:]))
    row_h = [max(sp.shape[0] for sp, _, _ in sprites[:10]), max(sp.shape[0] for sp, _, _ in sprites[10:])]
    sheet = np.zeros((sum(row_h), sheet_w), np.uint8)
    tracks = [dict(row=c['row'], start_x=c['start'], ticks_per_px=jround(1 / (0.025 + 0.035 * c['speed'])))
              for c in clouds]
    for n, (sprite, dx, dy) in enumerate(sprites):
        row = n // 10
        x = sum(sp.shape[1] for sp, _, _ in sprites[row * 10:n])
        y = row_h[0] * row
        sheet[y:y + sprite.shape[0], x:x + sprite.shape[1]] = sprite
        tracks[n % 10]['grown' if row else 'normal'] = dict(sheet=[x, y, sprite.shape[1], sprite.shape[0]], dx=dx, dy=dy)
    return {'clouds.png': sheet}, tracks


def layer_sea_fx(roles, beach):
    """sea_fx.png: Beach.water's far glints, in five groups GLINT_0..4 (Java lights three of the five at a time)."""
    ids = np.array([roles.add(f'GLINT_{g}', each_state(lambda s: grade(SKY_LOW, s)), f'glint on far water, group {g}')
                    for g in range(5)], np.uint8)
    img = np.zeros((H, W), np.uint8)
    y, x = np.mgrid[0:H, 0:W]
    far = (beach.kind == K_SEA) & (beach.dist > 112) & (y < HORIZON + 26)
    cell = jhash(x[far] // 7, y[far], 62)
    on = (cell % 41 == 0) & (x[far] % 7 < 4 + (cell >> 4) % 3)
    ys, xs = y[far][on], x[far][on]
    img[ys, xs] = ids[(cell[on] >> 8) % 5]
    return {'sea_fx.png': img}


def layer_paths(roles, beach):
    """path_sun.png and path_moon.png: the broken path of light under the low sun (x 400) and the moon (x 384).
    Java draws it in three frames that overlap, so a pixel's role names the frames it is lit in: PATH_A02 is lit in
    frames 0 and 2. Frame s lights every role whose name holds the digit s; scene.py hides the others."""
    out = {}
    y, x = np.mgrid[0:H, 0:W]
    water = (beach.kind == K_SEA) & (beach.dist > 5)   # Java: e > 8, and the wave's reach is at least 3
    for file, letter, px, state, colour in (
            ('path_sun.png', 'A', PATH_SUN_X, 'dawn', lambda: mix(0xFFF3C4, 0xFFB36A, glow_of('dawn'))),
            ('path_moon.png', 'B', PATH_MOON_X, 'night', lambda: grade(0xDDE6FF, 'night') | 0x404040)):
        half = 4 + (y - HORIZON) // 9
        off = np.abs(x - px)
        inside = water & (off <= half)
        mask = np.zeros((H, W), np.int64)
        for s in range(3):
            for yy in range(HORIZON, H):
                cols = np.nonzero(inside[yy])[0]
                if len(cols) == 0:
                    continue
                h = jhash(cols // 3 + (yy & 1), yy, 63 + (s + yy) % 3)
                lit = h % 5 < 3 - 2 * off[yy, cols] // (half[yy, cols] + 1)
                mask[yy, cols[lit]] |= 1 << s
        img = np.zeros((H, W), np.uint8)
        for m in range(1, 8):
            digits = ''.join(str(s) for s in range(3) if m >> s & 1)
            i = roles.add(f'PATH_{letter}{digits}',
                          each_state(lambda st: colour() if st == state else None),
                          f'path of light under the {"sun" if letter == "A" else "moon"}, lit in frames {digits}')
            img[mask == m] = i
        out[file] = img
    return out


def layer_hill(roles, beach):
    """hill.png: the headland, the wood, the trees, the cliff, the houses and the stack off the point.
    The house windows are HILL_WINDOW, lit at night."""
    windows = np.zeros((H, W), bool)
    for x, y in beach.left.lamps:
        windows[y, x] = True
    img = land_roles(roles, 'HILL', beach.left.base, beach.right.base, (beach.owner == OWN_HILL) & ~windows, 'headland')
    img[windows] = roles.add('HILL_WINDOW', each_state(lambda s: mix(land_colour(AQUA, AQUA, s), LAMP, lamps_on(s))),
                             'house windows: AQUA by day, the lamp colour at night')
    return {'hill.png': img}


def layer_lighthouse(roles, beach):
    """lighthouse.png: the tower; its 3x3 lantern room is LH_LANTERN, lit at night."""
    lantern = np.zeros((H, W), bool)
    lx, ly = beach.left.lantern
    lantern[ly - 1:ly + 2, lx - 1:lx + 2] = True
    img = land_roles(roles, 'LH', beach.left.base, beach.right.base, (beach.owner == OWN_LH) & ~lantern, 'lighthouse')
    on = each_state(lambda s: mix(0xE8C860, 0xFFF6C8, lamps_on(s)) if lamps_on(s) > 0 else land_colour(PALE, PALE, s))
    img[lantern] = roles.add('LH_LANTERN', on, 'lighthouse lantern room: PALE by day, lit at night')
    return {'lighthouse.png': img}


def layer_beam(roles, beach):
    """beam.png: the lighthouse beam's BEAM_ANGLES positions side by side, each 121x23 with the lantern at (60, 11)
    (Beach.lantern): a broken line of single pixels running out from the lantern, every fourth missing, 15 long for
    positions 0..8 and 7 for the rest, which point away. Java fades it out along its length; here the fade is three
    steps, BEAM_0 (nearest) .. BEAM_2, each an opaque colour between the night sky and the beam. Night only."""
    base = sky_colour('night', (beach.left.lantern[1] * 48 // HORIZON) / 47)      # the night sky behind the lantern
    ids = [roles.add(f'BEAM_{k}', each_state(lambda s, a=a: mix(base, 0xFFF0B0, a) if s == 'night' else None),
                     f'lighthouse beam, brightness step {k} of 0 (nearest) .. 2') for k, a in enumerate(BEAM_LEVELS)]
    w, h, ox, oy = 121, 23, 60, 11
    strip = np.zeros((h, w * BEAM_ANGLES), np.uint8)
    for f in range(BEAM_ANGLES):
        # Position f points along (4 cos, 3 sin) of f / BEAM_ANGLES of a turn: right first, then toward the viewer.
        turn = 2 * math.pi * f / BEAM_ANGLES
        dx, dy = 4 * math.cos(turn), 3 * math.sin(turn)
        if abs(dx) < 0.5:
            # The beam points straight at the viewer or straight away. A line of dots would run down the tower or up
            # the sky, so towards the viewer it is a flash, a small cross round the lantern, and away it is nothing.
            if dy > 0:
                for d, level in ((2, 0), (3, 1), (4, 2)):
                    for px, py in ((d, 0), (-d, 0), (0, d), (0, -d)):
                        strip[oy + py, f * w + ox + px] = ids[level]
            continue
        reach = 15 if f <= BEAM_ANGLES // 2 else 7             # shorter while it points away
        for k in range(2, reach + 1):
            if k % 4 == 0:
                continue
            alpha = 0.75 - 0.6 * k / reach
            level = 0 if alpha >= 0.5 else 1 if alpha >= 0.3 else 2
            strip[oy + jround(dy * k / 4), f * w + ox + jround(dx * k)] = ids[level]
    # The beam steps from position to position, one a second, with nothing between: a cross-fade of two positions
    # was tried on 2026-11-10 and looked like a blur.
    lx, ly = beach.left.lantern
    return {'beam.png': strip}, dict(file='beam.png', at=[lx - ox, ly - oy], size=[w, h], ticks_per_frame=BEAM_STEP,
                                     frames=BEAM_ANGLES)


def layer_rain(roles):
    """rain_far.png and rain_near.png: tiles of RAIN streaks that scene.py scrolls down and left and wraps. A streak
    leans one pixel left for every four down, as the tile moves, and none crosses the tile's top or bottom edge, so
    the wrap leaves no break in a streak. The colour is Java's mix of the sky with the rain tint, made opaque."""
    i = roles.add('RAIN', each_state(lambda s: mix(sky_colour(s, 0.5), 0xD8E6F2, 0.34)), 'rain streaks')
    tw, th = RAIN_TILE
    out = {}
    for name, p in RAIN_LAYERS.items():
        img = np.zeros((th, tw), np.uint8)
        for k in range(p['streaks']):
            x = jhash(k, 2, p['salt']) % tw
            y = jhash(k, 3, p['salt']) % (th - p['length'])
            for j in range(p['length']):
                img[y + j, (x - (y + j) // RAIN_LEAN + y // RAIN_LEAN) % tw] = i
        out[f'{name}.png'] = img
    return out


def layer_ripples(roles, beach):
    """ripples.png: Beach.water's drop rings on the sea, 16 frames of rows 100..269 stacked top to bottom; frame f
    is Java's tick 3f. A ring is a dash three pixels long in a 7x5 cell. Its role is the band it brightens, as Java
    brightens by its four bands: RIPPLE_0 on far water (d >= 104, TEAL), RIPPLE_1 on the middle (38 <= d < 104, AQUA),
    RIPPLE_2 near the shore (d < 38, PALE)."""
    ids = np.array([roles.add(f'RIPPLE_{k}', each_state(lambda s, c=c: grade(c, s)), use) for k, (c, use) in enumerate(
        [(TEAL, 'rain ring on far water'), (AQUA, 'rain ring on the middle water'), (PALE, 'rain ring near the shore')])],
        np.uint8)
    y, x = np.mgrid[HORIZON:H, 0:W]
    d = beach.dist[HORIZON:]
    sea = (beach.kind[HORIZON:] == K_SEA) & (d > 3)
    band = np.where(d >= 104, 0, np.where(d >= 38, 1, 2))
    cx, cy = x // 7, y // 5
    strip = np.zeros(((H - HORIZON) * RIPPLE_FRAMES, W), np.uint8)
    for f in range(RIPPLE_FRAMES):
        cell = jhash(cx, cy, 77 + (3 * f + cx * 3 + cy * 5) // 3)
        on = sea & (cell % 43 < 3) & (y % 5 == (cell >> 4) % 5) & (x % 7 >= 2) & (x % 7 <= 4)
        frame = np.zeros(d.shape, np.uint8)
        frame[on] = ids[band[on]]
        strip[f * (H - HORIZON):(f + 1) * (H - HORIZON)] = frame
    return {'ripples.png': strip}


def role_dog_shadow(roles):
    """DOG_SHADOW: the dog's shadow, which scene.py casts from the sprite onto the sand. Graded like the sand."""
    roles.add('DOG_SHADOW', each_state(lambda s: DOG_SHADOW_DAY if s == 'day' else grade(DOG_SHADOW_DAY, s)),
              "the dog's shadow on the sand")


def role_props(roles):
    """The props' roles (PROP_ROLES), registered right after the dog's so they take indexes 15..21. A palette file that
    lacks one gets the colour that file gives the role it copies."""
    files = {s: {e['name']: e['hex'] for e in json.loads((PALETTES / f'{s}.json').read_text())['colors']}
             for s in STATES}
    for name, source, use in PROP_ROLES:
        roles.add(name, each_state(lambda s, source=source: None if files[s].get(source) is None
                                   else int(files[s][source], 16)), use)


POSE_KEYS = {'name', 'parts'}
PART_KEYS = {'file', 'at', 'ground', 'flat', 'moves'}
MOVE_KEYS = {'name', 'timetable', 'ticks_per_frame', 'frames'}
TIMETABLE_KEYS = [{'period', 'length'}, {'slot', 'length', 'spread', 'chance', 'salt'}]   # regular, irregular
OP_KEYS = {'recolour': {'op', 'cells', 'to'}, 'shift': {'op', 'rect', 'dx', 'dy', 'fill'}, 'shear': {'op', 'rect', 'dx'}}


def pose_file(path, roles):
    """One pose read from tools/poses/<name>.json. Stops the build, naming the file and the fault, when the name inside
    is not the file's, a key is unknown, a part has not exactly one of ground and flat, a part's file is not a plain
    name in art/, a move has an unknown op or a role the palette does not hold, or an irregular timetable's
    length + spread passes its slot."""
    def fault(what):
        raise SystemExit(f'{path}: {what}')

    def keys(d, allowed, where):
        unknown = sorted(set(d) - set(allowed))
        if unknown:
            fault(f'unknown key {" ".join(unknown)} in {where}')

    try:
        pose = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        fault(f'not JSON: {e}')
    keys(pose, POSE_KEYS, 'the pose')
    if pose.get('name') != path.stem:
        fault(f'the name inside is {pose.get("name")!r}, the file is {path.stem}.json')
    for k, part in enumerate(pose['parts']):
        where = f'part {k}'
        keys(part, PART_KEYS, where)
        if ('ground' in part) == bool(part.get('flat')):
            fault(f'{where} needs exactly one of "ground" and "flat": true')
        f = part.get('file')
        if not isinstance(f, str) or f in ('', '.', '..') or Path(f).name != f or '\\' in f:
            fault(f'{where}: file {f!r} is not a plain name in art/')
        for move in part.get('moves', []):
            where = f'part {k} move {move.get("name")!r}'
            keys(move, MOVE_KEYS, where)
            t = move['timetable']
            keys(t, TIMETABLE_KEYS[1] if 'slot' in t else TIMETABLE_KEYS[0], f'{where} timetable')
            if 'slot' in t and t['length'] + t['spread'] > t['slot']:
                fault(f'{where}: length {t["length"]} + spread {t["spread"]} passes the slot {t["slot"]}')
            for frame in move['frames']:
                for op in frame:
                    if op.get('op') not in OP_KEYS:
                        fault(f'{where}: unknown op {op.get("op")!r}')
                    keys(op, OP_KEYS[op['op']], f'{where} op {op["op"]}')
                    name = op.get('to') or op.get('fill')
                    if name and name not in roles.index:
                        fault(f'{where}: the palette holds no role {name}')
    return pose


def part_roles(pose, part, roles):
    """Stops the build when a part of a pose holds a palette index that is not its own kind's: a file named dog*.png
    (the dog) may hold only the dog's roles, 1..DOG_ROLES - 1; any other part (a prop) only the props' roles, which
    follow them. The same holds for the roles its moves recolour to or fill with. Without this a dog drawn with a
    towel's role, or a ball with a coat role, would be built and would change colour with the wrong thing.
    Each operation of a move must also point at the sprite (move_off_sprite)."""
    props = DOG_ROLES + len(PROP_ROLES)
    dog = part['file'].startswith('dog')
    allowed = set(range(1, DOG_ROLES)) if dog else set(range(DOG_ROLES, props))
    kind = "the dog's roles" if dog else "the props' roles"
    used = set(np.unique(np.array(Image.open(ART / part['file'])))) - {0}
    foreign = sorted(int(i) for i in used - allowed)
    if foreign:
        names = [f'{i} {roles.names[i] if i < len(roles.names) else "(no role)"}' for i in foreign]
        raise SystemExit(f'pose {pose}: art/{part["file"]} holds palette indexes outside {kind}: {", ".join(names)}')
    image = np.array(Image.open(ART / part['file']))
    for move in part.get('moves', []):
        for frame in move['frames']:
            for op in frame:
                name = op.get('to') or op.get('fill')
                if name and roles.index[name] not in allowed:
                    raise SystemExit(f'pose {pose}: the move {move["name"]!r} of art/{part["file"]} uses the role '
                                     f'{name}, which is not one of {kind}')
                fault = move_off_sprite(image, op)
                if fault:
                    raise SystemExit(f'pose {pose}: the move {move["name"]!r} of art/{part["file"]}: {fault}')


def move_off_sprite(image, op):
    """What is wrong with where an operation of a move points, or None: a recoloured cell must be an opaque cell of the
    sprite, and a shifted or sheared rect must lie inside the picture and hold an opaque cell. A sprite that was
    repaired by hand keeps its moves' numbers; without this a blink can point at sand and a tail's rect at nothing."""
    h, w = image.shape
    if op['op'] == 'recolour':
        for x, y in op['cells']:
            if not (0 <= x < w and 0 <= y < h) or image[y, x] == 0:
                return f'the cell {x},{y} is not a cell of the sprite'
        return None
    x, y, rw, rh = op['rect']
    if op['op'] == 'shear':
        rh = len(op['dx'])
    if not (0 <= x and 0 <= y and x + rw <= w and y + rh <= h):
        return f'the rect {[x, y, rw, rh]} reaches outside the {w} x {h} picture'
    if not image[y:y + rh, x:x + rw].any():
        return f'the rect {[x, y, rw, rh]} holds no cell of the sprite'
    return None


def present_poses(roles):
    """stand, then the poses of POSE_FILES that have a file in tools/poses/, each checked by pose_file; only the poses
    whose PNG files all exist in art/ are kept, and each part of a kept pose is checked by part_roles. Prints the ones
    left out and why."""
    if POSE_CHANGE['jitter'] + POSE_CHANGE['fade_ticks'] > POSE_CHANGE['hold']:
        raise SystemExit('POSE_CHANGE: jitter + fade_ticks must not pass hold')
    poses = list(POSES)
    for name in POSE_FILES:
        path = POSES_DIR / f'{name}.json'
        if path.exists():
            poses.append(pose_file(path, roles))
        else:
            print(f'pose {name} left out: no tools/poses/{name}.json')
    out = []
    for pose in poses:
        missing = [p['file'] for p in pose['parts'] if not (ART / p['file']).exists()]
        if missing:
            print(f'pose {pose["name"]} left out: no {" ".join(missing)} in art/')
        else:
            for part in pose['parts']:
                part_roles(pose['name'], part, roles)
            out.append(pose)
    print(f'poses in scene.json: {" ".join(p["name"] for p in out) or "none"}')
    return out


def check_quotes():
    """Stops the build, naming the quote, if a quote needs more than quote_lines lines at quote_chars characters or
    holds a character the font does not have."""
    quotes = [q.strip() for q in (ART / QUOTES['quotes']).read_text(encoding='utf-8').splitlines() if q.strip()]
    for q in quotes:
        missing = sorted({c for c in q.upper() if c != ' ' and c not in FONT_CHARS})
        if missing:
            raise SystemExit(f'the font has no {" ".join(missing)} for the quote: {q}')
        if len(wrap(q, QUOTES['quote_chars'])) > QUOTES['quote_lines']:
            raise SystemExit(f'more than {QUOTES["quote_lines"]} lines at {QUOTES["quote_chars"]} characters: {q}')
    print(f'{len(quotes)} quotes, each fits {QUOTES["quote_lines"]} lines of {QUOTES["quote_chars"]} with the font')


def layer_text(roles):
    """font.png and digits.png: Hud's glyphs, each with its one-pixel edge already round it (TEXT_EDGE)."""
    ink = roles.add('TEXT', each_state(lambda s: SAND_LIGHT), 'clock and words')
    edge = roles.add('TEXT_EDGE', each_state(lambda s: NAVY), 'one-pixel edge round the clock and words')

    def cell(w, h, blocks):
        img = np.zeros((h + 2, w + 2), np.uint8)
        for x, y, bw, bh in blocks:
            img[y:y + bh + 2, x:x + bw + 2] = edge
        for x, y, bw, bh in blocks:
            img[y + 1:y + bh + 1, x + 1:x + bw + 1] = ink
        return img

    font = np.hstack([cell(5, 7, [(c, r, 1, 1) for r in range(7) for c in range(5) if rows[r] >> (4 - c) & 1])
                      for rows in FONT_ROWS])
    digit_cells, rects, x = [], {}, 0
    for d in '0123456789:':
        if d == '1':
            img = cell(3, 19, [(0, 1, 3, 8), (0, 10, 3, 8)])
        elif d == ':':
            img = cell(3, 19, [(0, 4, 3, 3), (0, 12, 3, 3)])
        else:
            img = cell(11, 19, [SEGMENT_AT[s] for s in range(7) if SEGMENTS[int(d)] >> (6 - s) & 1])
        rects[d] = [x, 0, img.shape[1], img.shape[0]]
        digit_cells.append(img)
        x += img.shape[1]
    return {'font.png': font, 'digits.png': np.hstack(digit_cells)}, rects


# ------------------------------------------------------------------------------------------- files

def hexs(c):
    return None if c is None else f'{c:06X}'


NOTE = ("The base design of one lighting state; art/palettes/<mm>/ holds what each month shows. The position in "
        "'colors' is the palette index used by every art PNG. The first 22 (the dog's 15 and the props' 7) never move; "
        "the scene's roles are renumbered when one is dropped, and every layer is rewritten with them. A kept role's "
        "colour here is the truth; a computed role's is rewritten by every build (tools/scene_build.py says which). "
        "Index 0 is transparent.")


MONTH_NOTE = ("One file per month and lighting state: the colours of art/palettes/<state>.json as this month shows "
              "them. Written by tools/scene_build.py; do not edit (see the note there on kept and computed roles).")


def write_if_changed(path, text):
    if not path.exists() or path.read_text() != text:
        path.write_text(text)


def write_palette(state, entries):
    """Writes one base palette file, one role per line, in columns."""
    width = max(len(json.dumps(e['name'])) for e in entries) + 1
    lines = [f'    {{"name": {(json.dumps(e["name"]) + ",").ljust(width)} "hex": {(json.dumps(e["hex"]) + ",").ljust(9)} '
             f'"use": {json.dumps(e["use"], ensure_ascii=False)}}}' for e in entries]
    write_if_changed(PALETTES / f'{state}.json', '{\n  "state": ' + json.dumps(state) + ',\n  "note": ' + json.dumps(NOTE)
                     + ',\n  "colors": [\n' + ',\n'.join(lines) + '\n  ]\n}\n')


def write_month_palette(month, state, entries):
    """Writes art/palettes/<mm>/<state>.json: each role's name and colour, in the order of the base file."""
    width = max(len(json.dumps(e['name'])) for e in entries) + 1
    lines = [f'    {{"name": {(json.dumps(e["name"]) + ",").ljust(width)} "hex": {json.dumps(e["hex"])}}}' for e in entries]
    folder = PALETTES / f'{month:02d}'
    folder.mkdir(exist_ok=True)
    write_if_changed(folder / f'{state}.json', '{\n  "month": ' + str(month) + ',\n  "state": ' + json.dumps(state)
                     + ',\n  "note": ' + json.dumps(MONTH_NOTE) + ',\n  "colors": [\n' + ',\n'.join(lines) + '\n  ]\n}\n')


def set_colours(state, colours):
    """Changes only the named roles' colours in one palette file, read right before it is written."""
    entries = json.loads((PALETTES / f'{state}.json').read_text())['colors']
    for e in entries:
        if e['name'] in colours:
            e['hex'] = colours[e['name']]
    write_palette(state, entries)


def set_command(state, pairs):
    """`scene_build.py set STATE NAME=HEX ...`: sets those roles' colours in one base palette file and nothing else.
    The months take the colour at the next build. A computed role's colour would be lost at the next build: change
    its table instead."""
    entries = {e['name']: e['hex'] for e in json.loads((PALETTES / f'{state}.json').read_text())['colors']}
    bad = [p for p in pairs if not re.fullmatch(r'[A-Za-z0-9_]+=[0-9A-Fa-f]{6}', p)]
    if bad:
        raise SystemExit(f'not NAME=RRGGBB: {" ".join(bad)}')
    colours = dict(p.split('=') for p in pairs)
    unknown = [n for n in colours if n not in entries]
    if unknown:
        raise SystemExit(f'{state}.json has no role {" ".join(unknown)}')
    set_colours(state, {n: h.upper() for n, h in colours.items()})
    print(f'{state}.json: ' + ', '.join(f'{n} {entries[n]} -> {h.upper()}' for n, h in colours.items()))


COLOUR_LIMIT = 160       # distinct colours on screen per lighting state and month, dog and text included; the sky's
                         # 48 tones, the sea's 16 and the sand's 16 are 80 of them (scene_dither.HOW)
NEAR = 6                 # count lists pairs of colours within this many units in every channel as merge candidates


def shown_roles(state):
    """Every role that some frame in this state can show: the layers this state draws (all frames of every strip,
    every animation step), every part of every pose and the roles its movements paint, the dog's shadow, and what the
    shadow makes of a prop (shadow_onto) when a pose has a flat part."""
    sc = json.loads((ART / 'scene.json').read_text())
    st = sc['states'][state]
    files = [st['sky'], st['sea'], st['sand'], 'clouds.png', 'sea_fx.png', 'path_sun.png', 'foam.png',
             'hill.png', 'lighthouse.png', 'beam.png', 'font.png', 'digits.png', 'specials.png', 'house_back.png',
             'house_front.png']
    if st['sun']:
        files.append('sun.png')
    if state in sc['moon']['states']:
        files += ['moon.png', 'stars.png', 'path_moon.png']
    if state in ('rain', 'night'):                 # the only states rain weather can be drawn in
        files += ['ripples.png', 'rain_far.png', 'rain_near.png']
    found = set()
    for f in files:
        found |= set(np.unique(np.array(Image.open(LAYERS / f))).tolist())
    names = [e['name'] for e in json.loads((PALETTES / f'{state}.json').read_text())['colors']]
    roles = {names[i] for i in found if i}
    for pose in sc['dog']['poses']:
        for part in pose['parts']:
            roles |= {names[i] for i in np.unique(np.array(Image.open(ART / part['file']))).tolist() if i}
            for move in part.get('moves', []):
                for frame in move['frames']:
                    roles |= {op.get('to') or op.get('fill') for op in frame} - {None}
        if any(part.get('flat') for part in pose['parts']):
            roles |= set(sc['dog']['shadow_onto'].values())
    roles.add('DOG_SHADOW')
    return roles


def count():
    """`scene_build.py count`: per state, the distinct colours any frame can show in the month that shows the most,
    and which roles share each; a line `state: N colours` that the merge script reads. Over the limit, the pairs of
    colours within NEAR units in every channel are listed as candidates to merge."""
    for state in STATES:
        shown = sorted(shown_roles(state))
        worst = None
        for month in MONTHS:
            hexes = {e['name']: e['hex'] for e in
                     json.loads((PALETTES / f'{month:02d}' / f'{state}.json').read_text())['colors']}
            by_colour = {}
            for name in shown:
                if hexes[name] is not None:
                    by_colour.setdefault(hexes[name], []).append(name)
            if worst is None or len(by_colour) > len(worst[1]):
                worst = (month, by_colour)
        month, by_colour = worst
        over = len(by_colour) > COLOUR_LIMIT
        print(f'{state}: {len(by_colour)} colours{" - OVER " + str(COLOUR_LIMIT) if over else ""} (month {month:02d}, the most)')
        for c, names in sorted(by_colour.items(), key=lambda kv: kv[1][0]):
            print(f'  {c}  {" ".join(names)}')
        if over:
            rgb = {c: [int(c[i:i + 2], 16) for i in (0, 2, 4)] for c in by_colour}
            pairs = [(a, b) for a in rgb for b in rgb if a < b and max(abs(p - q) for p, q in zip(rgb[a], rgb[b])) <= NEAR]
            print(f'  {len(pairs)} pairs within {NEAR} per channel:')
            for a, b in sorted(pairs):
                print(f'    {a} ({" ".join(by_colour[a])})  ~  {b} ({" ".join(by_colour[b])})')


def write_palettes(roles):
    """Writes the six base palette files in the order of the role list, then the 72 month files. In a base file a kept
    role that the file already has keeps its colour (matched by name), a kept role new to it gets the computed one,
    a computed role is always written again, and roles no layer registered are dropped. Each file is read right
    before it is written, so edits made meanwhile (the dog's roles) are kept. Each file must start with the dog's
    roles, then hold the props' roles at 15..21 or (before they were first added) none of them."""
    props = [name for name, _, _ in PROP_ROLES]
    fixed = DOG_ROLES + len(props)
    if roles.names[DOG_ROLES:fixed] != props:
        raise SystemExit(f'the role list does not hold the props\' roles at {DOG_ROLES}..{fixed - 1}')
    for state in STATES:
        path = PALETTES / f'{state}.json'
        old = {e['name']: e for e in json.loads(path.read_text())['colors']} if path.exists() else {}
        dog = {e['name']: e for e in json.loads((PALETTES / 'day.json').read_text())['colors']}
        old_names = list(old)
        if old_names[:DOG_ROLES] != roles.names[:DOG_ROLES]:
            raise SystemExit(f'{path} does not start with the dog\'s {DOG_ROLES} roles in their order')
        if old_names[DOG_ROLES:fixed] != props and any(n in old for n in props):
            raise SystemExit(f'{path} holds props\' roles, but not as {DOG_ROLES}..{fixed - 1} in their order')
        dropped = [n for n in old_names if n not in roles.index]
        entries, added = [], []
        for name in roles.names:
            if name in roles.computed:
                entries.append({'name': name, 'hex': hexs(roles.colour(name, state, 0)), 'use': roles.uses[name]})
                added += [name] if name not in old else []
            elif name in old:
                entries.append(old[name])
            else:
                added.append(name)
                if name in roles.colours:
                    entries.append({'name': name, 'hex': hexs(roles.colour(name, state, 0)), 'use': roles.uses[name]})
                else:
                    entries.append({'name': name, 'hex': dog_hex(dog, name, state), 'use': dog[name]['use']})
        write_palette(state, entries)
        for month in MONTHS:
            write_month_palette(month, state, [
                {'name': e['name'], 'hex': hexs(roles.colour(e['name'], state, month)) if e['name'] in roles.computed
                 else e['hex']} for e in entries])
        print(f'{state}.json: {len(entries)} entries' + (f'; added {len(added)}: {" ".join(added)}' if added else '')
              + (f'; dropped {len(dropped)}: {" ".join(dropped)}' if dropped else ''))


def dog_hex(dog, name, state):
    """A dog role in a state other than day: its day colour graded; lit from the right, the planes
    facing the front take the lit colour and those facing the rear the side colour."""
    if dog[name]['hex'] is None:
        return None
    if LIGHT[state]['side'] == 'right' and name in ('COAT_FRONT', 'COAT_REAR'):
        name = 'COAT_REAR' if name == 'COAT_FRONT' else 'COAT_FRONT'
    return hexs(grade(int(dog[name]['hex'], 16), state))


def write_png(name, img, day_rgb):
    path = LAYERS / name
    out = Image.frombytes('P', (img.shape[1], img.shape[0]), np.ascontiguousarray(img).tobytes())
    out.putpalette(day_rgb)
    out.save(path, transparency=0)
    back = np.array(Image.open(path))
    if not np.array_equal(back, img):
        raise SystemExit(f'{path} did not read back the indexes written')


def scene_json(tracks, digit_rects, beam, poses, state_files, specials, house):
    return {
        'note': 'Positions, timings and choices for scene.py. Written by tools/scene_build.py from its tables: '
                'change a number there and rebuild, not here.',
        'size': [W, H], 'scale': 8, 'ticks_per_second': TICKS_PER_SECOND,
        'evening': {**EVENING, 'note': 'day, evening, night: percent; night_from: minute of the day; see scene.settled_brightness.'},
        'weather': {**WEATHER, 'odds': scene_months.WEATHER_ODDS, 'gloom': scene_months.GLOOM,
                    'note': 'odds: one row for each month, January first. gloom: see scene.gloom_end.'},
        'months': {'fade_days': scene_months.FADE_DAYS,
                   'note': 'art/palettes/<mm>/<state>.json is month mm in a lighting state. A month shows its own '
                           'palette until its last fade_days days; on those it is mixed with the next month\'s, '
                           'k parts in fade_days + 1, k = 1 on the first of those days (scene.month_mix).'},
        'order': ['sky', 'surprises_sky', 'sun', 'moon', 'stars', 'clouds', 'sea', 'sea_fx', 'path_sun', 'path_moon', 'specials_back',
                  'surprises_back', 'sand', 'house_shadow', 'dog_shadow', 'foam', 'ripples', 'hill', 'lighthouse',
                  'specials_front', 'surprises_front', 'beam', 'house_back', 'dog', 'house_front',
                  'rain_far', 'rain_near', 'text'],
        'specials': specials,
        'full_layers': {n: f'{n}.png' for n in ('stars', 'sea_fx', 'path_sun', 'path_moon', 'hill', 'lighthouse', 'house_back',
                                                 'house_front')},
        'house': house,
        'clear_night_only': CLEAR_NIGHT_ONLY,
        'glints': {'roles': [f'GLINT_{g}' for g in range(GLINT_GROUPS)], 'ticks_per_step': GLINT_STEP,
                   'shown': GLINT_SHOWN, 'note': 'phase = (tick // ticks_per_step) % groups; group g shows when '
                                                 '(g - phase) % groups < shown.'},
        'paths': {'prefixes': ['PATH_A', 'PATH_B'], 'ticks_per_step': PATH_STEP, 'frames': PATH_FRAMES,
                  'note': 'phase = (tick // ticks_per_step) % frames; a path role shows when its name, after the '
                          'prefix, holds the digit of the phase.'},
        'twinkle': {**TWINKLE, 'roles': [f'STAR_T{g}' for g in range(TWINKLE['groups'])],
                    'note': 'Group g: s, at = divmod(tick + g * (slot // groups), slot). When hash(g, s, salt) % '
                            'one_in == 0 it is a = slot // 2 - |at - slot // 2| parts in slot // 2 of the way to the '
                            'colour of dim_to (scene.frame_colours).'},
        'beam': {**beam, 'note': 'frame = (tick // ticks_per_frame) % frames; the strip holds the frames side by side.'},
        'ripples': {'file': 'ripples.png', 'top': HORIZON, 'frame_height': H - HORIZON, 'frames': RIPPLE_FRAMES,
                    'ticks_per_frame': RIPPLE_STEP, 'weather': 'rain'},
        'rain': {'weather': 'rain', 'tile': RAIN_TILE, 'lean': RAIN_LEAN,
                 'layers': {n: {'file': f'{n}.png', 'speed': p['speed']} for n, p in RAIN_LAYERS.items()},
                 'note': 'At tick t the tile has moved down by speed * t and left by speed * t // lean, wrapping: frame '
                         'pixel (x, y) shows tile[(y - down) % tile_h][(x + left) % tile_w].'},
        'fade': {**FADE, 'note': 'A fade blends two finished frames per channel, (a * (steps - s) + b * s + steps // 2) '
                                 '// steps, s = 0..steps. A change of weather takes ticks ticks. A change of light '
                                 '(from one lighting state to the next at a fixed weather) takes light.minutes '
                                 'minutes in light.steps steps: into dawn or dusk in the minutes before it begins, '
                                 'otherwise in the minutes after the boundary (scene.state_fade).'},
        'states': {s: {**state_files[s], 'light_from': LIGHT[s]['side'], 'sun': SUN_AT.get(s)} for s in STATES},
        'states_note': 'sky, sea and sand are layers baked for the lighting state (Floyd-Steinberg dithering at build '
                       'time, tools/scene_dither.py); states whose layer is the same share a file.',
        'light_note': 'light_from is already in the palettes (the land roles); it is here to read, scene.py does not use it.',
        'day_parts': {
            'sunrise': scene_months.SUNRISE, 'sunset': scene_months.SUNSET, 'summer_time': scene_months.SUMMER_TIME,
            'dawn': [-scene_months.TWILIGHT, 60], 'dusk': [-60, scene_months.TWILIGHT],
            'note': 'sunrise and sunset: minutes after midnight in standard time on the 15th of each month, January '
                    'first; between two 15ths the value changes evenly by the day, and 60 is added while summer_time '
                    'is on (scene.sun_times). dawn and dusk are minutes from sunrise and sunset. Night is before dawn '
                    'opens and after dusk closes.'},
        'sun': {'file': 'sun.png', 'centre': [9, 9]},
        'moon': {'file': 'moon.png', 'size': 17, 'centre': [8, 8], 'at': MOON_AT, 'states': ['night'],
                 'epoch_jd_e9': 2451550260000000, 'month_e9': 29530588853,
                 'note': 'Phase k of 8 (0 new) is round(8 * days since the epoch new moon / month). New draws nothing, '
                         'and path_moon is drawn only when the moon is.'},
        'clouds': {'file': 'clouds.png', 'shown': CLOUDS_SHOWN, 'shown_clear': scene_months.CLOUDS_CLEAR,
                   'grown': CLOUDS_GROWN, 'span': W + 160, 'left': -80,
                   'note': 'x = (start_x + tick // ticks_per_px) % span + left; the sprite goes at (x + dx, row + dy). '
                           'The first shown[weather] tracks are drawn; in clear weather the first shown_clear[month - 1].',
                   'tracks': tracks},
        'foam': {'file': 'foam.png', 'top': HORIZON, 'frame_height': H - HORIZON, 'frames': FOAM_FRAMES,
                 'ticks_per_frame': TIDE_TICKS // FOAM_FRAMES},
        'dog': {**DOG, 'shadow': DOG_SHADOW_LEAN, 'shadow_day': scene_months.SHADOW_DAY,
                'shadow_thick': DOG_SHADOW_THICK, 'shadow_onto': SHADOW_ONTO,
                'poses': poses, 'pose_change': POSE_CHANGE,
                'note': 'Each part of a pose is a file in art/, placed with its top-left corner at (x + at[0], '
                        'y + at[1]); every frame of a part is its image with the active moves applied in order. At '
                        'dog_shadow the flat parts are stamped, then each other part casts its shadow; at dog the other '
                        'parts are stamped, in order. ground is a row for every column, or "outline": the lowest opaque '
                        'row of each column of the file. shadow[key] = [ax, bx, ay, by]: a part pixel (px, py) at h = '
                        'max(0, ground(px) - py) casts onto column x + at[0] + px + h * ax // bx, rows top .. top + '
                        'thick - 1 with top = y + at[1] + ground(px) + h * ay // by, floor division (Java: '
                        'Math.floorDiv). It lands only where the frame held, before any shadow was laid, a sand role '
                        '(it becomes DOG_SHADOW) or a key of shadow_onto (it becomes the value). key is the state, or '
                        '"no_moon" in a state that has a moon (moon.states) while no moon is drawn (frame 0, or weather '
                        'that hides the clear-night layers). By day the lean is the month\'s entry of shadow_day, January first. pose_change: see scene.pose_at; a change is a whole-frame '
                        'fade of fade_ticks ticks between the frames of the two poses.'},
        'text': {'font': 'font.png', 'chars': FONT_CHARS, 'cell': TEXT['cell'], 'advance': TEXT['advance'],
                 'line': TEXT['line'], 'digits': 'digits.png', 'digit_cells': digit_rects,
                 'margin_x': TEXT['margin_x'], 'margin_y': TEXT['margin_y'], 'opacity': TEXT_OPACITY, **QUOTES},
    }


def main():
    LAYERS.mkdir(parents=True, exist_ok=True)
    roles = Roles(e['name'] for e in json.loads((PALETTES / 'day.json').read_text())['colors'][:DOG_ROLES])
    role_props(roles)
    beach = Beach()
    layers = {}
    sb = sys.modules[__name__]
    state_files = {s: {} for s in STATES}

    def baked(kind, names, files):
        for s in STATES:
            state_files[s][kind] = names[s]
        layers.update(files)
    baked('sky', *scene_dither.sky_layers(roles, sb))
    layers.update(layer_sun(roles))
    layers.update(layer_moon(roles))
    layers.update(layer_stars(roles))
    clouds, tracks = layer_clouds(roles)
    layers.update(clouds)
    baked('sea', *scene_dither.sea_layers(roles, beach, sb))
    layers.update(layer_sea_fx(roles, beach))
    layers.update(layer_paths(roles, beach))
    baked('sand', *scene_sand.layer_sand(roles, beach, sb))
    layers.update(scene_foam.layer_foam(roles, beach, sb))
    layers.update(layer_hill(roles, beach))
    layers.update(layer_lighthouse(roles, beach))
    specials_png, specials = scene_specials.layer_specials(roles, sb)
    layers.update(specials_png)
    text, digit_rects = layer_text(roles)
    layers.update(text)
    check_quotes()
    beam_png, beam = layer_beam(roles, beach)
    layers.update(beam_png)
    layers.update(layer_rain(roles))
    layers.update(layer_ripples(roles, beach))
    role_dog_shadow(roles)
    poses = present_poses(roles)        # after every role is registered: the moves' roles are checked against them
    house_png, house = scene_house.layers(roles, (W, H), (DOG['x'], DOG['y']), poses, TICKS_PER_SECOND)
    layers.update(house_png)            # it adds no role: its colours are the hill's

    if len(roles.names) - 1 > 255:
        raise SystemExit(f'{len(roles.names) - 1} roles: a P-mode PNG holds 255 besides the transparent 0')
    print(f'{len(roles.names) - 1} roles (index 0 is transparent)')
    write_palettes(roles)

    day = json.loads((PALETTES / 'day.json').read_text())['colors']
    day_rgb = []
    for e in day:
        c = 0xFF00FF if e['hex'] is None else int(e['hex'], 16)
        day_rgb += [c >> 16, (c >> 8) & 255, c & 255]
    for name, img in layers.items():
        write_png(name, img, day_rgb)
    for stale in sorted(set(f.name for f in LAYERS.glob('*.png')) - set(layers)):
        (LAYERS / stale).unlink()
        print(f'deleted layers/{stale}: no layer of this build')
    (ART / 'scene.json').write_text(json.dumps(scene_json(tracks, digit_rects, beam, poses, state_files, specials, house), indent=1) + '\n')
    print(f'wrote {len(layers)} layers, 6 base palettes, {len(STATES) * len(MONTHS)} month palettes and scene.json')


if __name__ == '__main__':
    if sys.argv[1:2] == ['set']:
        set_command(sys.argv[2], sys.argv[3:])
    elif sys.argv[1:2] == ['count']:
        count()
    else:
        main()
