"""foam.png: the water's edge and the foam behind it. Scalloped lobes at the edge, broken edge foam of varying width,
and long wavy ribbons of foam that run along the shore behind the edge.

scene_build.py calls layer_foam(roles, beach, sb) in place of its own when this file exists. sb is scene_build.

Units. `d` is beach.dist, the distance from the still waterline in shore units (sea positive, sand negative); one
unit is `scale` pixels, scale = 0.30 at the horizon (y 100) to 1.0 at y 270, as build_shore measures it. `a` is
beach.along, the index of the nearest point of the shore line, about one pixel of shore per step (0..468 in the
water). Every table below is in those units unless it says pixels or ticks.

The wave. A pixel's water edge sits `R` units up the sand from the still waterline; R depends on the shore position
a and the tick. Each wave of WAVES runs up from the resting edge to its own scalloped peak and drains back, then the
water rests until the next. R never exceeds 13.0, today's highest reach, and the wet-edge margin stays 1.6 units, so
the water never reaches sand that today's waves leave dry. Everything is a table over (tick, a) built from integer
hashes, and the tick enters only through (tick + shift) % 152, so frame 151 runs into frame 0 like any other pair.

The ribbons (2026-11-10, evening). Before, the shallows held short straight strokes, most of them level whatever way
the shore ran: beside the style reference they read as stacked dashes. The reference's foam is a few long lines that
follow the shore and undulate, each the mark of an earlier wave. Three Gemini proposals of this shore were made from
the scene's own render and the reference's shore (proposals, never shipped).
From the third, on the scene's grid, come the numbers of RIBBONS: how many lines, how far apart, how thick, how far
and how slowly they swing. The lines themselves are drawn here, as contours of the distance behind the moving edge.
"""
import numpy as np

# ---------------------------------------------------------------------------------------------------------- tables

