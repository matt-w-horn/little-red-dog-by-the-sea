"""The headland: the wood, the firs, the grass, the cliff, the houses, the pines and the stack off the point.

scene_build.Painter calls paint_headland(p, sb) for each of its two paintings (p.dir = 1: lit from the left, -1: from
the right). The shapes are the same in both; only the tones differ, so each pixel's role is a pair of tones.

How it is drawn (2026-11-10; before, the wood was flat green with crescent highlights and the cliff three flat shapes):
- The wood is a field of leaf clumps in five greens. A clump is a flattened disc, lit on the side the light comes
  from and from above, darker underneath, its tones broken up by a per-pixel hash so that a clump is a cluster of
  pixels and not a smooth ball. Clumps are drawn from the back to the front over a floor of the darkest green, so the
  gaps between them are dark. Trunks show under the front row.
- Where the clumps lie: CLUMPS holds the lit tops read from a Gemini proposal of this crop on the scene's grid
  (a proposal, never shipped: only these centres and radii
  are used); the rest of the wood is filled from a jittered lattice.
- The grass has three greens: specks of the darker and the lighter one, a dark line under the wood, and a ragged
  lower edge with tufts on the sand.
- The cliff is rock in five browns: irregular blocks, lighter the higher they lie, with darker lower edges. The
  lightest is the lit top of the reference's cliff (its median where the rock is brightest but one): without it a
  reviewer found the cliff "dark and low in contrast with no lit top plane ... a dark smudge in every lighting".
The tones are measured in the style reference (a style reference, not shipped): its wood, grass and rock.
"""
import numpy as np

COLOURS = {
    'LEAF_0': 0x2F4220, 'LEAF_1': 0x3B4F20, 'LEAF_2': 0x4A5F23, 'LEAF_3': 0x5E7527, 'LEAF_4': 0x7A9440,
    'GRASS_0': 0x65732B, 'GRASS_1': 0x778E2F, 'GRASS_2': 0x8FA03C,
    'ROCK_0': 0x5A4033, 'ROCK_1': 0x70503D, 'ROCK_2': 0x8A674D, 'ROCK_3': 0xA0785A, 'ROCK_4': 0xAE8463,
    'WALL': 0xE9D8BC, 'WALL_SHADE': 0xB8A08C,
    'ROOF_RED': 0xA9584C, 'ROOF_RED_DARK': 0x86463E, 'ROOF_BLUE': 0x4E84AC, 'ROOF_BLUE_DARK': 0x3B6588,
    # specks whose colour comes from scene_months.BLOOM; in the base design they are the grass's middle tone
    'FLOWER_YELLOW': 0xF2D24A, 'FLOWER_ORANGE': 0xF08A2C, 'FLOWER_VIOLET': 0x8E6FD0, 'PUMPKIN': 0xE8792A,
}
LEAF = [COLOURS[f'LEAF_{k}'] for k in range(5)]
GRASS = [COLOURS[f'GRASS_{k}'] for k in range(3)]
ROCK = [COLOURS[f'ROCK_{k}'] for k in range(5)]

# Lit tops of leaf clumps read from the proposal: (x, y, radius) in scene pixels, y the clump's centre.
CLUMPS = [(78, 75, 9), (101, 77, 9), (6, 78, 9), (123, 79, 9), (141, 82, 9), (26, 84, 9), (59, 84, 9), (72, 89, 9),
          (109, 92, 9), (132, 92, 6), (91, 93, 9), (127, 94, 7), (11, 95, 6), (5, 96, 6), (29, 103, 9), (90, 105, 6),
          (69, 106, 9), (108, 106, 9), (83, 107, 7), (141, 107, 9), (6, 109, 8), (51, 112, 9)]
