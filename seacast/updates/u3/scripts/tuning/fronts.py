#!/usr/bin/env python3
"""The tuning's reading: from read.py's rows to fronts, by the reading the study plan fixed before any run and the
rules below completed.

    python3 fronts.py --seeds 7 [--expect LIST.dry]... [--select-seeds 7] [--cpu CPU.csv --cpu-machine NAME]
                      [--carry] [--pairs] [--csv OUT.csv] [--nodes 500] [--bound group] HOST=cells.csv...
    python3 fronts.py --selftest

Each cells.csv is read.py's output for one host's logs; HOST= names the host (A, B, ...).
--seeds is the stage's exact seed set (7; 7,8,9; 7,...,16; 1024,2048,3072). Rows of other seeds are not
used and are counted in the first line. --expect names the lists' .dry files (check_list.sh's output: one
line per cell that should have run): a cell of the stage's seeds that is in a list and not in the rows is
printed as missing, and --carry is refused for a point with a missing cell. Without --expect nothing says
that a cell never ran; --carry then needs --no-expect to say so on purpose.

What must be one, or it is an error and not a row: the node count (500, or --nodes), the SEACAST binary
(md5), the counter on in every SEACAST cell that can have it, one host per point (the study plan's "one host per
front"), one cell per setting and seed.

A setting is a SEACAST cell's knobs without its seed: (R, chunk size, code, parity factor, fast budget, ask
wait, target, projection, fault, loss, discipline). A point is a payload size and a network. Per point:
  - time and bytes of a setting are the medians over the stage's seeds of p99_s and mib; copies is bytes
    over the compressed size of payload 1 (the median comp_b of the point's size, read.py);
  - a setting's status: failed (a cell in which the network did not deliver a payload), short (a seed of
    the stage without a cell), censored (a cell with a warm payload that fewer than 99 % of all nodes ever
    completed, so that it has no time: in a passing test only under the spoofing fault, whose spoofers
    starve themselves; the count of honest nodes holding it at 3 s is printed with it), bound (a cell at a numeric offer bound, the
    fork's 256 among them, whose warm groups had an announcement refused at one of the offer table's two
    bounds: the harness's limit was in play; read.py's refused_warm), else ok. Under the bound that follows
    the group a refusal is no status but a mark, REFUSED UNDER THE GROUP BOUND, with its count: what that
    bound still refuses (a peer announcing more than 256 ids of a group before the node's first validated
    chunk of it) is the rule itself, and the setting is ranked. Only ok settings are ranked, carried
    or compared. The first of these that applies is the status; censoring and the offer bound are printed
    and exported beside any status;
  - PAST 3 s marks a setting with a cell whose worst warm payload fewer than 99 % of the nodes held at the
    3 s deadline (read.py's at_3s). It is a mark, not a status: the setting's time is its completion time
    whenever it came, as in Figure 6, and it is ranked by it;
  - a setting's kind: grid (coded by the code rule, or the specification's plain group where the
    specification sends one: 16 KiB chunks and 2K above 256), uncoded (the small-size corner), known (the
    table code gf8: the known-answer cells), other (a probe, a fault, a loss, the runner's discipline);
  - the front is over the ok grid settings: those no other one beats (at least as good on both time and
    bytes, better on one). Equal on both keeps both; equal on one axis and worse on the other loses.
    Uncoded settings are shown beside it and marked where one would be on it; they never enter it;
  - the base is the earlier posts' setting: R by size (4 to 256 KiB, 3 to 512 KiB, 2 above), 16 KiB chunks,
    coded by the code rule or plain where the specification sends plain, every probe knob at its default.
    A Leopard code other than the code rule's is a probe (other), and so is a fast budget other than the
    one that goes with R (6; R itself above 6), and an offer bound other than the stage's (--bound: group,
    the bound that follows the group; the known answers and the bound's measurement run others).
--carry prints what stage 1 carries to stage 2, per point:
  - at most 4 beside the base, in this order: the front's fastest, the front's lightest, the rest of the
    front by time, then the settings within the repeat noise of a front setting in both time and bytes
    (time 6 % and bytes 3 % from 512 KiB up; time 10 % and bytes 8 % below, where four runs of one cell
    spread by 6 to 8 % in bytes) by time; what the cap cuts is printed;
  - outside the cap, the ok neighbours of the front's fastest (one grid step in R or in chunk size), so
    that the study plan's test against the best neighbour has cells in the later stages;
  - outside the cap, the corner: each uncoded setting that would be on the front, and its coded twin if ok;
  - the base whatever its status (named with it); every other setting that is not ok is carried by no
    rule, and the neighbours and twins left out for their status are listed.
  Ties are broken by time, then bytes, then the setting's knobs, never by the order of the input.
--pairs prints, for the front's fastest setting, on how many seeds it is faster and lighter than the base
and than its best neighbour (the fastest ok neighbour by the median), paired by seed; with --select-seeds
also over the seeds that did not select it. A neighbour without all the stage's seeds is named with its
count, not skipped. The plan's words: "faster" at 3 of 3 (stage 2), named alone at 8 of 10 or more (stage
3); this prints the counts, the words are the reader's.
A neighbour of a setting differs from it in R by one step of the grid with every other knob equal, or in
chunk size by one step with every other knob equal but the code, which may follow the code rule from
Leopard GF(2^8) to GF(2^16); a plain or uncoded setting has neighbours of its own kind only.
The column spec names the constants of the specification a setting needs changed (the specification's
seacast-lite.md §1, §8.3): UNIT (another chunk size than 16 KiB), MAX_SEGMENT_SIZE (a compressed chunk above 32 KiB),
MAX_CHUNKS (a coded group above 256 chunks), N=2K, R_FAST, IWANT_WINDOW (with PROMISE), TARGET, offer lists
(the bound on the ordered lists an announcer is in, §8.2: a group above 256 chunks under the bound that
follows the group, or a numeric bound other than 256; a group of exactly 256 chunks fits the 256 and is not
marked), uncoded (no code where the specification codes). Every coded cell of the tuning uses a Leopard code where the
specification has the table code: that change is the same for all and not in the column. R is open in the
specification and never in it.
--cpu joins the codec's CPU table (payload_kib,k,n,...,code,op,median_ms,...): encode and
decode-half of the setting's shape and code in ms, on the machine --cpu-machine names (required with --cpu
and printed with the figures). A shape the table lacks is empty. The CPU figures take no part in any rule here.
"""
import csv
import math
import statistics as st
import sys
from collections import defaultdict

