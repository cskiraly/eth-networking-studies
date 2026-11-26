#!/usr/bin/env python3
"""The one schedule's cells, one row per point and seed, for the living text's Figure 6: at each point (size and
network), the ten cells of seeds 7 to 16 of the schedule's setting (schedule.py's SCHEDULE, the default where it
names none).

usage: schedule_cells.py --expect LIST.dry ... --best best-<machine>.csv --check schedule-<machine>.csv
                         --csv OUT HOST=cells.csv ...

The rows, the lists and best-<machine>.csv are schedule.py's, and fronts.analyse's checks hold. A point is
refused, and nothing is written, if its schedule setting is not ok at all ten seeds (fronts.py's status). Known
answer, checked on every run: at every point, the medians of the rows written (time, and bytes over the point's
compressed payload) must equal the schedule's time and copies in --check (schedule.py's CSV), as schedule.py
prints them, or the script exits 1. Output columns: host, network, size_kib, seed, setting, passed, msgs, p99_s,
mib, comp_b, bin_md5, log (the cell's own values; the figure counts bytes in copies of its own basis).
"""
import csv
import statistics as st
import sys

import best  # best.py's seeds; it imports fronts
import schedule  # the schedule itself and how its setting is found

fronts = best.fronts
COLS = ["host", "network", "size_kib", "seed", "setting", "passed", "msgs", "p99_s", "mib", "comp_b", "bin_md5", "log"]


def main():
    a = sys.argv[1:]
    files, expect, bests, checks, out_csv = [], [], [], [], None
    while a:
        x = a.pop(0)
        if x == "--expect":
            expect.append(a.pop(0))
        elif x == "--best":
            bests.append(a.pop(0))
        elif x == "--check":
            checks.append(a.pop(0))
        elif x == "--csv":
            out_csv = a.pop(0)
        elif x.startswith("--"):
            sys.exit(__doc__)
        else:
            files.append(x)
    if not files or not expect or not bests or not checks or not out_csv:
        sys.exit(__doc__)
    rows, exp = fronts.load(files), fronts.load_expect(expect)
    bad = best.strays(rows, exp)
    if bad:
        sys.exit(f"{len(bad)} rows of seeds 7 to 16 are no cell of the lists given: " + "; ".join(bad[:5]))
    _, res = fronts.analyse(rows, list(best.SEEDS), 500, exp)
    brow, want = {}, {}
    for p in bests:
        for r in csv.DictReader(open(p)):
            brow[(int(r["size_kib"]), r["network"])] = r
    for p in checks:
        for r in csv.DictReader(open(p)):
            want[(int(r["size_kib"]), r["network"])] = (r["schedule_s"], r["schedule_copies"])
    out, refused, differ = [], [], []
    for point in sorted(brow):
        size, net = point
        pi = res.get(point)
        nm = schedule.SCHEDULE[size] or brow[point]["default"]
        s = schedule.by_name(pi["settings"], nm) if pi and not pi["missing"] else None
        if s is None or pi["settings"][s]["status"] != "ok":
            refused.append(f"{size} {net} {nm}")
            continue
        d = pi["settings"][s]
        cells = [d["cells"][x] for x in sorted(d["cells"])]
        t = st.median(float(c["p99_s"]) for c in cells)
        cp = st.median(float(c["mib"]) for c in cells) / pi["comp_mib"]
        got = (f"{t:.4f}", f"{cp:.2f}")
        if want.get(point) != got:
            differ.append(f"{size} {net}: {got} against {want.get(point)}")
        for c in cells:
            out.append({"host": c["host"], "network": net, "size_kib": size, "seed": c["seed"], "setting": nm,
                        "passed": c["passed"], "msgs": c["msgs"], "p99_s": c["p99_s"], "mib": c["mib"],
                        "comp_b": c["comp_b"], "bin_md5": c["bin_md5"], "log": c["log"]})
        print(f"{size} KiB {net}: {nm}, {len(cells)} cells, {got[0]} s, {got[1]} copies")
    print(f"{len(brow) - len(refused)} points written, {len(refused)} refused{': ' + '; '.join(refused) if refused else ''}; "
          f"known answer (schedule.py's medians): {'DIFFERS at ' + '; '.join(differ) if differ else 'equal at every point'}")
    if refused or differ:
        sys.exit(1)
    with open(out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)


if __name__ == "__main__":
    main()
