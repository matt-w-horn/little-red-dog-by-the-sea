"""specials.png: small things that show only on some dates. The lights on the houses in December, something for each
holiday, and what belongs to a part of the year on this coast: a sailboat, the summer fog on the horizon, a crab
boat, driftwood, smoke from the chimneys in the cold months, a whale that blows and dives far out.

When a thing shows (one day for each holiday, though Christmas starts 2 to 3 weeks before: one item a day or two
before the next, and other holidays do the same). A holiday
is its day. Where it has more than one thing, one of them comes two days before and the rest on the day. December
fills up thing by thing: the lights on the houses on the 1st, the wreaths on the 5th, the lighthouse's lights on the
8th, the tree on the 11th, the pines' lights on the 15th, a string of lights from the red house to the lighthouse
on the 19th, and on the 24th and 25th the hat on the lighthouse, lanterns along the beach's upper edge and a star
in the night sky. An early Christmas night, with lights on two roofs and five on a small tree, looked sparse: hence the larger tree, the lights that change, the string, the lanterns and the star.

scene_build.py calls layer_specials(roles, sb) and puts its items into scene.json (`specials`). A sprite is a grid of
letters, one letter a pixel; a sprite with several frames is a list of grids of one size. An item places a sprite at a
spot of the scene on the dates of its rule, in the lighting states and hours it names (None: all). scene.py and
Scene.java draw the items of a slot when the order reaches it: `specials_back` lies on the sky and the sea, under the
sand, the waves and the land; `specials_front` lies on the land and the sand, under the lighthouse's beam and the dog.

Rules (scene.special_on reads them; all whole numbers):
    ['range', m1, d1, m2, d2]                 from the day d1 of month m1 to the day d2 of month m2, both included;
                                              it may run over the year's end
    ['nth', month, weekday, n, before, after] the n-th weekday of the month (weekday 0 = Monday .. 6 = Sunday;
                                              n = -1: the last), from `before` days before it to `after` days after
    ['easter', before, after]                 Easter Sunday of the western churches, with the same two margins
An item shows on a date that any of its rules names.

Colours. All sprites share seventeen roles: thirteen plain ones (SP_*), graded by the lighting state like the land, and
four lamps (GLOW_*), dull by day and lit at dusk and at night: the December lights, the tree's, a carved pumpkin's
face, the fireworks. A sprite may also use a role the scene already has (HEART_IN_SAND: a tone of the sand).

Where the ideas come from: one Gemini proposal for each holiday and each month, made from the scene's own render
(proposals, never shipped). From them: which things to show and where (a
flag on a pole beside the lighthouse, bunting under the eaves, a tree left of the blue house, a hat on the lighthouse,
a turkey by the red house, eggs along the grass, an umbrella on the sand, a sail and a fog bank on the horizon,
driftwood). Every sprite here is drawn on the scene's own grid, by hand or by the code below. Tried and taken out:
beds of kelp by the rock (a few dark dashes on the water, they read as fish).
"""
import math

import numpy as np

import scene_plants
import scene_surprises

# ---------------------------------------------------------------------------------------------------------- colours

PLAIN = {   # letter: (role, day colour, use)
    'W': ('SP_WHITE', 0xF4FAF8, 'specials: white'),
    'G': ('SP_GREY', 0xC5CFD8, 'specials: light grey (a pole, the fog\'s shade, weathered wood)'),
    'R': ('SP_RED', 0xC8433C, 'specials: red'),
    'N': ('SP_NAVY', 0x2E4A7E, 'specials: navy'),
    'D': ('SP_DARK', 0x3A2C2A, 'specials: dark brown'),
    'B': ('SP_BROWN', 0x8A674D, 'specials: brown'),
    'T': ('SP_GREEN', 0x2F6B3A, 'specials: fir green'),
    'O': ('SP_ORANGE', 0xE8792A, 'specials: orange'),
    'Y': ('SP_YELLOW', 0xF2D24A, 'specials: yellow'),
    'P': ('SP_PINK', 0xE58FB0, 'specials: pink'),
    'L': ('SP_LEAF', 0x3FAE4A, 'specials: bright green (the rainbow)'),
    'U': ('SP_BLUE', 0x3F7FE0, 'specials: bright blue (the rainbow)'),
    'V': ('SP_VIOLET', 0x8A4FC8, 'specials: violet (the rainbow)'),
}
GLOW = {    # letter: (role, unlit colour by day, lit colour, use)
    'w': ('GLOW_WARM', 0xB07A30, 0xFFE08A, 'specials: warm lamp'),
    'r': ('GLOW_RED', 0x9A3B34, 0xFF5A4A, 'specials: red lamp'),
    'g': ('GLOW_GREEN', 0x3F7A3A, 0x6BE06B, 'specials: green lamp'),
    'b': ('GLOW_BLUE', 0x3A5F9A, 0x6FB6FF, 'specials: blue lamp'),
}
GLOW_LIT = {'night': 1.0, 'dusk': 0.8, 'dawn': 0.4}     # how far a lamp is lit; in the other states it is unlit
# letter: a role the scene already has (three tones of the sand; the moon's white and two stars' greys, which
# only the night shows)
BORROWED = {'s': 'SAND_15', 'h': 'SAND_11', 'n': 'SAND_0', 'm': 'MOON', 'e': 'STAR_B', 'f': 'STAR_C'}
# What an item of scene.json holds besides name, slot, at, sheet, frames and ticks_per_frame, and its value where
# a line of a table leaves it out (tools/scene_surprises.py describes the last seven).
ITEM_DEFAULTS = dict(when=None, states=None, hours=None, ahead=0, clear=False, days=None, every=None, move=None,
                     jitter=None, once=False, fade=0)

