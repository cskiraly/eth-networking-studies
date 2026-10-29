#!/usr/bin/env python3
"""An overlay-aware lower bound on completion time for a chunked, coded payload broadcast from one
source over the network of our simulator (the harness): the real graph, each edge's one-way latency,
each node's links.

    python3 overlay_bound.py [--seeds 7-16] [--degree 16] [--ups 50,25,20,10] [--net home]
    python3 overlay_bound.py --selftest

The derivation in short, for the q-quantile of the receivers (M = ceil(q(N-1)) receivers, nearest rank):

  T(q) >= max(MATCH(q), AGG(q))

Model. The payload is S bytes; every chunk any protocol sends is at least c_min bytes (SEACAST:
compress first, 64 chunks of c = ceil(S/K), the last one 11619 B; --min-chunk 8982 also covers the
RS arm's truncated last chunk and gossipsub's whole message); a receiver completes once it holds
distinct chunks of the code totalling at least S bytes. A node forwards a chunk only once it holds
all of it. A node's uplink U_v carries at most MTU + U_v*t bytes in any interval of length t
(simnet's token bucket, one MTU of burst), so one chunk takes at least tau_v = 8(c_min - MTU)/U_v of
it, and the source's distinct chunks reach S bytes no earlier than B = 8(S - MTU)/U_s. A chunk sent
by u reaches v l(u,v) after its last bit left u. A receiver's downlink D_w likewise.

- Path: every completed receiver holds a late chunk (one that completed leaving the source when the
  source's distinct chunks reached S bytes, or later), which left the source no earlier than B and
  reached w over a graph path:
      a_w >= B + d'(w),   d'(w) = least sum of the path's latencies plus tau of every relay.
- Late chunks' spread jointly with the latency: keep, for every node, only the transfer that gave it
  its first late chunk (a tree from the source); treat "holds a late chunk" as one token; shift each
  node's retained transfers earlier by its tree path's latency. In that latency-free relaxation at
  most 2^(j+1) - 1 receivers hold the token by B + j*tau_f, and an h-hop tree path needs h - 1 relay
  transfers after B. So a receiver at level j (the 2^j receivers added at step j) over an h-hop path
  completes no earlier than B + max(j, h-1)*tau_f + l_h(w), l_h(w) the least latency over at most h
  hops.
- Per-receiver floors, folded in: the path term; the downlink, b_w + 8(S - MTU)/D_w with b_w the
  earliest a first bit can reach w (min over neighbours v of start(v) + l(v,w)); the incoming cut,
  sum over w's neighbours v of U_v*[T - l(v,w) - start(v)]_+ (+ one MTU each) >= 8S. Here
  start(v) = tau_s + d'(v), the earliest v holds any chunk (the source: 0).
- MATCH(q): the least T at which M receivers fit the levels with every floor <= T; an assignment to
  nested slots solved greedily by deadline.
- AGG(q): sum over all v of U_v*[T - l_min(v) - start(v)]_+ (+ one MTU each) >= 8*M*S.
The old bound (Figure 5's line before its correction of 22 October 2026) is printed beside it.
Graphs: graphgen/ (the harness's RandomRegular, copied); latencies: the geo model of the specification's
toy (scenario.py, toy/scenario.py at the specification's v0.6, unchanged), which equals the harness's
(checked against the harness's own latencies at 70 connections, seeds 7-9: same edges, within 1 us).
The publisher is node 0, as in the harness's cells.
"""
import argparse
import heapq
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scenario  # noqa: E402

COMPRESSION = (1 << 20) / 746262
CHUNKS = 64                            # SEACAST's data chunks (SEGMENT_FIXED_COUNT = 1 MiB / 16 KiB)
MTU = 1500                             # simnet's token-bucket burst on the virtual clock
OLD_CHUNK = 12000                      # the old bound's chunk
INF = float("inf")


class Shape:
    """The payload's chunking: S bytes in K data chunks of c, the last one shorter; c_min the smallest
    chunk the bound admits (default the last one; less to cover other protocols' chunks); burst in bytes."""

    def __init__(self, S, K=CHUNKS, burst=MTU, c_min=None):
        self.S, self.K, self.burst = S, K, burst
        self.c = math.ceil(S / K)
        self.c_min = S - (K - 1) * self.c if c_min is None else c_min
        assert 0 < self.c_min

    def tau(self, U):                  # least time one chunk occupies an uplink of U bits/s
        return 8 * max(0, self.c_min - self.burst) / U

    def inject(self, U):               # least time for the source's first S bytes of distinct chunks
        return 8 * max(0, self.S - self.burst) / U


