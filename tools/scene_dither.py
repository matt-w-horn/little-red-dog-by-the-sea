"""The gradients of the scene, baked by the build with Floyd-Steinberg dithering: the sky, the sea and the sand.

scene_build.py calls sky_layers, sea_layers and sand_bases (sb is the scene_build module). Each gradient is a field:
a number for every pixel that says where the pixel stands on a ramp of tones (0 = the ramp's first role). fs_levels
turns the field into whole tones by Floyd-Steinberg error diffusion at the scene's own 480 x 270 pixels, so a pixel
is always one of the ramp's roles (the fixed palette) and a stretch between two tones is a scatter of both. The result
is a layer of palette indexes for each lighting state, written once by the build: nothing is dithered while the scene
runs, so the pattern never moves. Sprites and text are not dithered.

A field is given in ramp steps, not in colours: the ramp's tones are neighbours in colour, so the share of the two
tones round a pixel is its place between them. The error is diffused in whole numbers (1/4096 of a step), in a
serpentine scan: left to right on even rows, right to left on odd rows.

How many tones (HOW): the sky 48, the sea 16, the sand 16. With few tones (6, 9 and 5, on the television on
2026-11-10 from 16:48) the dithering was grain: it looked too crisp, especially on the sky. Variants
were built side by side and compared. Flat bands without dithering show as stripes, at dawn and dusk as rings, and on
the sand as blobs, unless there are very many. Dithering between many close tones shows neither grain nor bands: two
neighbouring sky tones of the 48 are about one step of lightness apart.
"""
import os

import numpy as np

SCALE = 4096
# How each gradient becomes whole tones: ('fs', n) Floyd-Steinberg between n tones, ('bands', n) n flat bands with no
# dithering. n tones are taken evenly along the ramp tables below. For a trial the environment may set another choice:
# DOG_GRADIENTS="sky=bands:16,sea=fs:9".
HOW = dict(sky=('fs', 48), sea=('fs', 16), sand=('fs', 16))
for _part in filter(None, os.environ.get('DOG_GRADIENTS', '').split(',')):
    _name, _how = _part.split('=')
    HOW[_name] = (_how.split(':')[0], int(_how.split(':')[1]))

# Sky: SKY_0 at the top .. the last tone at the horizon (or at the glow of dawn and dusk); the tones are taken evenly
# along these six colours (tones).
SKY_DAY = [0x58AEEA, 0x68B9EF, 0x7AC4F3, 0x8ECEF6, 0xA3D8F8, 0xBCE4F9]
# Sea: SEA_0 the palest (shallow) .. the deepest, taken evenly along these nine colours. SEA_BY_DISTANCE is in steps of
# this table of nine: (distance from the waterline in shore units, step):
# right behind the foam a band of darker cyan, then the pale shallows, then deeper with the distance.
SEA_DAY = [0xCFEDEF, 0xA8DADF, 0x81C6CE, 0x66BAD0, 0x4BAED1, 0x439FCB, 0x3B8FC5, 0x357FB8, 0x2E70AA]
SEA_BY_DISTANCE = [(0, 1.6), (2, 3.0), (6, 3.2), (10, 2.0), (16, 0.9), (26, 1.0), (40, 1.8), (58, 2.8), (80, 3.8),
                   (105, 4.8), (135, 5.6), (170, 6.3)]
SEA_FAR = dict(start=105, span=90, top=1.7, low=0.35)   # beyond `start` the sea deepens toward the horizon by up to `top`
SEA_NOISE = dict(cell=(70, 26), amount=0.45, salt=121)  # soft drifts of lighter and deeper water
GLOW_ON_SEA = dict(amount=1.3, width=120, depth=45)    # dawn, dusk: the water under the glow is lighter near the horizon
# Sand: SAND_0 the lightest (dry, sunlit) .. the wet sand, taken evenly along these five colours; the fields below are in
# steps of this table of five.
SAND_DAY = [0xF3D9B4, 0xECCA9D, 0xE4BB8F, 0xD6AC86, 0xC9A27E]
SAND_BASE = 1.0                                         # the plain sand is SAND_1
SAND_PATCH = [dict(cell=(150, 26), amount=1.0, salt=122), dict(cell=(64, 12), amount=0.45, salt=123)]   # long soft streaks
SAND_PATCH_EDGE = 2.2                                   # the streaks' noise is steepened by this much and cut off at
                                                        # -1 and 1: patches with a level middle and a shape, not one haze