# ---------------------------------------------------------------------------------------------------------- rules


def day(month, d):
    return ['range', month, d, month, d]


NEW_YEAR, VALENTINE, JUNETEENTH, JULY_4, VETERANS = day(1, 1), day(2, 14), day(6, 19), day(7, 4), day(11, 11)
MLK, PRESIDENTS = ['nth', 1, 0, 3, 0, 0], ['nth', 2, 0, 3, 0, 0]
EASTER = ['easter', 0, 0]
MEMORIAL, LABOR, COLUMBUS = ['nth', 5, 0, -1, 0, 0], ['nth', 9, 0, 1, 0, 0], ['nth', 10, 0, 2, 0, 0]
PRIDE = ['nth', 6, 6, -1, 0, 0]                  # the last Sunday of June: the day of San Francisco's Pride parade
HALLOWEEN = day(10, 31)
THANKSGIVING = ['nth', 11, 3, 4, 0, 0]


def lead(rule, days=2):
    """The rule with its days before: the one thing of a holiday that comes early."""
    if rule[0] == 'range':
        m, d = rule[1], rule[2]
        assert rule[1:3] == rule[3:5] and d > days, 'lead: a single day after the first days of its month'
        return ['range', m, d - days, m, d]
    return rule[:-2] + [days, rule[-1]] if rule[0] == 'nth' else ['easter', days, rule[2]]


def december(first, last=31):
    return ['range', 12, first, 12, last]


COLD_MONTHS = ['range', 11, 1, 2, 29]            # smoke from the chimneys
FIREWORKS = [JULY_4, day(12, 31)]               # in the evening (FIREWORK_HOURS)
# And at midnight of the New Year, the first hour of 1 January (an item's hours are whole hours). Until 2026-11-10 the
# rule ran from 31 December to 1 January with the evening's hours, so the fireworks came back on the evening of
# 1 January and never showed at midnight.
MIDNIGHT_FIREWORKS, MIDNIGHT_HOURS = [NEW_YEAR], [0, 1]
DARK = ['night', 'dusk', 'dawn']
FIREWORK_HOURS = [20, 24]
NOT_RAIN_OR_NIGHT = ['dawn', 'day', 'dusk', 'cloudy']

# ---------------------------------------------------------------------------------------------------------- sprites

FLAG_US = ['NNNRRRRR',
           'NWNWWWWW',
           'NNNRRRRR',
           'WWWWWWWW',
           'RRRRRRRR']
FLAG_JUNETEENTH = ['NNNNNNNN',
                   'NNNWWNNN',
                   'NNWWWWNN',
                   'RRRWWRRR',
                   'RRRRRRRR']
FLAG_RAINBOW = ['RRRRRRRR', 'OOOOOOOO', 'YYYYYYYY', 'LLLLLLLL', 'UUUUUUUU', 'VVVVVVVV']
POLE = dict(x=243, top=87, foot=104)             # right of the lighthouse, on the point
FLUTTER = 'AAAABBAAAAAABAAB'                     # the flag's frames, 6 ticks each: mostly at rest
FLAG_TICKS = 6

BUNTING = ['RRRWWWNNNRRRWWWNNN', '.R..W..N..R..W..N.']
BUNTING_JUNETEENTH = ['RRRDDDTTTRRRDDDTTT', '.R..D..T..R..D..T.']
PENNANTS_HEARTS = ['RR.PP.RR.PP.RR.PP.', '.R..P..R..P..R..P.']
BUNTING_RAINBOW = ['RROOYYLLUUVVRROOYY', 'R.O.Y.L.U.V.R.O.Y.']

BALLOONS = ['.RR..',
            '.RRYY',
            'NN.YY',
            'NN.G.',
            '.G.G.',
            '..GG.',
            '..G..']

HEART = ['R.R',
         'RRR',
         '.R.']