PEAK = 13.0             # the highest reach in units: today's (3 + 10 * surge at 1); must stay 13.0 or less
REST = 3.0              # the resting edge in units, as today
REST_SCALLOP = (0.0, 2.6)   # at rest the edge falls short of REST by up to this much, as the lobes of LOBES_REST
SHIFT = (1, 4)          # the wave reaches shore point a this many ticks later: (a * 1) // 4, 0..117 ticks over the shore
# The waves of one loop: start tick, ticks rising, ticks draining, height (share of PEAK - REST), lobe salt.
# A big surge (ticks 0..73), 16 still ticks, a smaller surge (90..137), 14 still ticks: not one beat repeated.
WAVES = [(0, 20, 54, 1.0, 101), (90, 14, 34, 0.55, 102)]
# Lobes: the shore is cut into runs of `run` units (from a hash); each run is a tongue that runs up the sand. Its
# middle falls `lift` units short of the top (so tongues of one wave reach different heights), and its reach falls
# along a parabola to the cusps at its two ends, each `cusp` units short of the top. A cusp belongs to both runs
# beside it, so the edge has no step there.
LOBES = dict(run=(18, 42), cusp=(2.5, 6.0), lift=(0.0, 2.0))
LOBES_REST = dict(run=(14, 36), cusp=(0.8, 2.6), lift=(0.0, 0.6), salt=100)
# Foam at the edge: lit runs and gaps alternate along the shore, lengths in units of a (about pixels of shore), from a
# hash. The pattern is fixed along the shore, so a gap travels with the edge as it runs up and falls back, and never
# opens or closes. In a gap no FOAM is drawn at the edge; the wet margin behind it stays.
EDGE_LIT = (6, 26)      # a lit run is 6..26 long
EDGE_GAP = (3, 9)       # a gap is 3..9 long
EDGE_TAPER = (2, 3)     # over its last 2 or 3 pixels at each end a run narrows to 1 pixel (per run end, by hash)
EDGE_SALT = 110
EDGE_EXTRA = (1.6, 3.4)  # per foam run, added to the width: at rest a run is 1.5..3 px wide before rounding
EDGE_MAX = 6            # the widest the edge foam gets, in pixels
# Width of the edge foam in pixels: 1, plus FAT * height * how far the wave is up * the hump of its tongue, plus the
# run's EDGE_EXTRA, at most EDGE_MAX, narrowed to 1 px at the run's ends (EDGE_TAPER): thickest where a lobe pushes
# up the sand. The back of the band is the unrounded reach minus the width, rounded to half units once, so within a rise or a drain it moves one way only and no pixel
# drops out of the band for a single tick (the front, R, is rounded on its own).
FAT = 3.0
WET_EDGE_UNITS = 1.6    # the dark margin of wet sand right behind the water, in units (today's)
# Wet sand: the sand stays wet to the highest reach of the last WET_HOLD ticks, then the wet line falls back
# WET_DRY units a tick.
WET_HOLD, WET_DRY = 40, 0.12
# Foam left on the wet sand: a pixel within BUBBLE_BAND units below the wet line is FOAM_BACK when
# hash(x, y, BUBBLE_SALT) % 1000 < BUBBLE_RATE. The wet line moves down as the sand dries, so each one shows
# once, for the ticks the line takes to pass it.
BUBBLE_BAND, BUBBLE_RATE, BUBBLE_SALT = 2.5, 30, 130
# Ribbons of foam in the shallows. A ribbon is the line where the distance behind the moving edge, in pixels of the
# near shore, equals off + the ribbon's swing at that shore position: one pixel thick, so it steps like a drawn line.
#   off     pixels behind the edge where the shore is near (toward the horizon everything shrinks with the scale)
#   swing   (pixels, shore positions): how far the line swings in and out, and over what length; a second, shorter
#           swing of SWING_2 of that size rides on it. Each ribbon has its own, so two lines pinch and part.
#   scallop (lengths of its arcs in shore positions, their depths in pixels): the line is a row of arcs like the
#           edge of the wave that left it, each bowed toward the sand, with a cusp between two arcs
#   fat     percent of its length where the line is two pixels thick (in runs, by a slow noise)
#   lit, gap  lengths of the drawn runs and of the breaks between them, in shore positions
#   role    FOAM (white) near the edge, FOAM_BACK (pale) farther out
#   follow  share of the edge's run-up that the line follows: the near lines ride with the wave, the far ones less
#   min_scale  the line is drawn only where the scale is at least this: the far lines stay off the far, small shore
#   show    a run shows while its hash is under rest + surge * (how far the water is up * the wave's height), so
#           the shallows fill as a wave runs up and thin out as it falls back
RIBBONS = [
    dict(off=6.0,  swing=(1.6, 38), scallop=((16, 34), (1.5, 4.0)), fat=70, lit=(40, 110), gap=(3, 7),   role='FOAM',      follow=0.95, min_scale=0.0,  show=(1.0, 0.0)),
    dict(off=13.0, swing=(2.2, 47), scallop=((20, 42), (2.0, 5.0)), fat=55, lit=(34, 96),  gap=(4, 10),  role='FOAM',      follow=0.82, min_scale=0.50, show=(0.9, 0.1)),
    dict(off=21.0, swing=(2.8, 58), scallop=((24, 50), (2.5, 6.0)), fat=35, lit=(30, 84),  gap=(5, 14),  role='FOAM_BACK', follow=0.70, min_scale=0.56, show=(0.85, 0.15)),
    dict(off=30.0, swing=(3.2, 69), scallop=((28, 58), (2.5, 6.5)), fat=20, lit=(26, 72),  gap=(7, 18),  role='FOAM_BACK', follow=0.58, min_scale=0.58, show=(0.75, 0.25)),
    dict(off=40.0, swing=(3.6, 81), scallop=((32, 66), (3.0, 7.0)), fat=10, lit=(22, 60),  gap=(9, 24),  role='FOAM_BACK', follow=0.48, min_scale=0.66, show=(0.65, 0.3)),
    dict(off=51.0, swing=(4.0, 94), scallop=((36, 74), (3.0, 7.0)), fat=0,  lit=(16, 48),  gap=(12, 34), role='FOAM_BACK', follow=0.40, min_scale=0.76, show=(0.5, 0.4)),
]
SWING_2 = (0.4, 0.37)   # the second swing: this share of the size, this share of the length
RIBBON_SALT = 160
SEAM = 12               # two neighbouring pixels whose shore positions differ by more than this lie across the bay's
                        # seam (each is nearest to another stretch of shore): no line is drawn between them

# ---------------------------------------------------------------------------------------------------------- helpers

