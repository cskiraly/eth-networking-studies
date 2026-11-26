#!/usr/bin/env python3
"""What stage 1 carries to stage 2, and what stage 2 would cost, from fronts.py's --carry text and the
stage-1 cells' own done files (rss, wall).

    python3 carry_cost.py [NEW_SEEDS] [--fronts DIR] [--done DIR]...
                                               (default 2: seeds 8 and 9 beside seed 7)

Reads fronts-A.txt and fronts-B.txt and A/done, B/done beside this script, or the fronts in --fronts
DIR (the grow batch's: ../grow) with the done files of this directory and of each --done DIR (../grow): a
setting's done file is looked up in each, and must be in exactly one. A setting above R = 6 has its fast
budget in its id (_rf8), as cell.sh writes it.

    ... --lists DIR [--seeds 8,9]

also writes the carried settings as cell lines of run1.sh's sixteen fields: DIR/s2-small-<machine>.txt (32 to
512 KiB, with gossipsub's whole message at 32 and 64 KiB) and DIR/s2-large-<machine>.txt (1 to 4 MiB),
seed-major, sizes ascending; and DIR/s2-seed7-<machine>.txt, the same settings at seed 7, whose cells must all
have run (check them with check_list.sh: their ids must be done files of stage 1 or the grow batch). A coded setting's code is
written "-" (cell.sh's rule, asserted equal to fronts.rule_code); "unc" and "plain" as they are. Per point: the settings
carried in the cap, the base, the fastest's neighbours, the corner (uncoded settings and their coded twins);
each counted once. Cost: each carried setting's stage-1 cell (seed 7) times NEW_SEEDS, its wall time and
peak memory (GNU time's rss, read as GiB as cell.sh wrote it). Gossipsub's whole message is not carried by
fronts.py; its two cells a host are listed apart.

The record publishes this script for cell_line and gossipsub_line, which make_lists.py imports; main() also
needs the cells' done files and stage 1's --carry text, which are not published.
"""
import os
import re
import sys

import fronts  # rule_code, rule_rfast

HERE = os.path.dirname(os.path.abspath(__file__))

NET = {"A": "home", "B": "dcb20"}
GOSSIPSUB_SIZES = (32, 64)
SET = re.compile(r"R=(\d+) unit=(\d+)K (\w+)")


def wall_s(w):
    p = [float(x) for x in w.split(":")]
    return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else p[0] * 60 + p[1]


def done_file(dirs, h, cid):
    found = [os.path.join(d, h, "done", cid) for d in dirs if os.path.exists(os.path.join(d, h, "done", cid))]
    if len(found) != 1:
        sys.exit(f"{cid} on {h}: {len(found)} done files in {dirs}")
    return open(found[0]).read()


def cell_line(net, size, seed, s):
    r, u, code = int(s[0]), int(s[1]), s[2]
    if code in ("leo8", "leo16"):
        assert code == fronts.rule_code(size, u, 1), (size, s)
        code = "-"
    rf = fronts.rule_rfast(r)
    return " ".join(str(x) for x in ("seacast", net, size, seed, r, "-" if u == 16 else u, code, "-",
                                      "-" if rf == "6" else rf, "-", "-", "-", "-", "-", 1, "group"))


def gossipsub_line(net, size, seed):
    return " ".join(str(x) for x in ("gossipsub", net, size, seed) + ("-",) * 12)


