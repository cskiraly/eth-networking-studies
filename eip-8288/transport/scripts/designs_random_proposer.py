#!/usr/bin/env python3
"""The five designs' capacity with a random proposer, as Markdown: data/designs-random-proposer.md.

usage: designs_random_proposer.py RUNS [--used FILE] > designs-random-proposer.md

RUNS is one flat directory of <cell>.jsonl files (configs/*.tsv name the cells). A run counts when
its <cell>.jsonl exists: the runner writes it only once the run has finished.

The every-node and 25% columns are a random proposer's (a node drawn each slot, as on Ethereum);
the one-builder columns are the fixed proposer's, as in designs-fixed-proposer.md: that builder
proposes by construction.

A seed's capacity counts the cells of one proposer only: the highest step held with every step run
below it held, '≥' when the highest step run held, '<' when the first failure's step below wasn't
run. Steps below the lowest cell run are taken as held: the random proposer's runs ran the steps
around each edge.
"""
from runs import Runs, arguments, write_used

NAMES = {"push": "1 push", "pull": "2 pull", "keep": "3 keep", "coverage": "4 coverage",
         "geth": "5 geth today"}
SETTINGS = {"every": "every node", "builder": "one builder", "quarter": "25% aggregators"}
SEEDS = (100, 101, 102, 103)
EXTENDED = (0, 3, 6, 9, 12, 18, 27, 36, 54, 72, 96)
RANDOM = ("quarter", "every")
args = arguments(__doc__.splitlines()[0])
runs = Runs(args.runs)


def share(d, s, n, p, b, proposer, seed):
    r = runs.get(d, s, n, p, b, proposer, None, seed)
    return None if r is None else r["metrics"]["included_txs"] / r["metrics"]["arrived_txs"]


def seed_capacity(d, s, n, b, seed, proposer):
    top = 0
    for p in EXTENDED[1:]:
        x = share(d, s, n, p, b, proposer, seed)
        if x is None:
            continue
        if x < 0.95:
            under = EXTENDED[EXTENDED.index(p) - 1]
            return str(top) if under == top else f"<{p}"
        top = p
    return f"≥{top}"


def capacity_cell(d, s, n, b):
    proposer = "random" if s in RANDOM else "fixed"
    caps = [seed_capacity(d, s, n, b, seed, proposer) for seed in SEEDS]
    return caps[0] if len(set(caps)) == 1 else " / ".join(caps)


out = ["### Capacity: privacy tx/s held on top of 15 signature tx/s, with a random proposer\n",
       "At seeds 100 / 101 / 102 / 103, one value where all four agree. '≥': the highest rung run "
       "held (seed 100 ran to 96, seeds 101–103 to 72). The every-node and 25% columns are a random "
       "proposer's (proposer_mode=random); the one-builder columns are node 0's, as in "
       "designs-fixed-proposer.md: that builder proposes by construction.\n"]
for b, title in ((6, "six-object block"), (501, "501-object block")):
    out.append(f"**{title}**\n")
    out.append("| design | " + " | ".join(f"{SETTINGS[s]}, {n:,} nodes" for s in SETTINGS for n in (100, 1000)) + " |")
    out.append("|---|" + "---|" * 6)
    for d in NAMES:
        out.append(f"| {NAMES[d]} | " + " | ".join(capacity_cell(d, s, n, b) for s in SETTINGS for n in (100, 1000)) + " |")
    out.append("")
print("\n".join(out))
write_used(runs, args.used)
