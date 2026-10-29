#!/usr/bin/env python3
"""The links' lower bound of Figure 5 before 22 October 2026, corrected: the max of terms each valid on
its own, for any overlay (it assumes every pair could connect), per seed's latencies.

    python3 simple_bound.py [--seeds 7-16] [--ups 50,25,20,10] [--q 0.99] [--csv seacast_elastic_all.csv]

For the q-quantile receiver, M = ceil(q(N-1)) receivers (nearest rank), with overlay_bound.py's
model (every chunk at least c_min bytes, a receiver needs distinct chunks totalling S; one MTU of
token-bucket burst):

  T(q) >= max( B + (ceil(log2(M+1)) - 1) tau_f,      spread of the late chunks (see overlay_bound.py)
               B + Q_q(d'(w)),                       a late chunk over w's best path
               (8 M S - N 8 MTU) / sum U,            every counted receiver takes S bytes
               Q_q(b_w + 8 (S - MTU) / D_w) )        w's own downlink, from the first bit that can reach it

B = 8(S - MTU)/U_s, tau_v = 8(c_min - MTU)/U_v. d'(w): least over paths on the full mesh of the edges'
one-way latencies plus tau of every relay (Dijkstra); the geo model breaks the triangle inequality,
so a relayed path can beat the direct one. b_w: the least over w's neighbours v of start(v) + l(v,w),
start(v) = tau_s + d'(v) (the source: 0).
Differences from the old bound: the spread no longer counts the source's step twice (at most
2^(j+1) - 1 receivers hold a late chunk j steps after the source's K-th); latency is the max with the
spread, not added to it (they overlap); latency is the best path's, not the direct pair's.
--csv adds the protocols' p99 (Figure 5's data) as ratios to the bound, per seed then median.
"""
import argparse
import csv
import math
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overlay_bound as ob  # noqa: E402


def simple(q, sh, ups, downs, adj, src=0):
    n = len(ups)
    tau = [sh.tau(u) for u in ups]
    tau_f = min(tau)
    B = sh.inject(ups[src])
    M = math.ceil(q * (n - 1))
    dp = ob.path_delay(adj, tau, src)
    start = [0.0 if v == src else tau[src] + dp[v] for v in range(n)]
    others = [w for w in range(n) if w != src]
    t = {"spread": B + (math.ceil(math.log2(M + 1)) - 1) * tau_f,
         "path": B + ob.nearest_rank([dp[w] for w in others], q),
         "agg": max(0.0, 8 * M * sh.S - n * 8 * sh.burst) / sum(ups),
         "recv": ob.nearest_rank([min(start[v] + l for v, l in adj[w]) + 8 * max(0, sh.S - sh.burst) / downs[w]
                                  for w in others], q)}
    t["T"] = max(t.values())
    t["dprime"] = ob.nearest_rank([dp[w] for w in others], q)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="7-16")
    ap.add_argument("--nodes", type=int, default=500)
    ap.add_argument("--ups", default="50,25,20,10")
    ap.add_argument("--net", default="home")
    ap.add_argument("--payload-kib", type=int, default=1024)
    ap.add_argument("--q", type=float, default=0.99)
    ap.add_argument("--csv", help="Figure 5's data (series,uplink_mbps,seed,p99_s,...)")
    ap.add_argument("--chunks", type=int, default=ob.CHUNKS)
    ap.add_argument("--burst", type=int, default=ob.MTU)
    ap.add_argument("--min-chunk", type=int, help="the smallest chunk admitted (default SEACAST's last)")
    a = ap.parse_args()
    S = round((a.payload_kib << 10) / ob.COMPRESSION)
    sh = ob.Shape(S, a.chunks, a.burst, a.min_chunk)
    n = a.nodes
    ups_list = [float(x) for x in a.ups.split(",")]
    rows = {}
    print(f"# S={S} B in K={sh.K} chunks of {sh.c} B (smallest admitted {sh.c_min}), burst {sh.burst} B, N={n}, q={a.q}, "
          f"net {a.net}, full mesh; ms")
    print("seed\tup_mbps\tbound\told\tspread\tpath\tagg\trecv\tdprime_q\tdirect_L_q")
    for seed in ob.parse_seeds(a.seeds):
        pair = ob.scenario.geo_latency(seed)(n, None)
        adj = [[(j, pair(i + 1, j + 1)) for j in range(n) if j != i] for i in range(n)]
        lat_src = [pair(1, j + 1) for j in range(1, n)]
        for u in ups_list:
            f = u / 50
            cls = ob.scenario.net(a.net, u * 1e6, 2 * u * 1e6, 1e9 * f, 1e9 * f)(n, None)
            ups = [cls[i + 1]["up"] for i in range(n)]
            downs = [cls[i + 1]["down"] for i in range(n)]
            t = simple(a.q, sh, ups, downs, adj)
            old = ob.old_bound(a.q, S, ups, downs, lat_src)
            rows[(seed, u)] = (t["T"], old)
            ms = lambda x: f"{x * 1000:.1f}"
            print("\t".join([str(seed), f"{u:g}", ms(t["T"]), ms(old), ms(t["spread"]), ms(t["path"]), ms(t["agg"]),
                             ms(t["recv"]), ms(t["dprime"]), ms(ob.nearest_rank(lat_src, a.q))]), flush=True)
    print("\n# per uplink over seeds: bound median [range]; old bound median [range]")
    for u in ups_list:
        b = [rows[(s, u)][0] * 1000 for s in ob.parse_seeds(a.seeds)]
        o = [rows[(s, u)][1] * 1000 for s in ob.parse_seeds(a.seeds)]
        print(f"{u:g}\t{statistics.median(b):.0f} [{min(b):.0f}-{max(b):.0f}]\t{statistics.median(o):.0f} [{min(o):.0f}-{max(o):.0f}]")
    if a.csv:
        p99 = {}
        for r in csv.DictReader(open(a.csv)):
            p99.setdefault(r["series"], {})[(int(r["seed"]), float(r["uplink_mbps"]))] = float(r["p99_s"])
        print("\n# p99 / bound: per-seed ratio median [range]; median p99 / median bound; same against the old bound")
        for series, d in p99.items():
            for u in ups_list:
                ss = [s for s in ob.parse_seeds(a.seeds) if (s, u) in d]
                if not ss:
                    continue
                r = [d[(s, u)] / rows[(s, u)][0] for s in ss]
                ro = [d[(s, u)] / rows[(s, u)][1] for s in ss]
                mm = statistics.median(d[(s, u)] for s in ss) / statistics.median(rows[(s, u)][0] for s in ss)
                mo = statistics.median(d[(s, u)] for s in ss) / statistics.median(rows[(s, u)][1] for s in ss)
                print(f"{series}\t{u:g}\tseeds {len(ss)}\t{statistics.median(r):.2f} [{min(r):.2f}-{max(r):.2f}]\t{mm:.2f}"
                      f"\told {statistics.median(ro):.2f} [{min(ro):.2f}-{max(ro):.2f}]\t{mo:.2f}")


if __name__ == "__main__":
    main()
