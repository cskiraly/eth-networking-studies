#!/usr/bin/env python3
"""The five designs with one fixed proposer, as Markdown: capacity with seeds, today's load per node
(upload and delay), 7,740 B signatures, and 2 signature tx/s: data/designs-fixed-proposer.md.

usage: designs_fixed_proposer.py RUNS [--used FILE] > designs-fixed-proposer.md

RUNS is one flat directory of <cell>.jsonl files (configs/*.tsv name the cells). A run counts when
its <cell>.jsonl exists: the runner writes it only once the run has finished.

Capacity is each seed's: seed 100 ran the whole ladder (72 and 96 where 54 held); seeds 101-103
ran p = 0 and the steps around each edge. Upload is per node over the 84 s run (five slots of
load and two to drain); delay is the mean in 12 s slots.
"""
import statistics

from runs import Runs, arguments, write_used

NAMES = {"push": "1 push", "pull": "2 pull", "keep": "3 keep", "coverage": "4 coverage",
         "geth": "5 geth today"}
SETTINGS = {"every": "every node", "builder": "one builder", "quarter": "25% aggregators"}
SEEDS = (100, 101, 102, 103)
EXTENDED = (0, 3, 6, 9, 12, 18, 27, 36, 54, 72, 96)
args = arguments(__doc__.splitlines()[0])
runs = Runs(args.runs)


def get(d, s, n, p, b, control, seed, f):
    r = runs.get(d, s, n, p, b, "fixed", control, seed)
    return None if r is None else f(r)


def share(*k):
    return get(*k, lambda r: r["metrics"]["included_txs"] / r["metrics"]["arrived_txs"])


def mbps(*k):
    return get(*k, lambda r: r["metrics"]["wire_bytes"] * 8 / r["workload"]["nodes"] / 84 / 1e6)


def delay(*k):
    return get(*k, lambda r: r["metrics"]["delay_mean_slots"])


def seed_capacity(d, s, n, b, seed):
    """The highest step held with every step run below it held, as text: '≥' when the highest step
    run held, '<' when the first failure's step below wasn't run. At seeds 101-103 the steps
    between p = 0 and the edge weren't run; they're taken as held."""
    top = 0
    for p in EXTENDED[1:]:
        x = share(d, s, n, p, b, None, seed)
        if x is None:
            continue
        if x < 0.95:
            under = EXTENDED[EXTENDED.index(p) - 1]
            return str(top) if under == top else f"<{p}"
        top = p
    return f"≥{top}"


def capacity_cell(d, s, n, b):
    caps = [seed_capacity(d, s, n, b, seed) for seed in SEEDS]
    return caps[0] if len(set(caps)) == 1 else " / ".join(caps)


def spread(values, fmt):
    values = [v for v in values if v is not None]
    if not values:
        return "–"
    mean = format(statistics.mean(values), fmt)
    lo, hi = format(min(values), fmt), format(max(values), fmt)
    return mean if lo == hi else f"{mean} ({lo}–{hi})"


print("### Capacity: privacy tx/s held on top of 15 signature tx/s\n")
print("At seeds 100 / 101 / 102 / 103, one value where all four agree. '≥': the highest rung run held "
      "(seed 100 ran to 96, seeds 101–103 to 72).\n")
for b, title in ((6, "six-object block"), (501, "501-object block")):
    print(f"**{title}**\n")
    print("| design | " + " | ".join(f"{SETTINGS[s]}, {n:,} nodes" for s in SETTINGS for n in (100, 1000)) + " |")
    print("|---|" + "---|" * 6)
    for d in NAMES:
        print(f"| {NAMES[d]} | " + " | ".join(capacity_cell(d, s, n, b) for s in SETTINGS for n in (100, 1000)) + " |")
    print()

print("### Today's load (15 signature tx/s, p = 0), six-object block: mean over seeds 100–103 (range)\n")
for what, f, fmt in (("Upload per node, Mbit/s", mbps, ".2f"), ("Delay, slots of 12 s", delay, ".2f")):
    print(f"**{what}**\n")
    print("| design | " + " | ".join(f"{SETTINGS[s]}, {n:,} nodes" for s in SETTINGS for n in (100, 1000)) + " |")
    print("|---|" + "---|" * 6)
    for d in NAMES:
        print(f"| {NAMES[d]} | " + " | ".join(
            spread([f(d, s, n, 0, 6, None, seed) for seed in SEEDS], fmt)
            for s in SETTINGS for n in (100, 1000)) + " |")
    print()

print("### 7,740 B signatures at today's load, against 2,560 B (same seed): change, mean over seeds (range)\n")
print("| design | setting | nodes | upload, Mbit/s per node | delay, slots | lowest inclusion |")
print("|---|---|---|---|---|---|")
for d in ("push", "coverage", "geth"):
    for s in SETTINGS:
        for n in (100, 1000):
            dw = [None if mbps(d, s, n, 0, 6, "sig7740", x) is None or mbps(d, s, n, 0, 6, None, x) is None
                  else mbps(d, s, n, 0, 6, "sig7740", x) - mbps(d, s, n, 0, 6, None, x) for x in SEEDS]
            dd = [None if delay(d, s, n, 0, 6, "sig7740", x) is None or delay(d, s, n, 0, 6, None, x) is None
                  else delay(d, s, n, 0, 6, "sig7740", x) - delay(d, s, n, 0, 6, None, x) for x in SEEDS]
            sh = [x for x in (share(d, s, n, 0, 6, "sig7740", y) for y in SEEDS) if x is not None]
            print(f"| {NAMES[d]} | {SETTINGS[s]} | {n:,} | {spread(dw, '+.2f')} | {spread(dd, '+.2f')} | "
                  f"{min(sh):.1%} |" if sh else f"| {NAMES[d]} | {SETTINGS[s]} | {n:,} | – | – | – |")
print()
print("### 2 signature tx/s, every node aggregating, 1,000 nodes, p = 0: mean over seeds (range)\n")
print("| design | upload, Mbit/s per node | delay, slots | lowest inclusion |")
print("|---|---|---|---|")
for d in ("push", "coverage"):
    sh = [x for x in (share(d, "every", 1000, 0, 6, "sigtps2", y) for y in SEEDS) if x is not None]
    print(f"| {NAMES[d]} | {spread([mbps(d, 'every', 1000, 0, 6, 'sigtps2', x) for x in SEEDS], '.2f')} | "
          f"{spread([delay(d, 'every', 1000, 0, 6, 'sigtps2', x) for x in SEEDS], '.2f')} | "
          f"{min(sh):.1%} |" if sh else f"| {NAMES[d]} | – | – | – |")
write_used(runs, args.used)