def nearest_rank(xs, q):
    xs = sorted(xs)
    return xs[max(0, math.ceil(q * len(xs)) - 1)]


def graph(n, d, seed, _cache={}):
    """The harness's edges for (n, d, seed), from graphgen."""
    if "bin" not in _cache:
        out = os.path.join(tempfile.mkdtemp(prefix="graphgen-"), "graphgen")
        subprocess.run(["go", "build", "-o", out, "main.go"], cwd=os.path.join(HERE, "graphgen"), check=True,
                       env=dict(os.environ, GO111MODULE="off"))
        _cache["bin"] = out
    txt = subprocess.run([_cache["bin"], "-n", str(n), "-d", str(d), "-seed", str(seed)], check=True,
                         capture_output=True, text=True).stdout
    return [tuple(map(int, l.split())) for l in txt.splitlines()]


def adjacency(n, edges, lat):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append((b, lat(a, b)))
        adj[b].append((a, lat(b, a)))
    return adj


def path_delay(adj, tau, src=0):
    """d'(w): least sum of edge latencies plus each relay's tau (not the source's), Dijkstra."""
    dist = [INF] * len(adj)
    dist[src] = 0.0
    pq = [(0.0, src)]
    while pq:
        dv, v = heapq.heappop(pq)
        if dv > dist[v]:
            continue
        out = dv + (tau[v] if v != src else 0.0)
        for w, l in adj[v]:
            if out + l < dist[w]:
                dist[w] = out + l
                heapq.heappush(pq, (dist[w], w))
    return dist


def hop_latency(adj, src=0):
    """lh[h][w]: least latency of a path of at most h hops (h = 0.. until nothing improves)."""
    cur = [INF] * len(adj)
    cur[src] = 0.0
    lh = [cur]
    while True:
        nxt = cur[:]
        for v, dv in enumerate(cur):
            if dv < INF:
                for w, l in adj[v]:
                    if dv + l < nxt[w]:
                        nxt[w] = dv + l
        if nxt == cur:
            return lh
        lh.append(nxt)
        cur = nxt


def solve(f, need, hi=1.0):
    """The least T >= 0 with f(T) >= need, f nondecreasing; the bracket grows until it holds, and a
    supply that never reaches the need (no sender at all) is infinite."""
    while f(hi) < need:
        if f(2 * hi) <= f(hi):
            return INF
        hi *= 2
    lo = 0.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if f(mid) >= need:
            hi = mid
        else:
            lo = mid
    return hi


def ramp(ups, starts, lats, burst_bits):
    """Bits a set of senders can land by T: each from start + latency, at its rate, one burst each."""
    def f(T):
        return sum(u * (T - s - l) + burst_bits for u, s, l in zip(ups, starts, lats) if T > s + l)
    return f


def match_bound(B, tau_f, floors, lh, M, src=0):
    """MATCH: the least T at which M receivers fit the late chunks' levels (see the module doc)."""
    n = len(floors)
    H = len(lh) - 1
    recv = [w for w in range(n) if w != src]

    def cost(w, j):                    # completion floor of w placed at level j
        best = INF
        for h in range(1, H + 1):
            if lh[h][w] < INF:
                best = min(best, B + max(j, h - 1) * tau_f + lh[h][w])
        return max(best, floors[w])

    J = math.ceil(math.log2(M + 1))    # levels 0..J-1 hold 2^J - 1 >= M receivers
    costs = {w: [cost(w, j) for j in range(J)] for w in recv}

    def feasible(T):
        deadlines = []
        for w in recv:
            dl = -1
            for j in range(J):
                if costs[w][j] <= T:
                    dl = j                 # cost is nondecreasing in j
            if dl >= 0:
                deadlines.append(dl)
        deadlines.sort()
        placed = 0
        for dl in deadlines:
            if placed < 2 ** (dl + 1) - 1:   # levels 0..dl hold 2^(dl+1) - 1
                placed += 1
        return placed >= M

    cands = sorted({c for cs in costs.values() for c in cs})
    lo, hi = 0, len(cands) - 1
    if not feasible(cands[hi]):
        return INF
    while lo < hi:
        mid = (lo + hi) // 2
        if feasible(cands[mid]):
            hi = mid
        else:
            lo = mid + 1
    return cands[lo]


