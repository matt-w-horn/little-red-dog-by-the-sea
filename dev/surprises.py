"""Every surprise on review sheets, from a copy of the tools (default dev/).

    python3 -I -B dev/surprises.py NAME [TOOLS]

Writes out/NAME_surprises_1.png ...: one tile for each surprise at a moment it shows
(scene.special_moment): 120 x 68 pixels of the scene round it, enlarged 4 times, without the dog and the text, twelve
tiles a sheet; a thing wider than that (the aurora, the rainbow, a ship with its wake of sky) gets the whole frame
on NAME_surprises_whole.png, at the scene's real size.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shot  # noqa: E402

OUT = shot.OUT


def main():
    name = sys.argv[1]
    tools = Path(sys.argv[2]) if len(sys.argv) > 2 else shot.ADDON_TOOLS
    sc = shot.scene_of(tools)
    sp = sc.scene()['specials']
    tiles, whole = [], []
    for item in sp['items']:
        if not item['slot'].startswith('surprises'):
            continue
        time, weather, state, tick = sc.special_moment(item)
        img, x, y = sc.special_piece(item, sc.layer(sp['file']), state, weather, time, tick)
        frame = shot.frame(tools, time, weather, state, tick)
        label = f'{item["name"]}  {time:%d %b %H:%M} {state}'
        if img.shape[1] > 110:
            ImageDraw.Draw(frame).text((4, 256), label, fill=(255, 255, 255))
            whole.append(frame)
            continue
        cx, cy = x + img.shape[1] // 2, y + img.shape[0] // 2
        x0, y0 = max(0, min(480 - 120, cx - 60)), max(0, min(270 - 68, cy - 34))
        tile = frame.crop((x0, y0, x0 + 120, y0 + 68)).resize((480, 272), Image.NEAREST)
        d = ImageDraw.Draw(tile)
        d.rectangle((0, 258, 8 + 6 * len(label), 272), fill=(0, 0, 0))
        d.text((4, 259), label, fill=(255, 255, 255))
        tiles.append(tile)
    for page in range(0, len(tiles), 12):
        part = tiles[page:page + 12]
        sheet = Image.new('RGB', (3 * 490, ((len(part) + 2) // 3) * 282), (30, 30, 30))
        for k, t in enumerate(part):
            sheet.paste(t, ((k % 3) * 490, (k // 3) * 282))
        sheet.save(OUT / f'{name}_surprises_{page // 12 + 1}.png')
    sheet = Image.new('RGB', (2 * 490, ((len(whole) + 1) // 2) * 280), (30, 30, 30))
    for k, t in enumerate(whole):
        sheet.paste(t, ((k % 2) * 490, (k // 2) * 280))
    sheet.save(OUT / f'{name}_surprises_whole.png')
    print(f'wrote {len(tiles)} tiles and {len(whole)} whole frames to', OUT / f'{name}_surprises_*.png')


main()
