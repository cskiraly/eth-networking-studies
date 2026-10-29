#!/usr/bin/env python3
"""SEACAST under Shadow against our simulator (the harness) at ten seeds: data/seacast_shadow_500.csv.

usage: lane_compare.py --shadow-dir DIR --harness-dir DIR --msgextract PATH
                       [--seeds 7-16] [--nets home,dcb20] [--csv OUT]

Shadow records are msgextract.py's (t4_16k_<seed>_quic_p1m_n500_d16[_<net>]_v05all_shpaced.json; the
net suffix may follow the degree, so it is looked up both ways). The harness side is the rerun of
Figures 4 and 5 on the same code and settings: its cell logs
(aadaptcf_..._m6[_dcb20]_v05p4r_brd16_s0a_q0_seed<seed>.log), read with msgextract.py's own parser so
both sides are summarised alike. msgextract.py is in the prysm snapshot's testing/shadowstudy/. Per seed and network: warm p99 (median over payloads 2-6 of the
per-payload p99), rx/node and link rx/node, Shadow minus harness; then, per network, the ten-seed
medians, the ratio of medians, and the sign count (Shadow faster on k of n seeds). Only seeds with
both sides complete are paired.
"""
import argparse
import csv
import glob
import importlib.util
import json
import os
import statistics
import sys

PORT_LOG = "aadaptcf_both_cancel_rare_rt4b_hc_pr2_hp2_sc_selfewest_hoseonstfs_pggroup_pace16_m6{net}_v05p4r_brd16_s0a_q0_seed{seed}.log"


def load_msgextract(path):
    sys.dont_write_bytecode = True  # no __pycache__ in the code checkout it is loaded from
    spec = importlib.util.spec_from_file_location("msgextract", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def seeds_of(s):
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def shadow_record(d, seed, net):
    sfx = "" if net == "home" else f"_{net}"
    for name in (f"t4_16k_{seed}_quic_p1m_n500_d16_v05all_shpaced{sfx}.json",
                 f"t4_16k_{seed}_quic_p1m_n500_d16{sfx}_v05all_shpaced.json"):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return json.load(open(p))
    return None


def harness_record(d, seed, net, mx):
    p = os.path.join(d, PORT_LOG.format(net="" if net == "home" else f"_{net}", seed=seed))
    if not os.path.exists(p):
        return None
    per, health = mx.harness_messages(p)
    if health["failed_nodes"] or len(per) < 2:
        return None
    cold, warm = mx.summary(per)
    return {"warm": warm, "cold": cold, "complete_all": all(not x["timeout"] for x in per), "msgs": len(per)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shadow-dir", required=True)
    ap.add_argument("--harness-dir", required=True)
    ap.add_argument("--msgextract", required=True)
    ap.add_argument("--seeds", default="7-16")
    ap.add_argument("--nets", default="home,dcb20")
    ap.add_argument("--csv")
    a = ap.parse_args()
    mx = load_msgextract(a.msgextract)
    rows = []
    for net in a.nets.split(","):
        print(f"== {net}")
        print(f"{'seed':>4}  {'shadow p99':>10} {'harness p99':>11} {'d ms':>6}  {'sh link MiB':>11} {'hn link MiB':>11} {'d %':>6}  {'sh rx MiB':>9} {'hn rx MiB':>9}")
        paired = []
        for seed in seeds_of(a.seeds):
            s, h = shadow_record(a.shadow_dir, seed, net), harness_record(a.harness_dir, seed, net, mx)
            if not s or not h or not s.get("ok") or not s.get("complete_all") or not h["complete_all"]:
                print(f"{seed:>4}  {'-' if not s else ('ok' if s.get('ok') else 'NOT OK'):>10} {'-' if not h else 'ok':>11}")
                continue
            sw, hw = s["warm"], h["warm"]
            d = (sw["p99_s"] - hw["p99_s"]) * 1000
            dl = (sw["link_rx_node_bytes"] - hw["link_rx_node_bytes"]) / hw["link_rx_node_bytes"] * 100
            print(f"{seed:>4}  {sw['p99_s']*1000:>10.0f} {hw['p99_s']*1000:>11.0f} {d:>+6.0f}  "
                  f"{sw['link_rx_node_bytes']/1048576:>11.3f} {hw['link_rx_node_bytes']/1048576:>11.3f} {dl:>+6.1f}  "
                  f"{sw['rx_node_bytes']/1048576:>9.3f} {hw['rx_node_bytes']/1048576:>9.3f}")
            row = {"net": net, "seed": seed, "shadow_p99_s": sw["p99_s"], "harness_p99_s": hw["p99_s"],
                   "shadow_link_rx": sw["link_rx_node_bytes"], "harness_link_rx": hw["link_rx_node_bytes"],
                   "shadow_rx": sw["rx_node_bytes"], "harness_rx": hw["rx_node_bytes"],
                   "shadow_cold_p99_s": s["cold"]["p99_s"], "harness_cold_p99_s": h["cold"]["p99_s"]}
            rows.append(row)
            paired.append(row)
        if paired:
            med = lambda k: statistics.median(r[k] for r in paired)  # noqa: E731
            faster = sum(1 for r in paired if r["shadow_p99_s"] < r["harness_p99_s"])
            print(f"  {len(paired)} paired seeds: median warm p99 shadow {med('shadow_p99_s')*1000:.0f} ms, harness "
                  f"{med('harness_p99_s')*1000:.0f} ms (ratio {med('shadow_p99_s')/med('harness_p99_s'):.3f}); Shadow faster on "
                  f"{faster}/{len(paired)}; link rx {med('shadow_link_rx')/1048576:.3f} against {med('harness_link_rx')/1048576:.3f} MiB "
                  f"(ratio {med('shadow_link_rx')/med('harness_link_rx'):.3f}); seed ranges p99 shadow "
                  f"{min(r['shadow_p99_s'] for r in paired)*1000:.0f}-{max(r['shadow_p99_s'] for r in paired)*1000:.0f}, harness "
                  f"{min(r['harness_p99_s'] for r in paired)*1000:.0f}-{max(r['harness_p99_s'] for r in paired)*1000:.0f} ms")
    if a.csv and rows:
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
