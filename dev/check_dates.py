"""The date rules of scene.special_on against the system's own calendar, for every day of 2024 to 2060.

    python3 -I -B dev/check_dates.py [TOOLS]       (default: the add-on's tools/)

What it compares:
- ['nth', month, weekday, n, 0, 0] with a count of that weekday through the month made with datetime.date;
- ['range', ...] with a comparison of dates made with datetime.date, also for a range that runs over the year's end;
- ['easter', 0, 0] with Gauss's rule for the Gregorian calendar (another formula than scene.easter's) and with
  thirteen Easter dates written out below;
- a margin (before, after) with datetime.timedelta.
It fails on the first difference. Controls: a rule moved by one day, and a wrong Easter, must each be reported.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / 'tools'))
import scene  # noqa: E402

KNOWN_EASTER = ['2024-03-31', '2025-04-20', '2026-04-05', '2027-03-28', '2028-04-16', '2029-04-01', '2030-04-21',
                '2031-04-13', '2032-03-28', '2033-04-17', '2034-04-09', '2035-03-25', '2038-04-25']


def gauss_easter(year):
    a, b, c = year % 19, year % 4, year % 7
    k = year // 100
    p, q = (13 + 8 * k) // 25, k // 4
    m, n = (15 - p + k - q) % 30, (4 + k - q) % 7
    d = (19 * a + m) % 30
    e = (2 * b + 4 * c + 6 * d + n) % 7
    day = 22 + d + e
    if d == 29 and e == 6:
        day -= 7
    if d == 28 and e == 6 and (11 * m + 11) % 30 < 19:
        day -= 7
    return date(year, 3, 1) + timedelta(days=day - 1)


def nth_weekday(year, month, weekday, n):
    days = [date(year, month, d) for d in range(1, scene.days_in_month(year, month) + 1)]
    hits = [d for d in days if d.weekday() == weekday]
    return hits[n - 1] if n > 0 else hits[-1]


def expected(rule, day):
    if rule[0] == 'range':
        first, last = (rule[1], rule[2]), (rule[3], rule[4])
        here = (day.month, day.day)
        return first <= here <= last if first <= last else here >= first or here <= last
    if rule[0] == 'nth':
        target, before, after = nth_weekday(day.year, rule[1], rule[2], rule[3]), rule[4], rule[5]
    else:
        target, before, after = gauss_easter(day.year), rule[1], rule[2]
    return target - timedelta(days=before) <= day <= target + timedelta(days=after)


RULES = [['nth', m, w, n, 0, 0] for m in range(1, 13) for w in range(7) for n in (1, 2, 3, 4, -1)] \
    + [['nth', 11, 3, 4, 1, 3], ['nth', 5, 0, -1, 2, 0], ['easter', 0, 0], ['easter', 2, 1],
       ['range', 12, 1, 12, 31], ['range', 12, 31, 1, 1], ['range', 11, 15, 1, 31], ['range', 2, 14, 2, 14],
       ['range', 12, 1, 2, 29], ['range', 4, 1, 9, 30], ['range', 2, 29, 2, 29]]


def differences(special_on):
    out, day = [], date(2024, 1, 1)
    while day.year <= 2060:
        for rule in RULES:
            if bool(special_on([rule], day.year, day.month, day.day)) != expected(rule, day):
                out.append((day, rule))
        day += timedelta(days=1)
    return out


def main():
    for text in KNOWN_EASTER:
        y, m, d = map(int, text.split('-'))
        assert scene.easter(y) == (m, d), f'scene.easter({y}) = {scene.easter(y)}, the table says {text}'
        assert gauss_easter(y) == date(y, m, d), f'the check\'s own Easter of {y} is not the table\'s'
    assert all(scene.easter(y) == (gauss_easter(y).month, gauss_easter(y).day) for y in range(1900, 2300)), 'Easter 1900..2299'
    bad = differences(scene.special_on)
    assert not bad, f'{len(bad)} differences, the first: {bad[:3]}'
    # controls: each must be reported
    moved = differences(lambda when, y, m, d: scene.special_on(when, y, m, d + 1 if d < 28 else d))
    late_easter = scene.easter
    scene.easter = lambda year: (late_easter(year)[0], late_easter(year)[1] - 1 if late_easter(year)[1] > 1 else 2)
    wrong = differences(scene.special_on)
    scene.easter = late_easter
    assert moved and wrong, 'a control was not reported'
    days = (date(2060, 12, 31) - date(2024, 1, 1)).days + 1
    print(f'RESULT: every check passed: {len(RULES)} rules on {days} days, Easter of 1900 to 2299 by two formulas and '
          f'{len(KNOWN_EASTER)} written dates; controls reported ({len(moved)} and {len(wrong)} differences)')


main()
