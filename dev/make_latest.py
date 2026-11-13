"""The status sheet: every pose of the dog in every lighting state, as the add-on has them, whole frames at real size.

    python3 -I dev/make_latest.py

Writes out/latest.png: one row for each pose of scene.json (and the dog in the doghouse's doorway), one
column for each lighting state. It is 3054 pixels wide, so a viewer that shrinks large pictures shows it reduced:
it says which poses exist and in which light, not what a sprite's cells are.
"""
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import scene  # noqa: E402

SHOTS = [('dawn', datetime(2026, 11, 9, 6, 52), 'clear'), ('day', datetime(2026, 11, 9, 13, 0), 'clear'),
         ('dusk', datetime(2026, 11, 9, 17, 0), 'clear'), ('night', datetime(2026, 11, 24, 23, 0), 'clear'),
         ('cloudy', datetime(2026, 11, 9, 14, 0), 'cloudy'), ('rain', datetime(2026, 11, 9, 8, 23), 'rain')]
W, H, LABEL, SIDE = scene.W, scene.H, 18, 150
FONT = ImageFont.load_default(size=14)


def still_tick(pose):
    """A tick at which the pose's frame equals the frame with every movement left out."""
    name, time, weather = SHOTS[1]
    for tick in range(40, 4000):
        if scene.finished(time, weather, tick, name, (), pose).tobytes() == \
                scene.finished(time, weather, tick, name, ('dog_moves',), pose).tobytes():
            return tick
    raise SystemExit(f'no still tick found for {pose}')


def main():
    sc = scene.scene()
    poses = [p['name'] for p in sc['dog']['poses']] + [sc['house']['pose']['name']]
    sheet = Image.new('RGB', (SIDE + len(SHOTS) * (W + 4), len(poses) * (H + LABEL + 4)), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    for r, pose in enumerate(poses):
        y, tick = r * (H + LABEL + 4), still_tick(pose)
        draw.text((6, y + 6), pose.upper(), fill=(255, 255, 255), font=FONT)
        for c, (state, time, weather) in enumerate(SHOTS):
            x = SIDE + c * (W + 4)
            sheet.paste(scene.render(time, weather, tick, state, pose).convert('RGB'), (x, y))
            draw.text((x + 4, y + H + 2), state, fill=(255, 255, 255), font=FONT)
    out = ROOT / 'out' / 'latest.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f'wrote {out} {sheet.size}: {" ".join(poses)}')


if __name__ == '__main__':
    main()
