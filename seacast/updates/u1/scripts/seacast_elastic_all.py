"""Elasticity of three protocols in one simulator: today's gossipsub, ECBroadcast's Reed-Solomon mode
and SEACAST, every node's uplink at 50, 25, 20 and 10 Mbps (downlink twice that), 16 connections per
node, the all-home network, ten paired seeds per point.

usage: seacast_elastic_all.py [--csv PATH] [--out PATH]

--csv  one row per cell: series (seacast | ecbroadcast-rs | gossipsub), uplink_mbps, seed, p99_s (median
       over the warm payloads of the time for 99 % of nodes to hold the payload), mib (link rx per node
       to network completion, median over the warm payloads), payloads, gap_s. Default:
       seacast_elastic_all.csv beside this script.
--out  the PNG. Default: seacast_elastic_all.png beside this script.

Left: p99 against the uplink (both log), medians with the seed range as bars, and the lower bound the
links set (BOUND_P99 below; per seed in seacast_elastic_all_bound.tsv). Right: bytes per node
against the uplink, with a dotted line at one copy of the compressed payload. Refuses to draw a point
with fewer than ten seeds.
"""
import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

HERE = Path(__file__).resolve().parent
MIN_SEEDS = 10
SERIES = [("seacast", "SEACAST"), ("ecbroadcast-rs", "ECBroadcast RS"), ("gossipsub", "today's gossipsub")]
COLOUR = {"seacast": "#2a78d6", "ecbroadcast-rs": "#eb6834", "gossipsub": "#3a3a36"}
MARKER = {"seacast": "o", "ecbroadcast-rs": "s", "gossipsub": "^"}
# x nudge so bars do not overlap; off by default since 2026-10-22 (no two series' ranges overlap at any
# uplink in either panel), on with --dodge
OFFSET = {"seacast": 1.0, "ecbroadcast-rs": 1.035, "gossipsub": 0.966}
# The lower bound for the 99th-percentile receiver, median over the ten networks: the corrected links'
# bound, the max of individually valid terms: the payload's bytes out of the source, then the late chunks'
# doubling or their fastest paths at one chunk's sending time per forwarding node (less the one-packet burst);
# the total upload; each receiver's downlink from its first possible incoming bit. Per warm payload, with that
# payload's size and the smallest chunk any of the three arms sends, so one line bounds all three. Per network
# in data/seacast_elastic_all_bound.tsv. It replaces an earlier formula, which added overlapping terms, counted
# the source's step twice and took the direct latency as a floor.
BOUND_P99 = {50: 0.201, 25: 0.322, 20: 0.382, 10: 0.683}
ONE_COPY_MIB = 746262 / 2**20          # the compressed payload, the copies' unit elsewhere in the post
INK, MUTED, GRID, BOUNDC = "#1f1f1f", "#55554f", "#e6e6e6", "#b4b4ae"

ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("--csv", type=Path, default=HERE / "seacast_elastic_all.csv")
ap.add_argument("--out", type=Path, default=HERE / "seacast_elastic_all.png")
ap.add_argument("--dodge", action="store_true", help="set the series a little apart sideways")
args = ap.parse_args()

cells = defaultdict(dict)    # (series, uplink) -> {seed: (p99, mib)}
for row in csv.DictReader(open(args.csv, newline="")):
    key = (row["series"].strip(), int(float(row["uplink_mbps"])))
    cells[key][row["seed"].strip()] = (float(row["p99_s"]), float(row["mib"]))
uplinks = sorted({u for _, u in cells})
few = [f"{s} at {u} Mbps: {len(cells.get((s, u), {}))} seeds" for s, _ in SERIES for u in uplinks
       if len(cells.get((s, u), {})) < MIN_SEEDS]
if few:
    sys.exit("fewer than ten seeds:\n  " + "\n  ".join(few))

plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})
fig, (axt, axb) = plt.subplots(1, 2, figsize=(9, 3.7), dpi=150)
handles = []
for s, name in SERIES:
    xs = [u * (OFFSET[s] if args.dodge else 1.0) for u in uplinks]
    for ax, k in ((axt, 0), (axb, 1)):
        med = [statistics.median(v[k] for v in cells[(s, u)].values()) for u in uplinks]
        lo = [min(v[k] for v in cells[(s, u)].values()) for u in uplinks]
        hi = [max(v[k] for v in cells[(s, u)].values()) for u in uplinks]
        h = ax.errorbar(xs, med, yerr=[[m - l for m, l in zip(med, lo)], [h_ - m for m, h_ in zip(med, hi)]],
                        color=COLOUR[s], marker=MARKER[s], ms=5, lw=1.6, capsize=2.5, elinewidth=1.0,
                        label=name, zorder=3)
        if ax is axt:
            handles.append(h)
hb, = axt.plot(uplinks, [BOUND_P99[u] for u in uplinks], color=BOUNDC, lw=2.2, zorder=1,
               label="lower bound the links set (median of the networks)")
axb.axhline(ONE_COPY_MIB, color=MUTED, lw=0.9, ls=(0, (1, 2)), zorder=1)
axb.text(uplinks[-1] * 1.05, ONE_COPY_MIB * 0.93, "one copy", color=MUTED, fontsize=8, ha="right", va="top")

for ax in (axt, axb):
    ax.set_xscale("log")
    ax.set_xlim(uplinks[0] * 0.85, uplinks[-1] * 1.12)
    ax.xaxis.set_major_locator(FixedLocator(uplinks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel("every node's uplink (Mbps); downlink twice that")
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
axt.set_yscale("log")
axt.set_ylim(0.15, 40)
axt.yaxis.set_major_locator(FixedLocator([0.2, 0.5, 1, 2, 5, 10, 20]))
axt.yaxis.set_minor_locator(NullLocator())
axt.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
axt.set_ylabel("time for 99 % of nodes (s, log)")
axb.set_ylim(0, 6.2)
axb.set_ylabel("bytes received per node (MiB)")
fig.legend(handles=handles + [hb], loc="lower center", ncol=4, frameon=False, fontsize=8.5,
           bbox_to_anchor=(0.5, -0.01))
fig.tight_layout(rect=(0, 0.07, 1, 1), w_pad=2.0)
args.out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(args.out, facecolor="white")
print(f"wrote {args.out}")