SAND_SHEAR = 2.2                                        # the streaks run with the beach: this many pixels sideways a row
# The damp band beside the water, in shore units: `tone` as far as reach - edge up the sand, then back to the dry
# sand over `edge`; the reach swings by `wobble` over `cell` pixels and by wobble_2 over cell_2, so its inner edge
# is uneven, as the reference's.
SAND_DAMP = dict(reach=19, edge=7, tone=3.5, wobble=6, cell=40, wobble_2=3, cell_2=13, salt=124)
SAND_FAR = dict(top=100, low=150, amount=-0.35)         # the far, dry sand is a little lighter
SAND_RAIN = dict(shift=1.3, patch=0.4)                  # in rain all the sand is wet: darker and flatter
# The sand's five tones in rain, set by hand: the graded day tones came out in the dog's own tone (a reader: "the body
# is the same tone as the sand"). Wet sand mirrors the grey sky, lighter and greyer than his coat (9D7051). At night
# the sand had hand-set tones too (7A7080 .. 534D60, lighter and cooler than his coat, for a reader who saw "the legs
# and belly merge into the dark sand"). They were 0.52 of the day sand's brightness, where the night's light leaves
# every other surface at 0.33 to 0.35 of its own, and grey-lilac where the day sand is tan, so it looked as if it
# would be white by day. The night sand now takes its brightness from the night's light, like everything else (0.34 of
# the day's); the dog then stands off it by about the same ratio as by day. The day sand in that light alone (574754
# .. 48353B) looked a little too warm at night; it should be a little greyer, but not as pale as the hand-set sand
# was. Hence SAND_NIGHT: each tone goes `grey` percent of the way to the grey of its own brightness (moonlight takes
# colour away), and its blue is raised to `blue` percent, because in the evening the app warms the whole picture (blue
# to 74 percent, scene_build.EVENING) and a grey would come out brown.
SAND_NIGHT = dict(grey=75, blue=115)
SAND_STATE = {
    'rain': [0xCDBFAF, 0xC4B5A5, 0xBBAB9B, 0xB1A192, 0xA69688],
}


