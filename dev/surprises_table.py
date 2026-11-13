"""The surprises of scene.json in words: when each can show and how often, on average.

    python3 -I -B dev/surprises_table.py [ART]       (default: the add-on's art/)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
art = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'art'
sp = json.loads((art / 'scene.json').read_text())['specials']
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def span(ticks):
    s = ticks / 8
    return f'{s:.0f} s' if s < 90 else f'{s / 60:.0f} min' if s < 5400 else f'{s / 3600:.1f} h'


def dates(when):
    if when is None:
        return 'all year'
    out = []
    for r in when:
        if r[0] == 'range':
            a, b = f'{r[2]} {MONTHS[r[1] - 1]}', f'{r[4]} {MONTHS[r[3] - 1]}'
            out.append(a if a == b else f'{a} to {b}')
        elif r[0] == 'nth':
            out.append(f'weekday {r[2]} no. {r[3]} of {MONTHS[r[1] - 1]}, {r[4]} before to {r[5]} after')
        else:
            out.append('Easter')
    return ', '.join(out)


def line(i):
    parts = [dates(i['when'])]
    if i['states']:
        parts.append('/'.join(i['states']))
    if i.get('clear'):
        parts.append('clear sky')
    if i.get('hours'):
        parts.append(f'{i["hours"][0]}:00 to {i["hours"][1]}:00')
    if i.get('days'):
        parts.append(f'1 {"night" if i["days"][3] else "day"} in {i["days"][0]}' + (f', {i["days"][2]} in a row' if i['days'][2] > 1 else ''))
    if i.get('every'):
        slot, one_in, length, _ = i['every']
        parts.append(f'about every {span(slot * one_in)}, for {span(length)}')
    else:
        parts.append('there the whole time')
    return f'{i["name"]:16s} ' + '; '.join(parts)


for i in sp['items']:
    if i['slot'].startswith('surprises'):
        print(line(i))
for t in sp['tints']:
    print(line({**t, 'every': None}))
m = sp['meteors']
print(f'{"shooting star":16s} all year; night; clear sky; about every {m["slot_ms"] * m["one_in"] / 60000:.0f} min, for '
      f'{m["life_ms"] / 1000:.2f} s; in a shower every ' + ' / '.join(f'{m["slot_ms"] * s[4] / 1000:.0f} s' for s in m['showers'])
      + ' (' + ', '.join(f'{s[1]} {MONTHS[s[0] - 1]}' for s in m['showers']) + ')')
