"""Plants that come and go with the year: flowers in spring, and something growing in every month.

Flowers in the spring, and some other plant life throughout the year.

scene_specials.layer_specials puts these sprites on the sheet and these items into scene.json beside the holidays':
each is a holiday-like item with date rules, drawn at `specials_front` (on the land, under the dog). A plant is a
small stamp (a grid of letters, the colours of tools/scene_specials.py) set at several spots; a spot is the pixel
its foot stands on. Most plants come in two steps, as December's lights do: every other spot for the whole of its
time (`all`), and the spots between them only in the middle of it (`full`), so that a bloom begins thin, fills and
thins again. Nothing here moves.

The year on this coast, by what shows:
    January    calla lilies, toyon berries, mushrooms under the wood, red-hot pokers by the lighthouse
    February   wild mustard, plum blossom on two trees of the wood, callas, mushrooms, pokers
    March      poppies, mustard, plum blossom, callas
    April      poppies, lupine, callas, ice plant in flower on the cliff
    May        lupine, poppies, ice plant, bougainvillea on the red house
    June       ice plant, agapanthus by the red house, bougainvillea
    July       sunflowers by the blue house, agapanthus, bougainvillea
    August     sunflowers, pampas grass in plume, bougainvillea
    September  sunflowers, pampas grass, bougainvillea
    October    pampas grass, bougainvillea (and the pumpkins of tools/scene_land.py)
    November   pampas grass, toyon berries
    December   toyon berries, mushrooms, pokers
    all year   tufts of dune grass on the sand's upper edge, an agave on the cliff
(The specks of flowers in the grass, by month, are the palette's: tools/scene_months.py, BLOOM.)
"""
ALL_YEAR = ['range', 1, 1, 12, 31]

# name: the stamps (spot k takes stamp k modulo their number), the spots, when every other spot shows, when the rest
PLANTS = {
    'mustard': dict(stamps=[['Y', 'Y', 'L'], ['YY', 'Y.', 'L.'], ['.Y', 'YY', '.L']],
                    spots=[(157, 100), (27, 121), (168, 94), (52, 120), (178, 98), (117, 114), (199, 97), (142, 112), (212, 100), (215, 101)],
                    all=['range', 2, 1, 4, 15], full=['range', 2, 15, 3, 31]),
    'poppies': dict(stamps=[['OO', 'L.'], ['O', 'L'], ['OO', '.L'], ['.O.', 'OLO', '.L.']],
                    spots=[(8, 126), (153, 108), (21, 127), (33, 125), (162, 106), (46, 124), (59, 123), (175, 104), (97, 121),
                           (110, 119), (203, 101), (123, 118), (136, 117), (147, 115)],
                    all=['range', 3, 1, 5, 31], full=['range', 3, 20, 5, 10]),
    'lupine': dict(stamps=[['U', 'V', 'V', 'L'], ['U', 'V', 'L'], ['.U', 'UV', 'VV', '.L']],
                   spots=[(160, 102), (14, 122), (171, 99), (40, 119), (196, 104), (90, 117), (217, 102), (103, 115), (130, 113)],
                   all=['range', 4, 1, 6, 10], full=['range', 4, 15, 5, 25]),
    'calla': dict(stamps=[['.W', 'WY', 'T.', 'TT'], ['W.', 'YW', '.T', 'TT']],
                  spots=[(65, 122), (86, 121), (67, 120), (88, 123)],
                  all=['range', 1, 15, 4, 30], full=['range', 2, 1, 4, 10]),
    'agapanthus': dict(stamps=[['.U.', 'UVU', '.L.', '.L.', 'TLT'], ['.V.', 'VUV', '.L.', 'TLT']],
                       spots=[(176, 103), (197, 104), (179, 102)],
                       all=['range', 6, 1, 8, 31], full=['range', 6, 15, 8, 15]),
    'sunflowers': dict(stamps=[['.Y.', 'YDY', '.Y.', '.L.', 'LL.', '.L.', '.L.'], ['.Y.', 'YDY', '.Y.', '.L.', '.LL', '.L.']],
                       spots=[(87, 121), (93, 122), (90, 121)],
                       all=['range', 7, 1, 9, 20], full=['range', 7, 15, 9, 5]),
    'pampas': dict(stamps=[['..W..', '.WWW.', '.WGW.', '..L..', '.LLL.', 'LLTLL'], ['.W...', '.WW.W', '.GWWW', '..LL.', '.LLL.', 'LLTLL']],
                   spots=[(160, 104), (219, 102), (200, 100)],
                   all=['range', 8, 15, 11, 30], full=['range', 9, 1, 11, 15]),
    'toyon': dict(stamps=[['.TTT.', 'TRTTR', 'TTRTT', '.TTR.'], ['.TT..', 'TTRT.', 'RTTTR', '.TRT.']],
                  spots=[(112, 118), (32, 123)],
                  all=['range', 11, 15, 1, 31], full=['range', 12, 1, 1, 15]),
    'mushrooms': dict(stamps=[['.R.', 'RWR', '.W.'], ['RR', 'WW']],
                      spots=[(18, 119), (126, 112), (44, 117), (47, 118)],
                      all=['range', 12, 1, 2, 15], full=['range', 12, 15, 2, 1]),
    'pokers': dict(stamps=[['O.O', 'OYO', 'Y.Y', 'LLL']], spots=[(229, 102)], all=['range', 12, 15, 2, 28], full=None),
    'bougainvillea': dict(stamps=[['.PP.', 'PPRP', 'TPPP', '.PPT', '..P.', '..P.']], spots=[(192, 100)],
                          all=['range', 5, 15, 10, 15], full=None),
    'agave': dict(stamps=[['T.T.T', '.TLT.', 'TTLTT']], spots=[(223, 102)], all=ALL_YEAR, full=None),
}
# The ice plant: a mat along the cliff's upper edge, green all year, in flower from mid April to mid July. Each mat:
# the x of its left end, its row (None: on the sand, three rows under the grass's foot there) and its length. Two
# mats on the sand under the grass's right end were tried and taken out: dark green runs on pale sand, like worms.
ICE_PLANT = dict(mats=[(214, 103, 17)], flowers=['range', 4, 15, 7, 15], salt=191)
# Dune grass: tufts on the sand's upper edge, each this many rows under the grass's foot at its x.
DUNE_GRASS = dict(stamps=[['L.L.', '.LTL', 'TLTT'], ['.L.L', 'LTL.', 'TTLT'], ['L..L', '.LL.', 'TLTL']],
                  spots=[(12, 4), (34, 3), (58, 5), (83, 3), (109, 4), (131, 6), (148, 5)])
