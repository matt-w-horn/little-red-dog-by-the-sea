"""The plants through the year on one sheet, from a copy of the tools (default dev/).

    python3 -I -B dev/plants.py NAME [TOOLS]

Writes out/NAME_plants.png: the headland and the top of the beach (x 0 .. 260, y 72 .. 138) on the
15th of each month at 13:00, clear, enlarged 3 times, without the dog and the text; January at the top left, two in
a row. Surprises that happen to show at that tick are in the picture too.
"""
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot  # noqa: E402

OUT = shot.OUT
BOX = (0, 72, 260, 138)
name = sys.argv[1]
tools = Path(sys.argv[2]) if len(sys.argv) > 2 else shot.ADDON_TOOLS
w, h = (BOX[2] - BOX[0]) * 3, (BOX[3] - BOX[1]) * 3
sheet = Image.new('RGB', (2 * (w + 8), 6 * (h + 8)), (30, 30, 30))
for m in range(12):
    tile = shot.frame(tools, datetime(2026, m + 1, 15, 13, 0), 'clear', 'day', 20).crop(BOX).resize((w, h), Image.NEAREST)
    d = ImageDraw.Draw(tile)
    d.rectangle((0, 0, 30, 13), fill=(0, 0, 0))
    d.text((4, 1), shot.scene_of(tools).MONTHS[m], fill=(255, 255, 255))
    sheet.paste(tile, ((m % 2) * (w + 8), (m // 2) * (h + 8)))
sheet.save(OUT / f'{name}_plants.png')
print('wrote', OUT / f'{name}_plants.png', sheet.size)
