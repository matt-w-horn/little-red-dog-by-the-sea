"""Review pictures of a trial copy of the tools and art beside the add-on as it is and beside the style reference.

    python3 -I -B dev/look.py NAME TOOLS [TICK ...]      TOOLS: the trial copy's tools/ (its art/ beside it)

Writes out/NAME_shore_tTICK.png for each tick (default 20, 60, 110): the shore of the day frame
without the dog, enlarged 3 times: the add-on above, the trial copy below, the style picture's shore beside it (if a file style-ref.jpg is in a folder named ref at the root; left out otherwise);
and NAME_day.png: the whole day frame of the trial copy at its real size over the add-on's.
"""
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot  # noqa: E402

OUT = shot.OUT
WHEN = datetime(2026, 11, 9, 13, 0)
BOX = (150, 96, 480, 270)


def main():
    name = sys.argv[1]
    trial = Path(sys.argv[2])
    ticks = [int(t) for t in sys.argv[3:]] or [20, 60, 110]
    w, h = (BOX[2] - BOX[0]) * 3, (BOX[3] - BOX[1]) * 3
    style = shot.ROOT / 'ref' / 'style-ref.jpg'               # optional: not part of this repository
    ref = Image.open(style).convert('RGB').crop((230, 400, 802, 1020)) if style.exists() else None
    if ref is not None:
        ref = ref.resize((ref.width * h // ref.height, h), Image.LANCZOS)
    for tick in ticks:
        sheet = Image.new('RGB', (w + 10 + (ref.width if ref is not None else 0), 2 * h + 10), (30, 30, 30))
        for row, tools in enumerate((shot.ADDON_TOOLS, trial)):
            f = shot.frame(tools, WHEN, 'clear', 'day', tick)
            sheet.paste(f.crop(BOX).resize((w, h), Image.NEAREST), (0, row * (h + 10)))
        if ref is not None:
            sheet.paste(ref, (w + 10, h + 10))
        sheet.save(OUT / f'{name}_shore_t{tick}.png')
    both = Image.new('RGB', (480, 550), (30, 30, 30))
    both.paste(shot.frame(trial, WHEN, 'clear', 'day', ticks[0], skip=()), (0, 0))
    both.paste(shot.frame(shot.ADDON_TOOLS, WHEN, 'clear', 'day', ticks[0], skip=()), (0, 280))
    both.save(OUT / f'{name}_day.png')
    print('wrote', OUT / f'{name}_shore_t*.png', sheet.size)


main()
