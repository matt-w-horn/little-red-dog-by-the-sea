"""The doghouse: a small cottage at the left edge of the sand, cut off by the edge, its doorway at the right end.

It is a grid of letters, drawn in two layers so that the dog can lie in the doorway: house_back (the end wall right
of the doorway, the doorway, the far edge of the roof) is stamped before the dog, house_front (the long wall, the
roof, the end wall left of the doorway) after him. Its shadow is cast as the dog's is (scene.cast_shadow), from
house_cast: the walls and the roof over them as one upright shape that stands on the walls' foot.

Its colours are the hill cottages' own roles, so it changes with the month and the light as they do, and it needs
no role of its own. The long wall faces the viewer and the end wall faces right: the two take the cottages' pair
roles, which swap with the side the light comes from (states.light_from)."""
import numpy as np

AT = (0, 154)            # the grid's top-left corner in the picture
DOOR = 50                # the doorway's first column
WALL_END = 70            # the walls end before this column; right of it only the roof's edge overhangs
COURSE = 6               # rows in a course of shingles
DOOR_POSE = dict(name='door', part_of='belly', at=(-34, 206))
#   In the house the dog lies in the doorway: the first part of the pose part_of (the dog on his belly, with its
#   moves) with its top-left corner at this place in the picture. His body is behind the front layer; his head, his
#   collar and his front paws show.
STAY = dict(look_minutes=[0, 4, 8], out_one_in=6, salt=131)
#   When he is in the house (scene.in_house): a pose slot is 5 minutes, and its pose shows for up to 8. He spends a
#   slot in the house when it rains, or is night, at one of look_minutes after the slot's start: so he goes in before
#   the rain or the dark and comes out after it. On a night without rain he is out in one slot of out_one_in.

# Upper case: the front layer. Lower case: the back layer.
#   R the roof   K, k its edge   E the eave   L the long wall   U its shade under the eave
#   G, g the end wall   h its shade under the roof's edge   i inside the doorway   j the doorway's far jamb
GRID = [
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKk..............',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKk..............',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKK..............',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKk.............',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKK.............',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKk............',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKk............',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKk...........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKk...........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKhhhkkkkk..........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKhhhkkkkk..........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKhhhkkkkk..........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKgghhhkkkkk.........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKgghhhkkkkk.........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKgggghhhkkkkk........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKgggghhhkkkkk........',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggghhhkkkkk.......',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKgggggghhhkkkkk.......',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggggghhhkkkkk......',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggggghhhkkkkk......',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggggggghhhkkkkk......',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKgggggggggghhhkkkkk.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKgggggggggghhhkkkkk.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggggggggghhhkkkkk....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKgggggggggggghhhkkkkk....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggggggggggghhhkkkkk...',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggggggggggghhhkkkkk...',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggggggggggggghhhkkkkk..',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKggggggggggggggghhhkkkkk..',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGgggggggggggggggghhhkkkkk.',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGgggggggggggggggghhhkkkkk.',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGgggggggggggggggghhhkkkkk.',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGggggggggggggggggghhhkkkkk',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGggggggggggggggggghhhkkkkk',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGgggggggggggggggghhhh.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGgggggggggggggggghhhh.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGgggggggggggggggghhhh.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGgggggggggggggggghhhh.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGGgggggggggggggggggggg.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGGgggggggggggggggggggg.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGGgggggggggggggggggggg.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGGGggggggggggggjjgggggg.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGGGggggggggggjjjjgggggg.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGGGggggggggiijjjjgggggg.....',
    'RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRKKKGGGGGGGGggggggiiiijjjjgggggg.....',
    'EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEGGGGGGGGggggiiiiiijjjjgggggg.....',
    'EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEGGGGGGGGggiiiiiiiijjjjgggggg.....',
    'UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'UUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggggg.....',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgggg.......',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjjgg.........',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijjjj...........',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiiijj.............',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiiiii...............',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiiiii.................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiiiii...................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGiiii.....................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGGii.......................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGGGG.........................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGGGG...........................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGGGG.............................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGGGG...............................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGGGG.................................',
    'LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLGG...................................',
]

