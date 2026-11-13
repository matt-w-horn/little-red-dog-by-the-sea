"""The doghouse in the six lighting states, with the dog standing or in its doorway.

    python3 -I -B dev/house_look.py stand|door [TOOLS [AT_X AT_Y]]

Writes out/states_POSE.png: the left part of the picture, enlarged 3 times. TOOLS is the tools/ to draw
with (default: the add-on's). AT_X AT_Y try another place for the dog in the doorway than house.pose's.
"""
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shot  # noqa: E402

sc = shot.scene_of(sys.argv[2] if len(sys.argv) > 2 else shot.ADDON_TOOLS)
pose = sys.argv[1] if len(sys.argv) > 1 else 'stand'
label = pose
if pose == 'door':           # the belly pose's dog (its first part, with its moves) moved into the doorway
    belly = next(q for q in sc.scene()['dog']['poses'] if q['name'] == 'belly')['parts'][0]
    at = [int(v) for v in sys.argv[3:5]] if len(sys.argv) > 4 else sc.scene()['house']['pose']['parts'][0]['at']
    pose = dict(name='door', parts=[{**belly, 'at': at}])
WHEN = {'day': (13, 'clear'), 'dusk': (17, 'clear'), 'night': (22, 'clear'), 'dawn': (7, 'clear'), 'cloudy': (13, 'cloudy'),
        'rain': (13, 'rain')}
box, k = (0, 130, 200, 270), 3
w, h = (box[2] - box[0]) * k, (box[3] - box[1]) * k
out = Image.new('RGB', (w * 2 + 10, (h + 16) * 3), (20, 20, 20))
d = ImageDraw.Draw(out)
for i, (state, (hour, weather)) in enumerate(WHEN.items()):
    im = sc.render(datetime(2026, 11, 12, hour, 0), weather, 20, state, pose).crop(box).resize((w, h), Image.NEAREST)
    x, y = (i % 2) * (w + 10), (i // 2) * (h + 16)
    d.text((x + 4, y + 2), f'{state}, {label}', fill=(255, 255, 255))
    out.paste(im, (x, y + 16))
out.save(shot.OUT / f'states_{label}.png')
print(shot.OUT / f'states_{label}.png', out.size)