def runs(n, lo_hi, salt, sb, gap=None):
    """Cuts 0..n-1 into runs whose lengths come from a hash. Returns (index of the run, position 0..1 inside it,
    lit) per a. With gap, runs alternate lit / unlit and gap gives the unlit lengths."""
    k = np.zeros(n, np.int64)
    u = np.zeros(n, np.float32)
    lit = np.zeros(n, bool)
    a, i = 0, 0
    while a < n:
        rng = lo_hi if gap is None or i % 2 == 0 else gap
        length = rng[0] + sb.jhash(i, 0, salt) % (rng[1] - rng[0])
        end = min(n, a + length)
        k[a:end] = i
        u[a:end] = (np.arange(a, end) - a + np.float32(0.5)) / np.float32(length)
        lit[a:end] = gap is None or i % 2 == 0
        a, i = end, i + 1
    return k, u, lit


def frac(h, lo, hi):
    """A hash as a value in lo..hi, in steps of 1/1000."""
    return np.float32(lo) + np.float32(hi - lo) * (h % 1001).astype(np.float32) / np.float32(1000)


def lobes(n, p, salt, sb):
    """Shortfall below the tongue tops per a (0 in the middle of the highest tongues) and the hump 0..1 (1 in the
    middle of a tongue, 0 at a cusp)."""
    k, u, _ = runs(n, p['run'], salt, sb)
    hump = np.float32(1) - (np.float32(2) * u - np.float32(1)) ** 2
    cusp = np.where(u < np.float32(0.5), frac(sb.jhash(k, 1, salt), *p['cusp']), frac(sb.jhash(k + 1, 1, salt), *p['cusp']))
    lift = frac(sb.jhash(k, 2, salt), *p['lift'])
    lift = np.minimum(lift, cusp)
    return (lift * hump + cusp * (np.float32(1) - hump)).astype(np.float32), hump.astype(np.float32)


def smooth(x):
    x = np.clip(x, 0, 1).astype(np.float32)
    return x * x * (np.float32(3) - np.float32(2) * x)


