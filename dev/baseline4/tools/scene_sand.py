"""The sand layers: the speckle, the paw prints and the shade on the dithered sand. scene_build.py calls
layer_sand(roles, beach, sb); sb is the scene_build module.

The rule. A speckle may sit only on plain dry sand (scene_build's `plain`: the sand's own pixels that are SAND in
both paintings), more than LINE['far'] shore units up from the waterline or on the high-water line, and never within
GAP pixels (QUIET_GAP inside the quiet box) of a paw print, the shade under the turf and the cliff, or another speckle.
Each pixel of that sand is a candidate when jhash(x, y, FIELD_SALT) % 100000 is below its rate, and candidates are
tried in order of that hash. The rate is the product of three integer factors:
  - RATE_BY_Y: per 100000 pixels, a ramp from the far end of the beach (y = HORIZON) to the bottom of the frame;
  - the weight of the coarse cell the pixel is in, in quarters: cells are CELL_W x CELL_H, each row of cells shifted
    by CELL_SHIFT so no grid lines up, and a cell's weight is CELL_WEIGHT[jhash(cx, cy, CELL_SALT) % len], at most
    QUIET_CAP inside the quiet box: some cells are empty, some double, so the speckle comes in loose drifts;
  - quiet_percent: QUIET_RATE percent inside the quiet box around the dog (QUIET), climbing back to 100 over
    QUIET_FEATHER pixels outside it.
A speckle that is placed is one pixel, or two side by side, or three (a pair with one pixel under its left or right
end: a 2 x 2 with one corner missing), by jhash(x, y, SIZE_SALT) % 100 against PAIR_BY_Y and TRIPLE_BY_Y (one pixel
only inside the quiet box). Its tone is
by jhash(x, y, TONE_SALT) % 100: shade (SAND_3) mostly, light (SAND_0) for LIGHT_PERCENT, and on the near sand the
third, darker tone grain (SAND_4) for GRAIN_PERCENT. The high-water line (LINE) is kept from today's layer: one try per LINE['every']
pixels of shore, at the pixel of the band with the lowest hash, one pixel toned by the same rule; a try is
skipped when jhash(segment, 0, LINE['salt']) % 100 >= quiet_percent there, so the line thins by the dog too.
"""
import numpy as np

# The sand around the dog that stays quiet: his sprite covers x 189..316, y 165..244, and he also lies down there.
QUIET = dict(x0=172, x1=334, y0=212, y1=256)   # inclusive bounds, scene pixels
QUIET_RATE = 8   # percent of the rate outside the box (the brief's limit is a third); holds the box near 9 per 100x100
QUIET_FEATHER = 14       # outside the box the percent climbs back to 100 over this many pixels, so no edge shows
QUIET_CAP = 4            # the cell weight inside the box is at most this (the plain rate), so no drift lands there
QUIET_GAP = 6            # inside the box a speckle keeps this many pixels from any other

# Rate per 100000 pixels of plain sand, by scene y: (y, rate) stops, linear between them in integer arithmetic.
# The far end of the beach, next to the text, stays sparse; the near sand is as dense as the reference's.
RATE_BY_Y = [(100, 150), (150, 800), (210, 3000), (270, 5400)]
FIELD_SALT = 91          # salt of the per-pixel hash that picks candidates and their order

# Coarse cells that make drifts and bare patches. Weights are in quarters: 0 empty, 4 the plain rate, 8 double.
CELL_W, CELL_H = 23, 13  # cell size in pixels (odd sizes, so cells do not line up with anything else in the scene)
CELL_SHIFT = 9           # each row of cells is shifted right by this many pixels times its row number
CELL_WEIGHT = [0, 0, 2, 4, 8, 10]   # picked by jhash(cx, cy, CELL_SALT) % 6
CELL_SALT = 92

GAP = 2                  # free pixels kept round every speckle, paw print and shade pixel (as today)

# Size of a placed speckle, by h = jhash(x, y, SIZE_SALT) % 100: three pixels when h < TRIPLE_BY_Y at its y, two when
# h < PAIR_BY_Y (which counts the triples too), one otherwise. (y, percent) stops, linear between them like RATE_BY_Y.
PAIR_BY_Y = [(100, 0), (150, 3), (165, 30), (205, 32), (225, 50), (270, 52)]
TRIPLE_BY_Y = [(100, 0), (205, 0), (225, 10), (270, 12)]
SIZE_SALT = 93

# Tone of a speckle, by t = jhash(x, y, TONE_SALT) % 100: SAND_LIGHT when t < LIGHT_PERCENT; the third tone GRAIN
# when t >= 100 - GRAIN_PERCENT and y >= GRAIN_FROM (the near sand only); SAND_SHADE otherwise.
LIGHT_PERCENT = 10
GRAIN_PERCENT = 40
GRAIN_FROM = 150
TONE_SALT = 94
# The loose line along the high-water mark, kept from today's sand layer (scene_build.SAND_MARK's line).
LINE = dict(far=20, near=12, every=9, salt=84)


def by_y(stops, ys):
    """A table of (y, value) stops at each y of an integer array, linear between stops, integer arithmetic."""
    ys = np.asarray(ys)
    out = np.zeros(ys.shape, np.int64)
    for (y0, r0), (y1, r1) in zip(stops, stops[1:]):
        m = (ys >= y0) & (ys <= y1)
        out[m] = r0 + (r1 - r0) * (ys[m] - y0) // (y1 - y0)
    return out


def in_quiet(x, y):
    q = QUIET
    return (x >= q['x0']) & (x <= q['x1']) & (y >= q['y0']) & (y <= q['y1'])


