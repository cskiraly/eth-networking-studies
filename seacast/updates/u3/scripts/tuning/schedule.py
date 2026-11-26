#!/usr/bin/env python3
"""One schedule for both networks (the record's section of that name): per point, the schedule's setting
against the default on that network at seeds 7 to 16, paired by seed, with best.py's verdicts (clear on at
least 8 of 10 seeds and beyond the noise allowance), and the network's own best from stage 3's reading
(best-<machine>.csv, with the author's choice at dcb20 4 MiB) beside it.

usage: schedule.py --expect LIST.dry ... --best best-<machine>.csv [--csv OUT] HOST=cells.csv ...

The rows and lists are best.py's (stages 1, grow, 2 and 3), plus the later run's for dcb20 (fill/). A point is
refused if its schedule setting or its default is not ok at all ten seeds (fronts.py's status). The schedule's
entry holds on a network unless it is clearly slower than the default there; a clearly slower entry is
printed TO THE AUTHOR. Known answer, checked on every run: wherever the schedule's setting is the setting
best-<machine>.csv prefers, its gaps and counts must equal that CSV's (best.py's own numbers), or the script
exits 1.
"""
import csv
import sys

import best  # best.py's verdicts, seeds and noise allowance; it imports fronts

fronts = best.fronts
SCHEDULE = {32: "R=6 unit=4K leo8", 64: "R=6 unit=4K leo8", 128: "R=6 unit=4K leo8", 256: None, 512: None,
            1024: None, 2048: None, 4096: "R=2 unit=32K leo8"}   # None: the default
AUTHOR = {(4096, "dcb20"): "R=2 unit=32K leo8"}   # the author's choice over the rule's preferred
COLS = ["size_kib", "network", "default", "schedule", "schedule_s", "schedule_copies", "time_gap_pct",
        "bytes_gap_pct", "faster_of_10", "lighter_of_10", "verdict", "holds", "own_best", "own_outcome"]


def by_name(S, nm):
    hit = [s for s in S if fronts.name(s) == nm]
    return hit[0] if len(hit) == 1 else None


def own_best(row, point):
    """The network's own text setting from stage 3's reading: the preferred where the outcome is CHANGE (the
    author's choice where they chose), else the default."""
    if point in AUTHOR:
        return AUTHOR[point], "CHANGE (the author's choice)"
    if row["outcome"] == "CHANGE":
        return row["preferred"], "CHANGE"
    return row["default"], row["outcome"]


def main():
    a = sys.argv[1:]
    files, expect, bests, out_csv = [], [], [], None
    while a:
        x = a.pop(0)
        if x == "--expect":
            expect.append(a.pop(0))
        elif x == "--best":
            bests.append(a.pop(0))
        elif x == "--csv":
            out_csv = a.pop(0)
        elif x.startswith("--"):
            sys.exit(__doc__)
        else:
            files.append(x)
    if not files or not expect or not bests:
        sys.exit(__doc__)
    rows, exp = fronts.load(files), fronts.load_expect(expect)
    bad = best.strays(rows, exp)
    if bad:
        sys.exit(f"{len(bad)} rows of seeds 7 to 16 are no cell of the lists given: " + "; ".join(bad[:5]))
    info, res = fronts.analyse(rows, list(best.SEEDS), 500, exp)
    brow = {}
    for p in bests:
        for r in csv.DictReader(open(p)):
            brow[(int(r["size_kib"]), r["network"])] = r
    print(f"seeds 7 to 16; SEACAST binary md5 {info['md5'] or '-'}; the schedule: "
          + "; ".join(f"{k} KiB {v or 'the default'}" for k, v in SCHEDULE.items()))
    out, refused, known_bad, to_author = [], [], [], []
    for point in sorted(brow):
        size, net = point
        pi, br = res.get(point), brow[point]
        print(f"\n== {size} KiB, {net} (host {pi['host'] if pi else '-'})")
        if pi is None or pi["missing"]:
            why = "NO ROWS" if pi is None else f"MISSING: {len(pi['missing'])} listed cells are not in the rows"
            print(f"   REFUSED: {why}")
            refused.append(f"{size} {net}")
            continue
        S = pi["settings"]
        base = by_name(S, br["default"])
        nm = SCHEDULE[size] or br["default"]
        s = by_name(S, nm)
        own, own_out = own_best(br, point)
        bad = [f"{x} {'has no cells' if k is None else 'is ' + S[k]['status'] + (' (lacks seeds ' + str(S[k]['lack']) + ')' if S[k]['lack'] else '')}"
               for x, k in (("the default " + br["default"], base), ("the schedule's " + nm, s))
               if k is None or S[k]["status"] != "ok"]
        if bad:
            print("   REFUSED: " + "; ".join(bad))
            refused.append(f"{size} {net}")
            continue
        t, c = f"{S[s]['time']:.4f}", f"{S[s]['copies']:.2f}"   # fronts.py's exact medians of ten
        print(f"   the default: {br['default']} ({br['default_s']} s, {br['default_copies']} copies)")
        print(f"   the network's own best (stage 3's reading): {own} [{own_out}]")
        if s == base:
            print(f"   the schedule: the default")
            out.append({"size_kib": size, "network": net, "default": br["default"], "schedule": "the default",
                        "schedule_s": t, "schedule_copies": c, "holds": "yes", "own_best": own, "own_outcome": own_out})
            continue
        v = best.verdict(s, base, S, size)
        holds = not v["slower"]
        print(f"   the schedule: {nm} ({t} s, {c} copies) against the default: {best.vtext(v)}")
        print(f"   {'HOLDS: not clearly slower than the default' if holds else 'TO THE AUTHOR: clearly slower than the default'}")
        if not holds:
            to_author.append(f"{size} {net}")
        if nm == br["preferred"]:
            want = (br["time_gap_pct"], br["bytes_gap_pct"], br["faster_of_10"], br["lighter_of_10"])
            got = (f"{float(v['tg']) * 100:.2f}", f"{float(v['bg']) * 100:.2f}", str(v["f"]), str(v["l"]))
            print(f"   known answer (the reading's preferred): {'equal' if got == want else 'DIFFERS: ' + str(got) + ' against ' + str(want)}")
            if got != want:
                known_bad.append(f"{size} {net}")
        out.append({"size_kib": size, "network": net, "default": br["default"], "schedule": nm, "schedule_s": t,
                    "schedule_copies": c, "time_gap_pct": f"{float(v['tg']) * 100:.2f}",
                    "bytes_gap_pct": f"{float(v['bg']) * 100:.2f}", "faster_of_10": v["f"], "lighter_of_10": v["l"],
                    "verdict": best.words(v), "holds": "yes" if holds else "no", "own_best": own, "own_outcome": own_out})
    print(f"\n{len(out)} points read, {len(refused)} refused{': ' + ', '.join(refused) if refused else ''}; "
          f"to the author: {', '.join(to_author) or 'none'}; known answer: "
          f"{'DIFFERS at ' + ', '.join(known_bad) if known_bad else 'equal wherever the schedule is the preferred'}")
    if out_csv and not refused and not known_bad:
        with open(out_csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            w.writeheader()
            w.writerows(out)
    sys.exit(1 if refused or known_bad else 0)


if __name__ == "__main__":
    main()