WOOD_RIGHT = 147             # no clump centre right of this
LATTICE = dict(dx=11, dy=7, jitter=3, r=(4, 8), keep_from=6, salt=131)    # the fill between the proposal's clumps
# The proposal's clumps are nearly all 9 across ("the canopies are nearly all one size, so the mass reads as a
# repeated pattern", a reviewer): each takes one of these sizes by hash, in percent of its own, so that a few big
# crowns stand among middle and small ones, as in the reference's wood.
CLUMP_SIZES = dict(percent=[70, 85, 100, 100, 130, 150], salt=137)
LEAF_STEPS = [-0.75, -0.35, 0.10, 0.72]      # the lit value above which a pixel takes LEAF_1, _2, _3, _4
LEAF_NOISE = 0.50
FIRS = [(5, 72, 15), (13, 70, 19), (22, 69, 14), (31, 70, 17), (44, 72, 13), (52, 75, 16), (62, 76, 12)]   # x, foot, height
HOUSES = [(70, 120, 'BLUE', True), (182, 102, 'RED', False)]
PINES = [(166, 88), (206, 97)]
LIGHTHOUSE = (236, 103)
CLIFF = [(154, 119), (170, 112), (188, 107), (214, 103), (240, 103), (254, 106), (262, 114), (252, 118), (240, 119),
         (225, 119), (190, 118)]
STACK = [(277, 116), (281, 112), (285, 111), (291, 111), (294, 113), (298, 116)]
FLOWERS = dict(rates=[0, 0, 0, 6, 12, 22, 34], salt=151)    # percent of a cell's grass pixels that flower
PUMPKINS = [(88, 121), (92, 122), (96, 121), (64, 122)]      # top-left of each, 2 x 2
BLOCK = dict(dx=10, dy=5, salt=141)          # the rock's blocks: one point in every 10 x 5 pixels, moved by hash


def noise(sb, x, y, salt):
    """-0.5 .. 0.5 for a pixel."""
    return (sb.jhash(x, y, salt) % 1000) / 1000 - 0.5


def wood_low(x):
    """The row where the wood ends and the grass strip begins, at column x."""
    return 117 - x / 15


