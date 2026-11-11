#!/usr/bin/env python3
"""Every node aggregating: a random proposer against the fixed one, cell by cell:
data/proposer-every-node.txt.

usage: proposer_every_node.py RUNS [--used FILE] > proposer-every-node.txt

RUNS is one flat directory of <cell>.jsonl files (configs/*.tsv name the cells). A run counts when
its <cell>.jsonl exists: the runner writes it only once the run has finished.

Each random-proposer cell with every node aggregating is paired with the fixed proposer's cell of
the same design, size, block, step and seed: inclusion by the run's end (h: held, at least 95%;
f: failed), its change in points, and mean delay in slots of 12 s; '–' where the fixed proposer's
ladder stopped below the step. The last line takes the cells where both proposers held 72 or more
(72 is the top step every seed ran; seed 100 ran 96).
"""
from runs import DESIGNS, Runs, arguments, write_used

NAMES = {"push": "1 push", "pull": "2 pull", "keep": "3 keep", "coverage": "4 coverage",
         "geth": "5 geth"}
SEEDS = (100, 101, 102, 103)
EXTENDED = (0, 3, 6, 9, 12, 18, 27, 36, 54, 72, 96)
args = arguments(__doc__.splitlines()[0])
runs = Runs(args.runs)


def held(x):
    return "h" if x >= 0.95 else "f"


print("design      nodes block seed step  fixed      random     change  delay fixed/random")
top = []
for d in DESIGNS:
    for n in (100, 1000):
        for b in (6, 501):
            for seed in SEEDS:
                for p in EXTENDED:
                    random = runs.get(d, "every", n, p, b, "random", None, seed)
                    if random is None:
                        continue
                    fixed = runs.get(d, "every", n, p, b, "fixed", None, seed)
                    r = random["metrics"]["included_txs"] / random["metrics"]["arrived_txs"]
                    rd = random["metrics"]["delay_mean_slots"]
                    if fixed is None:  # the fixed proposer's ladder stopped below this step
                        print(f"{NAMES[d]:<12}{n:<6}{b:<6}{seed:<5}{p:<5}     – –   "
                              f"{100 * r:6.1f} {held(r)}        –     –/{rd:.2f}")
                        continue
                    f = fixed["metrics"]["included_txs"] / fixed["metrics"]["arrived_txs"]
                    fd = fixed["metrics"]["delay_mean_slots"]
                    print(f"{NAMES[d]:<12}{n:<6}{b:<6}{seed:<5}{p:<5}{100 * f:6.1f} {held(f)}   "
                          f"{100 * r:6.1f} {held(r)}   {100 * (r - f):+6.1f}  {fd:.2f}/{rd:.2f}")
                    if p >= 72 and f >= 0.95 and r >= 0.95:
                        top.append((100 * abs(r - f), 12 * abs(rd - fd)))
print(f"\nWhere both held at 72 or above ({len(top)} cells): inclusion changed by at most "
      f"{max(t[0] for t in top):.1f} points, mean delay by at most {max(t[1] for t in top):.2f} s.")
write_used(runs, args.used)
