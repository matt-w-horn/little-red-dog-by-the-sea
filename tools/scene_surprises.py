"""Surprises: things that show now and then. Some every night (a shooting star), some a few times a year (the aurora),
some subtle (a distant jet), some large. scene_specials.layer_specials puts their sprites on the sheet and their items
into scene.json beside the holidays'; an item here has more fields than a holiday's (ITEM_DEFAULTS in scene_specials):

    days    [one_in, salt, block, noon]   a lottery by day: the item shows on about one day in one_in (block: days are
                                         drawn `block` at a time; noon 1: the day turns at noon, for things of the night)
    every   [slot, one_in, length, salt] a timetable in ticks (8 a second): in about one slot in one_in the item shows
                                         for `length` ticks, from a moment of the slot that a hash picks
    move    [dx, px, dy, py]             it moves dx pixels every px ticks and dy every py, in whole pixels
    jitter  [jx, jy, salt]               each time, it starts up to jx and jy pixels from its place
    once                                 its frames play once and the last stays (else they loop)
    fade                                 it comes and goes through a dither, over this many ticks (needs every)
    clear                                only in clear weather
    when                                 date rules as for the holidays; None: any date

How often, on average: a thing with `every` comes once in slot * one_in ticks while its other fields let it; one
with `days` on one day in one_in. `python3 -I -B dev/surprises_table.py` prints the table in words.

The shooting star (METEORS) is not an item: scene.meteor draws it by the millisecond, on every refresh of the screen,
on sky pixels only. TINTS give roles another colour on some nights (the surf that glows).

The aurora and the rainbow follow two sets of Gemini proposals made from the scene's own render
(proposals, never shipped): a curtain with a bright green lower edge
that waves, rays that rise from it and turn violet, a shimmer on the sea; one wide arc of six bands from the sea to
behind the headland, seen through. Both are drawn by the code below on the scene's grid.
"""
import math

DAYLIGHT = ['dawn', 'day', 'dusk', 'cloudy']
SUNLIT = ['dawn', 'day', 'dusk']

AURORA_ROLES = {    # letter: (role, colour at night, use); hidden in every other state
    'A': ('AURORA_0', 0x7CFFA0, 'aurora: the bright lower edge'),
    'C': ('AURORA_1', 0x2EA868, 'aurora: green'),
    'X': ('AURORA_2', 0x7A54C8, 'aurora: violet, high in the curtain'),
}

# ---------------------------------------------------------------------------------------------------------- sprites

JET = ['.....................W....',
       'G.GG.GGGGGWWWWWWWWWWWWWWD.',
       '.....................W....']
JET_LIGHTS = [['r.m'], ['r..']]                  # a red lamp and a white one that flashes
SATELLITE = ['e']
COMET = ['...............f',
         '.............ff.',
         '..........fff...',
         '.......efff.....',
         '....eeeff.......',
         '..meee..........',
         '.mmee...........',
         '..m.............']
UFO = [['....eee....', '...efffe...', '.eeeeeeeee.', 'w.g.w.g.w.g', '...fffff...'],
       ['....eee....', '...efffe...', '.eeeeeeeee.', '.g.w.g.w.g.', '...fffff...']]
SANTA = ['......................DD.....DD.....DD..',
         '.....R..............DDDD...DDDD...DDDDr.',
         'wRRRRR..fffffffffff.D..D...D..D...D..D..',
         '.RRRRRR.................................',
         '..DDDD..................................']
WITCH = ['......D......',
         '.....DDD.....',
         '....DDDDD....',
         '.....DD......',
         'w.DDDDDDDDBBB',
         '.....DD......']
