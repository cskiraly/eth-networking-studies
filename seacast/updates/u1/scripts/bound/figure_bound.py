#!/usr/bin/env python3
"""Figure 5's bound, per protocol and per warm payload: each payload's own size and chunks.

    python3 figure_bound.py [--seeds 7-16] [--ups 50,25,20,10] [--warm 2-6] [--q 0.99] [--record OUT]

Each message of a cell in our simulator (the harness) has its own content (q6cell_test.go, c.build),
so its own compressed size S and chunk sizes (data/payload-sizes.tsv, from payloadsize/). Per seed,
uplink and arm, this
computes the bound for every warm payload with that payload's S and smallest chunk c_min, and
reports their median: the figure's p99 is the median over warm payloads of each payload's p99, and if
every payload's p99 is at least its bound, the k-th smallest p99 is at least the k-th smallest bound.

Arms (what a receiver needs, and the smallest chunk it is sent):
  seacast    compress first, 64 data chunks: S = the compressed size, c_min = its last chunk
  rs         the whole message in 16384-byte chunks, padded: S = chunks x 16384, c_min = 16384
  gossipsub  the whole message: S = c_min = its size
  all        one line under all three: S = the least of the three, c_min = the least of the three
Both bounds: the overlay-aware one (overlay_bound.py, the 16-connection graph) and the all-pairs one
(simple_bound.py). --record writes the "all" rows as data/seacast_elastic_all_bound.tsv, Figure 5's
line (the all-pairs bound, median over the seeds) and the overlay-aware bound beside it.
"""
import argparse
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import overlay_bound as ob  # noqa: E402
import simple_bound as sb  # noqa: E402

RS_CHUNK = 16384
RECORD_HEAD = """\
# Figure 5's lower bound per seed: the median over warm payloads 2-6 of each payload's bound for the 99th-percentile
# receiver, q = 0.99, the all-home network at 16 connections, downlink twice the uplink, one-packet burst 1500 B; ms.
# Each payload's bound uses that payload's compressed size and the smallest chunk any of the three arms sends (SEACAST's),
# so one line bounds all three. allpairs: the corrected links' bound, Figure 5's line (median over seeds below); overlay:
# the overlay-aware bound on the simulator's own graphs, for reference.
"""


def sizes(path):
    rows = {}
    lines = [l.split("\t") for l in open(path).read().splitlines()]
    head = lines[0]
    for r in lines[1:]:
        d = dict(zip(head, r))
        rows[int(d["msg"])] = {k: int(v) for k, v in d.items()}
    return rows


def shapes(z, burst):
    """Per arm, (S, K, c_min) for one payload's sizes z."""
    arms = {"seacast": (z["compressed_bytes"], 64, z["last_chunk_bytes"]),
            "rs": (z["rs_bytes"], z["rs_chunks"], RS_CHUNK),
            "gossipsub": (z["whole_bytes"], 1, z["whole_bytes"])}
    S = min(v[0] for v in arms.values())
    arms["all"] = (S, 64, min(v[2] for v in arms.values()))
    return {k: ob.Shape(S_, K, burst, c) for k, (S_, K, c) in arms.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="7-16")
    ap.add_argument("--nodes", type=int, default=500)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--ups", default="50,25,20,10")
    ap.add_argument("--net", default="home")
    ap.add_argument("--warm", default="2-6")
    ap.add_argument("--q", type=float, default=0.99)
    ap.add_argument("--burst", type=int, default=ob.MTU)
    ap.add_argument("--sizes", default=os.path.join(HERE, "..", "..", "data", "payload-sizes.tsv"))
    ap.add_argument("--record")
    a = ap.parse_args()
    rec = []
    z = sizes(a.sizes)
    warm = ob.parse_seeds(a.warm)
    n = a.nodes
    print(f"# per seed, uplink and arm: the median over warm payloads {a.warm} of each payload's bound "
          f"(q = {a.q}, degree {a.degree}, burst {a.burst} B); ms")
    print("seed\tup_mbps\tarm\toverlay\toverlay_min\toverlay_max\tallpairs\tallpairs_min\tallpairs_max")
    for seed in ob.parse_seeds(a.seeds):
        pair = ob.scenario.geo_latency(seed)(n, None)
        lat = lambda i, j: pair(i + 1, j + 1)
        adj = ob.adjacency(n, ob.graph(n, a.degree, seed), lat)
        full = [[(j, lat(i, j)) for j in range(n) if j != i] for i in range(n)]
        for u in (float(x) for x in a.ups.split(",")):
            f = u / 50
            cls = ob.scenario.net(a.net, u * 1e6, 2 * u * 1e6, 1e9 * f, 1e9 * f)(n, None)
            ups = [cls[i + 1]["up"] for i in range(n)]
            downs = [cls[i + 1]["down"] for i in range(n)]
            per = {}
            for m in warm:
                for arm, sh in shapes(z[m], a.burst).items():
                    o = ob.bound(a.q, sh, ups, downs, adj)["T"]
                    p = sb.simple(a.q, sh, ups, downs, full)["T"]
                    per.setdefault(arm, []).append((o, p))
            for arm in ("all", "seacast", "rs", "gossipsub"):
                o = [x[0] * 1000 for x in per[arm]]
                p = [x[1] * 1000 for x in per[arm]]
                v = [f"{x:.1f}" for x in (statistics.median(o), min(o), max(o), statistics.median(p), min(p), max(p))]
                print("\t".join([str(seed), f"{u:g}", arm] + v), flush=True)
                if arm == "all":
                    rec.append([str(seed), f"{u:g}"] + v[3:] + v[:3])
    if a.record:
        ups = list(dict.fromkeys(r[1] for r in rec))
        meds = ", ".join(f"{u} Mbps {statistics.median(float(r[2]) for r in rec if r[1] == u):.1f}" for u in ups)
        with open(a.record, "w") as f:
            f.write(RECORD_HEAD + f"# medians over seeds, allpairs: {meds}\n")
            f.write("seed\tup_mbps\tallpairs\tallpairs_min\tallpairs_max\toverlay\toverlay_min\toverlay_max\n")
            f.writelines("\t".join(r) + "\n" for r in rec)


if __name__ == "__main__":
    main()
