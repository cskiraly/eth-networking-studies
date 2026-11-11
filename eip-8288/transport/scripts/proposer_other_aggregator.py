#!/usr/bin/env python3
"""A quarter of the nodes aggregating: one fixed proposer at node 0, one fixed proposer at another
aggregator, and a random proposer, cell by cell: data/proposer-other-aggregator.txt.

usage: proposer_other_aggregator.py RUNS [--used FILE] > proposer-other-aggregator.txt

RUNS is one flat directory of <cell>.jsonl files (configs/*.tsv name the cells). A run counts when
its <cell>.jsonl exists: the runner writes it only once the run has finished.

The other aggregator is the first-ranked of the quarter's aggregators at the cell's seed, fixed as
the proposer of every slot (each cell's command names it, proposer_id); node 0, the fixed
proposer of the designs' other runs, is made an aggregator instead. Each cell run with the other
aggregator, at node 0's edge (the step it held and the step above), is shown with node 0 (h: held,
at least 95%; f: failed) and the random proposer at the same design, size, block, step and seed;
in brackets, the change from node 0 in points. Below, the steps each proposer held per series:
'≥' where its highest step run held, '<' where it held none of them.
"""
from runs import Runs, arguments, write_used

NAMES = {"pull": "2 pull", "geth": "5 geth"}
SEEDS = (100, 101, 102, 103)
EXTENDED = (0, 3, 6, 9, 12, 18, 27, 36, 54, 72, 96)
PROPOSERS = ("fixed", "other", "random")
args = arguments(__doc__.splitlines()[0])
runs = Runs(args.runs)


def share(d, n, p, b, proposer, seed):
    r = runs.get(d, "quarter", n, p, b, proposer, None, seed)
    return None if r is None else 100 * r["metrics"]["included_txs"] / r["metrics"]["arrived_txs"]


series = {}
for d in NAMES:
    for n in (100, 1000):
        for b in (6, 501):
            for seed in SEEDS:
                for p in EXTENDED:
                    if share(d, n, p, b, "other", seed) is not None:
                        series.setdefault((d, n, b, seed), []).append(
                            (p, {v: share(d, n, p, b, v, seed) for v in PROPOSERS}))
print("design  nodes block seed step   node 0   other aggregator   random")
for (d, n, b, seed), cells in series.items():
    for p, x in cells:
        print(f"{NAMES[d]:<8}{n:<6}{b:<6}{seed:<5}{p:<4}{'h' if x['fixed'] >= 95 else 'f'}"
              f"   {x['fixed']:6.1f}   {x['other']:6.1f} ({x['other'] - x['fixed']:+5.1f})      "
              f"{x['random']:6.1f} ({x['random'] - x['fixed']:+5.1f})")
print("\nSteps held per series (node 0 / other aggregator / random)")
for (d, n, b, seed), cells in series.items():
    out = []
    for v in PROPOSERS:
        held = [p for p, x in cells if x[v] >= 95]
        if not held:
            out.append(f"<{cells[0][0]}")
        elif max(held) == cells[-1][0]:
            out.append(f"≥{max(held)}")
        else:
            out.append(str(max(held)))
    print(f"  {NAMES[d]:<8}n{n:<5}{b:<3} obj  s{seed}: {' / '.join(out)}")
write_used(runs, args.used)