AIRSHIP = ['.......WWWWWWWWWWWWW........',
           '....WWWWWWWWWWWWWWWWWWW.....',
           'G.WWWWWWWWWWWWWWWWWWWWWWW...',
           'GGWWWWWWWWWWWWWWWWWWWWWWWWW.',
           'GGNNNNNNNNNNNNNNNNNNNNNNNNNW',
           'GGWGGGGGGGGGGGGGGGGGGGGGGGG.',
           'G.GGGGGGGGGGGGGGGGGGGGGGG...',
           '....GGGGGGGGGGGGGGGGGGG.....',
           '.......GGGGGDDDDGGGG........',
           '............DDDD............']
ANGEL = ['.N....', 'WWNNNY', '.N....']         # one jet of the Blue Angels, flying right, and its smoke
ANGELS_AT = [(30, 4), (22, 1), (22, 7), (14, 4)]
GOOSE = [['D.D', '.D.'], ['.D.', 'D.D']]
GEESE_AT = [(20, 5), (15, 3), (15, 7), (10, 1), (10, 9), (5, 10)]
GULL = {'A': ['W...W', '.WWW.', '..G..'], 'B': ['.....', 'WWWWW', '..G..'], 'C': ['.....', '.WWW.', 'W.G.W']}
GULL_ORDER = 'ABCB'

CONTAINER_SHIP = ['..........................WW....',
                  '.....RROOUULLRRYYUUOO.....WW....',
                  '.....RROOUULLRRYYUUOO....WWWW...',
                  '.....LLYYRROOUULLRRUU....WWWW...',
                  'DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD.',
                  '.DDDDDDDDDDDDDDDDDDDDDDDDDDDDD..',
                  '..RRRRRRRRRRRRRRRRRRRRRRRRRRR...']
TRAWLER = ['......D.......',
           '......D..G....',
           '....WWDW......',
           '....WWWW......',
           'NNNNNNNNNNNN..',
           '.NNNNNNNNNN...',
           '..RRRRRRRR....']
TRAWLER_GULLS = [['W.....W.......', '...W..........'], ['.W.......W....', '....W.........']]
TUG = ['...D..........................',
       '..WWW.........................',
       '.RRRRR........BBBBBBBBBBBBBBB.',
       'DDDDDDD.GGGGG.DDDDDDDDDDDDDDDD',
       '.DDDDD........DDDDDDDDDDDDDDD.']
TALL_SHIP = ['....W.....W.....W..',
             '...WWW...WWW...WWW.',
             '...WWW...WWW...WWW.',
             '..WWWWW.WWWWW.WWWWW',
             '..WWWWW.WWWWW.WWWWW',
             '..WWWWW.WWWWW.WWWWW',
             '....D.....D.....D..',
             'DDDDDDDDDDDDDDDDDDD',
             '.DDDDDDDDDDDDDDDDDG',
             '..BBBBBBBBBBBBBBB..']
SAIL = ['..W..', '..WW.', '.WWW.', '.WWWW', '..D..']
REGATTA_AT = [(0, 2, 'R'), (8, 0, 'N'), (15, 2, 'Y'), (23, 1, 'R'), (30, 2, 'N')]
CRUISE_SHIP = ['..........DD................',
               '.........WWWW....WW.........',
               '....WWWWWWWWWWWWWWWWWW......',
               '...WwWwWwWwWwWwWwWwWwWW.....',
               '.WWWWWWWWWWWWWWWWWWWWWWWWW..',
               'WWwWwWwWwWwWwWwWwWwWwWwWwWWW',
               '.NNNNNNNNNNNNNNNNNNNNNNNNNN.']
SQUID_BOAT = ['....m....',
              '...mwm...',
              '....D....',
              '.DDDDDDD.',
              '..w.w.w..']
PELICAN = {'A': ['.D...D.', 'YWDDD..', '.......'], 'B': ['.......', 'YWDDDD.', '..D.D..']}
PELICAN_ORDER = 'AAAAAABB'
PELICANS_AT = [(0, 3), (9, 2), (18, 1), (27, 2), (36, 4)]
DOLPHINS = dict(frames=8, at=[(0, 0), (11, 3), (22, 5)])       # x of each dolphin and how many frames it is ahead

