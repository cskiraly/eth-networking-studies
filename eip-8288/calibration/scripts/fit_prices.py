#!/usr/bin/env python3
"""Calibration v2's proving prices, from leanVM 990b935 timed on exactly 1, 2 and 4 pinned cores.

    python3 fit_prices.py data/leanvm-cores.csv > data/prices.txt

Each run's `prove_s` is put on the 303 ms scale of leanVM's README (its 2-to-1 recursion over 900
leanXMSS signatures a leaf, on an M4 Max) through that 2-to-1 timed on the same cores, then
averaged over the three core counts. A cell with no accepted run on a core count takes its last
try (the runner kept it and flagged it after three). Then:
- the two leaves (aggregates of 16 and 512 leanSPHINCS signatures) give the cost of a proof and of
  a signature;
- folds of 4, 8 and 16 children over leaves of 512 give the cost of a nested proof, by least
  squares on what they cost above a proof.
bench.mainnet's `--calibration leanvm-990b935-timed` uses the results rounded: 25.9 ms a proof,
108.2 a nested proof, 1.667 a signature, and at least 303 once a proof verifies two nested proofs.
The table compares those prices with every measured shape.
"""
import collections
import csv
import statistics
import sys

ANCHOR = "anchor-n2-x900"
PROOF, NESTED, SIGNATURE, FLOOR = 25.9, 108.2, 1.667, 303.0   # as bench/mainnet.py has them

runs = collections.defaultdict(dict)
with open(sys.argv[1]) as handle:
    for row in csv.DictReader(handle):
        cell, cores = row["name"].split("-", 2)[2], int(row["cores"])
        key = (int(row["accepted"]), int(row["try"]))
        if cores not in runs[cell] or key > runs[cell][cores][0]:
            runs[cell][cores] = (key, float(row["prove_s"]))
scaled = {cell: statistics.fmean(303.0 * t / runs[ANCHOR][cores][1] for cores, (_, t) in by_cores.items())
          for cell, by_cores in runs.items()}

signature = (scaled["leaf-k512"] - scaled["leaf-k16"]) / (512 - 16)
proof = scaled["leaf-k16"] - 16 * signature
children = (4, 8, 16)
nested = (sum(n * (scaled[f"rec-n{n}-k512"] - proof) for n in children)
          / sum(n * n for n in children))
print(f"fitted: a proof {proof:.2f} ms, a nested proof {nested:.2f} ms, a signature {signature:.3f} ms")
print(f"priced: a proof {PROOF} ms, a nested proof {NESTED} ms, a signature {SIGNATURE} ms, "
      f"at least {FLOOR:g} ms from two nested proofs\n")


def price(cell):
    kind, *rest = cell.split("-")
    if kind == "leaf":
        return PROOF + int(rest[0][1:]) * SIGNATURE
    n = 2 if kind == "anchor" else int(rest[0][1:])
    return max(PROOF + n * NESTED, FLOOR)


print(f"{'shape':16} {'measured ms':>11} {'priced ms':>9} {'error':>7}")
for cell in sorted(scaled, key=lambda c: (c.split("-")[0], len(c), c)):
    print(f"{cell:16} {scaled[cell]:>11.1f} {price(cell):>9.1f} {100 * (price(cell) / scaled[cell] - 1):>+6.1f}%")