def night_sand(c):
    """A sand colour already in the night's light, greyed and cooled by SAND_NIGHT (whole numbers)."""
    r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
    lum, p = (2126 * r + 7152 * g + 722 * b + 5000) // 10000, SAND_NIGHT['grey']
    r, g, b = ((v * (100 - p) + lum * p + 50) // 100 for v in (r, g, b))
    return (r << 16) | (g << 8) | min(255, b * SAND_NIGHT['blue'] // 100)


def fs_levels(field, mask, levels):
    """Floyd-Steinberg error diffusion of field (H x W, in ramp steps) to whole steps 0 .. levels - 1, for the pixels
    of mask. The error of a pixel goes to its four unvisited neighbours in parts of 7, 3, 5 and 1 sixteenths; a part
    whose neighbour is outside the mask or the picture is dropped. Returns an H x W int array, 0 outside the mask."""
    h, w = field.shape
    val = [[int(round(v * SCALE)) for v in row] for row in field.tolist()]
    inside = mask.tolist()
    out = [[0] * w for _ in range(h)]
    half = SCALE // 2
    for y in range(h):
        row, m_row, o_row = val[y], inside[y], out[y]
        below, m_below = (val[y + 1], inside[y + 1]) if y + 1 < h else (None, None)
        step = 1 if y % 2 == 0 else -1
        for x in (range(w) if step == 1 else range(w - 1, -1, -1)):
            if not m_row[x]:
                continue
            v = row[x]
            q = (v + half) // SCALE
            q = 0 if q < 0 else levels - 1 if q >= levels else q
            o_row[x] = q
            e = v - q * SCALE
            if e == 0:
                continue
            e7, e3, e5 = e * 7 // 16, e * 3 // 16, e * 5 // 16
            ahead, behind = x + step, x - step
            if 0 <= ahead < w and m_row[ahead]:
                row[ahead] += e7
            if below is not None:
                if 0 <= behind < w and m_below[behind]:
                    below[behind] += e3
                if m_below[x]:
                    below[x] += e5
                if 0 <= ahead < w and m_below[ahead]:
                    below[ahead] += e - e7 - e3 - e5
    return np.array(out, np.int64)


def tones(ramp, n):
    """n colours taken evenly along a ramp of colours (the ramp itself when n is its length)."""
    out = []
    for k in range(n):
        t = k * (len(ramp) - 1) / max(1, n - 1)
        i = min(int(t), len(ramp) - 2)
        f = t - i
        out.append(sum(int(((ramp[i] >> sh) & 255) * (1 - f) + ((ramp[i + 1] >> sh) & 255) * f + 0.5) << sh
                       for sh in (16, 8, 0)))
    return out


def levels(name, field, mask, steps):
    """The field (in steps of the ramp table, 0 .. steps - 1) as whole tones 0 .. n - 1, by HOW[name]."""
    how, n = HOW[name]
    field = field * (n - 1) / (steps - 1)
    if how == 'fs':
        return fs_levels(field, mask, n)
    return np.where(mask, np.clip(np.floor(field + 0.5), 0, n - 1), 0).astype(np.int64)


def value_noise(sb, cell, salt, shear=0.0):
    """Smooth noise in -1 .. 1 over the frame: hash values on a lattice of cell[0] x cell[1] pixels, eased between
    the lattice points. shear slides each row sideways by shear pixels a row, so the patches lie along the beach."""
    y, x = np.mgrid[0:sb.H, 0:sb.W].astype(float)
    gx, gy = (x + shear * y) / cell[0] + 64, y / cell[1] + 64
    x0, y0 = np.floor(gx).astype(np.int64), np.floor(gy).astype(np.int64)
    fx, fy = gx - x0, gy - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)

    def lattice(ix, iy):
        return (sb.jhash(ix, iy, salt) % 2048) / 1023.5 - 1

    top = lattice(x0, y0) * (1 - fx) + lattice(x0 + 1, y0) * fx
    low = lattice(x0, y0 + 1) * (1 - fx) + lattice(x0 + 1, y0 + 1) * fx
    return top * (1 - fy) + low * fy


def by_state(sb, make):
    """{state: file name}, {file name: image}: make(state) for every lighting state; states whose images are equal
    share the first one's file."""
    names, files = {}, {}
    for state in sb.STATES:
        kind, img = make(state)
        same = next((n for n, other in files.items() if n.startswith(kind) and np.array_equal(other, img)), None)
        if same is None:
            same = f'{kind}_{state}.png'
            files[same] = img
        names[state] = same
    return names, files


def ramp_roles(sb, roles, prefix, day, what, colour=None, kind='land'):
    """Registers the ramp's roles prefix_0 .. and returns their indexes. A tone's colour in a state and month is
    colour(k, state, month), by default the day tone lit for that state and month (sb.lit; kind names the thing for
    the month's change)."""
    colour = colour or (lambda k, state, month: sb.lit(day[k], state, month, kind))
    return np.array([roles.add(f'{prefix}_{k}', lambda s, m, k=k: colour(k, s, m), f'{what}, tone {k} of 0 .. {len(day) - 1}',
                               keep=False) for k in range(len(day))], np.uint8)


def sky_layers(roles, sb):
    """The sky of each state: rows 0 .. HORIZON - 1, SKY_0 at the top to SKY_5 at the horizon; at dawn and dusk the
    tones are pulled up round the glow (sb.sky_field)."""
    n = HOW['sky'][1]
    ids = ramp_roles(sb, roles, 'SKY', tones(SKY_DAY, n), 'sky, from the top to the horizon or the glow',
                     lambda k, s, m: sb.sky_tone(k, n, s, m))
    mask = np.zeros((sb.H, sb.W), bool)
    mask[:sb.HORIZON] = True

    def make(state):
        field = np.zeros((sb.H, sb.W))
        field[:sb.HORIZON] = (len(SKY_DAY) - 1) * sb.sky_field(sb.GLOW_X.get(state))
        img = np.zeros((sb.H, sb.W), np.uint8)
        img[mask] = ids[levels('sky', field, mask, len(SKY_DAY))[mask]]
        return 'sky', img
    return by_state(sb, make)


def sea_field(beach, sb, state):
    d = np.maximum(beach.dist, 0).astype(float)
    xs, tones = zip(*SEA_BY_DISTANCE)
    field = np.interp(d, xs, tones)
    y, x = np.mgrid[0:sb.H, 0:sb.W].astype(float)
    f = SEA_FAR
    far = np.clip((d - f['start']) / f['span'], 0, 1)
    height = 1 - np.clip((y - sb.HORIZON) / (sb.H - sb.HORIZON), 0, 1)        # 1 at the horizon, 0 at the bottom
    field += far * f['top'] * (f['low'] + (1 - f['low']) * height)
    n = SEA_NOISE
    field += n['amount'] * value_noise(sb, n['cell'], n['salt'], 0.6) * np.clip((d - 20) / 30, 0, 1)
    gx = sb.GLOW_X.get(state)
    if gx is not None:
        g = GLOW_ON_SEA
        field -= g['amount'] * np.exp(-((x - gx) / g['width']) ** 2) * np.exp(-(y - sb.HORIZON) / g['depth']) \
            * np.clip((d - 10) / 20, 0, 1)
    return np.clip(field, 0, len(SEA_DAY) - 1)


def sea_layers(roles, beach, sb):
    """The still sea of each state: SEA_0 (the palest shallows) .. SEA_8 (the deepest), by the distance from the
    waterline, with a band of darker cyan right behind the foam."""
    ids = ramp_roles(sb, roles, 'SEA', tones(SEA_DAY, HOW['sea'][1]), 'sea, from the pale shallows to the deep', kind='sea')
    mask = beach.bare == sb.K_SEA

    def make(state):
        img = np.zeros((sb.H, sb.W), np.uint8)
        img[mask] = ids[levels('sea', sea_field(beach, sb, state), mask, len(SEA_DAY))[mask]]
        return 'sea', img
    return by_state(sb, make)


def sand_field(beach, sb, state):
    y, x = np.mgrid[0:sb.H, 0:sb.W].astype(float)
    up = np.maximum(-beach.dist, 0).astype(float)             # shore units up the sand from the waterline
    patches = sum(p['amount'] * np.clip(SAND_PATCH_EDGE * value_noise(sb, p['cell'], p['salt'], SAND_SHEAR), -1, 1)
                  for p in SAND_PATCH)
    rain = state == 'rain'
    field = SAND_BASE + patches * (SAND_RAIN['patch'] if rain else 1.0)
    far = SAND_FAR
    field += far['amount'] * np.clip((far['low'] - y) / (far['low'] - far['top']), 0, 1)
    damp = SAND_DAMP
    reach = damp['reach'] + damp['wobble'] * value_noise(sb, (damp['cell'], damp['cell']), damp['salt']) \
        + damp['wobble_2'] * value_noise(sb, (damp['cell_2'], damp['cell_2']), damp['salt'] + 1)
    wet = np.clip((reach - up) / damp['edge'], 0, 1)
    wet = wet * wet * (3 - 2 * wet)
    field = field * (1 - wet) + damp['tone'] * wet
    if rain:
        field += SAND_RAIN['shift']
    return np.clip(field, 0, len(SAND_DAY) - 1)


def sand_bases(roles, beach, sb):
    """The sand of each state before its marks: SAND_0 (the lightest) .. SAND_4 (wet), broad soft patches and a damp
    band beside the water. Returns ({state: image}, the roles' indexes); scene_sand puts the marks on."""
    n = HOW['sand'][1]
    day = tones(SAND_DAY, n)

    def colour(k, state, month):
        if state in SAND_STATE:                 # set by hand: the dog must stand out from the sand (see SAND_STATE)
            c = tones(SAND_STATE[state], n)[k]
            return sb.scene_months.tint(c, month, 'land') if month else c
        c = sb.lit(day[k], state, month, 'sand')
        return night_sand(c) if state == 'night' else c
    ids = ramp_roles(sb, roles, 'SAND', day, 'sand, from the lightest to the wet', colour)
    mask = (beach.bare != sb.K_SEA) & (np.arange(sb.H)[:, None] >= sb.HORIZON)
    out = {}
    for state in sb.STATES:
        img = np.zeros((sb.H, sb.W), np.uint8)
        img[mask] = ids[levels('sand', sand_field(beach, sb, state), mask, len(SAND_DAY))[mask]]
        out[state] = img
    return out, ids, mask