def schedule(n, sb):
    """R[tick, a]: the edge's reach in units, rounded to half units as today; fat[tick, a]: extra foam width in
    pixels; raw[tick, a]: the reach before rounding; energy[tick, a]: how far the water is up times the wave's
    height, 0..1."""
    T = sb.TIDE_TICKS
    rest_short, _ = lobes(n, LOBES_REST, LOBES_REST['salt'], sb)
    rest = (np.float32(REST) - np.minimum(rest_short, np.float32(REST_SCALLOP[1]))).astype(np.float32)
    a = np.arange(n)
    q = (np.arange(T)[:, None] + (a[None, :] * SHIFT[0]) // SHIFT[1]) % T          # the tick each a is at
    R = np.broadcast_to(rest, (T, n)).astype(np.float32).copy()
    fat = np.zeros((T, n), np.float32)
    energy = np.zeros((T, n), np.float32)
    for start, rise, drain, height, salt in WAVES:
        short, hump = lobes(n, LOBES, salt, sb)
        top = np.maximum(rest, np.float32(REST) + np.float32(height) * (np.float32(PEAK - REST)) - short)
        s = (q - start) % T
        up = np.where(s < rise, smooth(s.astype(np.float32) / np.float32(rise)),
                      np.where(s < rise + drain, np.float32(1) - smooth((s - rise).astype(np.float32) / np.float32(drain)),
                               np.float32(0))).astype(np.float32)
        R = np.where(up > 0, rest + up * (top - rest), R).astype(np.float32)
        fat = np.maximum(fat, up * hump * np.float32(FAT) * np.float32(height))
        energy = np.maximum(energy, up * np.float32(height))
    raw = np.minimum(R, np.float32(PEAK)).astype(np.float32)
    R = (np.floor(R * np.float32(2) + np.float32(0.5)) / np.float32(2)).astype(np.float32)
    R = np.minimum(R, np.float32(PEAK))
    return R, fat.astype(np.float32), raw, energy


def wet_line(R, sb):
    """hw[tick, a]: how far up the sand is wet: the highest reach of the last 152 ticks, held WET_HOLD ticks, then
    falling WET_DRY units a tick. Taken over one whole loop back, so it is periodic by construction."""
    T = sb.TIDE_TICKS
    hw = R.copy()
    for back in range(1, T):
        hw = np.maximum(hw, np.roll(R, back, axis=0) - np.float32(WET_DRY) * np.float32(max(0, back - WET_HOLD)))
    return hw.astype(np.float32)


def swing(n, size, length, salt, sb):
    """A smooth swing per shore position a, about -size .. size: hash values at every `length` positions, eased
    between them."""
    g = np.arange(n) / np.float64(length)
    i = np.floor(g).astype(np.int64)
    t = g - i
    t = t * t * (3 - 2 * t)
    v0 = (sb.jhash(i, 0, salt) % 2001) / 1000 - 1
    v1 = (sb.jhash(i + 1, 0, salt) % 2001) / 1000 - 1
    return size * (v0 * (1 - t) + v1 * t)


def ribbon_tables(n, sb):
    """Per ribbon: its offset per a (pixels of the near shore), where it is two pixels thick, where it is lit, and
    each a's show threshold 0..1 (one per lit run)."""
    out = []
    for k, r in enumerate(RIBBONS):
        salt = RIBBON_SALT + 10 * k
        size, length = r['swing']
        arcs, _ = lobes(n, dict(run=r['scallop'][0], cusp=r['scallop'][1], lift=(0.0, 1.0)), salt + 4, sb)
        off = r['off'] + swing(n, size, length, salt, sb) + swing(n, size * SWING_2[0], length * SWING_2[1], salt + 1, sb) \
            + arcs - np.float32(sum(r['scallop'][1]) / 4)
        fat = swing(n, 1.0, 23, salt + 2, sb) > 1 - r['fat'] / 50
        run, _, lit = runs(n, r['lit'], salt + 3, sb, r['gap'])
        out.append((off, fat, lit, (sb.jhash(run, 1, salt + 3) % 1000) / 1000))
    return out


def contour(f, a, ok):
    """The pixels of ok where f >= 0 that have a neighbour (left, right, above or below) in ok where f < 0: the line
    f = 0, one pixel thick, with no doubled corner. A neighbour across the bay's seam does not count."""
    out = np.zeros(f.shape, bool)
    inside = ok & (f >= 0)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nf = np.roll(f, (dy, dx), axis=(0, 1))
        na = np.roll(a, (dy, dx), axis=(0, 1))
        nok = np.roll(ok, (dy, dx), axis=(0, 1))
        if dy:
            nok[0 if dy == 1 else -1, :] = False
        else:
            nok[:, 0 if dx == 1 else -1] = False
        out |= inside & nok & (nf < 0) & (np.abs(na - a) <= SEAM)
    return out


def segments(n, sb):
    """The edge foam along the shore: lit (bool per a), extra width (px per a, from the run's hash) and taper (0..1 per
    a: 0 on a run's end pixel, rising to 1 over the run's EDGE_TAPER pixels at that end)."""
    lit = np.zeros(n, bool)
    extra = np.zeros(n, np.float32)
    taper = np.ones(n, np.float32)
    a, i = 0, 0
    while a < n:
        on = i % 2 == 0
        lo, hi = EDGE_LIT if on else EDGE_GAP
        end = min(n, a + lo + sb.jhash(i, 0, EDGE_SALT) % (hi - lo + 1))
        if on:
            lit[a:end] = True
            extra[a:end] = frac(np.int64(sb.jhash(i, 3, EDGE_SALT)), *EDGE_EXTRA)
            pos = np.arange(a, end)
            t0 = EDGE_TAPER[0] + sb.jhash(i, 4, EDGE_SALT) % (EDGE_TAPER[1] - EDGE_TAPER[0] + 1)
            t1 = EDGE_TAPER[0] + sb.jhash(i, 5, EDGE_SALT) % (EDGE_TAPER[1] - EDGE_TAPER[0] + 1)
            taper[a:end] = np.minimum(1, np.minimum((pos - a) / t0, (end - 1 - pos) / t1))
        a, i = end, i + 1
    return lit, extra, taper


# ---------------------------------------------------------------------------------------------------------- the layer

def layer_foam(roles, beach, sb):
    """Returns {'foam.png': (170 * 152) x 480 uint8 array of palette indexes, frames stacked top to bottom}."""
    grade, PALE, WHITE, MAUVE, WET_SAND = sb.grade, sb.PALE, sb.WHITE, sb.MAUVE, sb.WET_SAND
    names = [('WASH', grade, PALE, 'water run up over the sand'), ('FOAM', grade, WHITE, 'foam: the broken edge and the ribbons near it'),
             ('FOAM_BACK', grade, PALE, 'foam: the ribbons farther out, and bubbles left on the wet sand'), ('WET_EDGE', grade, MAUVE, 'dark margin of wet sand right behind the water'),
             ('WET', grade, WET_SAND, 'wet sand the wave left')]
    ids = {n: roles.add(n, sb.each_state(lambda s, c=c: fn(c, s)), use) for n, fn, c, use in names}

    rows = slice(sb.HORIZON, sb.H)
    water = beach.water[rows]
    shore = beach.kind[rows] == sb.K_SHORE
    d = beach.dist[rows]
    a = beach.along[rows].astype(np.int64)
    n = int(a.max()) + 1
    y = np.arange(sb.HORIZON, sb.H)[:, None]
    scale = (np.float32(0.30) + np.float32(0.70) * ((y - sb.HORIZON).astype(np.float32) / np.float32(sb.H - sb.HORIZON)))
    px = (np.float32(1) / np.broadcast_to(scale, d.shape)).astype(np.float32)    # one pixel in units, per pixel

    R, fat, raw, energy = schedule(n, sb)
    hw = wet_line(R, sb)
    yy, xx = np.mgrid[sb.HORIZON:sb.H, 0:sb.W]
    bubble = sb.jhash(xx, yy, BUBBLE_SALT) % 1000 < BUBBLE_RATE
    edge_lit, extra, taper = segments(n, sb)
    lit = edge_lit[a]
    tables = ribbon_tables(n, sb)
    near = np.broadcast_to(scale / np.minimum(np.float32(1), scale / np.float32(0.85)), d.shape)   # units -> pixels of the near shore

    strip = np.zeros(((sb.H - sb.HORIZON) * sb.FOAM_FRAMES, sb.W), np.uint8)
    for f in range(sb.FOAM_FRAMES):
        tick = f * (sb.TIDE_TICKS // sb.FOAM_FRAMES)
        reach = R[tick][a]
        e = (d + reach).astype(np.float32)
        frame = np.zeros(d.shape, np.uint8)
        sand_side = e < 0
        wet = (d + hw[tick][a]).astype(np.float32)
        frame[sand_side & (wet > 0)] = ids['WET']
        frame[sand_side & (wet > 0) & (wet < np.float32(BUBBLE_BAND)) & bubble] = ids['FOAM_BACK']
        frame[sand_side & (e > np.float32(-WET_EDGE_UNITS))] = ids['WET_EDGE']
        frame[~sand_side & shore] = ids['WASH']
        sea = ~sand_side & water
        for r, (off, fat, r_lit, r_show) in zip(RIBBONS, tables):
            g = (d + raw[tick][a] * np.float32(r['follow'])) * near - off[a]
            shown = r_lit[a] & (r_show[a] < r['show'][0] + r['show'][1] * energy[tick][a]) \
                & (np.broadcast_to(scale, d.shape) >= r['min_scale'])
            line = contour(g, a, sea)
            behind = np.zeros_like(line)                  # the pixels right behind the line, for where it is two thick
            behind[1:] |= line[:-1]
            behind[:-1] |= line[1:]
            behind[:, 1:] |= line[:, :-1]
            behind[:, :-1] |= line[:, 1:]
            line |= behind & sea & (g >= 0) & fat[a]
            frame[line & shown] = ids[r['role']]
        full = np.minimum(np.float32(EDGE_MAX), np.float32(1) + fat[tick] + extra)
        width = (np.float32(1) + (full - np.float32(1)) * taper)[a] * px
        back = np.floor((raw[tick][a] - width) * np.float32(2) + np.float32(0.5)) / np.float32(2)
        frame[~sand_side & (d + back < 0) & lit] = ids['FOAM']
        frame[~water] = 0
        strip[f * (sb.H - sb.HORIZON):(f + 1) * (sb.H - sb.HORIZON)] = frame
    return {'foam.png': strip}
