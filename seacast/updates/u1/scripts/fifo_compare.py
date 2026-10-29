#!/usr/bin/env python3
"""Figure 4 with Shadow's queue against the post's Figure 4: data/figure4_fifo_queue.csv.

usage: fifo_compare.py --fifo-dir DIR --msgextract PATH [--csv FIG4_CSV] [--seeds 7-16] [--out CSV]

The FIFO cells run Figure 4's three arms -- tier 4 (SEACAST), ECBroadcast RS, gossipsub whole
message -- on Figure 4's code plus the queue knob, with SIMNET_FLOW_BUCKETS=1 and CoDel never
dropping (SIMNET_CODEL_TARGET_MS=100000): our simulator (the harness) with Shadow's FIFO and nothing
else changed. Each cell is read with msgextract.py's harness parser (which reproduces the figure's CSV
exactly on its seed-7 cells; in the prysm snapshot's testing/shadowstudy/) and paired with the cell of
the same arm, network and seed in the post's Figure 4 (default data/post/seacast_compare.csv): warm
p99 (the median over payloads 2-6 of the per-payload p99) and link rx per node by the network's
completion.

Prints, per network and arm: the per-seed pairs, the ten-seed medians and their ratio, and how many
seeds the FIFO queue made faster; then, per network, the arm-to-arm comparisons the post makes (RS and
gossipsub against tier 4: ratios of medians in time and bytes, and the per-seed sign counts) under
both queues. The knob-unset known answer (QUEUE fq, tier 4 seed 7 all-home) is printed first.
"""
import argparse
import csv
import importlib.util
import os
import statistics
import sys

ARMS = ("t4", "rs", "gs")
PROTO = {"t4": "seacast", "rs": "ecbroadcast-rs", "gs": "gossipsub"}
NAME = {"t4": "tier 4", "rs": "ECBroadcast RS", "gs": "gossipsub"}
NETS = (("home", "all-home"), ("dcb20", "dcb20"))
T4 = "aadaptcf_both_cancel_rare_rt4b_hc_pr2_hp2_sc_selfewest_hoseonstfs_pggroup_pace16_m6{net}_t4_brd16_{q}_s0a_q0_seed{seed}.log"
GS = "wholend_re4fd_m6{net}_brd16_{q}_s0a_q0_seed{seed}.log"
RS = "ecrs_cmp_d16{net}_{q}_seed{seed}.log"
LOG = {"t4": T4, "gs": GS, "rs": RS}
MIB = 1048576