def quiet_percent(x, y):
    """Percent of the rate kept at (x, y): QUIET_RATE in the box, climbing to 100 over QUIET_FEATHER pixels."""
    q = QUIET
    d = np.maximum.reduce([q['x0'] - x, x - q['x1'], q['y0'] - y, y - q['y1'], np.zeros_like(x)])
    return np.minimum(100, QUIET_RATE + (100 - QUIET_RATE) * d // QUIET_FEATHER)


def cell_weight(xs, ys, sb):
    cy = ys // CELL_H
    cx = (xs + cy * CELL_SHIFT) // CELL_W
    w = np.array(CELL_WEIGHT)[sb.jhash(cx, cy, CELL_SALT) % len(CELL_WEIGHT)]
    return np.where(in_quiet(xs, ys), np.minimum(w, QUIET_CAP), w)


def shape(x, y, sb):
    """The pixels of a speckle whose first pixel is (x, y): [(x, y)], a pair, or a pair with one pixel under it."""
    h = sb.jhash(x, y, SIZE_SALT) % 100
    if in_quiet(x, y) or h >= by_y(PAIR_BY_Y, y):
        return [(x, y)]
    if h < by_y(TRIPLE_BY_Y, y):
        return [(x, y), (x + 1, y), (x + h % 2, y + 1)]
    return [(x, y), (x + 1, y)]


def speckles(beach, sb):
    """The speckles, as (pixels, tone) each, tone 'shade', 'light' or 'grain', in the order placed: the line along
    the high-water mark first, then the field."""
    H, W = sb.H, sb.W
    y, x = np.mgrid[0:H, 0:W]
    own = (beach.owner == sb.OWN_SAND) & (beach.bare != sb.K_SEA) & (y >= sb.HORIZON)
    plain = own & (beach.left.base == sb.SAND) & (beach.right.base == sb.SAND)
    taken = own & ~plain                       # paw prints, and the shade under the turf and the cliff
    out = []

    def place(x0, y0, pixels):
        if any(not (0 <= px < W and 0 <= py < H) or not plain[py, px] for px, py in pixels):
            return False
        g = QUIET_GAP if in_quiet(x0, y0) else GAP
        for px, py in pixels:
            if taken[max(0, py - g):py + g + 1, max(0, px - g):px + g + 1].any():
                return False
        for px, py in pixels:
            taken[py, px] = True
        t = sb.jhash(x0, y0, TONE_SALT) % 100
        tone = 'light' if t < LIGHT_PERCENT else 'grain' if t >= 100 - GRAIN_PERCENT and y0 >= GRAIN_FROM else 'shade'
        out.append((pixels, tone))
        return True

    band = plain & (beach.dist >= -LINE['far']) & (beach.dist <= -LINE['near'])
    ys, xs = np.nonzero(band)
    segment = beach.along[ys, xs] // LINE['every']
    h = sb.jhash(xs, ys, LINE['salt'])
    for s in np.unique(segment):
        here = np.nonzero(segment == s)[0]
        order = here[np.argsort(h[here], kind='stable')]
        x0, y0 = int(xs[order[0]]), int(ys[order[0]])
        if sb.jhash(int(s), 0, LINE['salt']) % 100 >= quiet_percent(np.array(x0), np.array(y0)):
            continue                           # by the dog the line thins out like the rest
        for i in order:
            if place(int(xs[i]), int(ys[i]), [(int(xs[i]), int(ys[i]))]):
                break
    line = len(out)

    field = plain & (beach.dist < -LINE['far'])
    rate = by_y(RATE_BY_Y, y) * cell_weight(x, y, sb) // 4
    rate = rate * quiet_percent(x, y) // 100
    h = sb.jhash(x, y, FIELD_SALT) % 100000
    ys, xs = np.nonzero(field & (h < rate))
    for i in np.argsort(h[ys, xs], kind='stable'):
        x0, y0 = int(xs[i]), int(ys[i])
        place(x0, y0, shape(x0, y0, sb))
    print(f'sand speckles: {len(out)} ({line} along the high-water mark, {len(out) - line} on the dry sand)')
    return out


def layer_sand(roles, beach, sb):
    """Returns ({state: file name}, {file name: H x W uint8 array of palette indexes}): for each lighting state all
    the beach: the dithered sand of scene_dither.sand_bases (SAND_0 the lightest .. SAND_4 wet), and on it the paw
    prints and the shade under the turf and the cliff (SAND_3) and the speckle (SAND_0 light, SAND_3 shade, SAND_4
    grain). In rain the sand is wet all over and carries no speckle."""
    bases, ids, sand = sb.scene_dither.sand_bases(roles, beach, sb)
    own = beach.owner == sb.OWN_SAND
    left = np.where(own, beach.left.base, beach.left.sand_only)
    right = np.where(own, beach.right.base, beach.right.sand_only)
    shade = sand & ((left == sb.SAND_SHADE) | (right == sb.SAND_SHADE))
    dark = ids[len(ids) - 1]                     # with five tones: SAND_4; shade is the tone three quarters down
    mid = ids[(3 * (len(ids) - 1) + 2) // 4]
    tone = {'light': ids[0], 'shade': mid, 'grain': dark}
    marks = speckles(beach, sb)

    def make(state):
        img = bases[state].copy()
        img[shade] = dark if state == 'rain' else mid
        if state != 'rain':
            for pixels, t in marks:
                for px, py in pixels:
                    img[py, px] = tone[t]
        return 'sand', img
    return sb.scene_dither.by_state(sb, make)
