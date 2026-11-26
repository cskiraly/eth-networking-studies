#!/usr/bin/env python3
"""Figure 6's tuned line read against update 2's lines: the numbers the living text cites for it.

usage: figure6.py --sizes update-2/data/sizes.csv [--sizes small/sizes-small.csv] schedule-cells-A.csv
                  schedule-cells-B.csv

--sizes is repeatable: update 2's cells (128 KiB to 4 MiB), and update 3's of the same arms at 32 and 64 KiB.
Per point (network, size) of Figure 6: the medians over the ten networks (seeds 7 to 16) of
the time for 99 % of the nodes and of the bytes per node, in copies of the point's compressed payload as
Figure 6 counts them (the median of ECBroadcast's compressed payloads at that size, from sizes.csv), for the
one schedule (the tuning's cells), ECBroadcast RS and SEACAST at the earlier settings (sizes.csv's SEACAST line:
the ask discipline on below 512 KiB, the plain group at 4 MiB). Then, paired by seed: on how many networks the
schedule is faster and lighter than ECBroadcast, and the median of the per-network time gains
(1 - t_schedule / t_ECBroadcast); and, also paired by seed, the same counts against today's gossipsub as Figure 6
draws it (payloads 40 s apart at 2 and 4 MiB), with its medians. Where the schedule is the earlier settings
(256 KiB to 2 MiB), the median of the per-network changes between the two runs (t_schedule / t_earlier - 1, and
the same for bytes).
Exits 1 if a point lacks a seed in any of the four.
"""
import csv
import statistics as st
import sys
from collections import defaultdict

SEEDS = {str(s) for s in range(7, 17)}


def main():
    a = sys.argv[1:]
    rows = []
    while len(a) >= 2 and a[0] == "--sizes":
        rows += csv.DictReader(open(a[1], newline=""))
        a = a[2:]
    if not rows or not a:
        sys.exit(__doc__)
    comp = defaultdict(list)
    for r in rows:
        if r["protocol"] == "ecbroadcast-rs" and r["compressed_b"]:
            comp[int(r["size_kib"])].append(int(r["compressed_b"]))
    one = {s: st.median(v) / 2**20 for s, v in comp.items()}
    ecb, earlier, sched, gs = defaultdict(dict), defaultdict(dict), defaultdict(dict), defaultdict(dict)
    for r in rows:
        s = int(r["size_kib"])
        k, v = (r["network"], s), (float(r["p99_s"]), float(r["mib"]) / one[s])
        if r["protocol"] == "ecbroadcast-rs":
            ecb[k][r["seed"]] = v
        elif r["protocol"] == "seacast" and (r["disc"] in ("", "all")) and r["shape"] in ("", "plain"):
            earlier[k][r["seed"]] = v
        elif r["protocol"] == "gossipsub" and r["gap_ms"] == ("40000" if s >= 2048 else ""):
            gs[k][r["seed"]] = v
    for path in a:
        for r in csv.DictReader(open(path, newline="")):
            s = int(r["size_kib"])
            if s in one:
                sched[(r["network"], s)][r["seed"]] = (float(r["p99_s"]), float(r["mib"]) / one[s])
    short = [f"{k}" for k in sorted(sched)
             if not (set(sched[k]) == set(ecb[k]) == set(earlier[k]) == set(gs[k]) == SEEDS)]
    if short or not sched:
        sys.exit(f"points without the ten seeds in all four: {short or 'no schedule rows'}")
    med = lambda d, i: st.median(v[i] for v in d.values())  # noqa: E731
    print("point: medians of ten (s, copies): the schedule | ECBroadcast RS | the earlier settings; "
          "the schedule against ECBroadcast, paired by seed")
    for k in sorted(sched):
        t, e, o = sched[k], ecb[k], earlier[k]
        fast = sum(t[x][0] < e[x][0] for x in t)
        light = sum(t[x][1] < e[x][1] for x in t)
        gain = st.median(1 - t[x][0] / e[x][0] for x in t)
        line = (f"{k[1]:>5} KiB {k[0]:<8} {med(t, 0):.4f} s {med(t, 1):.2f} | {med(e, 0):.4f} s {med(e, 1):.2f} | "
                f"{med(o, 0):.4f} s {med(o, 1):.2f}; faster on {fast} of 10, lighter on {light} of 10, "
                f"median time gain {gain * 100:.1f} %")
        g = gs[k]
        line += (f"; against gossipsub ({med(g, 0):.4f} s {med(g, 1):.2f}): faster on "
                 f"{sum(t[x][0] < g[x][0] for x in t)} of 10, lighter on {sum(t[x][1] < g[x][1] for x in t)} of 10")
        if 256 <= k[1] <= 2048:
            dt = st.median(t[x][0] / o[x][0] - 1 for x in t)
            db = st.median(t[x][1] / o[x][1] - 1 for x in t)
            line += f"; against the earlier settings' run: time {dt * 100:+.1f} %, bytes {db * 100:+.1f} %"
        print(line)


if __name__ == "__main__":
    main()