HEART_IN_SAND = ['..sss...sss..',
                 '.s...s.s...s.',
                 's.....s.....s',
                 's...........s',
                 's...........s',
                 '.s.........s.',
                 '..s.......s..',
                 '...s.....s...',
                 '....s...s....',
                 '.....s.s.....',
                 '......s......']

BUNNY = ['.W.W.',
         '.WPW.',
         '.WWW.',
         '.WDW.',
         'WWWWW',
         'WWWWW',
         '.W.W.']
EGGS = [(22, 5, 'P'), (37, 3, 'Y'), (49, 6, 'U'), (61, 4, 'P'), (98, 3, 'Y'), (112, 2, 'U'), (127, 0, 'P'), (141, 1, 'Y')]
EGGS_AT = (0, 118)                               # the eggs' x, y are counted from here: along the grass under the wood

BEACH_DAY = ['....RWR.............',
             '..RRWWWRR...........',
             '.RRWWRWWRR..........',
             'RRWW.G.WWRR.........',
             '.....G..............',
             '.....G.....NWNWNWNWN',
             '.....G.....NWNWNWNWN',
             '...ssGsss..NWNWNWNWN',
             '..sssssssss.........']

SMALL_FLAGS = ['NR....NR....NR',
               'RW....RW....RW',
               'G.....G.....G.',
               'G.....G.....G.']

TURKEY = ['..OBOBO...',
          '.OBBBBBO..',
          '.BBBDDBB..',
          '.BBDDDD.D.',
          '..DDDDDDR.',
          '..DDDDD...',
          '...Y.Y....']
HARVEST = ['.O..YYYY',
           'OOO.YBYY',
           'OOO.YYBY']

JACK = ['..T..',
        '.OOO.',
        'OwOwO',
        'OOwOO',
        '.OOO.']
GHOST = ['.WWW.',
         'WDWDW',
         'WWWWW',
         'WWWWW',
         'W.W.W']

TREE_SPRITE = ['.....w.....',            # the star: a lamp that stays warm (TREE_STAR_ROWS are not changed by twinkle)
               '....www....',
               '.....T.....',
               '....TTT....',
               '....TrT....',
               '...TTTTT...',
               '...TTbTw...',
               '..TTTTTTT..',
               '..TwTTTgT..',
               '.TTTTrTTTT.',
               '.TbTTTTTwT.',
               'TTTTTgTTTTT',
               'TTrTTTTbTTT',
               'TTTTwTTTTrT',
               '.....B.....',
               '.....B.....']
TREE_STAR_ROWS = 2
WREATH = ['TTT',
          'T.T',
          'TRT']
SANTA_HAT = ['...RR.W.',
             '..RRRRW.',
             '.RRRRR..',
             '.WWWWWWW']

# Strings of lamps. Each is drawn in two frames: in the second every lamp has the next colour (TWINKLE), so the
# colours step along the string every LIGHT_TICKS ticks.
LIGHTS_BLUE_HOUSE = ['...w.r.g.b.w.r...',      # the ridge, x 72 .. 82
                     '.................',
                     '.g.............b.',      # the two rakes
                     'w.r.g.b.w.r.g.b.w']      # the eave, x 69 .. 85
LIGHTS_RED_HOUSE = ['...r.g.b.w....',
                    '..............',
                    '.w..........r.',
                    'g.b.w.r.g.b.w.']
LIGHTS_LIGHTHOUSE = ['w.g.r.w',                # the gallery, x 233 .. 239
                     '.......',
                     '.b.....',                # then a string wound down the tower
                     '.......',
                     '...w...',
                     '.......',
                     '.....r.',
                     '.......',
                     '.g.....',
                     '.......',
                     '...b...',
                     '.......',
                     '.....w.',
                     '.......',
                     'r......',
                     '.......',
                     '...g...']
LIGHTS_PINE = ['...w...g...r..',               # on an umbrella pine's crown
               '..............',
               '.r...b...w...g',
               '..............',
               '...g...r...b..']
TWINKLE = {'w': 'r', 'r': 'g', 'g': 'b', 'b': 'w'}
LIGHT_TICKS = 16
# A string of lamps from the red house's eave to the lighthouse's gallery: a lamp every 3 pixels, hanging `sag` low.
STRING = dict(x0=195, y0=95, x1=232, y1=85, sag=5, every=3)
LANTERNS = dict(x0=6, x1=150, every=6)           # along the grass's lower edge, each a warm lamp two pixels high
STAR = ['...w...',
        '...w...',
        '..www..',
        'wwwwwww',
        '..www..',
        '...w...',
        '...w...']

SMOKE = dict(height=13, frames=6, ticks=8,       # it climbs a pixel a frame; three rows of smoke, three of air
             lean=[0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 5, 6], width=[1, 2, 2, 2, 2, 3, 3, 3, 3, 2, 2, 2, 1], thin_from=9, pale_from=5)

