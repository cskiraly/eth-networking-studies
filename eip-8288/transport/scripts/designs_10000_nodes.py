#!/usr/bin/env python3
"""The five designs at 10,000 nodes against 1,000, as Markdown: data/designs-10000-nodes.md.

usage: designs_10000_nodes.py RUNS [--used FILE] > designs-10000-nodes.md

RUNS is one flat directory of <cell>.jsonl files (configs/*.tsv name the cells). Seeds 100-107,
six-object block unless noted. Every node aggregating and one builder have node 0 as the fixed
proposer (with one builder, the builder); a quarter aggregating has a random proposer. At 10,000
nodes only each 1,000-node edge and the step above it ran, and a step below or above where an
edge moved; at 1,000 nodes, the first record's series.

A capacity is the highest step of privacy load, on top of 15 signature tx/s, at which a run
includes at least 95% of its transactions, with every lower step run held; steps not run are taken
as held ('≥': the highest step run held). Upload counts every message a node sends, over the 60 s
of load (load_traffic.wire_bytes_per_second), per node, in Mbit/s; delay is the mean from a
transaction's arrival to its block, in seconds.
"""
import statistics

from runs import Runs, arguments, write_used

NAMES = {"push": "1 push", "pull": "2 pull", "keep": "3 keep", "coverage": "4 coverage",
         "geth": "5 geth's rules"}
SETTINGS = {"every": ("every node", "fixed"), "builder": ("one builder", "fixed"),
            "quarter": ("25% aggregators", "random")}
SEEDS = (100, 101, 102, 103, 104, 105, 106, 107)
LADDER = (0, 3, 6, 9, 12, 18, 27, 36, 54, 72, 96)
args = arguments(__doc__.splitlines()[0])
runs = Runs(args.runs)


def get(d, s, n, p, seed, control=None, objects=6):
    return runs.get(d, s, n, p, objects, SETTINGS[s][1], control, seed)


def share(r):
    return r["metrics"]["included_txs"] / r["metrics"]["arrived_txs"]


def upload(r):
    return r["metrics"]["load_traffic"]["wire_bytes_per_second"] * 8 / 1e6


def delay(r):
    return r["metrics"]["delay_mean_slots"] * 12


def seed_capacity(d, s, n, seed):
    top, ran = 0, False
    for p in LADDER[1:]:
        r = get(d, s, n, p, seed)
        if r is None:
            continue
        ran = True
        if share(r) < 0.95:
            under = LADDER[LADDER.index(p) - 1]
            return str(top) if under == top else f"<{p}"
        top = p
    return f"≥{top}" if ran else None


def capacity(d, s, n):
    caps = [seed_capacity(d, s, n, seed) for seed in SEEDS]
    if all(c is None for c in caps):
        return "not run"
    caps = [c or "–" for c in caps]
    return caps[0] if len(set(caps)) == 1 else " / ".join(caps)


def spread(values, fmt):
    values = [v for v in values if v is not None]
    if not values:
        return "–"
    lo, hi = format(min(values), fmt), format(max(values), fmt)
    return lo if lo == hi else f"{lo}–{hi}"


print("### Capacity: privacy tx/s held on top of 15 signature tx/s, six-object block\n")
print("At seeds 100 to 107 in order, one value where all eight agree.\n")
print("| design | " + " | ".join(f"{SETTINGS[s][0]}, {n:,} nodes" for s in SETTINGS
                               for n in (1000, 10000)) + " |")
print("|---|" + "---|" * 6)
for d in NAMES:
    print(f"| {NAMES[d]} | " + " | ".join(capacity(d, s, n) for s in SETTINGS for n in (1000, 10000))
          + " |")
print()

print("### Every step run at 10,000 nodes, against the same cell at 1,000\n")
print("| design | setting | step | seed | included, 10,000 | included, 1,000 | upload, 10,000 "
      "| upload, 1,000 | delay, s, 10,000 | delay, s, 1,000 |")
print("|---|---|---|---|---|---|---|---|---|---|")
for d in NAMES:
    for s in SETTINGS:
        for p in LADDER:
            for seed in SEEDS:
                big = get(d, s, 10000, p, seed)
                if big is None:
                    continue
                small = get(d, s, 1000, p, seed)
                cells = [f"{share(big):.1%}", f"{share(small):.1%}" if small else "–",
                         f"{upload(big):.2f}", f"{upload(small):.2f}" if small else "–",
                         f"{delay(big):.2f}", f"{delay(small):.2f}" if small else "–"]
                print(f"| {NAMES[d]} | {SETTINGS[s][0]} | {p} | {seed} | " + " | ".join(cells) + " |")
print()

print("### Every node aggregating, no privacy load: upload per node over the load, Mbit/s, "
      "range over seeds\n")
print("| design | 15 signature tx/s, 1,000 | 15, 10,000 | 2 signature tx/s, 1,000 | 2, 10,000 |")
print("|---|---|---|---|---|")
for d in NAMES:
    cells = []
    for control in (None, "sigtps2"):
        for n in (1000, 10000):
            cells.append(spread([upload(r) for r in (get(d, "every", n, 0, seed, control)
                                                     for seed in SEEDS) if r], ".2f"))
    print(f"| {NAMES[d]} | " + " | ".join(cells) + " |")
print()

print("### Pull with one builder, a prover 1,000 times faster (anchor 0.303 ms)\n")
print("Included, by seed; the ordinary prover beside it where it ran at 10,000 nodes. At 1,000 "
      "nodes the control ran at seed 100 only.\n")
print("| nodes | step | block | prover | " + " | ".join(str(seed) for seed in SEEDS) + " |")
print("|---|---|---|---|" + "---|" * len(SEEDS))
for n in (1000, 10000):
    for p in (12, 18):
        for objects in (6, 501):
            for control, label in (("fastprover", "1,000× faster"), (None, "ordinary")):
                if n == 1000 and control is None:
                    continue
                found = [get("pull", "builder", n, p, seed, control, objects) for seed in SEEDS]
                if not any(found):
                    continue
                print(f"| {n:,} | {p} | {objects} objects | {label} | "
                      + " | ".join(f"{share(r):.1%}" if r else "–" for r in found) + " |")
write_used(runs, args.used)
