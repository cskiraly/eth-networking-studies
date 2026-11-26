#!/usr/bin/env python3
"""The one schedule on fresh networks (the record's "One schedule for both networks"): per point where the schedule
differs from the default up to 2 MiB (32, 64 and 128 KiB: R = 6 in 4 KiB chunks), the schedule's setting against
the default at seeds 1024, 2048 and 3072, paired by seed, with stage 2's three-seed verdict: clear if all three
seeds agree and the median per-seed gap 1 - x/x_default is beyond the noise allowance (best.noise: time 10 %,
bytes 8 % below 512 KiB). An entry is confirmed where it is clearly faster; otherwise it is printed TO THE AUTHOR.

usage: fresh.py --expect LIST.dry ... HOST=cells.csv ...   (the fresh networks' rows and lists; one host a network)
A point is refused if either setting is not ok at all three seeds (fronts.py's status) or a listed cell is missing.
"""
import sys

import best  # best.py's gap, wins and noise; it imports fronts

fronts = best.fronts
SEEDS = (1024, 2048, 3072)
POINTS = {32: ("R=6 unit=4K leo8", "R=4 unit=16K leo8"), 64: ("R=6 unit=4K leo8", "R=4 unit=16K leo8"),
          128: ("R=6 unit=4K leo8", "R=4 unit=16K leo8")}   # size: (the schedule's setting, the default)


def by_name(S, nm):
    hit = [s for s in S if fronts.name(s) == nm]
    return hit[0] if len(hit) == 1 else None


def three(a, b, S, size):
    xs = best.both(a, b, S, SEEDS)
    tt, tb = best.noise(size)
    full = len(xs) == len(SEEDS)
    f, l = best.wins(a, b, S, xs, "p99_s"), best.wins(a, b, S, xs, "mib")
    tg, bg = best.gap(a, b, S, xs, "p99_s"), best.gap(a, b, S, xs, "mib")
    return {"n": len(xs), "f": f, "l": l, "tg": tg, "bg": bg,
            "faster": full and f == len(SEEDS) and tg > tt, "lighter": full and l == len(SEEDS) and bg > tb,
            "slower": full and best.wins(b, a, S, xs, "p99_s") == len(SEEDS) and best.gap(b, a, S, xs, "p99_s") > tt,
            "heavier": full and best.wins(b, a, S, xs, "mib") == len(SEEDS) and best.gap(b, a, S, xs, "mib") > tb}


def main():
    a = sys.argv[1:]
    files, expect = [], []
    while a:
        x = a.pop(0)
        if x == "--expect":
            expect.append(a.pop(0))
        elif x.startswith("--"):
            sys.exit(__doc__)
        else:
            files.append(x)
    if not files or not expect:
        sys.exit(__doc__)
    rows, exp = fronts.load(files), fronts.load_expect(expect)
    info, res = fronts.analyse(rows, list(SEEDS), 500, exp)
    print(f"seeds {', '.join(map(str, SEEDS))} (fresh networks); {info['ignored']} rows of other seeds not used; "
          f"SEACAST binary md5 {info['md5'] or '-'}; clear: on all three seeds and beyond the noise allowance")
    refused, confirmed, to_author = [], [], []
    for point in sorted(res):
        size, net = point
        pi = res[point]
        print(f"\n== {size} KiB, {net} (host {pi['host']})")
        if size not in POINTS:
            print("   REFUSED: not a point of this check")
            refused.append(f"{size} {net}")
            continue
        if pi["missing"]:
            print(f"   REFUSED: MISSING: {len(pi['missing'])} listed cells are not in the rows")
            refused.append(f"{size} {net}")
            continue
        S = pi["settings"]
        sn, dn = POINTS[size]
        s, d = by_name(S, sn), by_name(S, dn)
        bad = [f"{nm} {'has no cells' if k is None else 'is ' + S[k]['status']}"
               for nm, k in ((sn, s), (dn, d)) if k is None or S[k]["status"] != "ok"]
        if bad:
            print("   REFUSED: " + "; ".join(bad))
            refused.append(f"{size} {net}")
            continue
        v = three(s, d, S, size)
        words = best.words(v)
        print(f"   the default {dn}: {S[d]['time']:.4f} s, {S[d]['copies']:.2f} copies (median of three)")
        print(f"   the schedule {sn}: {S[s]['time']:.4f} s, {S[s]['copies']:.2f} copies")
        print(f"   against the default: faster on {v['f']} of {v['n']} (median {best.pct(v['tg'])}), lighter on "
              f"{v['l']} of {v['n']} (median {best.pct(v['bg'])}): {words}")
        if v["faster"]:
            print("   CONFIRMED: clearly faster on fresh networks")
            confirmed.append(f"{size} {net}")
        else:
            print("   TO THE AUTHOR: not clearly faster on fresh networks")
            to_author.append(f"{size} {net}")
    print(f"\n{len(confirmed)} confirmed{': ' + ', '.join(confirmed) if confirmed else ''}; to the author: "
          f"{', '.join(to_author) or 'none'}; refused: {', '.join(refused) or 'none'}")
    sys.exit(1 if refused else 0)


if __name__ == "__main__":
    main()