def main():
    a = sys.argv[1:]
    seeds, fronts_dir, dirs, lists, list_seeds = 2, HERE, [HERE], None, (8, 9)
    while a:
        x = a.pop(0)
        if x == "--fronts":
            fronts_dir = a.pop(0)
        elif x == "--done":
            dirs.append(a.pop(0))
        elif x == "--lists":
            lists = a.pop(0)
        elif x == "--seeds":
            list_seeds = tuple(int(v) for v in a.pop(0).split(","))
        elif x.isdigit():
            seeds = int(x)
        else:
            sys.exit(__doc__)
    carried = {}
    grand = {"cells": 0, "s": 0.0}
    for h in ("A", "B"):
        txt = open(os.path.join(fronts_dir, f"fronts-{h}.txt")).read().split("\n== ")[1:]
        print(f"== host {h} ({NET[h]})")
        tot_n, tot_s, small_s, large_s, peak = 0, 0.0, 0.0, 0.0, 0.0
        for sec in txt:
            size = int(sec.split(" KiB")[0])
            parts = {"cap": [], "base": [], "neighbours": [], "corner": []}
            for line in sec.splitlines():
                l = line.strip()
                if l.startswith("carried:"):
                    cap, base = l[len("carried:"):].split("| base:")
                    parts["cap"] = SET.findall(cap)
                    parts["base"] = SET.findall(base)
                elif l.startswith("carried outside the cap, the fastest's neighbours:"):
                    parts["neighbours"] = SET.findall(l.split(":", 1)[1])
                elif l.startswith("carried outside the cap, the corner"):
                    parts["corner"] = SET.findall(l.split(":", 1)[1])
            seen, rows = set(), []
            for part in ("base", "cap", "neighbours", "corner"):
                for s in parts[part]:
                    if s in seen:
                        continue
                    seen.add(s)
                    r, u, code = s
                    rf = f"_rf{r}" if int(r) > 6 else ""
                    cid = f"seacast_{NET[h]}_{size}k_s7_r{r}_u{u}_{code}{rf}_oppgroup_cnt"
                    d = done_file(dirs, h, cid)
                    rss = float(re.search(r"rss=([\d.]+)GiB", d).group(1))
                    w = wall_s(re.search(r"wall=([\d:.]+)", d).group(1))
                    rows.append((part, s, rss, w))
            carried[(h, size)] = [s for _, s, _, _ in rows]
            n = len(rows)
            s_sum = sum(w for *_, w in rows) * seeds
            tot_n += n * seeds
            tot_s += s_sum
            if size <= 512:
                small_s += s_sum
            else:
                large_s += s_sum
            peak = max([peak] + [x for _, _, x, _ in rows])
            counts = {p: sum(1 for q, *_ in rows if q == p) for p in parts}
            print(f"  {size:5} KiB: {n:2} settings (base {counts['base']}, cap {counts['cap']}, neighbours {counts['neighbours']}, "
                  f"corner {counts['corner']}) -> {n * seeds:3} cells, {s_sum / 3600:5.1f} cell-h, "
                  f"peak {max(x for _, _, x, _ in rows):4.1f} GiB")
        gs = [f for f in os.listdir(os.path.join(HERE, h, "done")) if f.startswith("gossipsub_")]
        print(f"  total: {tot_n} SEACAST cells, {tot_s / 3600:.1f} cell-hours ({small_s / 3600:.1f} at 32-512 KiB, "
              f"{large_s / 3600:.1f} at 1-4 MiB), peak {peak:.1f} GiB a cell; gossipsub apart: {len(gs)} settings, {len(gs) * seeds} cells")
        grand["cells"] += tot_n
        grand["s"] += tot_s
    print(f"both hosts: {grand['cells']} SEACAST cells, {grand['s'] / 3600:.1f} cell-hours at {seeds} new seeds")
    if lists:
        for h in ("A", "B"):
            net = NET[h]
            sizes = sorted(size for hh, size in carried if hh == h)
            out = {"small": [], "large": [], "seed7": []}
            for seed in list_seeds:
                for size in sizes:
                    lane = "small" if size <= 512 else "large"
                    out[lane] += [cell_line(net, size, seed, s) for s in carried[(h, size)]]
                    if size in GOSSIPSUB_SIZES:
                        out[lane].append(gossipsub_line(net, size, seed))
            for size in sizes:
                out["seed7"] += [cell_line(net, size, 7, s) for s in carried[(h, size)]]
                if size in GOSSIPSUB_SIZES:
                    out["seed7"].append(gossipsub_line(net, size, 7))
            for k, v in out.items():
                assert len(v) == len(set(v)), (h, k)
                with open(os.path.join(lists, f"s2-{k}-{h}.txt"), "w") as fh:
                    fh.write("\n".join(v) + "\n")
            print(f"lists for {h}: s2-small {len(out['small'])}, s2-large {len(out['large'])} lines at seeds {list_seeds}; "
                  f"s2-seed7 {len(out['seed7'])}")


if __name__ == "__main__":
    main()