def clump_list(sb):
    """Every clump of the wood as (x, y, r): the proposal's, then lattice points with none of those near, each moved
    and sized by hash; only those whose lower edge stays above the grass strip and inside the headland."""
    top = dict(sb.LAND_TOP)
    xs = sorted(top)

    def ridge(x):
        for a, b in zip(xs, xs[1:]):
            if a <= x <= b:
                return top[a] + (top[b] - top[a]) * (x - a) / (b - a)
        return 999

    sizes = CLUMP_SIZES['percent']
    out = [(x, y, max(4, sb.jround(r * sizes[sb.jhash(x, y, CLUMP_SIZES['salt']) % len(sizes)] / 100)))
           for x, y, r in CLUMPS if x <= WOOD_RIGHT]
    lat = LATTICE
    for row, y in enumerate(range(62, 120, lat['dy'])):
        for col, x in enumerate(range(-4 + (row % 2) * lat['dx'] // 2, WOOD_RIGHT + 8, lat['dx'])):
            h = sb.jhash(col + 50, row + 50, lat['salt'])
            cx, cy = x + h % (2 * lat['jitter'] + 1) - lat['jitter'], y + (h >> 4) % (2 * lat['jitter'] + 1) - lat['jitter']
            r = lat['r'][0] + (h >> 8) % (lat['r'][1] - lat['r'][0] + 1)
            if cx > WOOD_RIGHT or cy < ridge(max(0, min(cx, 262))) - 1:
                continue
            if any((cx - u) ** 2 + (cy - v) ** 2 < lat['keep_from'] ** 2 for u, v, _ in out):
                continue
            out.append((cx, cy, r))
    out = [(x, y, r) for x, y, r in out if y + 0.85 * r <= wood_low(x) + 1]
    front, x = [], 3                                       # the front row, right above the grass strip
    while x <= WOOD_RIGHT - 2:
        h = sb.jhash(x, 3, lat['salt'])
        r = 5 + h % 3
        front.append((x, int(wood_low(x) - 0.85 * r - 1 - (h >> 4) % 2), r))
        x += r + 3 + (h >> 8) % 4
    out = [c for c in out if all((c[0] - u) ** 2 + (c[1] - v) ** 2 >= 30 for u, v, _ in front)] + front
    return sorted(out, key=lambda c: (c[1], c[0]))


def leaf_tone(lit):
    return sum(lit > s for s in LEAF_STEPS)


def clump(p, sb, cx, cy, r):
    ry = 0.85 * r
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(cx - r - 1, cx + r + 2):
            nx, ny = (x - cx) / r, (y - cy) / ry
            edge = nx * nx + ny * ny
            if edge > 1 or (edge > 0.8 and sb.jhash(x, y, 132) % 3 == 0):     # a ragged rim
                continue
            lit = -(nx * p.dir * 0.45 + ny * 0.9) + LEAF_NOISE * noise(sb, x, y, 133)
            if ny > 0.55:
                lit -= 0.45                                                   # the underside, over the clump in front
            p.solid(x, y, LEAF[leaf_tone(lit)])


def fir(p, sb, cx, foot, height):
    """A fir behind the wood: tiers that widen toward the foot, the darkest green, with the lit side one tone up and
    a lighter pixel at each tier's lit tip."""
    for k in range(height + 1):
        w = max(0, sb.jround(4 * (1 - k / height) + (1 if k % 4 == 0 else 0)))
        for x in range(cx - w, cx + w + 1):
            side = -(x - cx) * p.dir                                          # > 0 on the lit side
            tone = 1 if side > 0 and w > 0 else 0
            if k % 4 == 0 and side == w and w > 1:
                tone = 2
            p.solid(x, foot - k, LEAF[tone])


def grass(p, sb):
    """The headland as grass: GRASS_1, lighter on the open slope's upper part and in specks, darker in specks."""
    p.poly(sb.LAND_TOP + sb.LAND_FOOT, GRASS[1])
    hill = (p.owner == sb.OWN_HILL)
    ys, xs = np.nonzero(hill)
    for x, y in zip(xs.tolist(), ys.tolist()):
        if p.base[y, x] != GRASS[1]:
            continue
        h = sb.jhash(x, y, 134) % 100
        top = y - first_row(hill, x)                                          # rows below the headland's top edge
        light = top < 3 or (x > 150 and top < 7 + (sb.jhash(x // 5, 0, 135) % 5))
        tone = 2 if (light and h >= 12) or h < 4 else 0 if h >= 94 else 1
        p.solid(x, y, GRASS[tone])


def first_row(mask, x):
    col = mask[:, x]
    return int(np.argmax(col)) if col.any() else 0


def wood(p, sb):
    clumps = clump_list(sb)
    for cx, cy, r in clumps:                               # the floor of the wood: the darkest green wherever a clump
        for y in range(cy - r - 1, cy + r + 2):            # reaches when it is grown by two pixels
            for x in range(cx - r - 2, cx + r + 3):
                if (x - cx) ** 2 + ((y - cy) / 0.85) ** 2 <= (r + 2) ** 2 and y <= wood_low(max(x, 0)) \
                        and 0 <= x < sb.W and p.owner[y, x] == sb.OWN_HILL:
                    p.solid(x, y, LEAF[0])
    for cx, cy, r in clumps:
        clump(p, sb, cx, cy, r)
    leaf = np.isin(p.base, LEAF) & (p.owner == sb.OWN_HILL)     # no grass shows through the wood: a cell of grass
    for y in range(60, 120):                                    # with leaves above it and below it, each within
        for x in range(0, WOOD_RIGHT + 8):                      # eight rows, is floor
            if p.owner[y, x] == sb.OWN_HILL and not leaf[y, x] and p.base[y, x] not in ROCK \
                    and leaf[max(0, y - 8):y, x].any() and leaf[y + 1:y + 9, x].any():
                p.solid(x, y, LEAF[0])
    for cx, cy, r in clumps:                                                  # trunks under the front row
        low = int(wood_low(cx))
        if cy + 0.85 * r < low - 4 or sb.jhash(cx, cy, 137) % 4 == 0:
            continue
        x = cx + sb.jhash(cx, cy, 138) % 3 - 1
        for y in range(int(cy + 0.85 * r) - 1, low + 3):
            if 0 <= x < sb.W and p.base[y, x] not in LEAF[2:]:
                p.solid(x, y, ROCK[1] if p.dir * (sb.jhash(cx, 0, 139) % 2 * 2 - 1) > 0 else ROCK[0])
        for dx in (-1, 0, 1):                                                 # its shade on the grass
            if 0 <= x + dx < sb.W and p.owner[low + 3, x + dx] == sb.OWN_HILL:
                p.solid(x + dx, low + 3, GRASS[0])
    for x in range(0, WOOD_RIGHT):                                            # the wood's shade on the grass strip
        y = int(wood_low(x)) + 1
        if p.owner[y, x] == sb.OWN_HILL and p.base[y, x] in GRASS and sb.jhash(x, 0, 140) % 5:
            p.solid(x, y, GRASS[0])


def ragged_foot(p, sb):
    """The grass's lower edge on the sand: it reaches down 0 to 2 pixels more, in runs, and a few tufts lie on the
    sand below it. Then the sand right under the turf is in shade, as before."""
    for x in range(0, 152):
        y0 = sb.foot_at(x)
        reach = sb.jhash(x // 3, 1, 142) % 3 if sb.jhash(x // 3, 0, 142) % 3 else 0
        for y in range(y0, y0 + reach):
            if p.kind_at(x, y) == sb.K_SOLID and p.owner[y, x] == sb.OWN_SAND:
                p.solid(x, y, GRASS[1] if sb.jhash(x, y, 143) % 3 else GRASS[0])
        if sb.jhash(x, 7, 144) % 47 == 0:                                     # a tuft out on the sand
            ty = y0 + 3 + sb.jhash(x, 8, 144) % 4
            if p.kind_at(x, ty) == sb.K_SOLID and p.owner[ty, x] == sb.OWN_SAND:
                p.solid(x, ty, GRASS[0])
                if p.kind_at(x, ty - 1) == sb.K_SOLID and p.owner[ty - 1, x] == sb.OWN_SAND:
                    p.solid(x, ty - 1, GRASS[2])
    p.layer = sb.OWN_SAND
    for x in range(0, 152):
        for y in range(sb.foot_at(x), sb.foot_at(x) + 5):
            if p.kind_at(x, y) == sb.K_SOLID and p.owner[y, x] == sb.OWN_SAND:
                if p.owner[y - 1, x] == sb.OWN_HILL:
                    p.solid(x, y, sb.SAND_SHADE)
                break
    p.layer = sb.OWN_HILL


def rock(p, sb, shape, lip):
    """Rock in five browns inside the polygon: irregular blocks (each pixel belongs to the nearest of a scatter of
    points, the distance counted 1.7 times in y, so blocks are wider than tall). A block is lighter the higher it
    lies, one tone darker on the side away from the light, and its lower edge and its edge away from the light are a
    tone darker: the cracks. lip: grass along the top edge."""
    before = p.base.copy()
    p.poly(shape, ROCK[1])
    mask = (p.base == ROCK[1]) & (before != ROCK[1])
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    seeds = []
    for row, gy in enumerate(range(y0 - 2, y1 + 4, BLOCK['dy'])):
        for col, gx in enumerate(range(x0 - 5 + (row % 2) * BLOCK['dx'] // 2, x1 + 6, BLOCK['dx'])):
            h = sb.jhash(col + 20, row + 20, BLOCK['salt'])
            seeds.append((gx + h % 7 - 3, gy + (h >> 4) % 3 - 1, (h >> 8) % 100))
    sx, sy = np.array([q[0] for q in seeds]), np.array([q[1] for q in seeds])
    block = np.full((sb.H, sb.W), -1)
    block[ys, xs] = np.argmin((xs[:, None] - sx[None, :]) ** 2 + ((ys[:, None] - sy[None, :]) * 1.7) ** 2, axis=1)
    top = {x: int(np.argmax(mask[:, x])) for x in range(x0, x1 + 1)}
    low = {x: sb.H - 1 - int(np.argmax(mask[::-1, x])) for x in range(x0, x1 + 1)}
    for x, y in zip(xs.tolist(), ys.tolist()):
        b = int(block[y, x])
        t = (seeds[b][1] - top[x]) / max(1, low[x] - top[x])                  # the block's height in the cliff here
        away = (x - (x0 + x1) / 2) / max(1, x1 - x0) * p.dir                  # > 0 on the side away from the light
        v = 4.3 - 2.9 * min(1.0, max(0.0, t)) + (seeds[b][2] - 50) / 110 - 0.8 * max(0.0, away)
        tone = max(0, min(4, int(round(v))))
        beside = block[y, x + p.dir] if 0 <= x + p.dir < sb.W else -1         # the neighbour away from the light
        under = block[y + 1, x] if y + 1 < sb.H else -1
        if (under != b and under >= 0) or (beside != b and beside >= 0 and sb.jhash(x, y, 146) % 3):
            tone = max(0, tone - 1)
        if y == low[x]:
            tone = 0
        p.solid(x, y, ROCK[tone])
    for x in range(x0, x1 + 1):
        if lip:
            p.solid(x, top[x], GRASS[2] if sb.jhash(x, 1, 147) % 4 else GRASS[1])
            if sb.jhash(x, 2, 147) % 3 == 0 and low[x] > top[x] + 1:
                p.solid(x, top[x] + 1, GRASS[0])
        if p.kind_at(x, low[x] + 1) != sb.K_SEA and p.owner[min(low[x] + 1, sb.H - 1), x] == sb.OWN_SAND:
            p.layer = sb.OWN_SAND                                             # the sand right under the rock is in shade
            p.solid(x, low[x] + 1, sb.SAND_SHADE)
            p.layer = sb.OWN_HILL


def house(p, sb, x, ground, roof, wide):
    """A house 12 or 15 wide: walls with the end away from the light in shade, a roof of two tones with a dark eave,
    a chimney, a door, lit windows (the lamps), and a dark line where it meets the grass."""
    w = 15 if wide else 12
    light, dark = COLOURS[f'ROOF_{roof}'], COLOURS[f'ROOF_{roof}_DARK']
    for dx in range(w):
        shade = dx >= w - 4 if p.dir > 0 else dx < 4
        for dy in range(1, 7):
            p.solid(x + dx, ground - dy, COLOURS['WALL_SHADE'] if shade or dy == 6 else COLOURS['WALL'])
        p.solid(x + dx, ground, GRASS[0])
    for row in range(4):
        for dx in range(-1 + row, w - row + 1):
            lit_half = (dx - w / 2) * p.dir < 0
            p.solid(x + dx, ground - 7 - row, dark if row == 0 or (row < 3 and not lit_half) else light)
    for dy in (10, 11, 12):                               # the chimney: on the ridge's right part, two rows above it
        p.solid(x + w - 5, ground - dy, ROCK[2] if p.dir > 0 else ROCK[0])
        p.solid(x + w - 4, ground - dy, ROCK[0] if p.dir > 0 else ROCK[2])
    door = 7 if wide else 5
    for dy in range(1, 4):
        p.solid(x + door, ground - dy, ROCK[0])
    for wx in ([2, 10] if wide else [2]):
        for dy in (3, 4):
            for dx in (0, 1):
                p.solid(x + wx + dx, ground - dy, sb.AQUA)
                p.lamps.append((x + wx + dx, ground - dy))


def pine(p, sb, x, ground):
    """An umbrella pine: a trunk two wide, a flat crown in four greens, lit above on the light's side."""
    for dy in range(7):
        p.solid(x, ground - dy, ROCK[2] if p.dir > 0 else ROCK[0])
        p.solid(x + 1, ground - dy, ROCK[0] if p.dir > 0 else ROCK[2])
    for row in range(6):
        half = 4 if row == 0 else 5 if row == 5 else 6
        for dx in range(-half, half + 2):
            lit = 0.9 - row * 0.4 - dx * p.dir * 0.12 + 0.5 * noise(sb, x + dx, ground - 12 + row, 148)
            p.solid(x + dx, ground - 12 + row, LEAF[leaf_tone(lit)])
    for dx in (-1, 0, 1, 2):
        p.solid(x + dx, ground + 1, GRASS[0])


def lighthouse(p, sb, x, ground):
    """The tower as before, its red bands in the roofs' red."""
    red, red_dark = COLOURS['ROOF_RED'], COLOURS['ROOF_RED_DARK']
    for dy in range(1, 19):
        half = 3 if dy < 7 else 2
        band = 5 <= dy <= 7 or 12 <= dy <= 14
        for dx in range(-half, half + 1):
            lit_side = p.dir * dx >= half - 1
            p.solid(x + dx, ground - dy, (red_dark if band else sb.AQUA) if lit_side else (red if band else sb.PALE))
    for dx in range(-3, 4):
        p.solid(x + dx, ground - 19, sb.SEA)
    for dy in range(20, 23):
        for dx in range(-2, 3):
            p.solid(x + dx, ground - dy, sb.SEA if dx in (-2, 2) else sb.PALE)
    for dx in range(-3, 4):
        p.solid(x + dx, ground - 23, red)
    for dx in range(-1, 2):
        p.solid(x + dx, ground - 24, red)
    p.solid(x, ground - 1, ROCK[0])
    p.solid(x, ground - 2, ROCK[0])
    p.lantern = (x, ground - 21)


def flowers(p, sb):
    """Specks of three flowers on the open grass, in loose drifts: a pixel of plain middle-tone grass becomes a
    flower when its hash is under the rate of the coarse cell it lies in (most cells have none). What a flower
    shows, and in which months, is scene_months.BLOOM's. Pumpkins: four by the blue house."""
    kinds = [COLOURS['FLOWER_YELLOW'], COLOURS['FLOWER_ORANGE'], COLOURS['FLOWER_VIOLET']]
    ys, xs = np.nonzero((p.owner == sb.OWN_HILL) & (p.base == GRASS[1]))
    for x, y in zip(xs.tolist(), ys.tolist()):
        cell = sb.jhash(x // 9, y // 5, FLOWERS['salt'])
        rate = FLOWERS['rates'][cell % len(FLOWERS['rates'])]
        if sb.jhash(x, y, FLOWERS['salt'] + 1) % 100 < rate:
            p.solid(x, y, kinds[(cell >> 5) % 3] if sb.jhash(x, y, FLOWERS['salt'] + 2) % 4 else kinds[(cell >> 9) % 3])
    for x, y in PUMPKINS:
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            p.solid(x + dx, y + dy, COLOURS['PUMPKIN'])


def paint_headland(p, sb):
    p.layer = sb.OWN_HILL
    for f in FIRS:
        fir(p, sb, *f)
    grass(p, sb)
    flowers(p, sb)
    wood(p, sb)
    rock(p, sb, CLIFF, lip=True)
    rock(p, sb, STACK, lip=False)
    for h in HOUSES:
        house(p, sb, *h)
    for t in PINES:
        pine(p, sb, *t)
    ragged_foot(p, sb)
    p.layer = sb.OWN_LH
    lighthouse(p, sb, *LIGHTHOUSE)
    p.layer = sb.OWN_SAND
