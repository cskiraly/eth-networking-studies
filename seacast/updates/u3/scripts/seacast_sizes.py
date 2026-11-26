"""Payload size: today's gossipsub, ECBroadcast's Reed-Solomon mode and SEACAST in one simulator, 128 KiB to
4 MiB, 500 nodes with 16 connections each, the all-home network and the mixed-bandwidth network with a datacenter
builder, ten paired seeds per point (render with seacast_sizes_render.sh).

usage: seacast_sizes.py [--csv PATH] [--schedule PATH ...] [--out PATH] [--gs-gap MS] [--min-seeds N]
                        [--no-variants]

--csv  one row per cell (update 2's data/sizes.csv): network, protocol, size_kib, seed, gap_ms, disc, shape,
       passed, msgs, p99_s, mib, p99_max_warm_s, compressed_b, log; other columns are ignored. Repeat it to
       add files of the same columns (update 3's 32 and 64 KiB cells). Default: seacast_sizes.csv beside this
       script.
--schedule  one row per cell of SEACAST's one schedule from the tuning (update 3's
       data/tuning/schedule-cells-A.csv and -B.csv, written by schedule_cells.py): network, size_kib, seed,
       setting, passed, msgs, p99_s, mib, bin_md5, log; other columns are ignored. Repeat it for each file. Only
       the sizes of --csv are drawn. Without it the figure is update 2's.
--out  the PNG. Default: seacast_sizes.png beside this script.
--gs-gap  gossipsub's gap (ms) at 2 and 4 MiB, as run ("" = the harness's 12 s).
--no-variants  leave out the two open variants below; version 3's published figure has it.

Top: the time for 99 % of the nodes (log) against the payload (log). Bottom: bytes received per node, in copies
of that size's compressed payload (from ECBroadcast's logs, the payloads being the same at every seed). Points
are medians over the networks, bars their range. SEACAST's line is the specification's: the ask discipline at
every size, and at 4 MiB the plain group the codec limit leaves (MAX_CHUNKS = 256, data and parity). Two
variants are drawn open: below 512 KiB with the ask discipline off, as the runner of the earlier posts left
it, and with it the three v0.5 rules that need parking (the promise at the write, the last resort, the ledger
from offers; the other three on); and at 4 MiB coded with 32 KiB chunks. Refuses to draw a point with fewer than --min-seeds seeds (ten).

With --schedule, SEACAST tuned by size (the one schedule) is the main SEACAST line, drawn from the tuning's
cells on the same networks, and update 2's SEACAST lines (the earlier posts' settings, and the two open
variants) are drawn in a lighter blue. The two families are set slightly apart on the size axis (a factor of
1.04 each way) so that both stay visible where the schedule keeps the earlier settings. The tuning's bytes are
counted in copies of the same basis as the others (ECBroadcast's compressed payload).
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
COLOUR = {"seacast": "#2a78d6", "seacast-earlier": "#7fb0ee", "ecbroadcast-rs": "#eb6834", "gossipsub": "#3a3a36"}
INK, MUTED, GRID = "#1f1f1f", "#55554f", "#e6e6e6"
NETS = [("all-home", "all-home network"), ("dcb20", "mixed-bandwidth network, datacenter builder")]

ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
ap.add_argument("--csv", type=Path, action="append", default=[])
ap.add_argument("--schedule", type=Path, action="append", default=[])
ap.add_argument("--out", type=Path, default=HERE / "seacast_sizes.png")
ap.add_argument("--gs-gap", default="")
ap.add_argument("--min-seeds", type=int, default=10)
ap.add_argument("--no-variants", action="store_true", help="leave out the two open variants")
ap.add_argument("--note", default="", help="a banner across the top, for provisional renders")
args = ap.parse_args()

# series key -> (network, size) -> {seed: (p99, mib)}
cells = defaultdict(lambda: defaultdict(dict))
comp = defaultdict(list)
rows = [r for path in (args.csv or [HERE / "seacast_sizes.csv"]) for r in csv.DictReader(open(path, newline=""))]
for r in rows:
    if r["passed"] != "True" or r["msgs"] != "6":
        sys.exit(f"a cell that did not pass or ran short: {r['log']}")
    proto, net, size = r["protocol"], r["network"], int(r["size_kib"])
    if proto == "gossipsub":
        if size >= 2048 and r["gap_ms"] != args.gs_gap:
            continue
        if size < 2048 and r["gap_ms"]:
            continue
        key = "gossipsub"
    elif proto == "ecbroadcast-rs":
        key = "ecbroadcast-rs"
        if r["compressed_b"]:
            comp[size].append(int(r["compressed_b"]))
    else:
        if size < 512:
            key = "seacast" if r["disc"] == "all" else "seacast-nodisc"
        elif size == 4096:
            key = "seacast" if r["shape"] == "plain" else "seacast-unit32"
        else:
            key = "seacast"
    if args.no_variants and key in ("seacast-nodisc", "seacast-unit32"):
        continue
    if r["seed"] in cells[key][(net, size)]:
        sys.exit(f"two cells of one point and seed: {r['log']}")
    cells[key][(net, size)][r["seed"]] = (float(r["p99_s"]), float(r["mib"]))

one_copy = {s: statistics.median(v) / 2**20 for s, v in comp.items()}
TUNED = bool(args.schedule)
if TUNED:
    md5s = set()
    for path in args.schedule:
        for r in csv.DictReader(open(path, newline="")):
            if r["passed"] != "True" or r["msgs"] != "6":
                sys.exit(f"a schedule cell that did not pass or ran short: {r['log']}")
            net, size = r["network"], int(r["size_kib"])
            if size not in one_copy:
                continue    # a size Figure 6 does not run (32 and 64 KiB)
            md5s.add(r["bin_md5"])
            if r["seed"] in cells["seacast-schedule"][(net, size)]:
                sys.exit(f"two schedule cells of one point and seed: {r['log']}")
            cells["seacast-schedule"][(net, size)][r["seed"]] = (float(r["p99_s"]), float(r["mib"]))
    if len(md5s) != 1:
        sys.exit(f"the schedule's cells ran {len(md5s)} SEACAST binaries")
    if {k for k in cells["seacast-schedule"]} != {k for k in cells["seacast"]}:
        sys.exit("the schedule's points are not Figure 6's SEACAST points")
few =[f"{k} {n} {s} KiB: {len(v)} seeds" for k, d in cells.items() for (n, s), v in d.items()
       if len(v) < args.min_seeds]
if few:
    sys.exit(f"fewer than {args.min_seeds} seeds:\n  " + "\n  ".join(sorted(few)))

STYLE = {  # key: label, colour, marker, filled, line style
    "seacast": ("SEACAST", "seacast", "o", True, "-"),
    "seacast-nodisc": ("SEACAST below 512 KiB, ask discipline off\n(and v0.5's three rules that need it)", "seacast", "o", False, (0, (3, 2))),
    "seacast-unit32": ("SEACAST at 4 MiB, coded with 32 KiB chunks", "seacast", "D", False, ""),
    "ecbroadcast-rs": ("ECBroadcast RS", "ecbroadcast-rs", "s", True, "-"),
    "gossipsub": ("today's gossipsub", "gossipsub", "^", True, "-"),
}
SHIFT = {}
if TUNED:
    STYLE.update({
        "seacast-schedule": ("SEACAST tuned by size (one schedule)", "seacast", "o", True, "-"),
        "seacast": ("SEACAST at the earlier posts' settings", "seacast-earlier", "o", True, "-"),
        "seacast-nodisc": ("earlier settings below 512 KiB, ask discipline off\n(and v0.5's three rules that need it)",
                           "seacast-earlier", "o", False, (0, (3, 2))),
        "seacast-unit32": ("earlier settings at 4 MiB, coded with 32 KiB chunks\n(the specification's code)",
                           "seacast-earlier", "D", False, ""),
    })
    SHIFT = {"seacast-schedule": 1.04, "seacast": 1 / 1.04, "seacast-nodisc": 1 / 1.04, "seacast-unit32": 1 / 1.04}
sizes_all =sorted({s for d in cells.values() for (_, s) in d})

plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})
TALL = TUNED and not args.no_variants   # the legend's two-line labels take a third row
fig, axes = plt.subplots(2, 2, figsize=(9, 6.8 if TALL else 6.4), dpi=150, sharex=True)
handles = {}
for col, (net, title) in enumerate(NETS):
    axt, axb = axes[0][col], axes[1][col]
    axt.set_title(title, fontsize=9, color=INK)
    for key in ["gossipsub", "ecbroadcast-rs", "seacast-nodisc", "seacast-unit32", "seacast", "seacast-schedule"]:
        if key not in cells:
            continue
        label, c, mk, filled, ls = STYLE[key]
        dx, top = SHIFT.get(key, 1), 0.5 if key == "seacast-schedule" else 0   # the tuned line on top
        pts = sorted(s for (n, s) in cells[key] if n == net)
        if key == "seacast-nodisc" and (net, 512) in cells["seacast"]:
            pts_line = pts + [512]    # the open line joins SEACAST's at 512 KiB, where both are the same
        else:
            pts_line = pts
        for ax, k in ((axt, 0), (axb, 1)):
            def stat(s, f):
                src = cells["seacast"] if (key == "seacast-nodisc" and s == 512) else cells[key]
                v = [x[k] for x in src[(net, s)].values()]
                if k == 1:
                    v = [x / one_copy[s] for x in v]
                return f(v)
            med = [stat(s, statistics.median) for s in pts_line]
            lo = [stat(s, min) for s in pts]
            hi = [stat(s, max) for s in pts]
            if ls:
                ax.plot([s * 1024 * dx for s in pts_line], med, color=COLOUR[c], lw=1.4 if filled else 1.1, ls=ls,
                        zorder=2 + top)
            h = ax.errorbar([s * 1024 * dx for s in pts], [stat(s, statistics.median) for s in pts],
                            yerr=[[m - l for m, l in zip([stat(s, statistics.median) for s in pts], lo)],
                                  [h_ - m for m, h_ in zip([stat(s, statistics.median) for s in pts], hi)]],
                            color=COLOUR[c], marker=mk, ms=5 if filled else 5.5, lw=0, elinewidth=1.0, capsize=2.5,
                            mfc=COLOUR[c] if filled else "white", mec=COLOUR[c], label=label, zorder=3 + top)
            handles.setdefault(key, h)
    axb.axhline(1.0, color=MUTED, lw=0.9, ls=(0, (1, 2)), zorder=1)
    axb.text(sizes_all[-1] * 1024 * 1.25, 0.93, "one copy", color=MUTED, fontsize=8, ha="right", va="top")

for ax in axes.flat:
    ax.set_xscale("log", base=2)
    ax.set_xlim(sizes_all[0] * 1024 / 1.3, sizes_all[-1] * 1024 * 1.3)
    ax.xaxis.set_major_locator(FixedLocator([s * 1024 for s in sizes_all]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 2**20:g} MiB" if v >= 2**20 else f"{v / 1024:g} KiB"))
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
for ax in axes[0]:
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(FixedLocator([0.1, 0.2, 0.5, 1, 2, 5, 10, 20]))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
axes[0][0].set_ylabel("time for 99 % of nodes (s, log)")
axes[1][0].set_ylabel("bytes received per node\n(copies of the compressed payload)")
for ax in axes[1]:
    ax.set_xlabel("payload (uncompressed)")
    ax.set_ylim(bottom=0)
order = [k for k in ["seacast-schedule", "seacast", "seacast-nodisc", "seacast-unit32", "ecbroadcast-rs", "gossipsub"]
         if k in handles]
fig.legend(handles=[handles[k] for k in order], loc="lower center", ncol=2 if len(order) == 4 else 3,
           frameon=False, fontsize=8.5,
           bbox_to_anchor=(0.5, -0.005))
top = 1.0
if args.note:
    fig.suptitle(args.note, color="#b3261e", fontsize=9.5, fontweight="bold")
    top = 0.95
fig.tight_layout(rect=(0, 0.115 if TALL else 0.075, 1, top), w_pad=2.0, h_pad=1.2)
args.out.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(args.out, facecolor="white")
print(f"wrote {args.out}")