# A grey whale far out: its back, its blow, its back again, its flukes, then a long stillness. One letter a frame of
# WHALE_ORDER, WHALE_TICKS ticks each.
WHALE_BACK = ['....DDDDD....',
              '...DDDDDDD...']
WHALE_BLOW_LOW = ['.....W.W.....',
                  '......W......',
                  '......W......']
WHALE_BLOW_HIGH = ['....W...W....',
                   '.....W.W.....',
                   '.....W.W.....',
                   '......W......',
                   '......W......',
                   '......W......']
WHALE_MIST = ['...G.....G...',
              '.....G.G.....']
WHALE_FLUKES = ['..DD.....DD..',
                '...DDD.DDD...',
                '....DDDDD....',
                '......D......',
                '......D......',
                '.....DDD.....',
                '....WWWWW....']
WHALE_RIPPLE = ['....WW.WW....']
WHALE_HEIGHT = 10
WHALE_ORDER = 'bbLHMb..bfFFf.r' + '.' * 25           # b back, L H M the blow, f flukes half up, F flukes, r ripple
WHALE_TICKS = 8

SAILBOAT = ['...W...',
            '...WW..',
            '..GWW..',
            '..GWWW.',
            '.GGWWW.',
            '.GGWWWW',
            '...D...',
            'RRRRRRR',
            '.RRRRR.']
CRAB_BOAT = ['....D.....',
             '....D.WW..',
             '...WWWWW..',
             'RRRRRRRRRR',
             '.NNNNNNNN.']

DRIFTWOOD = ['...............GG.......',
             '..............GG........',
             '..GGGGGGGGGGGGGGGGGGGG..',
             'GGGBBGGGGGGBBBGGGGGGBGGG',
             'BBBBBBBBBBBBBBBBBBBBBBB.',
             '.DDDDDDDDDDDDDDDDDDDD...']
DRIFTWOOD_SMALL = ['..GGGGGG..',
                   'GGBBBBBBGG',
                   '.DDDDDDDD.']

FOG = dict(x=346, top=92, low=101, width=134, rise=46, salt=171)         # a bank on the horizon, thin at its left end

FIREWORK = dict(size=23, frames=16, ticks=4, rays=10)
# Three bursts over the sea, clear of the moon and under the quote's box (it ends at row 53; a burst is 11 high
# above its centre): letter, centre x, centre y, ticks it starts later.
BURSTS = [('w', 300, 68, 0), ('r', 348, 66, 22), ('b', 454, 71, 43)]


def with_pole(flag, drop):
    """The frames of a flag on its pole (FLUTTER): the pole one pixel wide with a pale knob, the flag `drop` rows
    under the top. In frame B the flag's outer half hangs one row lower."""
    height = POLE['foot'] - POLE['top'] + 1
    frames = []
    for letter in FLUTTER:
        grid = [['.'] * 9 for _ in range(height)]
        for y in range(height):
            grid[y][0] = 'W' if y == 0 else 'G'
        for fy, row in enumerate(flag):
            for fx, c in enumerate(row):
                grid[1 + drop + fy + (1 if letter == 'B' and fx >= 4 else 0)][1 + fx] = c
        frames.append([''.join(r) for r in grid])
    return frames


def eggs():
    w, h = max(x for x, _, _ in EGGS) + 2, max(y for _, y, _ in EGGS) + 3
    grid = [['.'] * w for _ in range(h)]
    for x, y, c in EGGS:                                 # two wide, three tall, a band round the middle
        for dx in (0, 1):
            grid[y][x + dx] = grid[y + 2][x + dx] = c
            grid[y + 1][x + dx] = 'W' if c != 'W' else 'P'
    return [''.join(r) for r in grid]


