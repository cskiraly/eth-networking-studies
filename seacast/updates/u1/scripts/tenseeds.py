#!/usr/bin/env python3
"""SEACAST in Figures 4 and 5, rerun on the fixed code, against the post's cells, network by network.

    python3 tenseeds.py LOGDIR [--post-compare CSV] [--post-elastic CSV] [--out DIR]

LOGDIR holds the rerun's cell logs (*_v05p4r_brd16_s0a_q0_seed<seed>.log: version 0.5's rules and the
source's paced HAVE, on the code the README names). The post's SEACAST rows come from its Figure 4's
CSV (all-home and dcb20 at 50 Mbps; default data/post/seacast_compare.csv) and its Figure 5's
(all-home at 50/25/20/10 Mbps; data/post/seacast_elastic_all.csv). Per setting: the medians over
seeds 7-16 on both sides, the median of the paired per-seed differences, their range, and how many
seeds the rerun is faster (lighter) on. With --out, the two CSVs with the rerun's SEACAST rows in
place of the post's, every other row kept: data/seacast_elastic_all.csv, and data/seacast_compare.csv
before read_fd.py's FullDAS rows were added at its end.
"""
import argparse
import csv
import glob
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v05read  # noqa: E402

POST = os.path.join(HERE, "..", "data", "post")
SEEDS = range(7, 17)
SETTINGS = [("all-home", 50), ("dcb20", 50), ("all-home", 25), ("all-home", 20), ("all-home", 10)]


def published(compare, elastic):
    pub = {}
    for r in csv.DictReader(open(compare)):
        if r["protocol"] == "seacast":
            pub[(r["network"], 50, int(r["seed"]))] = (float(r["p99_s"]), float(r["mib"]))
    for r in csv.DictReader(open(elastic)):
        if r["series"] == "seacast":
            pub[("all-home", int(r["uplink_mbps"]), int(r["seed"]))] = (float(r["p99_s"]), float(r["mib"]))
    return pub


def rerun(logdir):
    out = {}
    for f in glob.glob(os.path.join(logdir, "*_v05p4r_brd16_s0a_q0_seed*.log")):
        r = v05read.row(f)
        if not r["passed"] or r["msgs"] != 6:
            print(f"skip (not passed or short): {os.path.basename(f)}", file=sys.stderr)
            continue
        out[(r["net"], r["up"], r["seed"])] = (r["p99_s"], r["mib"], r["sock_mib"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logdir")
    ap.add_argument("--post-compare", default=os.path.join(POST, "seacast_compare.csv"))
    ap.add_argument("--post-elastic", default=os.path.join(POST, "seacast_elastic_all.csv"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    pub, new = published(a.post_compare, a.post_elastic), rerun(a.logdir)
    print("setting        n   p99 published  rerun   paired diff [range]       faster  |  MiB published  rerun  paired diff [range]   lighter  | socket/link")
    for net, up in SETTINGS:
        seeds = [s for s in SEEDS if (net, up, s) in pub and (net, up, s) in new]
        if not seeds:
            continue
        pp = [pub[(net, up, s)][0] for s in seeds]
        rp = [new[(net, up, s)][0] for s in seeds]
        pm = [pub[(net, up, s)][1] for s in seeds]
        rm = [new[(net, up, s)][1] for s in seeds]
        dp = [r - p for r, p in zip(rp, pp)]
        dm = [r - p for r, p in zip(rm, pm)]
        socks = [new[(net, up, s)][2] / new[(net, up, s)][1] for s in seeds if new[(net, up, s)][2]]
        sock = f"{st.median(socks):.4f}" if socks else "-"
        print(f"{net:8s} {up:3d}  {len(seeds):2d}  {st.median(pp):.3f} s      {st.median(rp):.3f}   {st.median(dp)*1000:+5.0f} ms [{min(dp)*1000:+.0f}, {max(dp)*1000:+.0f}]"
              f"   {sum(d < 0 for d in dp):2d}/{len(seeds)}  |  {st.median(pm):.3f}      {st.median(rm):.3f}  {st.median(dm):+.3f} [{min(dm):+.3f}, {max(dm):+.3f}]  {sum(d < 0 for d in dm):2d}/{len(seeds)}  | {sock}")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        rows = list(csv.DictReader(open(a.post_compare)))
        with open(os.path.join(a.out, "seacast_compare.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")  # as the post's CSV
            w.writeheader()
            for r in rows:
                key = (r["network"], 50, int(r["seed"]))
                if r["protocol"] == "seacast" and key in new:
                    r = dict(r, p99_s=f"{new[key][0]:.4f}", mib=f"{new[key][1]:.4f}")
                w.writerow(r)
        rows = list(csv.DictReader(open(a.post_elastic)))
        with open(os.path.join(a.out, "seacast_elastic_all.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            for r in rows:
                key = ("all-home", int(r["uplink_mbps"]), int(r["seed"]))
                if r["series"] == "seacast" and key in new:
                    r = dict(r, p99_s=f"{new[key][0]:.4f}", mib=f"{new[key][1]:.4f}")
                w.writerow(r)
        print(f"wrote {a.out}/seacast_compare.csv and seacast_elastic_all.csv")


if __name__ == "__main__":
    main()