def load_msgextract(path):
    sys.dont_write_bytecode = True  # no __pycache__ in the code checkout it is loaded from
    spec = importlib.util.spec_from_file_location("msgextract", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seeds_of(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def cell(d, arm, net, seed, q, mx):
    """(warm p99 s, link rx/node bytes) of one lane cell, or None when absent, failed or incomplete."""
    p = os.path.join(d, LOG[arm].format(net="" if net == "home" else f"_{net}", q=q, seed=seed))
    if not os.path.exists(p):
        return None
    per, health = mx.harness_messages(p)
    if health["failed_nodes"] or len(per) != 6 or any(x["timeout"] for x in per):
        return None
    _, warm = mx.summary(per)
    return warm["p99_s"], warm["link_rx_node_bytes"]


def published(path):
    """{(network, protocol, seed): (p99_s, mib)} from Figure 4's CSV."""
    out = {}
    for r in csv.DictReader(open(path)):
        out[(r["network"], r["protocol"], int(r["seed"]))] = (float(r["p99_s"]), float(r["mib"]))
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--fifo-dir", required=True)
    ap.add_argument("--msgextract", required=True)
    ap.add_argument("--csv", default=os.path.join(here, "..", "data", "post", "seacast_compare.csv"))
    ap.add_argument("--seeds", default="7-16")
    ap.add_argument("--out")
    a = ap.parse_args()
    mx = load_msgextract(a.msgextract)
    pub = published(a.csv)
    seeds = seeds_of(a.seeds)

    ka = cell(a.fifo_dir, "t4", "home", 7, "fq", mx)
    pk = pub[("all-home", "seacast", 7)]
    if ka:
        print(f"known answer (knob unset, tier 4, seed 7, all-home): {ka[0]:.3f} s, {ka[1] / MIB:.4f} MiB; "
              f"published {pk[0]:.3f} s, {pk[1]:.4f} MiB ({(ka[0] - pk[0]) * 1000:+.0f} ms, {(ka[1] / MIB / pk[1] - 1) * 100:+.1f} %)")
    else:
        print("known answer: not there yet")

    rows = []
    for net, pnet in NETS:
        got = {}
        for arm in ARMS:
            print(f"\n== {pnet}, {NAME[arm]}")
            print(f"{'seed':>4}  {'fifo p99':>8} {'fq p99':>8} {'d ms':>6} {'ratio':>6}  {'fifo MiB':>8} {'fq MiB':>8} {'d %':>6}")
            pairs = []
            for seed in seeds:
                f, p = cell(a.fifo_dir, arm, net, seed, "fifo", mx), pub.get((pnet, PROTO[arm], seed))
                if not f or not p:
                    print(f"{seed:>4}  {'-' if not f else 'ok':>8} {'-' if not p else 'ok':>8}")
                    continue
                fm = f[1] / MIB
                print(f"{seed:>4}  {f[0]:>8.3f} {p[0]:>8.3f} {(f[0] - p[0]) * 1000:>+6.0f} {f[0] / p[0]:>6.3f}  "
                      f"{fm:>8.4f} {p[1]:>8.4f} {(fm / p[1] - 1) * 100:>+6.1f}")
                pairs.append((seed, f[0], p[0], fm, p[1]))
                rows.append({"network": pnet, "arm": PROTO[arm], "seed": seed, "fifo_p99_s": round(f[0], 4),
                             "fq_p99_s": p[0], "fifo_mib": round(fm, 4), "fq_mib": p[1]})
            got[arm] = {s: (fp, qp, fm, qm) for s, fp, qp, fm, qm in pairs}
            if pairs:
                med = lambda i: statistics.median(x[i] for x in pairs)  # noqa: E731
                faster = sum(1 for x in pairs if x[1] < x[2])
                print(f"  {len(pairs)} seeds: median p99 fifo {med(1):.3f} s, fq {med(2):.3f} s (ratio {med(1) / med(2):.3f}); "
                      f"fifo faster on {faster}/{len(pairs)}; median MiB fifo {med(3):.3f}, fq {med(4):.3f} (ratio {med(3) / med(4):.3f}); "
                      f"p99 ranges fifo {min(x[1] for x in pairs):.3f}-{max(x[1] for x in pairs):.3f}, fq {min(x[2] for x in pairs):.3f}-{max(x[2] for x in pairs):.3f}")
        # The post's comparisons: each other arm against tier 4, on the seeds all three arms have.
        both = [s for s in seeds if all(s in got.get(arm, {}) for arm in ARMS)]
        if not both:
            continue
        print(f"\n== {pnet}: against tier 4, {len(both)} seeds with all three arms")
        for arm in ("rs", "gs"):
            for qi, qn in ((0, "fifo"), (1, "fq")):
                t = statistics.median(got["t4"][s][qi] for s in both)
                o = statistics.median(got[arm][s][qi] for s in both)
                tb = statistics.median(got["t4"][s][qi + 2] for s in both)
                ob = statistics.median(got[arm][s][qi + 2] for s in both)
                ft = sum(1 for s in both if got["t4"][s][qi] < got[arm][s][qi])
                lb = sum(1 for s in both if got["t4"][s][qi + 2] < got[arm][s][qi + 2])
                gap = min(got[arm][s][qi] - got["t4"][s][qi] for s in both)
                print(f"  {NAME[arm]:>15} / tier 4, {qn:>4}: time {o / t:.2f}x, bytes {ob / tb:.2f}x; tier 4 faster on {ft}/{len(both)}, "
                      f"lighter on {lb}/{len(both)}; smallest time gap {gap * 1000:.0f} ms")
    if a.out and rows:
        with open(a.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