def fog(sb):
    """A fog bank lying on the horizon: its lit top white and lumpy, its foot grey and level; it rises from nothing
    at its left end."""
    f = FOG
    h = f['low'] - f['top'] + 1
    grid = [['.'] * f['width'] for _ in range(h)]
    for x in range(f['width']):
        lump = (sb.jhash(x // 9, 0, f['salt']) % 3 + sb.jhash((x + 4) // 17, 1, f['salt']) % 3) / 2
        tall = min(1.0, (x + 1) / f['rise']) * (h - 2.5) + lump * min(1.0, x / 12)
        tall = max(0, min(h, int(tall + 0.5)))
        for k in range(tall):
            grid[h - 1 - k][x] = 'G' if k < 2 + (sb.jhash(x // 5, 2, f['salt']) % 2) and tall > 3 else 'W'
    return [''.join(r) for r in grid]


def firework(letter):
    """A rocket's burst, FIREWORK['frames'] frames: a trail that climbs, a ring of sparks that opens and thins as it
    falls, then dark frames: stillness between two bursts."""
    n, c = FIREWORK['size'], FIREWORK['size'] // 2
    frames = []
    for k in range(FIREWORK['frames']):
        grid = [['.'] * n for _ in range(n)]
        if k < 2:                                        # the rocket climbs
            for y in range(n - 1 - 5 * k, n - 6 - 5 * k, -2):
                grid[y][c] = letter
        elif k < 8:                                      # the burst: radius 2 .. 10, sparser and sinking as it ages
            age = k - 2
            radius = [2, 4.5, 7, 8.5, 9.5, 10][age]
            for ray in range(FIREWORK['rays'] * (2 if age in (2, 3) else 1)):
                turn = 2 * math.pi * (ray + 0.25) / (FIREWORK['rays'] * (2 if age in (2, 3) else 1))
                for r in ([radius] if age < 1 or age > 3 else [radius, radius * 0.6]):
                    if age >= 4 and (ray + age) % 2:
                        continue
                    x = int(round(c + r * math.cos(turn)))
                    y = int(round(c + r * math.sin(turn) * 0.95 + max(0, age - 3) * 1.2))
                    if 0 <= x < n and 0 <= y < n:
                        grid[y][x] = letter
            if age < 2:
                grid[c][c] = letter
        frames.append([''.join(r) for r in grid])
    return frames


def twinkle(grid, keep_rows=0):
    """The two frames of a string of lamps: as drawn, and with every lamp in the next colour of TWINKLE."""
    return [grid, [row if y < keep_rows else ''.join(TWINKLE.get(c, c) for c in row) for y, row in enumerate(grid)]]


def light_string():
    """The lamps of STRING on a grid whose top-left pixel is (x0, the highest lamp's row)."""
    t = STRING
    lamps = []
    for k, x in enumerate(range(t['x0'], t['x1'] + 1, t['every'])):
        u = (x - t['x0']) / (t['x1'] - t['x0'])
        lamps.append((x - t['x0'], int(round(t['y0'] + (t['y1'] - t['y0']) * u + t['sag'] * math.sin(math.pi * u))), 'wrgb'[k % 4]))
    top = min(y for _, y, _ in lamps)
    grid = [['.'] * (t['x1'] - t['x0'] + 1) for _ in range(max(y for _, y, _ in lamps) - top + 1)]
    for x, y, c in lamps:
        grid[y - top][x] = c
    return [''.join(r) for r in grid], top


def lanterns(sb):
    """A lantern every LANTERNS['every'] pixels on the lowest rows of the grass: (grid, the row of its top)."""
    t = LANTERNS
    spots = [(x, sb.foot_at(x) - 2) for x in range(t['x0'], t['x1'] + 1, t['every'])]
    top = min(y for _, y in spots)
    grid = [['.'] * (t['x1'] - t['x0'] + 1) for _ in range(max(y for _, y in spots) + 2 - top)]
    for x, y in spots:
        grid[y - top][x - t['x0']] = grid[y + 1 - top][x - t['x0']] = 'w'
    return [''.join(r) for r in grid], top


def smoke():
    """Smoke from a chimney, SMOKE['frames'] frames: it leans with the wind (the flag flies the same way), widens,
    pales and thins as it climbs. Row 0 of the grid is the top; the lowest row lies right above the chimney."""
    t = SMOKE
    w = max(a + b for a, b in zip(t['lean'], t['width']))
    frames = []
    for k in range(t['frames']):
        grid = [['.'] * w for _ in range(t['height'])]
        for h in range(t['height']):
            if (h - k) % t['frames'] < (2 if h >= t['thin_from'] else 3):
                for x in range(t['lean'][h], t['lean'][h] + t['width'][h]):
                    grid[t['height'] - 1 - h][x] = 'G' if h >= t['pale_from'] else 'W'
        frames.append([''.join(r) for r in grid])
    return frames


def whale():
    parts = {'.': [], 'b': [WHALE_BACK], 'L': [WHALE_BLOW_LOW, WHALE_BACK], 'H': [WHALE_BLOW_HIGH, WHALE_BACK],
             'M': [WHALE_MIST, ['.' * 13] * 4, WHALE_BACK], 'f': [WHALE_FLUKES[:4]], 'F': [WHALE_FLUKES], 'r': [WHALE_RIPPLE]}
    frames = []
    for letter in WHALE_ORDER:
        rows = [row for part in parts[letter] for row in part]
        frames.append(['.' * 13] * (WHALE_HEIGHT - len(rows)) + rows)
    return frames


def sprites(sb):
    """{name: (frames, ticks per frame)}; every frame of a sprite has one size."""
    one = {'bunting_long': [row[:15] for row in BUNTING], 'bunting_short': [row[:12] for row in BUNTING],
           'bunting_juneteenth': [row[:15] for row in BUNTING_JUNETEENTH],
           'bunting_rainbow_long': [row[:15] for row in BUNTING_RAINBOW],
           'bunting_rainbow_short': [row[:12] for row in BUNTING_RAINBOW],
           'pennants_hearts': [row[:12] for row in PENNANTS_HEARTS], 'balloons': BALLOONS, 'heart': HEART, 'heart_in_sand': HEART_IN_SAND, 'bunny': BUNNY, 'eggs': eggs(),
           'beach_day': BEACH_DAY, 'small_flags': SMALL_FLAGS, 'turkey': TURKEY, 'harvest': HARVEST, 'jack': JACK,
           'ghost': GHOST, 'wreath': WREATH, 'santa_hat': SANTA_HAT, 'star': STAR, 'sailboat': SAILBOAT, 'crab_boat': CRAB_BOAT,
           'driftwood': DRIFTWOOD, 'driftwood_small': DRIFTWOOD_SMALL, 'fog': fog(sb)}
    out = {name: ([grid], 1) for name, grid in one.items()}
    for name, grid in (('lights_blue_house', LIGHTS_BLUE_HOUSE), ('lights_red_house', LIGHTS_RED_HOUSE),
                       ('lights_lighthouse', LIGHTS_LIGHTHOUSE), ('lights_pine', LIGHTS_PINE),
                       ('light_string', light_string()[0]), ('lanterns', lanterns(sb)[0])):
        out[name] = (twinkle(grid), LIGHT_TICKS) if name != 'lanterns' else ([grid], 1)
    out['tree'] = (twinkle(TREE_SPRITE, TREE_STAR_ROWS), LIGHT_TICKS)
    out['smoke'] = (smoke(), SMOKE['ticks'])
    out['whale'] = (whale(), WHALE_TICKS)
    out['flag_us'] = (with_pole(FLAG_US, 0), FLAG_TICKS)
    out['flag_us_half'] = (with_pole(FLAG_US, 6), FLAG_TICKS)
    out['flag_juneteenth'] = (with_pole(FLAG_JUNETEENTH, 0), FLAG_TICKS)
    out['flag_rainbow'] = (with_pole(FLAG_RAINBOW, 0), FLAG_TICKS)
    for letter, _, _, _ in BURSTS:
        out[f'firework_{letter}'] = (firework(letter), FIREWORK['ticks'])
    return out


# ---------------------------------------------------------------------------------------------------------- items

FLAG_AT = (POLE['x'], POLE['top'])
BLUE_HOUSE, RED_HOUSE = (70, 114), (182, 96)     # the top-left pixel of each house's wall, right under its eave
BACK, FRONT = 'specials_back', 'specials_front'


def items(sb):
    """name, sprite, slot, (x, y) of its top-left pixel, rules, states (None: all), hours (None: all), ticks its
    frames run ahead."""
    half = FIREWORK['size'] // 2
    smoke_w = SMOKE['height']
    out = [
        # the year on this coast
        ('sailboat', 'sailboat', BACK, (318, 93), [['range', 4, 1, 9, 30]], NOT_RAIN_OR_NIGHT, None, 0),
        ('fog_bank', 'fog', BACK, (FOG['x'], FOG['top']), [['range', 6, 1, 8, 31]], NOT_RAIN_OR_NIGHT, None, 0),
        ('crab_boat', 'crab_boat', BACK, (322, 98), [['range', 11, 15, 1, 31]], NOT_RAIN_OR_NIGHT, None, 0),
        ('whale', 'whale', BACK, (424, 104), [['range', 12, 15, 4, 30]], NOT_RAIN_OR_NIGHT, None, 0),
        ('driftwood', 'driftwood', FRONT, (52, 168), [['range', 12, 1, 2, 29]], None, None, 0),
        ('driftwood_small', 'driftwood_small', FRONT, (126, 204), [['range', 12, 1, 2, 29]], None, None, 0),
        ('smoke_blue_house', 'smoke', FRONT, (80, 108 - smoke_w), [COLD_MONTHS], None, None, 0),
        ('smoke_red_house', 'smoke', FRONT, (189, 90 - smoke_w), [COLD_MONTHS], None, None, 20),
        # December, thing by thing
        ('lights_blue_house', 'lights_blue_house', FRONT, (69, 110), [december(1)], None, None, 0),
        ('lights_red_house', 'lights_red_house', FRONT, (181, 92), [december(1)], None, None, 16),
        ('wreath_blue_house', 'wreath', FRONT, (76, 114), [december(5)], None, None, 0),
        ('wreath_red_house', 'wreath', FRONT, (186, 96), [december(5)], None, None, 0),
        ('lights_lighthouse', 'lights_lighthouse', FRONT, (233, 84), [december(8)], None, None, 0),
        ('tree', 'tree', FRONT, (55, 107), [december(11)], None, None, 8),
        ('lights_pine_left', 'lights_pine', FRONT, (160, 76), [december(15)], None, None, 16),
        ('lights_pine_right', 'lights_pine', FRONT, (200, 85), [december(15)], None, None, 0),
        ('light_string', 'light_string', FRONT, (STRING['x0'], light_string()[1]), [december(19)], None, None, 8),
        ('santa_hat', 'santa_hat', FRONT, (232, 77), [december(24, 25)], None, None, 0),
        ('lanterns', 'lanterns', FRONT, (LANTERNS['x0'], lanterns(sb)[1]), [december(24, 25)], None, None, 0),
        ('star', 'star', BACK, (214, 28), [december(24, 25)], DARK, None, 0),
        # the flag: the federal holidays that have no picture of their own, and those that add to it
        ('flag', 'flag_us', FRONT, FLAG_AT, [NEW_YEAR, MLK, PRESIDENTS, JULY_4, LABOR, COLUMBUS, VETERANS], None, None, 0),
        ('flag_half_staff', 'flag_us_half', FRONT, FLAG_AT, [MEMORIAL], None, None, 0),
        ('flag_juneteenth', 'flag_juneteenth', FRONT, FLAG_AT, [JUNETEENTH], None, None, 0),
        ('flag_rainbow', 'flag_rainbow', FRONT, FLAG_AT, [PRIDE], None, None, 0),
        # what comes two days before its holiday (lead), and what comes on the day
        ('balloons', 'balloons', FRONT, (86, 112), [['range', 12, 30, 1, 1]], None, None, 0),   # right of the house: the tree stands left
        ('heart', 'heart', FRONT, (76, 114), [lead(VALENTINE)], None, None, 0),
        ('heart_in_sand', 'heart_in_sand', FRONT, (96, 168), [VALENTINE], None, None, 0),
        ('pennants_hearts', 'pennants_hearts', FRONT, RED_HOUSE, [VALENTINE], None, None, 0),
        # Presidents' Day has no lead: two days before it can be Valentine's Day, whose heart hangs in the same place
        ('bunting_blue_house', 'bunting_long', FRONT, BLUE_HOUSE, [PRESIDENTS, lead(JULY_4)], None, None, 0),
        ('bunting_red_house', 'bunting_short', FRONT, RED_HOUSE, [JULY_4], None, None, 0),
        ('bunny', 'bunny', FRONT, (172, 101), [lead(EASTER)], None, None, 0),
        ('eggs', 'eggs', FRONT, EGGS_AT, [EASTER], None, None, 0),
        ('small_flags', 'small_flags', FRONT, (90, 120), [lead(MEMORIAL), lead(VETERANS)], None, None, 0),
        ('bunting_juneteenth', 'bunting_juneteenth', FRONT, BLUE_HOUSE, [lead(JUNETEENTH)], None, None, 0),
        ('bunting_rainbow_blue_house', 'bunting_rainbow_long', FRONT, BLUE_HOUSE, [lead(PRIDE)], None, None, 0),
        ('bunting_rainbow_red_house', 'bunting_rainbow_short', FRONT, RED_HOUSE, [PRIDE], None, None, 0),
        ('beach_day', 'beach_day', FRONT, (104, 146), [JULY_4, lead(LABOR)], NOT_RAIN_OR_NIGHT, None, 0),
        ('jack_blue_house', 'jack', FRONT, (80, 120), [lead(HALLOWEEN)], None, None, 0),
        ('jack_red_house', 'jack', FRONT, (195, 99), [HALLOWEEN], None, None, 0),
        ('ghost', 'ghost', FRONT, (88, 116), [HALLOWEEN], None, None, 0),
        ('harvest', 'harvest', FRONT, (87, 119), [lead(THANKSGIVING)], None, None, 0),
        ('turkey', 'turkey', FRONT, (169, 101), [THANKSGIVING], None, None, 0),
    ]
    for letter, cx, cy, ahead in BURSTS:
        out.append((f'firework_{letter}', f'firework_{letter}', BACK, (cx - half, cy - half), FIREWORKS, ['night'],
                    FIREWORK_HOURS, ahead))
        out.append((f'firework_{letter}_midnight', f'firework_{letter}', BACK, (cx - half, cy - half), MIDNIGHT_FIREWORKS,
                    ['night'], MIDNIGHT_HOURS, ahead))
    return out


# ---------------------------------------------------------------------------------------------------------- the layer

def layer_specials(roles, sb):
    """Returns ({'specials.png': the sheet of every sprite's frames}, the `specials` entry of scene.json)."""
    ids = {'.': 0}
    for letter, (name, colour, use) in PLAIN.items():
        ids[letter] = roles.add(name, lambda s, m, c=colour: sb.grade(c, s), use, keep=False)
    for letter, (name, unlit, lit, use) in GLOW.items():
        ids[letter] = roles.add(name, lambda s, m, a=unlit, b=lit: sb.mix(sb.grade(a, s), b, GLOW_LIT.get(s, 0.0)), use,
                                keep=False)
    for letter, name in BORROWED.items():
        ids[letter] = roles.index[name]

    for letter, (name, colour, use) in scene_surprises.AURORA_ROLES.items():
        ids[letter] = roles.add(name, lambda s, m, c=colour: c if s == 'night' else None, use, keep=False)

    plant_sprites, plant_items = scene_plants.build(sb)
    made = {**sprites(sb), **{name: ([grid], 1) for name, grid in plant_sprites.items()}, **scene_surprises.sprites(sb)}
    width = max(len(frames) * len(frames[0][0]) for frames, _ in made.values())
    height = sum(len(frames[0]) for frames, _ in made.values())
    sheet = np.zeros((height, width), np.uint8)
    place, y = {}, 0
    for name, (frames, ticks) in made.items():
        h, w = len(frames[0]), len(frames[0][0])
        for k, grid in enumerate(frames):
            if len(grid) != h or any(len(row) != w for row in grid):
                raise SystemExit(f'specials: the frames of {name} are not all {w} x {h}: '
                                 f'{[len(row) for row in grid]} in frame {k}')
            for gy, row in enumerate(grid):
                for gx, c in enumerate(row):
                    if c not in ids:
                        raise SystemExit(f'specials: {name} holds the letter {c!r}, which names no colour')
                    sheet[y + gy, k * w + gx] = ids[c]
        place[name] = dict(sheet=[0, y, w, h], frames=len(frames), ticks_per_frame=ticks)
        y += h

    lines = [dict(name=name, sprite=sprite, slot=slot, at=at, when=when, states=states, hours=hours, ahead=ahead)
             for name, sprite, slot, at, when, states, hours, ahead in items(sb)] + plant_items + scene_surprises.items(sb)
    listed, salts = [], {}
    for line in lines:
        unknown = set(line) - set(ITEM_DEFAULTS) - {'name', 'sprite', 'slot', 'at'}
        if unknown:
            raise SystemExit(f'specials: {line["name"]} has the unknown field {" ".join(sorted(unknown))}')
        item = {**ITEM_DEFAULTS, **line}
        p = place[item.pop('sprite')]
        x, y0 = item['at']
        if not item['move'] and not (0 <= x and x + p['sheet'][2] + (item['jitter'] or [0])[0] <= sb.W
                                     and 0 <= y0 and y0 + p['sheet'][3] <= sb.H):
            raise SystemExit(f'specials: {item["name"]} does not lie inside the picture')
        if item['fade'] and not item['every']:
            raise SystemExit(f'specials: {item["name"]} fades, which needs a timetable (every)')
        if item['every'] and item['every'][2] > item['every'][0]:
            raise SystemExit(f'specials: {item["name"]} shows longer than its slot')
        tables = (item['days'], item['every'], item['jitter'])
        for salt in {v[k] for v, k in zip(tables, (1, 3, 2)) if v}:
            if salts.setdefault(salt, tables) != tables:        # the same salt and the same tables: one thing in two slots
                raise SystemExit(f'specials: the salt {salt} of {item["name"]} is used by another item')
        listed.append({**item, 'at': list(item['at']), **p})
    unused = sorted(set(place) - {line['sprite'] for line in lines})
    if unused:
        raise SystemExit(f'specials: no item shows the sprite {" ".join(unused)}')
    for tint in scene_surprises.TINTS:
        missing = [name for name in tint['roles'] if name not in roles.index]
        if missing:
            raise SystemExit(f'specials: the tint {tint["name"]} names the unknown role {" ".join(missing)}')
    meteors = scene_surprises.METEORS
    missing = [name for name in meteors['levels'] if name not in roles.index]
    if missing:
        raise SystemExit(f'specials: the shooting star names the unknown role {" ".join(missing)}')
    return {'specials.png': sheet}, dict(
        file='specials.png', items=listed, meteors=meteors, tints=scene_surprises.TINTS,
        note='An item shows its sprite with the top-left pixel at `at` when the order reaches its slot, on a date '
             'that one of the rules of `when` names (scene.special_on), in the lighting states of `states` and from '
             'the hour hours[0] up to, not including, hours[1] (null: all). Its frame is ((tick + ahead) // '
             'ticks_per_frame) % frames; frame k is the part of the sheet at x = sheet[0] + k * sheet[2]. An item '
             'with days, every, move, jitter, once, fade or clear is a surprise: tools/scene_surprises.py describes '
             'those fields, the meteors and the tints; scene.special_piece, scene.meteor and scene.frame_colours '
             'read them.')
