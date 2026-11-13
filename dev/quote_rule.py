"""Checks of the hourly quote rule (the quote changes hourly, and the order of each pass is a random sort), on the
renderer in TOOLS (default: the add-on's tools/):
- over 10 passes from the epoch, every quote shows exactly once in each pass;
- no two hours in a row show the same quote over those 10 passes, and over the 48 hours around the epoch;
- the orders of passes 0, 1 and 2 differ from each other in at least 80% of the n places.
Prints the numbers; exits 1 if a check fails.

    python3 -I -B dev/quote_rule.py [TOOLS]

The export's own stops do not see one fixed order used for every pass; the third check here does.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1
                else str(Path(__file__).resolve().parents[1] / 'tools'))
import scene  # noqa: E402

q = scene.quotes()
n = len(q)
index = {quote: k for k, quote in enumerate(q)}
epoch = datetime(scene.scene()['text']['quote_epoch_year'], 1, 1)
failed = []


def shown(first, hours):
    return [index[scene.quote_of(first + timedelta(hours=h))] for h in range(hours)]


ten = shown(epoch, 10 * n)
once = [len(set(ten[k * n:(k + 1) * n])) == n for k in range(10)]
print(f'n = {n}; passes 0..9 showing every quote exactly once: {sum(once)} of 10')
if not all(once):
    failed.append('once')

around = shown(epoch - timedelta(hours=24), 48)
for name, seq in (('10 passes', ten), ('48 hours around the epoch', around)):
    repeats = [k for k in range(len(seq) - 1) if seq[k] == seq[k + 1]]
    print(f'{name}: {len(seq)} hours, {len(seq) - 1} neighbouring pairs, same quote twice in a row: {len(repeats)}')
    if repeats:
        failed.append(name)

orders = [ten[k * n:(k + 1) * n] for k in range(3)]
for a, b in ((0, 1), (0, 2), (1, 2)):
    differ = sum(x != y for x, y in zip(orders[a], orders[b]))
    print(f'passes {a} and {b} differ in {differ} of {n} places')
    if differ < 0.8 * n:
        failed.append(f'passes {a} {b}')

print('RESULT:', 'FAILED ' + ', '.join(failed) if failed else 'every check passed')
sys.exit(1 if failed else 0)