SEA_LION = {'A': ['.......DD.', '......DDB.', '..DDDDDD..', '.DDDDDDD..', 'DDBBBBDDD.'],
            'B': ['..........', '..........', '..DDDDDDD.', '.DDDDDDDDB', 'DDBBBBBDD.']}
SEA_LION_ORDER = 'AAAB'
SANDCASTLE = ['.....DRR...',
              '.....D.....',
              '.n.n.n.s.s.',
              '.nnnnnhsss.',
              '.nnnnnhsss.',
              'nnnnsnnhsss',
              'nnnnsnnhsss',
              '.sssssssss.']
CRAB = [['R...R', '.RRR.', 'R.R.R'], ['.R.R.', '.RRR.', '.R.R.']]
BONFIRE = [['....w....', '...wO....', '...OwO...', '..OwwrO..', '..rOwOr..', '.DDrOrDD.', 'DDDDDDDDD'],
           ['.........', '....Ow...', '...wOO...', '..OOwwO..', '..rwOOr..', '.DDrOrDD.', 'DDDDDDDDD'],
           ['.....w...', '...O.O...', '...wOw...', '..rOwOO..', '..OwOwr..', '.DDrOrDD.', 'DDDDDDDDD']]
DEER = {'A': ['.........D.D', '.........BB.', '........BBB.', '.......BB...', 'BBBBBBBBB...', 'WBBBBBBBB...', '.BBBBBBBB...',
              '.B.B..B.B...', '.B.B..B.B...', '.D.D..D.D...'],
        'B': ['............', '............', '............', '............', 'BBBBBBBBB...', 'WBBBBBBBBB..', '.BBBBBBBBBB.',
              '.B.B..B.BBB.', '.B.B..B.B.BD', '.D.D..D.D...']}
DEER_ORDER = 'ABBB'
EGRET = {'A': ['...WW.', '...WWY', '...W..', '...W..', '..WW..', '.WWW..', '.WWW..', '..D...', '..D...', '..D...'],
         'B': ['......', '......', '......', '......', '..WWW.', '.WWWW.', '.WWWW.', '..D.W.', '..D.WY', '..D...']}
EGRET_ORDER = 'AAAB'
MONARCH = [['O.O', 'ODO'], ['.O.', '.D.']]

AURORA = dict(x=110, y=2, w=370, h=128, frames=12, ticks=16, sea=99)     # sea: the sprite's row where the sea begins
RAINBOW = dict(cx=300, cy=168, outer=150, band=2, x0=150, x1=450, low=99, letters='ROYLUV')


def mirror(grid):
    return [row[::-1] for row in grid]


def blank(w, h):
    return [['.'] * w for _ in range(h)]


def put(grid, sprite, x, y):
    for gy, row in enumerate(sprite):
        for gx, c in enumerate(row):
            if c != '.' and 0 <= y + gy < len(grid) and 0 <= x + gx < len(grid[0]):
                grid[y + gy][x + gx] = c


def rows(grid):
    return [''.join(r) for r in grid]


def group(frames_of_one, places, w, h):
    """Frames of several of one animal: frames_of_one[k] is its k-th frame; each place is (x, y)."""
    out = []
    for frame in frames_of_one:
        grid = blank(w, h)
        for x, y in places:
            put(grid, frame, x, y)
        out.append(rows(grid))
    return out


def angels():
    grid = blank(52, 11)
    for x, y in ANGELS_AT:
        put(grid, ['.' * 16 + ANGEL[0], 'GGGWWWWWWWWWWWWW' + ANGEL[1], '.' * 16 + ANGEL[2]], x - 14, y)
    return rows(grid)


def regatta():
    grid = blank(36, 8)
    for x, y, hull in REGATTA_AT:
        put(grid, SAIL + [hull * 5], x, y)
    return rows(grid)


