#!/usr/bin/env python3
"""Gossipsub under Shadow against Figure 4, and SEACAST against gossipsub in each simulator.

usage: gs_compare.py --gs-dir DIR [--lane-csv CSV] [--fig4 CSV] [--seeds 7-16] [--csv OUT]

- Gossipsub: its Shadow records (msgextract.py's, wholend_m6_<seed>_quic_p1m_n500_d16[_dcb20].json)
  against Figure 4's gossipsub cells (data/seacast_compare.csv), per seed.
- SEACAST against gossipsub, per simulator, on the seeds both have:
  - under Shadow: SEACAST's Shadow side (data/seacast_shadow_500.csv, shadow_*) against gossipsub's;
  - in our simulator (the harness): the rerun of Figure 4 (data/seacast_shadow_500.csv, harness_*),
    Figure 4's SEACAST after the update, against Figure 4's gossipsub.
  Ratios of medians in time (warm p99) and bytes (link rx per node), sign counts, smallest gaps.
With --csv, gossipsub's Shadow rows, one per record: data/gossipsub_shadow_500.csv.
"""
import argparse
import csv
import json
import os
import statistics

MIB = 1048576
NETS = (("home", "all-home"), ("dcb20", "dcb20"))


def seeds_of(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--gs-dir", required=True)
    ap.add_argument("--lane-csv", default=os.path.join(here, "..", "data", "seacast_shadow_500.csv"))
    ap.add_argument("--fig4", default=os.path.join(here, "..", "data", "seacast_compare.csv"))
    ap.add_argument("--seeds", default="7-16")
    ap.add_argument("--csv")
    a = ap.parse_args()
    seeds = seeds_of(a.seeds)
    fig4 = {(r["network"], r["protocol"], int(r["seed"])): (float(r["p99_s"]), float(r["mib"]))
            for r in csv.DictReader(open(a.fig4))}
    lane = {(r["net"], int(r["seed"])): r for r in csv.DictReader(open(a.lane_csv))}
    rows = []
    for net, pnet in NETS:
        sfx = "" if net == "home" else f"_{net}"
        sh = {}
        for s in seeds:
            p = os.path.join(a.gs_dir, f"wholend_m6_{s}_quic_p1m_n500_d16{sfx}.json")
            if os.path.exists(p):
                r = json.load(open(p))
                complete = bool(r.get("ok")) and all(not x["timeout"] for x in r["per_msg"])
                rows.append([pnet, s, complete, round(r["warm"]["p99_s"], 4), round(r["warm"]["link_rx_node_bytes"] / MIB, 4)])
                if complete:
                    sh[s] = (r["warm"]["p99_s"], r["warm"]["link_rx_node_bytes"] / MIB)
        print(f"== {pnet}: gossipsub, Shadow against Figure 4")
        print(f"{'seed':>4}  {'shadow s':>8} {'fig4 s':>7} {'ratio':>6}  {'shadow MiB':>10} {'fig4 MiB':>8} {'d %':>6}")
        both = [s for s in seeds if s in sh and (pnet, "gossipsub", s) in fig4]
        for s in both:
            (sp, sm), (fp, fm) = sh[s], fig4[(pnet, "gossipsub", s)]
            print(f"{s:>4}  {sp:>8.3f} {fp:>7.3f} {sp / fp:>6.3f}  {sm:>10.3f} {fm:>8.3f} {(sm / fm - 1) * 100:>+6.1f}")
        if both:
            m = lambda f: statistics.median(f(s) for s in both)  # noqa: E731
            msp, mfp = m(lambda s: sh[s][0]), m(lambda s: fig4[(pnet, "gossipsub", s)][0])
            msm, mfm = m(lambda s: sh[s][1]), m(lambda s: fig4[(pnet, "gossipsub", s)][1])
            faster = sum(1 for s in both if sh[s][0] < fig4[(pnet, "gossipsub", s)][0])
            lighter = sum(1 for s in both if sh[s][1] < fig4[(pnet, "gossipsub", s)][1])
            print(f"  {len(both)} seeds: median p99 shadow {msp:.3f} s, Figure 4 {mfp:.3f} s (ratio {msp / mfp:.3f}), Shadow faster on "
                  f"{faster}/{len(both)}; median MiB {msm:.3f} against {mfm:.3f} (ratio {msm / mfm:.3f}), lighter on {lighter}/{len(both)}; "
                  f"p99 ranges shadow {min(sh[s][0] for s in both):.3f}-{max(sh[s][0] for s in both):.3f}, "
                  f"Figure 4 {min(fig4[(pnet, 'gossipsub', s)][0] for s in both):.3f}-{max(fig4[(pnet, 'gossipsub', s)][0] for s in both):.3f}")
        # SEACAST against gossipsub, in each simulator.
        for sim, t4 in (("Shadow", lambda s: (float(lane[(net, s)]["shadow_p99_s"]), float(lane[(net, s)]["shadow_link_rx"]) / MIB)),
                        ("harness", lambda s: (float(lane[(net, s)]["harness_p99_s"]), float(lane[(net, s)]["harness_link_rx"]) / MIB))):
            gs = (lambda s: sh[s]) if sim == "Shadow" else (lambda s: fig4[(pnet, "gossipsub", s)])
            ss = [s for s in both if (net, s) in lane]
            if not ss:
                continue
            tt, gt = statistics.median(t4(s)[0] for s in ss), statistics.median(gs(s)[0] for s in ss)
            tb, gb = statistics.median(t4(s)[1] for s in ss), statistics.median(gs(s)[1] for s in ss)
            ft = sum(1 for s in ss if t4(s)[0] < gs(s)[0])
            lb = sum(1 for s in ss if t4(s)[1] < gs(s)[1])
            gap = min(gs(s)[0] - t4(s)[0] for s in ss)
            print(f"  SEACAST against gossipsub, {sim:>7}: {tt:.3f} against {gt:.3f} s ({gt / tt:.2f}x), {tb:.3f} against {gb:.3f} MiB "
                  f"({gb / tb:.2f}x); SEACAST faster on {ft}/{len(ss)}, lighter on {lb}/{len(ss)}; smallest time gap {gap * 1000:.0f} ms")
    if a.csv and rows:
        with open(a.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["network", "seed", "complete", "shadow_p99_s", "shadow_mib"])
            w.writerows(rows)


if __name__ == "__main__":
    main()
