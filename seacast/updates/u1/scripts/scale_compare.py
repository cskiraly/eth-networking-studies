#!/usr/bin/env python3
"""SEACAST (tier 4) in our simulator (the harness) at 500, 1000 and 2000 nodes, ten seeds.

usage: scale_compare.py --scale-dir DIR [--lane500 CSV] [--sizes 500,1000,2000] [--seeds 7-16]
                        [--nets home,dcb20] [--base own|port] [--replace N:NET:OLD:NEW ...] [--csv OUT]
                        [--record OUT]

Every size is msgextract.py's record of one cell (arm t4_16k; records
t4_16k_<seed>_harness_p1m_n<N>_d16_v05all_shpaced[_<net>].json, with version 0.5's rules, the source's
paced HAVE and 16 connections). Beside them, "500p" is the rerun of Figure 4 at 500 nodes on the same
code and settings, as summarised in data/seacast_shadow_500.csv's harness columns (lane_compare.py,
msgextract.py's parser, so all sides are summarised alike).

Per network: warm p99 per seed (median over payloads 2-6 of the per-payload p99); per size, the
ten-seed median and range of warm p99, cold p99, link rx and rx per node, the ratio of medians to the
base (--base: own 500-node cells, or port: the rerun's, 500p), and P(slower) = the share of (size-N cell, base cell)
pairs in which the size-N cell is slower. A seed's network differs with the size, so sizes are not
paired: each step between sizes is the difference of medians with a 95 % bootstrap interval
(resampling seeds within each size, 10,000 draws, fixed RNG); a step whose interval holds 0 is inside
the seed spread. The rerun's cells against these records' at 500 nodes are the same networks, so that
known answer is paired by seed. Only records with every payload complete count. --replace puts seed
NEW's record in seed OLD's row for size N on network NET (a replacement seed, marked in the table).
--record writes one row per record of each size: data/seacast_scale.csv, with
--replace 1000:home:12:17 (seed 12's network failed the simulator's mesh check before its first payload).
"""
import argparse
import csv
import json
import os
import random
import statistics