def trawler():
    return [gulls + TRAWLER for gulls in TRAWLER_GULLS]


def dolphins():
    """Three dolphins that leap one after the other: each rises out of the water, bends over and goes back in, eight
    pixels on, in DOLPHINS['frames'] frames; white water where it leaves and where it lands."""
    n, frames = DOLPHINS['frames'], []
    for k in range(n):
        grid = blank(34, 7)
        for x0, ahead in DOLPHINS['at']:
            u = ((k + ahead) % n) / (n - 1)
            for part in (-2, -1, 0, 1, 2):                      # five pixels along the arc, the head first
                v = u - part * 0.07
                if 0.02 < v < 0.98:
                    x, y = x0 + int(round(9 * v)), 6 - int(round(5.5 * math.sin(math.pi * v)))
                    grid[y][x] = 'G' if part == 2 else 'D'
                    if part == 0 and y > 0:
                        grid[y - 1][x] = 'D'                    # the fin
            if u < 0.15:
                grid[6][x0] = 'W'
            if u > 0.85:
                grid[6][x0 + 9] = grid[6][x0 + 10] = 'W'
        frames.append(rows(grid))
    return frames


def aurora(sb):
    """A curtain of light, AURORA['frames'] frames that close into a loop: (the sky's frames, the sea's). Its lower
    edge waves; rays rise from it, taller where the light is strong, solid at their foot, and thin out upward as broken upright
    strokes (each column keeps its pixels in runs of five rows, so the dither is rays and not dots), green below and
    violet above; a few green glints lie on the sea under the strong rays."""
    a = AURORA
    sky, sea = [], []
    for f in range(a['frames']):
        p = 2 * math.pi * f / a['frames']
        grid = blank(a['w'], a['h'])
        for x in range(a['w']):
            near = min(1.0, x / 70) * min(1.0, (a['w'] - x) / 40 + 0.5)             # it thins out toward the wood
            ray = 0.5 + 0.28 * math.sin(x * 0.41 + 3 * p + 0.7) + 0.22 * math.sin(x * 0.15 - 2 * p + 2.0)
            ray = max(0.0, min(1.0, ray)) * near
            base = int(round(64 + 15 * math.sin(x / 55 + 1.0 + p) + 6 * math.sin(x / 23 - 2 * p + 0.5)))
            tall = int(24 + 44 * ray)
            for y in range(max(0, base - tall), min(a['sea'] - 6, base + 1)):
                up = (base - y) / tall
                if base - y < 2 and ray > 0.3:
                    grid[y][x] = 'A'
                elif (up < 0.3 and ray > 0.3) or (1 - up) ** 0.8 * (0.5 + 0.5 * ray) > (sb.jhash(x, y // 5 + 7 * f, 182) % 100) / 100:
                    grid[y][x] = ('A' if ray > 0.6 else 'C') if up < 0.14 else 'C' if up < 0.55 else 'X'
            for y in range(a['sea'] + 2, a['h']):
                if ray > 0.62 and sb.jhash(x // 3, y * 16 + f // 3, 181) % (4 + (y - a['sea']) // 3) == 0:
                    grid[y][x] = 'C'
        sky.append(rows(grid[:a['sea']]))
        sea.append(rows(grid[a['sea']:]))
    return sky, sea


def rainbow():
    """An arc of six bands, each RAINBOW['band'] pixels, every other pixel left open so that the sky shows through."""
    r = RAINBOW
    w, top = r['x1'] - r['x0'] + 1, r['cy'] - r['outer']
    grid = blank(w, r['low'] - top + 1)
    for y in range(top, r['low'] + 1):
        for x in range(r['x0'], r['x1'] + 1):
            k = int((r['outer'] - math.hypot(x - r['cx'], y - r['cy'])) // r['band'])
            if 0 <= k < len(r['letters']) and (x + y) % 2 == 0:
                grid[y - top][x - r['x0']] = r['letters'][k]
    return rows(grid), top


def cycle(frames, order):
    return [frames[c] for c in order]


def sprites(sb):
    """{name: (frames, ticks per frame)}"""
    one = dict(jet_right=JET, jet_left=mirror(JET), satellite=SATELLITE, comet=COMET, santa=SANTA, witch=WITCH,
               airship=AIRSHIP, angels=angels(), container_ship=CONTAINER_SHIP, tug=TUG, tall_ship=TALL_SHIP,
               regatta=regatta(), cruise_ship=CRUISE_SHIP, squid_boat=SQUID_BOAT, sandcastle=SANDCASTLE,
               rainbow=rainbow()[0])
    out = {name: ([grid], 1) for name, grid in one.items()}
    out.update(
        jet_lights=(JET_LIGHTS, 6), ufo=(UFO, 4), geese=(group(GOOSE, GEESE_AT, 24, 12), 5),
        gull=(cycle(GULL, GULL_ORDER), 3), trawler=(trawler(), 8),
        pelicans=(group(cycle(PELICAN, PELICAN_ORDER), PELICANS_AT, 44, 7), 4), dolphins=(dolphins(), 3),
        sea_lion=(cycle(SEA_LION, SEA_LION_ORDER), 48), crab=(CRAB, 2), bonfire=(BONFIRE, 3),
        deer=(cycle(DEER, DEER_ORDER), 40), egret=(cycle(EGRET, EGRET_ORDER), 40), monarch=(MONARCH, 2),
        aurora=(aurora(sb)[0], AURORA['ticks']), aurora_glints=(aurora(sb)[1], AURORA['ticks']))
    return out


# ---------------------------------------------------------------------------------------------------------- the table

SKY, BACK, FRONT = 'surprises_sky', 'surprises_back', 'surprises_front'      # SKY: behind the moon, the stars and the clouds
SUMMER, COLD = ['range', 5, 1, 9, 30], ['range', 11, 1, 2, 29]


def items(sb):
    """One dict for each surprise: name, sprite, slot, at, and the fields the header describes. A salt is a number
    that no other line uses, but for two lines that are one thing in two slots (the aurora and its glints on the sea).
    The tick rate is scene_build's (sb.TICKS_PER_SECOND), its one home."""
    T = sb.TICKS_PER_SECOND
    MIN, HOUR = 60 * T, 3600 * T
    jet = (480 + 28) * 3
    return [
        # the sky by day
        dict(name='jet_right', sprite='jet_right', slot=BACK, at=(-28, 14), states=SUNLIT, every=[20 * MIN, 1, jet, 201],
             move=[1, 3, -1, 90], jitter=[0, 36, 201]),
        dict(name='jet_left', sprite='jet_left', slot=BACK, at=(480, 10), states=SUNLIT, every=[30 * MIN, 1, jet, 202],
             move=[-1, 3, -1, 120], jitter=[0, 30, 202]),
        dict(name='airship', sprite='airship', slot=BACK, at=(-30, 44), states=DAYLIGHT, days=[10, 203, 1, 0],
             every=[HOUR, 1, 510 * 10, 203], move=[1, 10, 0, 1], jitter=[0, 22, 203]),
        dict(name='blue_angels', sprite='angels', slot=BACK, at=(-54, 24), states=['day', 'cloudy'], hours=[12, 16],
             when=[['nth', 10, 0, 2, 2, -1]], every=[10 * MIN, 1, 180, 204], move=[3, 1, 0, 1], jitter=[0, 30, 204]),
        dict(name='geese', sprite='geese', slot=BACK, at=(-26, 30), states=DAYLIGHT, when=[['range', 10, 1, 12, 15], ['range', 2, 1, 3, 31]],
             every=[30 * MIN, 1, 510 * 3, 205], move=[1, 3, -1, 60], jitter=[0, 30, 205]),
        dict(name='gull', sprite='gull', slot=BACK, at=(-6, 70), states=DAYLIGHT, every=[5 * MIN, 2, 1000, 206],
             move=[1, 2, -1, 50], jitter=[0, 24, 206]),
        dict(name='rainbow', sprite='rainbow', slot=BACK, at=(RAINBOW['x0'], rainbow()[1]), states=['cloudy'],
             days=[5, 207, 1, 0], every=[2 * HOUR, 1, 20 * MIN, 207], fade=MIN),
        # the sky by night
        dict(name='jet_lights', sprite='jet_lights', slot=BACK, at=(-4, 14), states=['night'], clear=True,
             every=[20 * MIN, 1, jet, 208], move=[1, 3, -1, 90], jitter=[0, 36, 208]),
        dict(name='satellite', sprite='satellite', slot=BACK, at=(60, 60), states=['night'], clear=True,
             every=[30 * MIN, 2, 1300, 209], move=[1, 3, -1, 30], jitter=[200, 20, 209]),
        dict(name='aurora', sprite='aurora', slot=SKY, at=(AURORA['x'], AURORA['y']), states=['night'], clear=True,
             days=[40, 210, 1, 1], every=[HOUR, 2, 25 * MIN, 210], fade=MIN),
        dict(name='aurora_glints', sprite='aurora_glints', slot=BACK, at=(AURORA['x'], AURORA['y'] + AURORA['sea']),
             states=['night'], clear=True, days=[40, 210, 1, 1], every=[HOUR, 2, 25 * MIN, 210], fade=MIN),
        dict(name='comet', sprite='comet', slot=BACK, at=(236, 44), states=['night'], clear=True, days=[14, 211, 10, 1]),
        dict(name='ufo', sprite='ufo', slot=BACK, at=(300, 48), states=['night'], clear=True, days=[60, 212, 1, 1],
             every=[HOUR, 1, 200, 212], jitter=[120, 24, 212], fade=12),
        dict(name='santa', sprite='santa', slot=BACK, at=(-40, 82), states=['night'], clear=True, hours=[18, 24],
             when=[['range', 12, 24, 12, 24]], every=[10 * MIN, 1, 262, 213], move=[2, 1, -1, 12]),
        dict(name='witch', sprite='witch', slot=BACK, at=(480, 56), states=['night'], clear=True, hours=[18, 24],
             when=[['range', 10, 31, 10, 31]], every=[10 * MIN, 1, 250, 214], move=[-2, 1, 1, 20]),
        # the sea
        dict(name='container_ship', sprite='container_ship', slot=BACK, at=(480, 96), states=DAYLIGHT,
             every=[40 * MIN, 2, 512 * 16, 215], move=[-1, 16, 0, 1]),
        dict(name='trawler', sprite='trawler', slot=BACK, at=(-14, 95), states=DAYLIGHT, every=[HOUR, 2, 494 * 20, 216],
             move=[1, 20, 0, 1]),
        dict(name='tug', sprite='tug', slot=BACK, at=(480, 98), states=DAYLIGHT, days=[3, 217, 1, 0],
             every=[90 * MIN, 1, 510 * 28, 217], move=[-1, 28, 0, 1]),
        dict(name='tall_ship', sprite='tall_ship', slot=BACK, at=(-19, 93), states=DAYLIGHT, days=[15, 218, 1, 0],
             every=[HOUR, 1, 499 * 24, 218], move=[1, 24, 0, 1]),
        dict(name='regatta', sprite='regatta', slot=BACK, at=(-36, 95), states=['day'], hours=[12, 18], when=[SUMMER],
             days=[4, 219, 1, 0], every=[30 * MIN, 1, 516 * 10, 219], move=[1, 10, 0, 1]),
        dict(name='cruise_ship', sprite='cruise_ship', slot=BACK, at=(-28, 96), states=['dusk', 'night'],
             days=[5, 220, 1, 1], every=[2 * HOUR, 1, 508 * 12, 220], move=[1, 12, 0, 1]),
        dict(name='squid_boat', sprite='squid_boat', slot=BACK, at=(480, 98), states=['night'], when=[['range', 10, 1, 3, 31]],
             days=[3, 221, 1, 1], every=[HOUR, 2, 489 * 24, 221], move=[-1, 24, 0, 1]),
        dict(name='pelicans', sprite='pelicans', slot=BACK, at=(480, 104), states=DAYLIGHT, when=[['range', 5, 1, 11, 30]],
             every=[10 * MIN, 2, 524 * 2, 222], move=[-1, 2, 0, 1], jitter=[0, 8, 222]),
        dict(name='dolphins', sprite='dolphins', slot=BACK, at=(262, 120), states=DAYLIGHT, days=[3, 223, 1, 0],
             every=[20 * MIN, 1, 640, 223], move=[1, 3, 0, 1], jitter=[10, 16, 223]),
        dict(name='sea_lion', sprite='sea_lion', slot=FRONT, at=(282, 106), days=[3, 224, 1, 0]),
        # the land
        dict(name='sandcastle', sprite='sandcastle', slot=FRONT, at=(128, 178), when=[SUMMER], days=[6, 225, 1, 0]),
        dict(name='crab', sprite='crab', slot=FRONT, at=(-6, 200), states=DAYLIGHT, every=[15 * MIN, 1, 330, 226],
             move=[1, 3, 2, 9]),
        dict(name='bonfire', sprite='bonfire', slot=FRONT, at=(104, 212), states=['dusk', 'night'], hours=[16, 24],
             when=[['range', 6, 1, 10, 31]], days=[5, 227, 1, 1]),
        dict(name='deer', sprite='deer', slot=FRONT, at=(150, 92), states=['dawn', 'dusk'], days=[4, 228, 1, 0]),
        dict(name='egret', sprite='egret', slot=FRONT, at=(162, 127), states=['dawn', 'day', 'cloudy'], days=[4, 229, 1, 0]),
    ] + [
        dict(name=f'monarch_{k}', sprite='monarch', slot=FRONT, at=(36, 102), states=['day'], when=[COLD],
             every=[(150 + 40 * k) * T, 1, 240, 230 + k], move=[1, 6, -1, 14], jitter=[80, 14, 230 + k], fade=8, ahead=k)
        for k in range(3)
    ]


# The shooting star. Time is cut into slots of slot_ms; in about one slot in one_in (in a shower: its own number) a
# star starts at a moment and a place of `box` that a hash picks, and flies life_ms: `speed` pixels a second (from ..
# to), down by `slope` hundredths of a pixel for each pixel sideways, with a tail of `tail` pixels that shrinks over
# its last fade_ms. levels: the roles of its head, of the three pixels behind it and of the rest of the tail.
METEORS = dict(slot_ms=20000, one_in=15, life_ms=520, fade_ms=160, box=[90, 4, 470, 64], speed=[210, 360],
               slope=[25, 80], tail=12, salt=240, levels=['MOON', 'STAR_B', 'STAR_C'],
               showers=[[1, 3, 1, 4, 3], [4, 21, 4, 22, 4], [8, 11, 8, 13, 2], [10, 20, 10, 21, 4], [11, 16, 11, 17, 4],
                        [12, 13, 12, 14, 2]],
               note='showers: [month, day, month, day, one_in]: the Quadrantids, Lyrids, Perseids, Orionids, Leonids '
                    'and Geminids.')

# The surf that glows: on some late-summer nights the foam is the blue of sea sparkle.
TINTS = [dict(name='glowing_surf', states=['night'], when=[['range', 8, 1, 10, 31]], days=[6, 241, 1, 1],
              roles={'FOAM': '7DF9FF', 'FOAM_BACK': '2FB8E0'})]