def old_bound(q, S, ups, downs, lat_src):
    """The old bound's T(q), for comparison (receivers' links, the source's apart)."""
    n = len(ups) - 1
    K = math.ceil(S / OLD_CHUNK)
    tau_src = OLD_CHUNK * 8 / ups[0]
    tau_fast = OLD_CHUNK * 8 / max(ups)
    serial = K * tau_src
    spread = math.ceil(math.log2(q * n + 1)) * tau_fast
    agg = q * n * S * 8 / sum(ups)
    recv = S * 8 / -nearest_rank([-d for d in downs[1:]], q)
    return max(serial + spread, agg, recv) + nearest_rank(lat_src, q)


def bound(q, shape, ups, downs, adj, src=0):
    """The overlay-aware bound and its terms, in seconds."""
    n = len(ups)
    tau = [shape.tau(u) for u in ups]
    tau_f = min(tau)
    B = shape.inject(ups[src])
    burst = 8 * shape.burst
    dp = path_delay(adj, tau, src)
    lh = hop_latency(adj, src)
    start = [0.0 if v == src else tau[src] + dp[v] for v in range(n)]
    path = [B + dp[w] for w in range(n)]
    recv = [min(start[v] + l for v, l in adj[w]) + 8 * max(0, shape.S - shape.burst) / downs[w] for w in range(n)]
    cut = [solve(ramp([ups[v] for v, _ in adj[w]], [start[v] for v, _ in adj[w]], [l for _, l in adj[w]], burst),
                 8 * shape.S) if w != src else 0.0 for w in range(n)]
    floors = [max(path[w], recv[w], cut[w]) for w in range(n)]
    M = math.ceil(q * (n - 1))
    match = match_bound(B, tau_f, floors, lh, M, src)
    lmin = [min(l for _, l in adj[v]) for v in range(n)]
    agg = solve(ramp(ups, start, lmin, burst), 8 * M * shape.S)
    others = [w for w in range(n) if w != src]
    return {"T": max(match, agg), "match": match, "agg": agg,
            "path": nearest_rank([path[w] for w in others], q),
            "recv": nearest_rank([recv[w] for w in others], q),
            "cut": nearest_rank([cut[w] for w in others], q),
            "dprime": nearest_rank([dp[w] for w in others], q),
            "lat": nearest_rank([lh[-1][w] for w in others], q),
            "hops": max(next(h for h in range(len(lh)) if lh[h][w] < INF) for w in others),
            "inject": B}