def seeds_of(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def scale_record(d, seed, n, net):
    sfx = "" if net == "home" else f"_{net}"
    p = os.path.join(d, f"t4_16k_{seed}_harness_p1m_n{n}_d16_v05all_shpaced{sfx}.json")
    if not os.path.exists(p):
        return None
    r = json.load(open(p))
    ok = r.get("ok") and r.get("complete_all") and not r.get("failed_nodes") and not r.get("missing")
    return {"ok": bool(ok), "warm_p99_s": r["warm"]["p99_s"], "cold_p99_s": r["cold"]["p99_s"],
            "link_rx": r["warm"]["link_rx_node_bytes"], "rx": r["warm"]["rx_node_bytes"],
            "peak_gb": (r.get("cell_peak_kb") or 0) / 1048576}


def lane500(path, net):
    out = {}
    for row in csv.DictReader(open(path)):
        if row["net"] == net:
            out[int(row["seed"])] = {"ok": True, "warm_p99_s": float(row["harness_p99_s"]),
                                     "cold_p99_s": float(row["harness_cold_p99_s"]),
                                     "link_rx": float(row["harness_link_rx"]), "rx": float(row["harness_rx"]),
                                     "peak_gb": 0.0}
    return out


def p_slower(xs, base):
    pairs = [(x, b) for x in xs for b in base]
    return (sum(1 for x, b in pairs if x > b) + 0.5 * sum(1 for x, b in pairs if x == b)) / len(pairs)


def boot_median_diff(xs, ys, draws=10000, rng_seed=20261023):
    """median(ys) - median(xs) and its 95 % bootstrap interval, resampling each group on its own."""
    rng = random.Random(rng_seed)
    d = sorted(statistics.median(rng.choices(ys, k=len(ys))) - statistics.median(rng.choices(xs, k=len(xs)))
               for _ in range(draws))
    return statistics.median(ys) - statistics.median(xs), d[int(0.025 * draws)], d[int(0.975 * draws) - 1]


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--scale-dir", required=True)
    ap.add_argument("--lane500", default=os.path.join(here, "..", "data", "seacast_shadow_500.csv"))
    ap.add_argument("--sizes", default="500,1000,2000")
    ap.add_argument("--seeds", default="7-16")
    ap.add_argument("--nets", default="home,dcb20")
    ap.add_argument("--base", choices=("own", "port"), default="own")
    ap.add_argument("--replace", action="append", default=[], metavar="N:NET:OLD:NEW")
    ap.add_argument("--csv")
    ap.add_argument("--record")
    a = ap.parse_args()
    repl = {}
    for x in a.replace:
        n, net, old, new = x.split(":")
        repl[(int(n), net, int(old))] = int(new)
    seeds = seeds_of(a.seeds)
    sizes = [int(s) for s in a.sizes.split(",")]
    rows = []
    for net in a.nets.split(","):
        recs = {"500p": lane500(a.lane500, net)}
        for n in sizes:
            recs[n] = {s: r for s in seeds if (r := scale_record(a.scale_dir, repl.get((n, net, s), s), n, net))}
        good = {k: [recs[k][s] for s in seeds if s in recs[k] and recs[k][s]["ok"]] for k in recs}
        base = "500p" if a.base == "port" or len(good.get(500, [])) < 2 else 500
        b = good[base]
        print(f"== {net}: warm p99 per seed (ms); 500p = the rerun's cells, the rest these records'")
        print(f"{'seed':>4}" + "".join(f"{k:>9}" for k in recs))
        for s in seeds:
            cells = []
            for k in recs:
                r = recs[k].get(s)
                new = repl.get((k, net, s))
                mark = f"({new})" if new else ""
                cells.append("-" if r is None else (f"{mark}{r['warm_p99_s']*1000:.0f}" if r["ok"] else "NOT OK"))
                if r is not None:
                    rows.append({"net": net, "n": k, "seed": new or s, **r})
            print(f"{s:>4}" + "".join(f"{c:>9}" for c in cells))
        med = lambda rs, k: statistics.median(r[k] for r in rs)  # noqa: E731
        print(f"{'n':>5} {'seeds':>5}  {'warm p99':>8} {'range':>9} {'x' + str(base):>6} {'P(slower)':>9}  "
              f"{'cold p99':>8}  {'link MiB':>8} {'x' + str(base):>6}  {'rx MiB':>7}  {'peak GiB':>8}")
        for k in recs:
            rs = good[k]
            if not rs:
                print(f"{k:>5} {0:>5}")
                continue
            w = [r["warm_p99_s"] for r in rs]
            ps = p_slower(w, [r["warm_p99_s"] for r in b])
            print(f"{k:>5} {len(rs):>5}  {med(rs, 'warm_p99_s')*1000:>8.0f} {min(w)*1000:>4.0f}-{max(w)*1000:<4.0f} "
                  f"{med(rs, 'warm_p99_s')/med(b, 'warm_p99_s'):>6.3f} {ps:>9.2f}  {med(rs, 'cold_p99_s')*1000:>8.0f}  "
                  f"{med(rs, 'link_rx')/1048576:>8.3f} {med(rs, 'link_rx')/med(b, 'link_rx'):>6.3f}  "
                  f"{med(rs, 'rx')/1048576:>7.3f}  {max(r['peak_gb'] for r in rs):>8.1f}")
        own = [n for n in sizes if len(good[n]) >= 2]
        steps = list(zip(own, own[1:])) + ([(own[0], own[-1])] if len(own) > 2 else [])
        if base == "500p" and own:
            steps = [("500p", own[0])] + steps
        print("  steps (difference of medians, 95 % bootstrap interval; inside the seed spread if it holds 0):")
        for x, y in steps:
            for key, unit, scale in (("warm_p99_s", "ms", 1000), ("link_rx", "KiB", 1 / 1024)):
                d, lo, hi = boot_median_diff([r[key] * scale for r in good[x]], [r[key] * scale for r in good[y]])
                inside = "inside" if lo <= 0 <= hi else "outside"
                print(f"    {x:>5} -> {y:<5} {key:<10} {d:>+7.1f} {unit} [{lo:+.1f}, {hi:+.1f}]  {inside}")
        paired = [s for s in seeds if s in recs["500p"] and s in recs.get(500, {}) and recs[500][s]["ok"]]
        if paired:
            dd = [(recs[500][s]["warm_p99_s"] - recs["500p"][s]["warm_p99_s"]) * 1000 for s in paired]
            dl = [(recs[500][s]["link_rx"] / recs["500p"][s]["link_rx"] - 1) * 100 for s in paired]
            print(f"  known answer, these records against the rerun's cells at 500 nodes, paired on {len(paired)} seeds: "
                  f"warm p99 median {statistics.median(dd):+.0f} ms (range {min(dd):+.0f} to {max(dd):+.0f}; these records "
                  f"slower on {sum(1 for x in dd if x > 0)}/{len(dd)}), link rx median {statistics.median(dl):+.1f} %")
    if a.csv and rows:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    if a.record and rows:
        keep = sorted((r for r in rows if r["n"] in sizes), key=lambda r: (r["net"], r["n"], r["seed"]))
        with open(a.record, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["network", "nodes", "seed", "complete", "warm_p99_s", "mib"])
            for r in keep:
                w.writerow(["all-home" if r["net"] == "home" else r["net"], r["n"], r["seed"], r["ok"],
                            r["warm_p99_s"], round(r["link_rx"] / 1048576, 4)])


if __name__ == "__main__":
    main()