ROLES = {'R': 'HILL_ROOF_RED__ROOF_RED_DARK', 'D': 'HILL_ROOF_RED_DARK__ROOF_RED', 'K': 'HILL_ROOF_RED_DARK__ROOF_RED',
         'E': 'HILL_ROCK_0', 'L': 'HILL_WALL__WALL_SHADE', 'U': 'HILL_WALL_SHADE', 'G': 'HILL_WALL_SHADE__WALL',
         'H': 'HILL_WALL_SHADE', 'I': 'HILL_ROCK_0', 'F': 'HILL_ROCK_1', 'J': 'HILL_ROCK_3'}
# U and H are the shade a roof throws on the wall under it. They are HILL_WALL_SHADE in every state: on the wall
# toward the light it shows, on the wall away from the light it is the wall's own colour and does not.
# D: short marks on the lowest row of each course of shingles, in the roof's other tone.
# F: the lower part of the inside, lighter where the light reaches in, so the inside is not a black hole.


def letter(ch, x, y, door_top):
    """The letter that names a cell's role: the grid's own, but for the shingle marks and the inside's lower part."""
    if ch == 'R' and y % COURSE == COURSE - 1 and (x + 5 * (y // COURSE)) % 11 < 4:
        return 'D'
    if ch == 'i':
        return 'I' if y < door_top + 16 - (x - DOOR) else 'F'
    return ch.upper()


def layers(roles, size, dog, poses, ticks_per_second):
    """house_back.png and house_front.png, each the whole picture; house_cast.png, the shape that casts the shadow,
    cut to the grid. Returns the files and the entry for scene.json. dog: (x, y) of the dog's place, from which a
    part's at counts; poses: the poses of scene.json, for the one the dog takes in the doorway (left out, with the
    stay, when that pose is not there)."""
    w, h = size
    missing = sorted(set(ROLES.values()) - set(roles.index))
    if missing:
        raise SystemExit(f'the doghouse uses roles the hill no longer has: {" ".join(missing)}')
    width = max(len(row) for row in GRID)
    if any(len(row) != width for row in GRID):
        raise SystemExit('the doghouse grid has rows of different lengths')
    door_top = next(y for y, row in enumerate(GRID) if row[DOOR] == 'i')
    back, front = np.zeros((h, w), np.uint8), np.zeros((h, w), np.uint8)
    cast = np.zeros((len(GRID), width), np.uint8)
    for y, row in enumerate(GRID):
        for x, ch in enumerate(row):
            if ch == '.':
                continue
            index = roles.index[ROLES[letter(ch, x, y, door_top)]]
            (back if ch.islower() else front)[AT[1] + y, AT[0] + x] = index
            if x < WALL_END:
                cast[y, x] = index
    entry = {'cast': {'file': 'layers/house_cast.png', 'at': [AT[0] - dog[0], AT[1] - dog[1]], 'ground': 'outline', 'moves': []},
             'note': 'The doghouse. house_back and house_front are full layers (full_layers), stamped before and '
                     'after the dog. At house_shadow the part cast throws its shadow as a part of a pose does '
                     '(see dog.note), with the dog\'s leans; at is from (dog.x, dog.y) like a part\'s. pose: the dog '
                     'in the doorway, in the format of one of dog.poses; it is no part of their order. stay: he '
                     'spends pose slot s (dog.pose_change) in the house, in pose, when at one of look_minutes '
                     'minutes after the slot\'s first tick (s * hold; its minute of the day is the frame\'s time '
                     'moved by the ticks from that tick to the frame\'s, floor) the weather of that minute is rain; '
                     'or when at one of them the state of that minute and its weather is night and '
                     'hash(s, 2, salt) % out_one_in is not 0 (scene.in_house).'}
    source = next((p for p in poses if p['name'] == DOOR_POSE['part_of']), None)
    if source is None:
        print(f'the dog does not go into the doghouse: no pose {DOOR_POSE["part_of"]}')
    else:
        if 1_000_000 % ticks_per_second:
            raise SystemExit('the doghouse: a tick must be a whole number of microseconds')
        at = [DOOR_POSE['at'][0] - dog[0], DOOR_POSE['at'][1] - dog[1]]
        entry['pose'] = {'name': DOOR_POSE['name'], 'parts': [{**source['parts'][0], 'at': at}]}
        entry['stay'] = STAY
    return {'house_back.png': back, 'house_front.png': front, 'house_cast.png': cast}, entry