R_STEPS = (1, 2, 3, 4, 6, 8, 12)
UNIT_STEPS = (2, 4, 8, 16, 32, 64, 128)   # 2 KiB: where stage 1's grid grows below 4 KiB
KEY = ("push_r", "unit_kib", "code", "rsx", "r_fast", "ask_ms", "target_ms", "proj", "fault", "loss", "disc", "offer_bound")
STAGE_BOUND = "group"   # the offer bound the stage's grid runs with (--bound): the one that follows the group


def base_r(size):
    return 4 if size <= 256 else 3 if size <= 512 else 2


def spec_plain(size):
    """The specification sends a plain group where 2K passes MAX_CHUNKS at its UNIT of 16 KiB."""
    return 2 * -(-size // 16) > 256


def setting(row):
    return (int(row["push_r"]), int(row["unit_kib"]), row["code"], int(row["rsx"]), row["r_fast"],
            row["ask_ms"], row["target_ms"], row["proj"], row["fault"], row["loss"], row["disc"], row["offer_bound"])


def rule_rfast(r):
    """The fast nodes' budget that goes with R: 6, and R itself once the grid grows past 6."""
    return "6" if r <= 6 else str(r)


def rule_code(size, unit, rsx):
    """The code rule: Leopard GF(2^8) to 128 parity chunks, GF(2^16) above."""
    return "leo8" if -(-size // unit) * rsx <= 128 else "leo16"


def norm(s):
    """A setting with its fast budget replaced by "rule" where it is the one that goes with its R."""
    return s[:4] + ("rule" if s[4] == rule_rfast(s[0]) else s[4],) + s[5:]


def kind(s, size):
    r, unit, code, rsx, rfast, ask, tgt, proj, fault, loss, disc, bound = s
    if code == "gf8":
        return "known"
    if (rsx, rfast, ask, tgt, proj, fault, loss) != (1, rule_rfast(r), "200", "20", "2", "", "") or disc == "runner":
        return "other"
    if bound != STAGE_BOUND:
        return "other"
    if code in ("leo8", "leo16") and code != rule_code(size, unit, rsx):
        return "other"
    if code == "unc":
        return "uncoded"
    if code == "plain":
        return "grid" if unit == 16 and spec_plain(size) else "uncoded"
    return "grid"


def is_base(s, size):
    if kind(s, size) != "grid" or s[0] != base_r(size) or s[1] != 16:
        return False
    return (s[2] == "plain") == spec_plain(size)


def spec_change(s, size, k, n, chunk_b):
    r, unit, code, rsx, rfast, ask, tgt, proj, fault, loss, disc, bound = s
    out = []
    if unit != 16:
        out.append("UNIT")
    if chunk_b and chunk_b > 32768:
        out.append("MAX_SEGMENT_SIZE")
    if code not in ("unc", "plain") and n > 256:
        out.append("MAX_CHUNKS")
    if code == "unc" or (code == "plain" and not (unit == 16 and spec_plain(size))):
        out.append("uncoded")
    if rsx != 1:
        out.append("N=2K")
    if rfast != "6":
        out.append("R_FAST")
    if ask not in ("200", ""):
        out.append("IWANT_WINDOW")
    if tgt != "20":
        out.append("TARGET")
    if (bound == "group" and n > 256) or bound not in ("group", "256", ""):
        out.append("offer lists")   # a bound following the group changes nothing for a group of at most 256 chunks
    return "+".join(out) or "-"


def order(S):
    """The deterministic order of settings: time, bytes, then the knobs."""
    return lambda s: (S[s]["time"], S[s]["mib"], tuple(str(x) for x in s))


def front(points):
    """points: {key: (time, bytes)} -> the keys no other key beats (as good on both, better on one)."""
    out = set()
    for a, (ta, ba) in points.items():
        if not any((tb <= ta and bb <= ba) and (tb < ta or bb < ba) for b, (tb, bb) in points.items() if b != a):
            out.add(a)
    return out


def load(args):
    rows = []
    for arg in args:
        host, _, path = arg.partition("=")
        if not path:
            sys.exit(f"want HOST=cells.csv, got {arg}")
        with open(path) as fh:
            for row in csv.DictReader(fh):
                row["host"] = host
                rows.append(row)
    return rows


def load_expect(paths):
    """check_list.sh's .dry files -> {log name: (size, network, seed)}"""
    out = {}
    for p in paths:
        for ln in open(p):
            f = dict(kv.split("=", 1) for kv in ln.split()[1:])
            out[f["tag"] + ".log"] = (int(f["size"]), "dcb20" if f["net"] == "dcb20" else "all-home", int(f["seed"]))
    return out


def analyse(rows, seeds, nodes=500, expect=None):
    """-> (info, {point: {...}}); exits on what must be one and is not."""
    seeds = sorted(seeds)
    used = [r for r in rows if int(r["seed"]) in seeds]
    info = {"ignored": len(rows) - len(used), "seeds": seeds}
    if not used:
        sys.exit(f"no row of seeds {seeds}")
    bad = sorted({r["nodes"] for r in used} - {str(nodes)})
    if bad:
        sys.exit(f"rows of {bad} nodes among rows of {nodes}: another experiment")
    if any(r["protocol"] == "seacast" and not r["bin_md5"] for r in used):
        sys.exit("a SEACAST row without its binary's md5")
    md5s = sorted({r["bin_md5"] for r in used if r["protocol"] == "seacast"})
    if len(md5s) > 1:
        sys.exit(f"the SEACAST cells ran {len(md5s)} binaries: {md5s}")
    info["md5"] = md5s[0] if md5s else ""
    for r in used:
        if r["protocol"] == "seacast" and r["counted"] != "1" and r["disc"] != "runner":
            sys.exit(f"a SEACAST cell without the counter among counted ones: {r['log']}")
    have = {r["log"] for r in used}
    missing = defaultdict(list)
    for log, (size, net, seed) in (expect or {}).items():
        if seed in seeds and log not in have:
            missing[(size, net)].append(log)
    by_point = defaultdict(list)
    for r in used:
        by_point[(int(r["size_kib"]), r["network"])].append(r)
    comp = defaultdict(list)
    for r in used:
        if r["comp_b"]:
            comp[int(r["size_kib"])].append(int(r["comp_b"]))
    out = {}
    for point in sorted(set(by_point) | set(missing)):
        size, net = point
        prs = by_point.get(point, [])
        hosts = {r["host"] for r in prs}
        if len(hosts) > 1:
            sys.exit(f"{size} KiB on {net} has cells from hosts {sorted(hosts)}: one host per front")
        comp_mib = st.median(comp[size]) / 2**20 if comp[size] else None
        cells, gs = defaultdict(dict), {}
        for r in prs:
            tgt = cells[setting(r)] if r["protocol"] == "seacast" else gs
            if int(r["seed"]) in tgt:
                sys.exit(f"two cells of one setting and seed: {r['log']}")
            tgt[int(r["seed"])] = r
        S = {}
        for s, by_seed in cells.items():
            failed = sorted(x for x, c in by_seed.items() if c["passed"] != "True")
            lack = [x for x in seeds if x not in by_seed]
            d = {"kind": kind(s, size), "base": is_base(s, size), "cells": by_seed, "failed_seeds": failed, "lack": lack,
                 "k": int(next(iter(by_seed.values()))["k"]), "n": int(next(iter(by_seed.values()))["n"])}
            good = [c for c in by_seed.values() if c["passed"] == "True"]
            rec = sum(int(c["recorded_warm"]) for c in good if c["recorded_warm"] != "")
            ref = sum(int(c["refused_warm"]) for c in good if c["refused_warm"] != "")
            d["recorded"], d["refused"] = rec, ref
            d["bound_cells"] = sum(1 for c in good if c["refused_warm"] not in ("", "0"))
            d["censored"] = sum(int(c["censored_warm"]) for c in good if c["censored_warm"] != "")
            d["censored_cells"] = sum(1 for c in good if c["censored_warm"] not in ("", "0"))
            hc = [tuple(int(x) for x in c["honest_at_3s"].split("/")) for c in good if c["honest_at_3s"]]
            d["honest"] = min(hc, key=lambda t: t[0] / t[1]) if hc else None
            a3 = [tuple(int(x) for x in c["at_3s"].split("/")) for c in good if c["at_3s"]]
            d["at_3s"] = min(a3, key=lambda t: t[0] / t[1]) if a3 else None
            d["past_3s"] = sum(1 for a, b in a3 if a < math.ceil(0.99 * b))
            # a refusal under the bound that follows the group is the protocol's own (a mark); under a numeric
            # bound it is the harness's limit in play (the status bound)
            d["refused_mark"] = bool(d["bound_cells"]) and s[11] == "group"
            d["status"] = ("failed" if failed else "short" if lack else "censored" if d["censored_cells"]
                           else "bound" if d["bound_cells"] and s[11] != "group" else "ok")
            if good and not failed and not d["censored_cells"]:
                d["time"] = st.median(float(c["p99_s"]) for c in good)
                d["mib"] = st.median(float(c["mib"]) for c in good)
                d["copies"] = d["mib"] / comp_mib if comp_mib else None
                cb = [int(c["chunk_b"]) for c in good if c["chunk_b"]]
                d["chunk_b"] = int(st.median(cb)) if cb else 0
                for cls in ("dc_rx_mib", "other_rx_mib"):
                    v = [float(c[cls]) for c in good if c[cls]]
                    d[cls] = st.median(v) if len(v) == len(good) and v else None
            d["spec"] = spec_change(s, size, d["k"], d["n"], d.get("chunk_b", 0))
            S[s] = d
        elig = {s: (d["time"], d["mib"]) for s, d in S.items() if d["status"] == "ok" and d["kind"] == "grid"}
        fr = front(elig)
        for s, d in S.items():
            d["front"] = s in fr
            d["would_front"] = (d["status"] == "ok" and d["kind"] == "uncoded"
                                and s in front({**elig, s: (d["time"], d["mib"])}))
        g = None
        if gs:
            gfail = sorted(x for x, c in gs.items() if c["passed"] != "True")
            glack = [x for x in seeds if x not in gs]
            gg = [c for c in gs.values() if c["passed"] == "True"]
            gcens = sum(1 for c in gg if c["censored_warm"] not in ("", "0"))
            ga3 = [tuple(int(x) for x in c["at_3s"].split("/")) for c in gg if c["at_3s"]]
            g = {"status": "failed" if gfail else "short" if glack else "censored" if gcens else "ok",
                 "failed_seeds": gfail, "lack": glack, "past_3s": sum(1 for a, b in ga3 if a < math.ceil(0.99 * b)),
                 "at_3s": min(ga3, key=lambda t: t[0] / t[1]) if ga3 else None}
            if gg and not gfail and not gcens:
                g["time"] = st.median(float(c["p99_s"]) for c in gg)
                g["mib"] = st.median(float(c["mib"]) for c in gg)
        out[point] = {"host": hosts.pop() if hosts else "-", "comp_mib": comp_mib, "settings": S, "front": fr,
                      "gossipsub": g, "missing": sorted(missing.get(point, []))}
    return info, out


def neighbours(s, S):
    """Every setting of S one grid step from s in R or in chunk size, whatever its status."""
    out = []
    for cand in S:
        if cand == s or norm(cand)[3:] != norm(s)[3:] or S[cand].get("kind") != S.get(s, {}).get("kind"):
            continue   # a neighbour is of the setting's own kind: a probe is no neighbour of a grid setting
        r_step = cand[1] == s[1] and cand[2] == s[2] and s[0] in R_STEPS and cand[0] in R_STEPS and \
            abs(R_STEPS.index(cand[0]) - R_STEPS.index(s[0])) == 1
        leo = {"leo8", "leo16"}
        u_step = cand[0] == s[0] and (cand[2] == s[2] or {cand[2], s[2]} <= leo) and s[1] in UNIT_STEPS and \
            cand[1] in UNIT_STEPS and abs(UNIT_STEPS.index(cand[1]) - UNIT_STEPS.index(s[1])) == 1
        if r_step or u_step:
            out.append(cand)
    return sorted(out, key=lambda c: tuple(str(x) for x in c))


def carry(point, info, cap=4):
    """-> picked (the cap), base, cut, neighbours of the fastest, corner, bound"""
    size = point[0]
    tol_t, tol_b = (0.06, 0.03) if size >= 512 else (0.10, 0.08)   # the repeat noise; bytes below 512 KiB from four runs of one cell
    S = info["settings"]
    key = order(S)
    fr = sorted(info["front"], key=key)
    near = [s for s, d in S.items() if d["status"] == "ok" and d["kind"] == "grid" and s not in info["front"]
            and any(abs(d["time"] / S[f]["time"] - 1) <= tol_t and abs(d["mib"] / S[f]["mib"] - 1) <= tol_b for f in fr)]
    near.sort(key=key)
    seq = []
    if fr:
        lightest = min(fr, key=lambda s: (S[s]["mib"], S[s]["time"], tuple(str(x) for x in s)))
        for s in [fr[0], lightest] + fr + near:
            if s not in seq:
                seq.append(s)
    cands = [s for s in seq if not S[s]["base"]]
    picked, cut = cands[:cap], cands[cap:]
    base = sorted((s for s, d in S.items() if d["base"]), key=lambda c: tuple(str(x) for x in c))
    allnb = [s for s in (neighbours(fr[0], S) if fr else []) if s not in picked and not S[s]["base"]]
    nb = [s for s in allnb if S[s]["status"] == "ok"]
    out_of = [s for s in allnb if S[s]["status"] != "ok"]
    corner = []
    for s, d in sorted(S.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        if d["would_front"]:
            corner.append(s)
            twin = [c for c in S if c[:2] == s[:2] and c[3:] == s[3:] and c[2] in ("leo8", "leo16") and S[c]["kind"] == "grid"]
            corner += [c for c in twin if S[c]["status"] == "ok" and c not in picked and c not in corner and not S[c]["base"]]
            out_of += [c for c in twin if S[c]["status"] != "ok" and c not in out_of and not S[c]["base"]]
    bound = sorted((s for s, d in S.items() if d["status"] == "bound"), key=lambda c: tuple(str(x) for x in c))
    return picked, base, cut, nb, corner, bound, out_of


def paired(a, b, S, seeds):
    seeds = [x for x in seeds if x in S[a]["cells"] and x in S[b]["cells"]
             and S[a]["cells"][x]["passed"] == "True" and S[b]["cells"][x]["passed"] == "True"]
    faster = sum(float(S[a]["cells"][x]["p99_s"]) < float(S[b]["cells"][x]["p99_s"]) for x in seeds)
    lighter = sum(float(S[a]["cells"][x]["mib"]) < float(S[b]["cells"][x]["mib"]) for x in seeds)
    return faster, lighter, len(seeds)


def name(s):
    r, unit, code, rsx, rfast, ask, tgt, proj, fault, loss, disc, bound = s
    x = f"R={r} unit={unit}K {code}"
    x += f" rsx={rsx}" if rsx != 1 else ""
    x += f" rfast={rfast}" if rfast != "6" else ""
    x += " disc=runner" if disc == "runner" else f" ask={ask}" if ask != "200" else ""
    x += f" tgt={tgt}" if tgt != "20" else ""
    x += " noproj" if proj != "2" else ""
    x += f" {fault}" if fault else ""
    x += f" loss={loss}" if loss else ""
    x += f" bound={bound}" if bound != STAGE_BOUND else ""
    return x


def load_cpu(path):
    cpu = {}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            cpu[(int(r["payload_kib"]), int(r["k"]), int(r["n"]), r["code"], r["op"])] = float(r["median_ms"])
    return cpu


def cpu_of(cpu, size, d, s):
    code = {"gf8": "table"}.get(s[2], s[2])
    enc = cpu.get((size, d["k"], d["n"], code, "encode"))
    dec = cpu.get((size, d["k"], d["n"], code, "decode-half"))
    return ("" if enc is None else f"{enc:.2f}", "" if dec is None else f"{dec:.2f}")


CSV_HEAD = ["size_kib", "network", "host", *KEY, "status", "kind", "base", "front", "seeds", "p99_s", "mib", "copies",
            "k", "n", "chunk_b", "spec", "recorded_warm", "refused_warm", "refused_cells", "censored_warm", "censored_cells",
            "past_3s_cells", "at_3s_worst", "honest_at_3s_worst", "dc_rx_mib", "other_rx_mib",
            "cpu_encode_ms", "cpu_decode_ms", "cpu_machine", "bin_md5"]


def report(info, res, cpu=None, cpu_machine="", do_carry=False, do_pairs=False, out_csv=None, select=(), have_expect=False):
    seeds = info["seeds"]
    print(f"seeds {seeds}; the stage's offer bound: {STAGE_BOUND}; {info['ignored']} rows of other seeds not used; "
          f"SEACAST binary md5 {info['md5'] or '-'}"
          + (f"; CPU figures: {cpu_machine}" if cpu else "") + ("" if have_expect else "; no list given: a cell that never ran is not seen"))
    rows_out = []
    for point, pi in res.items():
        size, net = point
        S = pi["settings"]
        comp = f"{pi['comp_mib']:.4f} MiB" if pi["comp_mib"] else "unknown"
        print(f"\n== {size} KiB, {net} (host {pi['host']}; payload 1 compressed {comp})")
        if pi["missing"]:
            print(f"   MISSING: {len(pi['missing'])} cells of the lists never read: " + "; ".join(pi["missing"][:3])
                  + (" ..." if len(pi["missing"]) > 3 else ""))
        g = pi["gossipsub"]
        if g:
            if g["status"] == "ok":
                cp = f"{g['mib'] / pi['comp_mib']:.2f} copies" if pi["comp_mib"] else f"{g['mib']:.4f} MiB"
                print(f"   gossipsub, the whole message: {g['time']:.4f} s, {cp}"
                      + (f" PAST 3 s in {g['past_3s']} cells (worst warm payload {g['at_3s'][0]} of {g['at_3s'][1]})" if g["past_3s"] else ""))
            else:
                print(f"   gossipsub, the whole message: {g['status'].upper()} (failed seeds {g['failed_seeds']}, lacking {g['lack']})")
        ranked = sorted((s for s in S if "time" in S[s]), key=order(S))
        rest = sorted((s for s in S if "time" not in S[s]), key=lambda c: tuple(str(x) for x in c))
        for s in ranked + rest:
            d = S[s]
            marks = (" FRONT" if d["front"] else "") + (" base" if d["base"] else "")
            marks += {"uncoded": " (uncoded; would be on the front)" if d["would_front"] else " (uncoded)",
                      "known": " (the table code: a known-answer cell)", "other": " (outside the grid)"}.get(d["kind"], "")
            st_ = {"failed": f" FAILED on seeds {d['failed_seeds']}", "short": f" SHORT: no cell at seeds {d['lack']}",
                   "censored": "", "bound": "", "ok": ""}[d["status"]]
            # what a cell says beside its primary status, whatever that status is
            if d["censored_cells"]:
                st_ += f" CENSORED: on {d['censored']} warm payloads in {d['censored_cells']} cells fewer than 99 % of the nodes ever completed (no time)"
            if d["bound_cells"] and s[11] == "group":
                st_ += f" REFUSED UNDER THE GROUP BOUND: {d['refused']} of {d['recorded'] + d['refused']} warm announcements, in {d['bound_cells']} cells"
            elif d["bound_cells"]:
                st_ += f" AT THE HARNESS'S OFFER BOUND: {d['refused']} of {d['recorded'] + d['refused']} warm announcements refused, in {d['bound_cells']} cells"
            if d["past_3s"]:
                st_ += f" PAST 3 s: in {d['past_3s']} cells fewer than 99 % held it at the deadline (worst warm payload {d['at_3s'][0]} of {d['at_3s'][1]})"
            enc, dec = cpu_of(cpu, size, d, s) if cpu else ("", "")
            if "time" in d:
                cp = f"{d['copies']:.2f} copies" if d["copies"] is not None else ""
                print(f"   {name(s):34s} {d['time']:.4f} s  {d['mib']:.4f} MiB  {cp}  K={d['k']:<3d} spec {d['spec']}"
                      + (f"  cpu {enc or '-'}/{dec or '-'} ms" if cpu else "") + marks + st_)
            else:
                print(f"   {name(s):34s} no statistics  K={d['k']:<3d}" + marks + st_)
            if (s[8] or s[9]) and d["honest"]:
                print(f"   {'':34s} honest nodes holding it at 3 s, the worst warm payload: {d['honest'][0]} of {d['honest'][1]}")
            rows_out.append([size, net, pi["host"], *s, d["status"], d["kind"], d["base"],
                             "front" if d["front"] else "would" if d["would_front"] else "", len(d["cells"]),
                             f"{d['time']:.4f}" if "time" in d else "", f"{d['mib']:.4f}" if "time" in d else "",
                             f"{d['copies']:.3f}" if d.get("copies") is not None else "", d["k"], d["n"], d.get("chunk_b", ""),
                             d["spec"], d["recorded"], d["refused"], d["bound_cells"], d["censored"], d["censored_cells"],
                             d["past_3s"], "/".join(str(x) for x in d["at_3s"]) if d["at_3s"] else "",
                             "/".join(str(x) for x in d["honest"]) if d["honest"] else "",
                             f"{d['dc_rx_mib']:.4f}" if d.get("dc_rx_mib") is not None else "",
                             f"{d['other_rx_mib']:.4f}" if d.get("other_rx_mib") is not None else "", enc, dec,
                             cpu_machine if cpu else "", info["md5"]])
        nbound = sum(1 for d in S.values() if d["bound_cells"] and not d["refused_mark"])
        if nbound:
            print(f"   {nbound} settings at a numeric offer bound with refusals: the harness's limit was in play, they are not ranked")
        if do_carry:
            if pi["missing"]:
                print("   carry: NOT COMPUTED, cells are missing")
            else:
                picked, base, cut, nb, corner, bound, out_of = carry(point, pi)
                print("   carried: " + ("; ".join(name(s) for s in picked) or "-") + " | base: "
                      + ("; ".join(name(s) + ("" if S[s]["status"] == "ok" else f" [{S[s]['status']}]") for s in base) or "NONE"))
                if len(base) != 1:
                    print(f"   {len(base)} BASE SETTINGS at this point, want 1")
                dropped = [s for s in cut if s not in nb and s not in corner]
                if dropped:
                    print("   beyond the cap of 4, carried by no rule: " + "; ".join(name(s) for s in dropped))
                if len(dropped) < len(cut):
                    print("   beyond the cap of 4, carried by a rule below: " + "; ".join(name(s) for s in cut if s not in dropped))
                if nb:
                    print("   carried outside the cap, the fastest's neighbours: " + "; ".join(name(s) for s in nb))
                if corner:
                    print("   carried outside the cap, the corner (uncoded on the front, and coded twins): " + "; ".join(name(s) for s in corner))
                if out_of:
                    print("   neighbours and twins not carried, for their status: "
                          + "; ".join(f"{name(s)} [{S[s]['status']}]" for s in out_of))
                if bound:
                    print("   at the offer bound, carried by no rule: " + "; ".join(name(s) for s in bound if not S[s]["base"]))
                grid = [s for s in S if S[s]["kind"] == "grid"]
                edge = [s for s in sorted(pi["front"], key=order(S)) if grid and (
                    s[0] == max(x[0] for x in grid) or s[1] in (min(x[1] for x in grid), max(x[1] for x in grid)))]
                if edge:
                    print("   on the grid's edge (geometric only): " + "; ".join(name(s) for s in edge))
        if do_pairs and pi["front"]:
            best = min(pi["front"], key=order(S))
            fresh = [x for x in seeds if x not in select]

            def line(label, o):
                f, l, n = paired(best, o, S, seeds)
                txt = f"   fastest: {name(best)} against the {label} {name(o)}: faster on {f} of {n} seeds, lighter on {l} of {n}"
                if select:
                    f2, l2, n2 = paired(best, o, S, fresh)
                    txt += f"; on the seeds that did not select it ({n2}): faster on {f2}, lighter on {l2}"
                if S[o]["status"] != "ok":
                    txt += f" [{label} is {S[o]['status']}]"
                print(txt)
            bases = [s for s, d in S.items() if d["base"]]
            if not bases:
                print("   fastest: NO BASE at this point")
            for o in bases:
                if o == best:
                    print(f"   fastest: {name(best)} is the base")
                elif S[o]["status"] == "ok":
                    line("base", o)
                else:
                    print(f"   fastest: {name(best)}: the base {name(o)} is {S[o]['status']}: no comparison")
            nbs = neighbours(best, S)
            okn = sorted((s for s in nbs if S[s]["status"] == "ok"), key=order(S))
            for s in nbs:
                if S[s]["status"] != "ok":
                    print(f"   neighbour {name(s)} is {S[s]['status']} ({len(seeds) - len(S[s]['lack'])} of {len(seeds)} seeds): no comparison")
            if okn:
                line("best neighbour", okn[0])
            elif not nbs:
                print(f"   fastest: {name(best)} has NO NEIGHBOUR among the cells: the study plan's neighbour test cannot be made")
    if out_csv:
        with open(out_csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(CSV_HEAD)
            for r in rows_out:
                assert len(r) == len(CSV_HEAD), (len(r), len(CSV_HEAD))
                w.writerow(r)


def selftest():
    def cell(size, net, seed, r, unit, t, b, code="leo8", passed=True, **kw):
        k = -(-size // unit)
        row = {"protocol": "seacast", "network": net, "size_kib": str(size), "seed": str(seed), "nodes": "500",
               "push_r": str(r), "unit_kib": str(unit), "k": str(k), "n": str(k if code in ("unc", "plain") else 2 * k),
               "code": code, "rsx": "1", "r_fast": "6", "ask_ms": "200", "target_ms": "20", "proj": "2", "fault": "", "loss": "",
               "disc": "arm", "offer_bound": "group", "counted": "1", "chunk_b": str(int(unit * 1024 * 0.71)),
               "comp_b": "" if code == "plain" else str(int(size * 1024 * 0.71)), "bin_md5": "a" * 32,
               "passed": str(passed), "p99_s": f"{t}" if passed else "", "mib": f"{b}" if passed else "",
               "dc_rx_mib": "", "other_rx_mib": "", "recorded_warm": "1000" if passed else "", "refused_warm": "0" if passed else "",
               "censored_warm": "0" if passed else "", "honest_at_3s": "499/499" if passed else "",
               "at_3s": "499/499" if passed else "",
               "log": f"x{size}{net}{seed}r{r}u{unit}{code}{kw.get('r_fast', '')}", "host": "A"}
        row.update(kw)
        return row
    rows = []
    for seed in (7, 8, 9):
        j = (seed - 7) * 0.001
        rows += [cell(1024, "all-home", seed, 2, 16, 0.60 + j, 1.30),      # base: on the front (lightest)
                 cell(1024, "all-home", seed, 3, 16, 0.55 + j, 1.50),      # front
                 cell(1024, "all-home", seed, 4, 16, 0.50 + j, 1.80),      # front (fastest)
                 cell(1024, "all-home", seed, 6, 16, 0.52 + j, 2.20, at_3s="499/499" if seed != 8 else "480/499"),  # beaten by R=4
                 cell(1024, "all-home", seed, 4, 32, 0.51 + j, 1.82),      # beaten, but within noise of R=4/16
                 cell(1024, "all-home", seed, 1, 16, 0.90, 1.25, passed=(seed != 8)),   # failed on one seed
                 cell(1024, "all-home", seed, 2, 16, 0.40, 1.00, code="unc"),            # uncoded: beside the front
                 cell(1024, "all-home", seed, 2, 16, 0.30, 0.90, r_fast="12"),           # a probe: outside
                 cell(1024, "all-home", seed, 2, 16, 0.20, 0.80, code="gf8"),            # a known-answer cell: outside
                 cell(1024, "all-home", seed, 2, 4, 0.10, 0.50, code="leo16", offer_bound="256",
                      refused_warm="0" if seed != 9 else "3"),                           # a numeric bound with a refusal: bound
                 cell(1024, "all-home", seed, 3, 4, 0.70, 1.20, code="leo16", refused_warm="0" if seed != 9 else "5")]  # group: a mark
    rows += [cell(1024, "all-home", s, 3, 32, 0.56, 1.49) for s in (7, 8)]               # short: no seed 9
    rows += [cell(1024, "all-home", s, 1, 32, 0.05, 0.40, censored_warm="2" if s == 8 else "0",
                  p99_s="" if s == 8 else "0.05") for s in (7, 8, 9)]                    # censored on one seed
    info, res = analyse(rows, [7, 8, 9])
    pi = res[(1024, "all-home")]
    S = pi["settings"]
    key = lambda r, u, code="leo8", rf="6", ob="group": (r, u, code, 1, rf, "200", "20", "2", "", "", "arm", ob)  # noqa: E731
    assert pi["front"] == {key(2, 16), key(3, 16), key(4, 16), key(3, 4, "leo16")}, pi["front"]
    assert S[key(2, 16)]["base"] and not S[key(3, 16)]["base"] and not S[key(2, 16, "gf8")]["base"]
    assert S[key(1, 16)]["status"] == "failed" and not S[key(1, 16)]["front"]
    assert S[key(3, 32)]["status"] == "short" and not S[key(3, 32)]["front"]
    assert S[key(1, 32)]["status"] == "censored" and not S[key(1, 32)]["front"] and "time" not in S[key(1, 32)]
    assert S[key(6, 16)]["past_3s"] == 1 and S[key(6, 16)]["status"] == "ok"      # past 3 s is a mark, still ranked
    assert kind(key(2, 16, "leo16"), 1024) == "other" and kind(key(2, 4, "leo16"), 1024) == "grid"   # the code rule
    assert kind(key(8, 16, rf="8"), 1024) == "grid" and kind(key(8, 16), 1024) == "other"             # R above 6
    assert kind(key(2, 16, ob="256"), 1024) == "other" and kind(key(2, 16, "gf8", ob="256"), 1024) == "known"   # the stage's bound
    assert "bound=8192" in name(key(2, 16, ob="8192")) and spec_change(key(2, 16), 1024, 64, 128, 11600) == "-"
    assert spec_change(key(2, 4, "leo16"), 1024, 256, 512, 2900) == "UNIT+MAX_CHUNKS+offer lists"
    assert spec_change(key(2, 16, ob="8192"), 1024, 64, 128, 11600) == "offer lists"
    S8 = {key(6, 16): {"kind": "grid"}, key(8, 16, rf="8"): {"kind": "grid"}, key(8, 16): {"kind": "other"}}
    Sc = {key(4, 16): {"kind": "grid"}, key(4, 32, "leo16"): {"kind": "other"}, key(4, 32): {"kind": "grid"}}
    assert neighbours(key(4, 16), Sc) == [key(4, 32)], neighbours(key(4, 16), Sc)     # a forced code is no neighbour
    assert neighbours(key(6, 16), S8) == [key(8, 16, rf="8")], neighbours(key(6, 16), S8)
    kb = key(2, 4, "leo16", ob="256")
    assert S[kb]["status"] == "bound" and not S[kb]["front"] and S[kb]["refused"] == 3 and S[kb]["kind"] == "other"
    km = key(3, 4, "leo16")
    assert S[km]["status"] == "ok" and S[km]["refused_mark"] and S[km]["front"] and S[km]["refused"] == 5   # ranked, marked
    assert S[key(2, 16, "unc")]["kind"] == "uncoded" and S[key(2, 16, "unc")]["would_front"] and not S[key(2, 16, "unc")]["front"]
    assert S[key(2, 16, rf="12")]["kind"] == "other" and S[key(2, 16, "gf8")]["kind"] == "known"
    picked, base, cut, nb, corner, bound, out_of = carry((1024, "all-home"), pi)
    assert picked == [key(4, 16), key(3, 4, "leo16"), key(3, 16), key(4, 32)] and base == [key(2, 16)] and not cut, (picked, base, cut)
    assert nb == [key(6, 16)], nb                                       # R=3/16 and 4/32 are in the cap already
    assert corner == [key(2, 16, "unc")] and bound == [key(2, 4, "leo16", ob="256")], (corner, bound)
    assert set(neighbours(key(4, 16), S)) == {key(3, 16), key(6, 16), key(4, 32)}, neighbours(key(4, 16), S)
    assert key(3, 32) in neighbours(key(3, 16), S)                      # a short neighbour is still named
    assert paired(key(4, 16), key(2, 16), S, [7, 8, 9]) == (3, 0, 3) and paired(key(4, 16), key(2, 16), S, [8, 9]) == (2, 0, 2)
    assert S[key(4, 32)]["spec"] == "UNIT" and S[key(2, 16)]["spec"] == "-" and S[key(2, 16, "unc")]["spec"] == "uncoded"
    assert spec_change(key(2, 64, ob="256"), 1024, 16, 32, 46000) == "UNIT+MAX_SEGMENT_SIZE"
    assert spec_change(key(2, 16, "leo16", ob="256"), 4096, 256, 512, 11600) == "MAX_CHUNKS"
    # ties: the same time and bytes keep both, in the knobs' order; an input in another order gives the same carry
    rev = analyse(list(reversed(rows)), [7, 8, 9])[1][(1024, "all-home")]
    assert carry((1024, "all-home"), rev)[:3] == (picked, base, cut)
    # the base where the specification sends plain; a coded 16 KiB shape there is not the base
    r4 = [cell(4096, "dcb20", 7, 2, 16, 1.1, 5.0, code="plain"), cell(4096, "dcb20", 7, 2, 32, 0.9, 5.5),
          cell(4096, "dcb20", 7, 2, 16, 1.0, 5.2, code="leo16"), cell(4096, "dcb20", 7, 3, 16, 1.2, 5.6, code="plain")]
    S4 = analyse(r4, [7])[1][(4096, "dcb20")]["settings"]
    kp = key(2, 16, "plain")
    assert S4[kp]["base"] and not S4[key(2, 16, "leo16")]["base"] and S4[kp]["kind"] == "grid"
    assert neighbours(kp, S4) == [key(3, 16, "plain")], neighbours(kp, S4)     # plain has plain neighbours only
    assert key(2, 32) in neighbours(key(2, 16, "leo16"), S4)                    # the code rule across a chunk-size step
    assert is_base(key(2, 16, "plain"), 3072) and not is_base(key(2, 16, "leo16"), 3072) and is_base(key(2, 16), 2048)
    assert kind(key(4, 16, "plain"), 128) == "uncoded"
    # a list: a cell that never ran is missing
    exp = {r["log"]: (1024, "all-home", int(r["seed"])) for r in rows}
    exp["never-ran.log"] = (1024, "all-home", 9)
    exp["another-stage.log"] = (1024, "all-home", 12)
    assert analyse(rows, [7, 8, 9], expect=exp)[1][(1024, "all-home")]["missing"] == ["never-ran.log"]
    assert analyse(rows, [7], expect=exp)[0]["ignored"] == len(rows) - sum(1 for r in rows if r["seed"] == "7")
    for bad in (r4 + [cell(4096, "dcb20", 8, 2, 32, 0.9, 5.5, host="B")],           # two hosts at one point
                rows + [cell(1024, "all-home", 7, 2, 8, 0.6, 1.3, nodes="100")],    # another node count
                rows + [cell(1024, "all-home", 7, 2, 8, 0.6, 1.3, bin_md5="b" * 32)],  # another binary
                rows + [cell(1024, "all-home", 7, 2, 8, 0.6, 1.3, counted="0")],    # a cell without the counter
                rows + [rows[0]]):                                                  # one cell twice
        try:
            analyse(bad, [7, 8, 9])
        except SystemExit:
            continue
        raise AssertionError("accepted")
    assert front({"a": (1, 2), "b": (2, 1), "c": (2, 2), "d": (1, 2), "e": (1, 3)}) == {"a", "b", "d"}
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report(info, res, do_carry=True, do_pairs=True, select=(7,), have_expect=False)
    text = buf.getvalue()
    for want in ("AT THE HARNESS'S OFFER BOUND: 3 of 3003", "REFUSED UNDER THE GROUP BOUND: 5 of 3005", "SHORT: no cell at seeds [9]", "FAILED on seeds [8]",
                 "CENSORED: on 2 warm payloads in 1 cells", "PAST 3 s: in 1 cells fewer than 99 % held it at the deadline (worst warm payload 480 of 499)",
                 "on the seeds that did not select it (2): faster on 2", "against the best neighbour R=4 unit=32K leo8",
                 "carried outside the cap, the fastest's neighbours: R=6 unit=16K leo8"):
        assert want in text, (want, text)
    print("selftest: fronts, base, failed, short, bound, uncoded, known, probes, carry, neighbours, pairs, ties, "
          "the list, one host, one binary, one node count: ok")


def main():
    global STAGE_BOUND
    a = sys.argv[1:]
    if a == ["--selftest"]:
        return selftest()
    cpu = out_csv = None
    cpu_machine = ""
    do_carry = do_pairs = no_expect = False
    files, expect, seeds, select, nodes = [], [], None, (), 500
    while a:
        x = a.pop(0)
        if x == "--cpu":
            cpu = load_cpu(a.pop(0))
        elif x == "--cpu-machine":
            cpu_machine = a.pop(0)
        elif x == "--csv":
            out_csv = a.pop(0)
        elif x == "--carry":
            do_carry = True
        elif x == "--pairs":
            do_pairs = True
        elif x == "--no-expect":
            no_expect = True
        elif x == "--expect":
            expect.append(a.pop(0))
        elif x == "--seeds":
            seeds = [int(v) for v in a.pop(0).split(",")]
        elif x == "--select-seeds":
            select = tuple(int(v) for v in a.pop(0).split(","))
        elif x == "--nodes":
            nodes = int(a.pop(0))
        elif x == "--bound":
            STAGE_BOUND = a.pop(0)
            if not (STAGE_BOUND == "group" or (STAGE_BOUND.isdigit() and int(STAGE_BOUND) >= 1 and STAGE_BOUND[0] != "0")):
                sys.exit(f"--bound takes group or a number, not {STAGE_BOUND}")
        else:
            files.append(x)
    if not files or not seeds:
        sys.exit(__doc__)
    if cpu and not cpu_machine:
        sys.exit("--cpu needs --cpu-machine: a CPU figure is quoted with its machine")
    if do_carry and not expect and not no_expect:
        sys.exit("--carry needs --expect LIST.dry (or --no-expect, to carry without knowing what should have run)")
    info, res = analyse(load(files), seeds, nodes, load_expect(expect) if expect else None)
    report(info, res, cpu, cpu_machine, do_carry, do_pairs, out_csv, select, bool(expect))


if __name__ == "__main__":
    main()
