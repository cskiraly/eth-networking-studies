#!/usr/bin/env python3
"""Seed 100's controls, one fixed proposer: data/controls.txt. The request timeout (designs 2 and 4
at 5 s instead of 500 ms, design 5 at 500 ms instead of 5 s), the fold order (design 4 ranking a
fold's inputs by fee per proving cost), and one builder under pull proving 1,000 times faster.

usage: controls.py RUNS [--used FILE] > controls.txt

RUNS is one flat directory of <cell>.jsonl files (configs/*.tsv name the cells). A run counts when
its <cell>.jsonl exists: the runner writes it only once the run has finished.

Inclusion is the share of the run's transactions included by its end (five slots of load and two
to drain), held at 95%. c is a series' capacity at seed 100 with the design's own setting (the
highest step held with every lower step held), c+ the step above it. GB refused: bytes the
uplinks refused, over the run, at c+.
"""
from runs import Runs, arguments, write_used

NAMES = {"push": "1 push", "pull": "2 pull", "keep": "3 keep", "coverage": "4 coverage",
         "geth": "5 geth"}
SIZES = (100, 1000)
BLOCKS = (6, 501)
SEEDS = (100, 101, 102, 103)
EXTENDED = (0, 3, 6, 9, 12, 18, 27, 36, 54, 72, 96)
args = arguments(__doc__.splitlines()[0])
runs = Runs(args.runs)


def metric(d, s, n, p, b, control, seed, f):
    r = runs.get(d, s, n, p, b, "fixed", control, seed)
    return None if r is None else f(r)


def share(d, s, n, p, b, control=None, seed=100):
    return metric(d, s, n, p, b, control, seed,
                  lambda r: r["metrics"]["included_txs"] / r["metrics"]["arrived_txs"])


def refused(d, s, n, p, b, control=None, seed=100):
    return metric(d, s, n, p, b, control, seed, lambda r: r["metrics"]["egress_refused_bytes"])


def edge(d, s, n, b):
    """Seed 100's capacity c with the design's own setting, and the step above it."""
    top = 0
    for p in EXTENDED[1:]:
        x = share(d, s, n, p, b)
        if x is None or x < 0.95:
            break
        top = p
    return top, EXTENDED[EXTENDED.index(top) + 1]


def above(p, k=1):
    return EXTENDED[EXTENDED.index(p) + k]


def pct(x, w=7):
    return f"{'-':>{w}}" if x is None else f"{x:{w}.1%}"


def gb(x):
    return f"{'-':>4}" if x is None else f"{x / 1e9:.0f}".rjust(4)


def label(d, s, n, b):
    return f"{NAMES[d]:<11} {s:<8} n{n:<5} {b:<3} obj "


LADDER = {100: (18, 27, 36, 54, 72), 1000: (12, 18, 27, 36, 54, 72, 96)}
print("Design 2 at 25%, request timeout 500 ms -> 5 s, seed 100: inclusion up the ladder; GB refused at c+")
for n in SIZES:
    for b in BLOCKS:
        cp = edge("pull", "quarter", n, b)[1]
        row = "".join(f"  p{p:<3}{pct(share('pull', 'quarter', n, p, b), 6)}->"
                      f"{pct(share('pull', 'quarter', n, p, b, 'timeout5s'), 6)}" for p in LADDER[n])
        print(f"  {label('pull', 'quarter', n, b)}{row}   {gb(refused('pull', 'quarter', n, cp, b))} ->"
              f"{gb(refused('pull', 'quarter', n, cp, b, 'timeout5s'))}")
print("\nGeth at 25%, six-object block, request timeout 5 s -> 500 ms, seed 100: inclusion")
for n in SIZES:
    print(f"  {label('geth', 'quarter', n, 6)}" + "".join(
        f"  p{p:<3}{pct(share('geth', 'quarter', n, p, 6), 6)}->"
        f"{pct(share('geth', 'quarter', n, p, 6, 'timeout500ms'), 6)}" for p in (12, 18, 27, 36, 54)))
print("\nDesign 2 with one builder (at c and c+) and every node (at 72 and 96), request timeout 500 ms -> 5 s,"
      " seed 100: inclusion")
for n in SIZES:
    for b in BLOCKS:
        print(f"  {label('pull', 'builder', n, b)}" + "".join(
            f"  p{p:<3}{pct(share('pull', 'builder', n, p, b), 6)}->"
            f"{pct(share('pull', 'builder', n, p, b, 'timeout5s'), 6)}" for p in edge("pull", "builder", n, b)))
    print(f"  {label('pull', 'every', n, 6)}" + "".join(
        f"  p{p:<3}{pct(share('pull', 'every', n, p, 6), 6)}->"
        f"{pct(share('pull', 'every', n, p, 6, 'timeout5s'), 6)}" for p in (72, 96)))
print("\nDesign 4 at 25%, request timeout 500 ms -> 5 s at c and c+, seed 100: inclusion")
for n in SIZES:
    for b in BLOCKS:
        print(f"  {label('coverage', 'quarter', n, b)}" + "".join(
            f"  p{p:<3}{pct(share('coverage', 'quarter', n, p, b), 6)}->"
            f"{pct(share('coverage', 'quarter', n, p, b, 'timeout5s'), 6)}"
            for p in edge("coverage", "quarter", n, b)))
print("\nDesign 4, six-object block, a fold's inputs in the EIP's order -> ranked by fee per proving cost:"
      " inclusion (at 25%: 54 at each seed and 72 at seed 100; with one builder: c and c+ at seed 100)")
for n in SIZES:
    print(f"  {label('coverage', 'quarter', n, 6)}" + "".join(
        f"  p54 s{seed}{pct(share('coverage', 'quarter', n, 54, 6, seed=seed), 6)}->"
        f"{pct(share('coverage', 'quarter', n, 54, 6, 'feeorder', seed), 6)}" for seed in SEEDS)
        + f"  p72 s100{pct(share('coverage', 'quarter', n, 72, 6), 6)}->"
          f"{pct(share('coverage', 'quarter', n, 72, 6, 'feeorder'), 6)}")
    print(f"  {label('coverage', 'builder', n, 6)}" + "".join(
        f"  p{p:<3}{pct(share('coverage', 'builder', n, p, 6), 6)}->"
        f"{pct(share('coverage', 'builder', n, p, 6, 'feeorder'), 6)}" for p in edge("coverage", "builder", n, 6)))
print("\nOne builder under pull, proving 1,000 times faster, seed 100: inclusion at c, c+ and the step above")
for n in SIZES:
    for b in BLOCKS:
        c, cp = edge("pull", "builder", n, b)
        print(f"  {label('pull', 'builder', n, b)}" + "   ".join(
            f"p{p:<3}{pct(share('pull', 'builder', n, p, b))} ->{pct(share('pull', 'builder', n, p, b, 'fastprover'))}"
            for p in (c, cp, above(c, 2))))
write_used(runs, args.used)