def selftest():
    sh = Shape(10 * 1000, K=10, burst=0)                 # K = 10 chunks of 1000 B, no burst
    U = 1000 * 8 / 1e-3                                  # tau = 1 ms
    # 1. full mesh, no latency: K*tau + (ceil(log2(M+1)) - 1)*tau
    for n in (2, 3, 4, 9, 17, 100):
        edges = [(a, b) for a in range(n) for b in range(a + 1, n)]
        adj = adjacency(n, edges, lambda a, b: 0.0)
        b = bound(1.0, sh, [U] * n, [1e15] * n, adj)
        want = (10 + math.ceil(math.log2(n)) - 1) * 1e-3
        assert abs(b["match"] - want) < 1e-9, (n, b["match"], want)
    # 2. the counterexample to adding spread and latency: two receivers at 10 ms and 0 from the source;
    # all ten chunks to the far one in [0, 10], then to the near one in [10, 20]: both done at 20
    adj = adjacency(3, [(0, 1), (0, 2)], lambda a, b: 0.010 if 1 in (a, b) else 0.0)
    b = bound(1.0, sh, [U] * 3, [1e15] * 3, adj)
    assert b["T"] <= 0.020 + 1e-9, b
    assert abs(b["match"] - 0.020) < 1e-9, b
    # 3. a line of 4 with 5 ms edges: the last node is 3 hops, 2 relays out
    adj = adjacency(4, [(0, 1), (1, 2), (2, 3)], lambda a, b: 0.005)
    b = bound(1.0, sh, [U] * 4, [1e15] * 4, adj)
    assert abs(b["match"] - (0.010 + 0.015 + 0.002)) < 1e-9, b
    # 4. a slow downlink binds: all S through D from the first possible bit
    adj = adjacency(2, [(0, 1)], lambda a, b: 0.0)
    b = bound(1.0, sh, [U, U], [U, U / 4], adj)
    assert abs(b["match"] - 0.040) < 1e-9, b
    # 5. A diamond: s-a-w, s-b-w, K = 2, zero latency, source 100 chunks/s,
    # a and b 1 chunk/s, w's downlink 2 chunks/s; a feasible schedule completes everyone by 1.02 s
    sh2 = Shape(2 * 1000, K=2, burst=0)
    u = 1000 * 8
    adj = adjacency(4, [(0, 1), (0, 2), (1, 3), (2, 3)], lambda a, b: 0.0)
    b = bound(1.0, sh2, [100 * u, u, u, u], [1e15, 1e15, 1e15, 2 * u], adj)
    assert b["T"] <= 1.02 + 1e-9, b
    # 6. the burst: one MTU of a chunk is free, so a 1000 B chunk with a 500 B burst takes half
    sh3 = Shape(1000, K=1, burst=500)
    adj = adjacency(2, [(0, 1)], lambda a, b: 0.0)
    b = bound(1.0, sh3, [U, U], [1e15, 1e15], adj)
    assert abs(b["match"] - 0.0005) < 1e-9, b
    print("selftest: ok")


def parse_seeds(s):
    out = []
    for part in s.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="7-16")
    ap.add_argument("--nodes", type=int, default=500)
    ap.add_argument("--degree", type=int, default=16)
    ap.add_argument("--ups", default="50,25,20,10", help="the all-home uplink in Mbps; downlink twice that")
    ap.add_argument("--net", default="home")
    ap.add_argument("--payload-kib", type=int, default=1024)
    ap.add_argument("--chunks", type=int, default=CHUNKS)
    ap.add_argument("--burst", type=int, default=MTU)
    ap.add_argument("--min-chunk", type=int, help="the smallest chunk admitted (default SEACAST's last)")
    ap.add_argument("--quantiles", default="0.99")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    S = round((a.payload_kib << 10) / COMPRESSION)
    sh = Shape(S, a.chunks, a.burst, a.min_chunk)
    qs = [float(x) for x in a.quantiles.split(",")]
    print(f"# S={S} B in K={sh.K} chunks of {sh.c} B (smallest admitted {sh.c_min}), burst {sh.burst} B, N={a.nodes}, "
          f"degree {a.degree}, net {a.net}; ms")
    print("seed\tup_mbps\tq\tbound\told\tmatch\tagg\tpath\trecv\tcut\tinject\tdprime_q\tlat_q\tmaxhops")
    for seed in parse_seeds(a.seeds):
        pair = scenario.geo_latency(seed)(a.nodes, None)
        lat = lambda i, j: pair(i + 1, j + 1)          # toy ids are harness index + 1
        adj = adjacency(a.nodes, graph(a.nodes, a.degree, seed), lat)
        lat_src = [lat(0, j) for j in range(1, a.nodes)]
        for u in (float(x) for x in a.ups.split(",")):
            f = u / 50
            cls = scenario.net(a.net, u * 1e6, 2 * u * 1e6, 1e9 * f, 1e9 * f)(a.nodes, None)
            ups = [cls[i + 1]["up"] for i in range(a.nodes)]
            downs = [cls[i + 1]["down"] for i in range(a.nodes)]
            for q in qs:
                b = bound(q, sh, ups, downs, adj)
                old = old_bound(q, S, ups, downs, lat_src)
                ms = lambda x: f"{x * 1000:.1f}"
                print("\t".join([str(seed), f"{u:g}", f"{q:g}", ms(b["T"]), ms(old), ms(b["match"]), ms(b["agg"]),
                                 ms(b["path"]), ms(b["recv"]), ms(b["cut"]), ms(b["inject"]), ms(b["dprime"]),
                                 ms(b["lat"]), str(b["hops"])]), flush=True)


if __name__ == "__main__":
    main()
