#!/usr/bin/env python3
"""One builder at today's load, pull and geth's rules, both signature sizes, at 100, 1,000 and
10,000 nodes, as Markdown: data/today-one-builder.md.

usage: today_one_builder.py RUNS [--used FILE] > today-one-builder.md

RUNS is one flat directory of <cell>.jsonl files (configs/*.tsv name the cells). 15 signature
tx/s and no privacy load (p = 0), six-object block, seeds 100-107. The builder is node 0: the only
aggregator, and the proposer of every block. Upload counts every message a node sends, over the
60 s of load (load_traffic.wire_bytes_per_second_by_node), in Mbit/s; "other nodes" is the mean
over every node but the builder, "busiest" the most any of them sends. Delay is the mean from a
transaction's arrival to its block, in seconds. The builder's CPU is its busy share over the load.
"""
from runs import Runs, arguments, write_used

DESIGNS = {"pull": "2 pull", "geth": "5 geth's rules"}
SIGNATURES = {None: "2,560 B", "sig7740": "7,740 B"}
SEEDS = (100, 101, 102, 103, 104, 105, 106, 107)
args = arguments(__doc__.splitlines()[0])
runs = Runs(args.runs)


def row(record):
    m = record["metrics"]
    load = m["load_traffic"]["wire_bytes_per_second_by_node"]
    others = load[1:]
    mbit = 8 / 1e6
    return (f"{m['included_txs'] / m['arrived_txs']:.1%}",
            f"{sum(others) / len(others) * mbit:.3f}", f"{max(others) * mbit:.2f}",
            f"{load[0] * mbit:.2f}", f"{m['delay_mean_slots'] * 12:.2f}",
            f"{m['load_utilisation']['cpu_utilisation_by_node'][0]:.1%}")


print("### One builder at today's load: 15 signature tx/s, p = 0, six-object block\n")
print("Upload in Mbit/s per node over the 60 s of load; delay in seconds; the builder is node 0.\n")
print("| design | signatures | nodes | seed | included | upload, other nodes | busiest other node "
      "| the builder | delay, s | builder's CPU |")
print("|---|---|---|---|---|---|---|---|---|---|")
for design, label in DESIGNS.items():
    for control, size in SIGNATURES.items():
        for nodes in (100, 1000, 10000):
            for seed in SEEDS:
                record = runs.get(design, "builder", nodes, 0, 6, "fixed", control, seed)
                cells = row(record) if record else ("missing",) + ("",) * 5
                print(f"| {label} | {size} | {nodes:,} | {seed} | " + " | ".join(cells) + " |")
write_used(runs, args.used)