# Plum blossom: pink and white specks on the two crowns of the wood's front row nearest these x.
BLOSSOM = dict(near=[38, 118], when=['range', 2, 10, 3, 20], full=['range', 2, 20, 3, 10], salt=192)


def stamped(stamps, spots, pick):
    """A grid with stamp k at spot k for the spots that pick(k) keeps, and the (x, y) of its top-left pixel. A stamp's
    foot is the middle of its lowest row."""
    cells = {}
    for k, (x, y) in enumerate(spots):
        if not pick(k):
            continue
        stamp = stamps[k % len(stamps)]
        for gy, row in enumerate(stamp):
            for gx, c in enumerate(row):
                if c != '.':
                    cells[x - len(row) // 2 + gx, y - len(stamp) + 1 + gy] = c
    x0, y0 = min(x for x, _ in cells), min(y for _, y in cells)
    grid = [['.'] * (max(x for x, _ in cells) - x0 + 1) for _ in range(max(y for _, y in cells) - y0 + 1)]
    for (x, y), c in cells.items():
        grid[y - y0][x - x0] = c
    return [''.join(r) for r in grid], (x0, y0)


def ice_plant(sb, flowers):
    """The mats' leaves (flowers False) or only their flowers (True), as one grid, and its top-left pixel."""
    cells = {}
    for x0, row, length in ICE_PLANT['mats']:
        for k in range(length):
            x = x0 + k
            y = row if row is not None else sb.foot_at(x) + 3
            h = sb.jhash(x, 0, ICE_PLANT['salt'])
            if flowers:
                if h % 3 == 0:
                    cells[x, y - (h >> 4) % 2] = 'P'
            else:
                cells[x, y] = 'T' if h % 5 else 'L'
                if 0 < k < length - 1 and (h >> 8) % 2:
                    cells[x, y - 1] = 'T'
    return stamped([[c] for c in cells.values()], list(cells), lambda k: True)


def blossom(sb, pick):
    """Specks on two crowns of the wood's front row: about one pixel in four of each crown's upper part."""
    front = [c for c in sb.scene_land.clump_list(sb) if c[1] + 0.85 * c[2] >= sb.scene_land.wood_low(c[0]) - 4]
    cells = {}
    for n, near in enumerate(BLOSSOM['near']):
        cx, cy, r = min(front, key=lambda c: abs(c[0] - near))
        for y in range(cy - r, cy + 2):
            for x in range(cx - r, cx + r + 1):
                h = sb.jhash(x, y, BLOSSOM['salt'])
                if (x - cx) ** 2 + ((y - cy) / 0.85) ** 2 <= (r - 1) ** 2 and h % 4 == 0 and pick((h >> 4) % 2):
                    cells[x, y] = 'W' if (h >> 8) % 3 == 0 else 'P'
    return stamped([[c] for c in cells.values()], list(cells), lambda k: True)


def build(sb):
    """({sprite name: grid}, [item dicts]) for every plant."""
    sprites, items = {}, []

    def add(name, made, when):
        grid, at = made
        sprites[name] = grid
        items.append(dict(name=name, sprite=name, slot='specials_front', at=at, when=[when]))

    for name, p in PLANTS.items():
        if p['full']:
            add(name, stamped(p['stamps'], p['spots'], lambda k: k % 2 == 0), p['all'])
            add(name + '_more', stamped(p['stamps'], p['spots'], lambda k: k % 2 == 1), p['full'])
        else:
            add(name, stamped(p['stamps'], p['spots'], lambda k: True), p['all'])
    add('ice_plant', ice_plant(sb, False), ALL_YEAR)
    add('ice_plant_flowers', ice_plant(sb, True), ICE_PLANT['flowers'])
    add('dune_grass', stamped(DUNE_GRASS['stamps'], [(x, sb.foot_at(x) + under) for x, under in DUNE_GRASS['spots']],
                              lambda k: True), ALL_YEAR)
    add('blossom', blossom(sb, lambda bit: bit == 0), BLOSSOM['when'])
    add('blossom_more', blossom(sb, lambda bit: bit == 1), BLOSSOM['full'])
    return sprites, items
