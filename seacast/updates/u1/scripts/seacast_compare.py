"""Today's gossipsub, ECBroadcast's Reed-Solomon mode, FullDAS and SEACAST, run in one simulator with
paired seeds: Figure 4 of the SEACAST announcement post, as updated in its first reply.

usage: seacast_compare.py [--csv PATH] [--out PATH] [--allow-few]

--csv  one row per run: network (all-home | dcb20), protocol (seacast | ecbroadcast-rs | gossipsub,
       and optionally fulldas | tier1 | tier2 | tier3), seed, p99_s (time for 99 % of nodes to hold
       the payload, s), mib (bytes received per node, MiB), connections (per node). Default:
       seacast_compare.csv beside this script.
--out  the PNG. Default: seacast_compare.png beside this script.
--allow-few  draw even when a network x protocol has fewer than ten seeds (dummy tests only).

Two panels, one per network. x = bytes received per node (linear, from 0), y = p99 (log, shared
across panels: gossipsub's seconds and SEACAST's fractions of a second on one axis). Small points:
one per seed per protocol; thin grey lines join the protocols' points of the same seed; large
markers: each protocol's median over seeds (p99 and bytes each), labelled with both values. FullDAS
(every node sampling every cell, so that it delivers the whole payload), when the CSV has it: drawn
like the other three, second on the paired-seed line. Tiers
1-3 (the earlier posts' steps toward SEACAST, run at the same settings), when the CSV has them: their
medians only, open markers in SEACAST's colour, joined by a dashed line that ends at SEACAST's median
(the fourth tier).
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
NETWORKS = [("all-home", "All-home network"), ("dcb20", "Mixed-bandwidth network, datacenter builder")]
# Drawn in this order; the paired-seed line runs through them in this order (bytes rise along it).
PROTOCOLS = [("seacast", "SEACAST"), ("ecbroadcast-rs", "ECBroadcast RS"), ("gossipsub", "today's gossipsub")]
# Colour-blind-safe trio (a blue, an orange and a near-black), with shape as a second encoding.
COLOUR = {"seacast": "#2a78d6", "ecbroadcast-rs": "#eb6834", "gossipsub": "#3a3a36"}
MARKER = {"seacast": "o", "ecbroadcast-rs": "s", "gossipsub": "^"}
# FullDAS, when the CSV has it: the third categorical slot after the blue and orange (aqua), a diamond.
FULLDAS = ("fulldas", "FullDAS")
COLOUR["fulldas"], MARKER["fulldas"] = "#1baf7a", "D"
# Label placements that differ from the default rule below, placed by eye: (network, protocol) ->
# (anchor on the seed cloud, offset in points, ha, va, leader line to the median).
LABEL = {("all-home", "fulldas"): ("below", (0, 22), "center", "bottom", True),
         ("dcb20", "fulldas"): ("below", (18, 30), "center", "bottom", True),
         ("dcb20", "ecbroadcast-rs"): ("right", (6, 0), "left", "center", False)}
# The earlier posts' tiers 1-3, drawn as medians on the dashed path to SEACAST (tier 4). Label offsets
# in points per network, placed by eye clear of the protocols' labels.
TIERS = [("tier1", "tier 1"), ("tier2", "tier 2"), ("tier3", "tier 3")]
TIER_LABEL = {("all-home", "tier1"): (0, 7, "center", "bottom"), ("all-home", "tier2"): (-6, 0, "right", "center"),
              ("all-home", "tier3"): (6, -4, "left", "top"),
              ("dcb20", "tier1"): (0, 7, "center", "bottom"), ("dcb20", "tier2"): (-6, 0, "right", "center"),
              ("dcb20", "tier3"): (0, 8, "center", "bottom")}
INK, MUTED, GRID, PAIR = "#1f1f1f", "#55554f", "#e6e6e6", "#a8a8a8"
YTICKS = [0.2, 0.3, 0.5, 1, 2, 3, 5]

ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("--csv", type=Path, default=HERE / "seacast_compare.csv")
ap.add_argument("--out", type=Path, default=HERE / "seacast_compare.png")
ap.add_argument("--allow-few", action="store_true", help="draw with fewer than ten seeds (dummy tests only)")
args = ap.parse_args()

runs = defaultdict(dict)   # (network, protocol) -> {seed: (p99 s, MiB)}
conns = defaultdict(set)   # network -> connection counts seen
problems = []
for src in [args.csv]:
  with open(src, newline="") as f:
    for i, row in enumerate(csv.DictReader(f), start=2):
        key = (row["network"].strip(), row["protocol"].strip())
        seed = row["seed"].strip()
        if seed in runs[key]:
            problems.append(f"{src}:{i}: {key[0]} x {key[1]} seed {seed} appears twice")
        runs[key][seed] = (float(row["p99_s"]), float(row["mib"]))
        conns[key[0]].add(row["connections"].strip())

if any((n, FULLDAS[0]) in runs for n, _ in NETWORKS):
    PROTOCOLS = PROTOCOLS[:1] + [FULLDAS] + PROTOCOLS[1:]
PAIRED = len(PROTOCOLS)   # the paired-seed line runs through these
tiers = [(t, name) for t, name in TIERS if any((n, t) in runs for n, _ in NETWORKS)]
known = {(n, p) for n, _ in NETWORKS for p, _ in PROTOCOLS + tiers}
for key in sorted(set(runs) - known):
    print(f"note: skipping {key[0]} x {key[1]} ({len(runs[key])} rows): not in the figure", file=sys.stderr)
few = [f"{n} x {p}: {len(runs.get((n, p), {}))} seeds" for n, _ in NETWORKS for p, _ in PROTOCOLS + tiers
       if len(runs.get((n, p), {})) < MIN_SEEDS]
for n, _ in NETWORKS:
    if len(conns[n]) > 1:
        problems.append(f"{n}: rows with different connection counts {sorted(conns[n])}")
if problems or (few and not args.allow_few):
    for p in problems:
        print("error:", p, file=sys.stderr)
    if few and not args.allow_few:
        print(f"error: fewer than {MIN_SEEDS} seeds (pass --allow-few for a dummy test only):", file=sys.stderr)
        for line in few:
            print("  " + line, file=sys.stderr)
    sys.exit(1)
for line in few:
    print(f"warning: drawing with {line} (--allow-few)", file=sys.stderr)

plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})
fig, axes = plt.subplots(1, 2, figsize=(9, 3.9), dpi=150, sharey=True)
alltimes = [t for (n, p), seeds in runs.items() if (n, p) in known for t, _ in seeds.values()]
ylo, yhi = min(YTICKS[0], min(alltimes) * 0.6), max(alltimes) * 1.6

for ax, (net, title) in zip(axes, NETWORKS):
    order = [runs[(net, p)] for p, _ in PROTOCOLS[:PAIRED]]
    for seed in sorted(set.intersection(*(set(r) for r in order))):   # paired seeds, every protocol
        pts = [r[seed] for r in order]
        ax.plot([b for _, b in pts], [t for t, _ in pts], color=PAIR, lw=0.6, alpha=0.7, zorder=1,
                solid_capstyle="round")
    for proto, name in PROTOCOLS:
        seeds = runs[(net, proto)]
        ts = [t for t, _ in seeds.values()]
        bs = [b for _, b in seeds.values()]
        ax.scatter(bs, ts, s=14, marker=MARKER[proto], color=COLOUR[proto], alpha=0.45, linewidths=0, zorder=2)
        mt, mb = statistics.median(ts), statistics.median(bs)
        ax.scatter([mb], [mt], s=90, marker=MARKER[proto], color=COLOUR[proto], edgecolor="white",
                   linewidth=1.5, zorder=4)
        # SEACAST sits low and left: label it below and to the right of its seed cloud. The other two
        # sit higher and to the right: label each above and to the left of its cloud, clear of the
        # paired-seed lines, which run up and to the right.
        # With the tiers drawn, ECBroadcast's label goes below too: the dashed path from tier 1 to
        # tier 2 runs above its cloud.
        if proto == "seacast" or (tiers and proto == "ecbroadcast-rs"):
            xy, off, ha, va = (max(bs), min(ts)), (2, -5), "left", "top"
        else:
            xy, off, ha, va = (min(bs), max(ts)), (-2, 5), "right", "bottom"
        leader = None
        if (net, proto) in LABEL:
            anchor, off, ha, va, lead = LABEL[(net, proto)]
            xy = {"lower left": (min(bs), min(ts)), "lower right": (max(bs), min(ts)),
                  "upper left": (min(bs), max(ts)), "right": (max(bs), mt), "below": (mb, min(ts))}[anchor]
            if lead:   # the label sits away from its cloud: a thin line from it to the median
                xy, leader = (mb, mt), dict(arrowstyle="-", color=MUTED, lw=0.6, shrinkA=2, shrinkB=6)
        ax.annotate(f"{name}\n{mt:.2f} s, {mb:.1f} MiB", xy, xytext=off, textcoords="offset points",
                    ha=ha, va=va, color=INK, fontsize=8.5, linespacing=1.25, arrowprops=leader)
    # The tiers: medians on a dashed path that ends at SEACAST's median, the fourth tier.
    tier_meds = [(statistics.median(b for _, b in runs[(net, p)].values()),
                  statistics.median(t for t, _ in runs[(net, p)].values())) for p, _ in tiers]
    if tiers:
        s4 = runs[(net, "seacast")].values()
        path = tier_meds + [(statistics.median(b for _, b in s4), statistics.median(t for t, _ in s4))]
        ax.plot([b for b, _ in path], [t for _, t in path], color=COLOUR["seacast"], lw=1.0,
                ls=(0, (3, 2.5)), alpha=0.8, zorder=3)
        for (proto, name), (mb, mt) in zip(tiers, tier_meds):
            ax.scatter([mb], [mt], s=42, marker="o", facecolor="white", edgecolor=COLOUR["seacast"],
                       linewidth=1.3, zorder=4)
            dx, dy, ha, va = TIER_LABEL.get((net, proto), (6, 2, "left", "bottom"))
            ax.annotate(name, (mb, mt), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                        color=COLOUR["seacast"], fontsize=8)
    xmax = max([b for p, _ in PROTOCOLS for _, b in runs[(net, p)].values()] + [b for b, _ in tier_meds])
    ax.set_xlim(0, xmax * 1.1)
    ax.set_yscale("log")
    ax.set_ylim(ylo, yhi)
    ax.yaxis.set_major_locator(FixedLocator([v for v in YTICKS if ylo <= v <= yhi]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_title(title, fontsize=10, color=INK)
    ax.set_xlabel("bytes received per node (MiB)")
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
axes[0].set_ylabel("time for 99 % of nodes to\nhold the payload, p99 (s, log)")

# Mark key, in the empty top-left corner of the first panel.
key = [plt.Line2D([], [], ls="none", marker="o", ms=4, color=MUTED, alpha=0.45, mew=0, label="one simulated network"),
       plt.Line2D([], [], color=PAIR, lw=0.8, label=f"same network, {['two', 'three', 'four'][PAIRED - 2]} protocols"),
       plt.Line2D([], [], ls="none", marker="o", ms=8, color=MUTED, mec="white", mew=1.2,
                  label=f"median of {min(len(s) for k, s in runs.items() if k in known)} networks")]
if tiers:
    key.append(plt.Line2D([], [], color=COLOUR["seacast"], lw=1.0, ls=(0, (3, 2.5)), marker="o", ms=5.5,
                          mfc="white", mec=COLOUR["seacast"], mew=1.2,
                          label="tiers 1–3, the steps to SEACAST (medians)"))
axes[0].legend(handles=key, loc="upper left", frameon=False,
               fontsize=7.5, handlelength=1.6, labelcolor=MUTED)

fig.tight_layout(w_pad=2.0)
args.out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(args.out, facecolor="white")
print(f"wrote {args.out}")
