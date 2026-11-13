"""Every special of the year on review sheets, from a copy of the tools (default dev/).

    python3 -I -B dev/holidays.py NAME [TOOLS]

Writes out/NAME_specials_1.png, _2.png ...: one tile for each line of SHOTS, the left part of the
scene (x 20 .. 310, y 50 .. 215) enlarged 3 times, without the dog and the text, eight tiles a sheet; and
NAME_specials_whole.png: the same shots as whole frames at the scene's real size, with the dog and the text.
"""
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot  # noqa: E402

OUT = shot.OUT
BOX = (20, 50, 310, 215)
SHOTS = [  # label, time, weather, state, tick
    ("New Year's Eve, 31 Dec 22:00", datetime(2026, 12, 31, 22, 0), 'clear', 'night', 18),
    ("New Year's Day, 1 Jan", datetime(2026, 1, 1, 13, 0), 'clear', 'day', 20),
    ('January: smoke, driftwood, the whale blows', datetime(2026, 1, 15, 13, 0), 'clear', 'day', 28),
    ('Martin Luther King Jr. Day, 19 Jan', datetime(2026, 1, 19, 13, 0), 'clear', 'day', 20),
    ("Two days before Valentine's Day, 12 Feb", datetime(2026, 2, 12, 13, 0), 'clear', 'day', 20),
    ("Valentine's Day, 14 Feb", datetime(2026, 2, 14, 13, 0), 'clear', 'day', 20),
    ("Presidents' Day, 16 Feb", datetime(2026, 2, 16, 13, 0), 'clear', 'day', 20),
    ('Easter, 5 Apr', datetime(2026, 4, 5, 13, 0), 'clear', 'day', 20),
    ('Memorial Day, 25 May', datetime(2026, 5, 25, 13, 0), 'clear', 'day', 20),
    ('Juneteenth, 19 Jun', datetime(2026, 6, 19, 13, 0), 'clear', 'day', 20),
    ('Pride, last Sunday of June, 28 Jun', datetime(2026, 6, 28, 13, 0), 'clear', 'day', 20),
    ('Two days before Independence Day, 2 Jul', datetime(2026, 7, 2, 13, 0), 'clear', 'day', 20),
    ('Independence Day, 4 Jul', datetime(2026, 7, 4, 13, 0), 'clear', 'day', 20),
    ('Independence Day, 4 Jul 21:30', datetime(2026, 7, 4, 21, 30), 'clear', 'night', 18),
    ('Labor Day, 7 Sep', datetime(2026, 9, 7, 13, 0), 'clear', 'day', 20),
    ("Columbus / Indigenous Peoples' Day, 12 Oct", datetime(2026, 10, 12, 13, 0), 'clear', 'day', 20),
    ('Halloween, 31 Oct', datetime(2026, 10, 31, 13, 0), 'clear', 'day', 20),
    ('Halloween, 31 Oct 20:00', datetime(2026, 10, 31, 20, 0), 'clear', 'night', 20),
    ('Veterans Day, 11 Nov', datetime(2026, 11, 11, 13, 0), 'clear', 'day', 20),
    ('Thanksgiving, 26 Nov', datetime(2026, 11, 26, 13, 0), 'clear', 'day', 20),
    ('1 Dec at night: lights on the houses', datetime(2026, 12, 1, 21, 0), 'clear', 'night', 20),
    ('11 Dec at night: wreaths, lighthouse, tree', datetime(2026, 12, 11, 21, 0), 'clear', 'night', 20),
    ('19 Dec at dusk: pines, string of lights', datetime(2026, 12, 19, 17, 0), 'clear', 'dusk', 20),
    ('19 Dec at night', datetime(2026, 12, 19, 21, 0), 'clear', 'night', 20),
    ('Christmas Eve at night', datetime(2026, 12, 24, 21, 0), 'clear', 'night', 20),
    ('Christmas Day', datetime(2026, 12, 25, 13, 0), 'clear', 'day', 20),
    ('Christmas Day at night, lights in their other frame', datetime(2026, 12, 25, 21, 0), 'clear', 'night', 36),
    ('July: sailboat, fog bank', datetime(2026, 7, 15, 13, 0), 'clear', 'day', 20),
]


def main():
    name = sys.argv[1]
    tools = Path(sys.argv[2]) if len(sys.argv) > 2 else shot.ADDON_TOOLS
    w, h = (BOX[2] - BOX[0]) * 3, (BOX[3] - BOX[1]) * 3
    for page in range(0, len(SHOTS), 8):
        part = SHOTS[page:page + 8]
        sheet = Image.new('RGB', (2 * (w + 10), 4 * (h + 10)), (30, 30, 30))
        for k, (label, when, weather, state, tick) in enumerate(part):
            tile = shot.frame(tools, when, weather, state, tick).crop(BOX).resize((w, h), Image.NEAREST)
            d = ImageDraw.Draw(tile)
            d.rectangle((0, h - 14, 8 + 6 * len(label), h), fill=(0, 0, 0))
            d.text((4, h - 13), label, fill=(255, 255, 255))
            sheet.paste(tile, ((k % 2) * (w + 10), (k // 2) * (h + 10)))
        sheet.crop((0, 0, sheet.width, ((len(part) + 1) // 2) * (h + 10))).save(OUT / f'{name}_specials_{page // 8 + 1}.png')
    whole = Image.new('RGB', (4 * 490, ((len(SHOTS) + 3) // 4) * 280), (30, 30, 30))
    for k, (label, when, weather, state, tick) in enumerate(SHOTS):
        whole.paste(shot.frame(tools, when, weather, state, tick, skip=()), ((k % 4) * 490, (k // 4) * 280))
    whole.save(OUT / f'{name}_specials_whole.png')
    print('wrote', OUT / f'{name}_specials_*.png')


main()
