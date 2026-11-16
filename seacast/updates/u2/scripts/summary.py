#!/usr/bin/env python3
"""Figure 6's numbers as a table: summary.py [sizes.csv] > summary.txt

Per network, series and size: n (networks), the median and range of the time for 99 % of the nodes (s), and the
median and range of bytes per node in copies of that size's compressed payload (the median over ECBroadcast's
logs of each payload's compressed size, the same at every seed). Then, per network and size, paired by network
(seed): on how many networks SEACAST (the specification's form: the ask discipline below 512 KiB, the plain
group at 4 MiB) is faster and lighter than each other series.
"""
import collections
import csv
import os
import statistics as st
import sys

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "sizes.csv")
rows = list(csv.DictReader(open(path)))
comp = collections.defaultdict(list)
for r in rows:
    if r["compressed_b"]:
        comp[int(r["size_kib"])].append(int(r["compressed_b"]))
one = {s: st.median(v) / 2**20 for s, v in comp.items()}
d = collections.defaultdict(dict)
for r in rows:
    k = r["protocol"] + ("/" + r["disc"] if r["disc"] else "") + ("/" + r["shape"] if r["shape"] else "")
    d[(r["network"], k, int(r["size_kib"]))][int(r["seed"])] = (float(r["p99_s"]), float(r["mib"]))
SIZES = (128, 256, 512, 1024, 2048, 4096)
print("compressed payload, MiB:", ", ".join(f"{s} KiB {one[s]:.3f}" for s in sorted(one)))
for net in ("all-home", "dcb20"):
    print(f"\n== {net}: series, size: n, time median [min-max] s, copies median [min-max]")
    for k in sorted({x[1] for x in d if x[0] == net}):
        for s in SIZES:
            v = d.get((net, k, s))
            if not v:
                continue
            p = [x[0] for x in v.values()]
            c = [x[1] / one[s] for x in v.values()]
            print(f"  {k:16s} {s:5d}: n {len(v):2d}, {st.median(p):.3f} [{min(p):.3f}-{max(p):.3f}] s, "
                  f"{st.median(c):.2f} [{min(c):.2f}-{max(c):.2f}] copies")


def spec(s):
    return "seacast/all" if s < 512 else "seacast/plain" if s == 4096 else "seacast"


for net in ("all-home", "dcb20"):
    print(f"\n== {net}: SEACAST as specified against each series, paired by network")
    for s in SIZES:
        a = d.get((net, spec(s), s), {})
        out = []
        for o in ("ecbroadcast-rs", "gossipsub", "seacast/runner", "seacast/unit32"):
            b = d.get((net, o, s), {})
            com = sorted(set(a) & set(b))
            if com:
                out.append(f"{o}: faster {sum(a[x][0] < b[x][0] for x in com)}/{len(com)}, "
                           f"lighter {sum(a[x][1] < b[x][1] for x in com)}/{len(com)}")
        print(f"  {s:5d}: " + "; ".join(out))
