#!/usr/bin/env python3
"""Stage 3's reading: per point, the best setting at ten seeds, named alone or with its best neighbour, the
preferred one, and what it means for the living text, by the rules fixed before any stage 3 cell was read.

    python3 best.py --expect LIST.dry... --set STAGE3.csv... [--csv OUT.csv] HOST=cells.csv...
    python3 best.py --selftest

The cells: read.py's rows of stage 1, the grow batch, stage 2 and stage 3 for each host (stage 3's from the logs of
its two main lists only: its two repeat cells repeat stage 2's identities and are read apart).
--expect names every list's .dry file of those runs, and is required: a row of seeds 7 to 16 that is no cell of
them stops the run. --set names stage 2's choice of stage 3's settings with their roles (selection.py --roles
selected,base,fastest-neighbour --csv: stage2/stage3-<machine>.csv), and is required. fronts.analyse's checks hold
(one node count, one SEACAST binary, one host a point, one cell a setting and seed). A setting is ok at ten seeds
only with a passed cell at every seed 7 to 16 (fronts.py's statuses), so a point's ok settings are stage 3's set.

A point gets no reading (REFUSED, with the reason), and the run exits nonzero, where: a listed cell is not in
the rows (MISSING); the set names a point that has no rows (NO ROWS); a point with rows has no set (NO SET); the
set's host is not the point's (HOST); a role is not one selection.py writes (a base's status among them), a
setting holds a role twice or no role of the filter stage 2 ran (selected, base, fastest-neighbour), or the point
has not exactly one fastest and one base, or more than one lighter point or fastest's best neighbour (ROLES); a
setting of the set has no cells (ABSENT); a setting of the set, or gossipsub at a size where stage 3 ran it
(make_lists.GOSSIPSUB_SIZES), lacks a seed of the ten (SHORT: its list and rows were left out together); a
setting outside the set has a cell of seeds 10 to 16 (OUTSIDE); or the set's base is not the cells' base (BASE).
Per point otherwise:
  - the set at ten seeds, ranked by the median of ten (time, bytes, then the knobs; the medians exact, as
    fractions of the rows' decimal strings, so that an exact tie falls to the next key), each with its medians,
    copies, the specification's constants it changes (fronts.py's column), its marks (PAST 3 s, refused under
    the group bound) and its roles; the set's settings that are not ok are named with their status and marks and
    take no part;
  - every pair of the set's ok settings, the faster by the median first, compared paired by seed: the counts
    (faster, lighter on n of 10; a tie on a seed counts for neither), the median per-seed gaps (time
    1 - t_A / t_B, bytes 1 - b_A / b_B; positive where A is faster or lighter; the median of ten is the mean of
    the middle two), the verdict, and beside it the counts and the median time gap on seeds 10 to 16 alone,
    the seeds that took no part in the choice (stage 2 chose on 7 to 9). The verdict ("8 of 10, beyond
    noise"): "clearly faster" ("clearly lighter") where A is faster (lighter) on at
    least 8 of the 10 seeds and the median gap is beyond stage 1's noise allowance (time 6 % from 512 KiB up and
    10 % below; bytes 3 % and 8 %); "clearly slower" ("clearly heavier") where B is clearly faster (lighter)
    than A by B's own gap; else "close" on that axis. A pair without ten seeds both passed is never clear.
    Exact fractions, so that a gap of exactly the allowance is not beyond it;
  - the best: the fastest by the median of ten among the set's selected settings (stage 2's fastest and its
    lighter point: only they can be named best); a tie in time with the other
    selected setting is printed. Its best neighbour: the fastest by the median of ten of its ok neighbours
    (fronts.neighbours: one grid step in R or in chunk size), printed with how many of its neighbours among the
    cells are ok at ten seeds; a set setting that ranks above the best and is not selected is printed, with the
    key that put it there;
  - NAMED ALONE where the best is clearly faster than its best neighbour (the study plan's "beats its best neighbour on
    at least 8 of 10 seeds", read with the verdict's "clearly"; where
    the best wins on 8 or more seeds but within the allowance, a note says that the count alone would name it
    alone); otherwise BOTH NAMED; where the best has no ok neighbour, NOT COMPARED, and the best is named alone;
  - every named setting against the base (the default: fronts.is_base). The bar against the default: a setting
    clears it when it is clearly faster than the default, or clearly lighter and not clearly slower. PREFERRED,
    where both are named: the lighter by the median of ten (bytes, then time, then the knobs; the key that decided
    is printed) of those of the two that clear the bar, or of both where neither does (the study plan's "the lighter is
    preferred", with the clear gain first: the lighter rule picks only among the named settings that clear the
    bar). The outcome for the text, from the preferred
    setting against the default:
      CHANGE: the preferred setting is clearly faster than the default, its byte verdict beside it; or it is
        clearly lighter and close in time;
      DEFAULT HOLDS: the preferred setting is the default; or it is close in time and not clearly lighter (a gap
        that stays close is reported and the default kept); or it is clearly slower (the default is clearly
        faster), the preferred setting's byte verdict beside it;
      FOR THE AUTHOR: no selected setting is ok at ten seeds;
      NO COMPARISON: the default is not ok at ten seeds (first: also where no selected setting is ok); the best,
        the named settings, the preferred one, MISSED and gossipsub's comparison with the preferred setting are
        still given where a selected setting is ok;
    and these flags beside the outcome, for the author: SPLIT, where the outcome is DEFAULT HOLDS, a set setting
    that is not named and not the default clears the bar; MISSED, a set setting that is not selected (the default
    among them) is clearly faster than the best; with CHANGE only, PREFERRED NOT SELECTED (the change goes to the
    best's neighbour) and NO NEIGHBOUR TEST (the change goes to a best that was not compared with a neighbour);
  - gossipsub's whole message where the point has it, a reference outside the rules: its status and medians at
    ten seeds, and its comparisons, by the same verdict, with the default and with the preferred setting where
    that is not the default; at a point where stage 3 did not run it, named and not compared.
At the end: a table, one line a point, and the points by outcome. --csv writes that table, one row a point; it is
not written when a point is refused.
"""
import contextlib
import csv
import io
import os
import statistics as st
import sys
from fractions import Fraction

import fronts
import make_lists  # stage 3's lists: where it ran gossipsub

HERE = os.path.dirname(os.path.abspath(__file__))

SEEDS = tuple(range(7, 17))
FRESH = tuple(range(10, 17))   # stage 3's own seeds: they took no part in choosing the set
CLEAR = 8                      # "8 of 10"
GS = ("gossipsub",)            # gossipsub's key beside the settings, for the verdict
GS_SIZES = tuple(make_lists.GOSSIPSUB_SIZES)   # where stage 3 ran gossipsub
SELECTED = ("the fastest", "the lighter point")
ROLE_SET = ("the fastest", "the lighter point", "the base", "the fastest's best neighbour",
            "option: the lighter point's best neighbour", "option: the corner", "option: the corner (its coded twin)")
BASE_STATUS = ("failed", "short", "censored")   # selection.py's "the base [status]": fronts.py's statuses but ok
FILTER = ("the fastest", "the lighter point", "the fastest's best neighbour")   # with a base's: --roles
                                                                               # selected,base,fastest-neighbour
NOTE = ("gossipsub's whole message is a reference outside the rules: unsigned, with the author's peer id and a "
        "sequence number on every message, its relays skipping the author (as in u2's Figure 6); SEACAST's cells run "
        "Prysm's authorless policy. Its rows carry no binary md5: its binary's md5 was checked "
        "before each run")


def noise(size):
    """Stage 1's noise allowance (time, bytes): time 6 % and bytes 3 % from 512 KiB up, time 10 % and bytes
    8 % below (the repeat noise of four runs of one cell)."""
    return (Fraction("0.06"), Fraction("0.03")) if size >= 512 else (Fraction("0.10"), Fraction("0.08"))


def both(a, b, S, seeds):
    return [x for x in seeds if x in S[a]["cells"] and x in S[b]["cells"]
            and S[a]["cells"][x]["passed"] == "True" and S[b]["cells"][x]["passed"] == "True"]


def wins(a, b, S, xs, col):
    return sum(Fraction(S[a]["cells"][x][col]) < Fraction(S[b]["cells"][x][col]) for x in xs)


def gap(a, b, S, xs, col):
    return st.median(1 - Fraction(S[a]["cells"][x][col]) / Fraction(S[b]["cells"][x][col]) for x in xs) if xs else None


def verdict(a, b, S, size):
    """a against b, paired by seed over the ten seeds; also the counts and the time gap on seeds 10 to 16."""
    xs = both(a, b, S, SEEDS)
    tol_t, tol_b = noise(size)
    full = len(xs) == len(SEEDS)
    fx = [x for x in xs if x in FRESH]
    return {"f": wins(a, b, S, xs, "p99_s"), "l": wins(a, b, S, xs, "mib"), "n": len(xs),
            "tg": gap(a, b, S, xs, "p99_s"), "bg": gap(a, b, S, xs, "mib"),
            "faster": full and wins(a, b, S, xs, "p99_s") >= CLEAR and gap(a, b, S, xs, "p99_s") > tol_t,
            "lighter": full and wins(a, b, S, xs, "mib") >= CLEAR and gap(a, b, S, xs, "mib") > tol_b,
            # a clear loss is b clearly faster (lighter) than a, by b's own gap: the verdicts are antisymmetric
            "slower": full and wins(b, a, S, xs, "p99_s") >= CLEAR and gap(b, a, S, xs, "p99_s") > tol_t,
            "heavier": full and wins(b, a, S, xs, "mib") >= CLEAR and gap(b, a, S, xs, "mib") > tol_b,
            "ff": wins(a, b, S, fx, "p99_s"), "fl": wins(a, b, S, fx, "mib"), "fn": len(fx), "ftg": gap(a, b, S, fx, "p99_s")}


def pct(x):
    return f"{float(x) * 100:+.2f} %"


def words(v):
    t = "clearly faster" if v["faster"] else "clearly slower" if v["slower"] else ""
    b = "clearly lighter" if v["lighter"] else "clearly heavier" if v["heavier"] else ""
    return " and ".join(x for x in (t, b) if x) or "close"


def vtext(v):
    """'faster on 9 of 10 (median +7.12 %), lighter on 0 of 10 (median -12.30 %): clearly heavier; on seeds 10 to
    16 (7): faster on 6 (median +6.50 %), lighter on 0'"""
    if not v["n"]:
        return "no seed with both cells passed"
    s = (f"faster on {v['f']} of {v['n']} (median {pct(v['tg'])}), lighter on {v['l']} of {v['n']} "
         f"(median {pct(v['bg'])}): {words(v)}")
    if v["fn"]:
        s += f"; on seeds 10 to 16 ({v['fn']}): faster on {v['ff']} (median {pct(v['ftg'])}), lighter on {v['fl']}"
    return s


def knobs(s):
    return tuple(str(x) for x in s)


def med(S, s, col):
    """The exact median of a setting's passed cells (all ten for an ok setting)."""
    return st.median(Fraction(c[col]) for c in S[s]["cells"].values() if c["passed"] == "True")


def decided(S, a, b, cols):
    """The first of cols on which a and b differ by the exact median of ten, or None (the knobs decide)."""
    return next((c for c in cols if med(S, a, c) != med(S, b, c)), None)


def marks(d):
    m = ""
    if d.get("past_3s"):
        m += f" PAST 3 s in {d['past_3s']} cells (worst warm payload {d['at_3s'][0]} of {d['at_3s'][1]})"
    if d.get("refused_mark"):
        m += f" REFUSED UNDER THE GROUP BOUND: {d['refused']} of {d['recorded'] + d['refused']} warm announcements in {d['bound_cells']} cells"
    return m


def fig(S, s):
    d = S[s]
    cp = f", {d['copies']:.2f} copies" if d.get("copies") is not None else ""
    return f"{fronts.name(s)} ({d['time']:.4f} s, {d['mib']:.4f} MiB{cp}; spec {d['spec']})" + marks(d)


def load_set(paths):
    """stage3-0N.csv files -> {point: {"host": h, "roles": {setting: [role, ...]}}}"""
    out = {}
    for p in paths:
        with open(p) as fh:
            for r in csv.DictReader(fh):
                pt, s = (int(r["size_kib"]), r["network"]), fronts.setting(r)
                d = out.setdefault(pt, {"host": r["host"], "roles": {}})
                if d["host"] != r["host"] or s in d["roles"]:
                    sys.exit(f"{p}: {pt} has two hosts or a setting twice: {r}")
                d["roles"][s] = r["roles"].split("; ")
    return out


def is_base_role(r):
    return r == "the base" or r in tuple(f"the base [{x}]" for x in BASE_STATUS)


def check_roles(roles):
    """-> why the roles are not selection.py's, or None."""
    bad = sorted({r for rs in roles.values() for r in rs if r not in ROLE_SET and not is_base_role(r)})
    if bad:
        return "unknown roles " + ", ".join(repr(r) for r in bad)
    cls = lambda r: "the base" if is_base_role(r) else r  # noqa: E731
    twice = [fronts.name(s) for s in sorted(roles, key=knobs) if len(roles[s]) != len({cls(r) for r in roles[s]})]
    if twice:
        return "a role twice on " + ", ".join(twice)
    none = [fronts.name(s) for s in sorted(roles, key=knobs) if not any(r in FILTER or is_base_role(r) for r in roles[s])]
    if none:
        return "no role of the filter (selected, base, fastest-neighbour) on " + ", ".join(none)
    n = {k: sum(1 for rs in roles.values() if any(f(r) for r in rs)) for k, f in (
        ("fastest", lambda r: r == "the fastest"), ("lighter point", lambda r: r == "the lighter point"),
        ("base", is_base_role), ("fastest's best neighbour", lambda r: r == "the fastest's best neighbour"))}
    if n["fastest"] != 1 or n["base"] != 1 or n["lighter point"] > 1 or n["fastest's best neighbour"] > 1:
        return "counts " + ", ".join(f"{k} {v}" for k, v in n.items())
    return None


def judge(pi, point, sset, gsc=None):
    """-> the point's reading, or {"refused": why}. pi: fronts.analyse's entry for the point (or None); sset:
    load_set's entry (or None); gsc: gossipsub's rows by seed at the point."""
    size = point[0]
    if pi is None:
        return {"refused": "NO ROWS: the set names this point, the rows have none"}
    S = pi["settings"]
    if pi["missing"]:
        return {"refused": f"MISSING: {len(pi['missing'])} listed cells are not in the rows"}
    if sset is None:
        return {"refused": "NO SET: stage 2 chose no settings for this point"}
    if sset["host"] != pi["host"]:
        return {"refused": f"HOST: the set is host {sset['host']}'s, the cells host {pi['host']}'s"}
    roles = sset["roles"]
    why = check_roles(roles)
    if why:
        return {"refused": f"ROLES: {why}"}
    absent = sorted((s for s in roles if s not in S), key=knobs)
    if absent:
        return {"refused": "ABSENT: the set's " + ", ".join(fronts.name(s) for s in absent) + " has no cells"}
    short = [f"{fronts.name(s)} lacks seeds {S[s]['lack']}" for s in sorted(roles, key=knobs) if S[s]["lack"]]
    g = pi["gossipsub"]
    if size in GS_SIZES and g is None:
        short.append("gossipsub has no rows")
    elif g and g["lack"] and (size in GS_SIZES or any(x in gsc for x in FRESH)):
        short.append(f"gossipsub lacks seeds {g['lack']}")
    if short:
        return {"refused": "SHORT: " + "; ".join(short)}
    outside = sorted((s for s, d in S.items() if s not in roles and any(x in d["cells"] for x in FRESH)), key=knobs)
    if outside:
        return {"refused": "OUTSIDE: cells of seeds 10 to 16 of a setting outside the set: "
                           + ", ".join(fronts.name(s) for s in outside)}
    named_base = [s for s in roles if any(is_base_role(r) for r in roles[s])]
    bases = [s for s, d in S.items() if d["base"]]
    if bases != named_base:
        return {"refused": f"BASE: the set's base is {', '.join(fronts.name(s) for s in named_base)}; the cells' base is "
                           + (", ".join(fronts.name(s) for s in bases) or "none")}
    base = named_base[0]
    key = lambda s: (med(S, s, "p99_s"), med(S, s, "mib"), knobs(s))  # noqa: E731
    ok = sorted((s for s in roles if S[s]["status"] == "ok"), key=key)
    not_ok = sorted((s for s in roles if S[s]["status"] != "ok"), key=knobs)
    selected = [s for s in ok if any(r in SELECTED for r in roles[s])]
    out = {"ok": ok, "not_ok": not_ok, "base": base, "roles": roles, "notes": [],
           "pairs": [(a, b, verdict(a, b, S, size)) for i, a in enumerate(ok) for b in ok[i + 1:]],
           "flags": [], "gossipsub": None}
    base_ok = S[base]["status"] == "ok"
    S2 = dict(S)
    if gsc:
        S2[GS] = {"cells": gsc}
        fresh = any(x in gsc for x in FRESH)
        out["gossipsub"] = {"g": g, "fresh": fresh,
                            "base": verdict(GS, base, S2, size) if fresh and g["status"] == "ok" and base_ok else None}
    if not base_ok or not selected:
        out.update(best=None, nb=None, vnb=None, named=[], pref=None, naming="no best" if not selected else "-",
                   vs_base={}, outcome=("NO COMPARISON", f"the default is {S[base]['status']} at ten seeds"
                                        + ("; no selected setting is ok" if not selected else ""))
                   if not base_ok else ("FOR THE AUTHOR", "no selected setting is ok at ten seeds"))
        if base_ok or not selected:
            return out
    best = selected[0]
    if len(selected) > 1 and med(S, selected[1], "p99_s") == med(S, best, "p99_s"):
        how = ("the lighter ranks first" if decided(S, selected[1], best, ("mib",)) else
               "equal in bytes too: the knobs rank it first")
        out["notes"].append(f"the best is tied in time with {fronts.name(selected[1])} by the median of ten; {how}")
    nbs = fronts.neighbours(best, S)
    okn = sorted((c for c in nbs if S[c]["status"] == "ok"), key=key)
    nb = okn[0] if okn else None
    vnb = verdict(best, nb, S, size) if nb else None
    if nb is None:
        named, naming = [best], "not compared"
    elif vnb["faster"]:
        named, naming = [best], "alone"
    else:
        named, naming = [best, nb], "both"
        if vnb["f"] >= CLEAR:
            out["notes"].append(f"the best is faster than its neighbour on {vnb['f']} of {vnb['n']} seeds, within the "
                                "allowance: by the count alone it would be named alone")
    vs_base = {s: "is" if s == base else verdict(s, base, S, size) if base_ok else S[base]["status"] for s in named}
    # the bar against the default: clearly faster, or clearly lighter and not clearly slower
    cands = [s for s in named if isinstance(vs_base[s], dict) and clears(vs_base[s])]
    pool = cands or named
    pref = min(pool, key=lambda s: (med(S, s, "mib"), med(S, s, "p99_s"), knobs(s)))
    if len(named) == 2:
        other = named[1] if pref == named[0] else named[0]
        # the key that decided between the two: bytes, then time, then the knobs
        light = {"mib": "the lighter", "p99_s": "the faster of two equal in bytes",
                 None: "the first by the knobs, the two equal in bytes and in time"}[decided(S, pref, other, ("mib", "p99_s"))]
    pref_why = ("" if len(named) == 1 else
                "the only one of the two that clears the bar against the default" if len(cands) == 1 else
                light + "; both clear the bar against the default" if len(cands) == 2 else
                light + ("; neither clears the bar against the default" if base_ok else ""))
    if len(pool) == 2 and not decided(S, pool[0], pool[1], ("mib",)):
        out["notes"].append("the two are equal in bytes by the median of ten; " + (
            "the faster is preferred" if decided(S, pool[0], pool[1], ("p99_s",)) else "equal in time too: the knobs decide"))
    # independent of the default: kept where the default is not ok
    missed = [(f"MISSED: the default {fronts.name(s)} is clearly faster than the best" if s == base else
               f"MISSED: {fronts.name(s)}, not selected, is clearly faster than the best")
              for s in ok if s not in selected and verdict(s, best, S, size)["faster"]]
    if out["gossipsub"] and out["gossipsub"]["fresh"] and g["status"] == "ok":
        out["gossipsub"]["pref"] = verdict(GS, pref, S2, size) if pref != base else None
    out.update(best=best, nb=nb, vnb=vnb, n_nbs=len(nbs), n_okn=len(okn), named=named, pref=pref, naming=naming,
               pref_why=pref_why, vs_base=vs_base)
    if not base_ok:
        out["flags"] = missed
        return out
    if pref == base:
        outcome = ("DEFAULT HOLDS", "the preferred setting is the default")
    else:
        v = vs_base[pref]
        bw = "clearly heavier" if v["heavier"] else "clearly lighter" if v["lighter"] else "close in bytes"
        if v["faster"]:
            outcome = ("CHANGE", "the preferred setting is clearly faster than the default, " + bw)
        elif v["lighter"] and not v["slower"]:
            outcome = ("CHANGE", "the preferred setting is clearly lighter than the default and close in time")
        elif v["slower"]:
            # the byte verdict is the preferred setting's
            outcome = ("DEFAULT HOLDS", "the default is clearly faster than the preferred setting, which is " + bw)
        else:
            outcome = ("DEFAULT HOLDS", "the preferred setting is close in time to the default"
                       + (", clearly heavier" if v["heavier"] else ""))
    flags = []
    if outcome[0] == "DEFAULT HOLDS":
        flags += [f"SPLIT: {fronts.name(s)}, not named, clears the bar against the default; the outcome follows the "
                  "named settings" for s in ok if s not in named and s != base and clears(verdict(s, base, S, size))]
    flags += missed
    if outcome[0] == "CHANGE" and pref not in selected:
        flags.append(f"PREFERRED NOT SELECTED: the change goes to {fronts.name(pref)}, the best's neighbour, not a "
                     "setting stage 2 selected")
    if outcome[0] == "CHANGE" and naming == "not compared":
        flags.append("NO NEIGHBOUR TEST: the change goes to a best with no neighbour ok at ten seeds")
    out.update(outcome=outcome, flags=flags)
    return out


def clears(v):
    """The bar against the default: clearly faster, or clearly lighter and not clearly slower."""
    return v["faster"] or (v["lighter"] and not v["slower"])


OUTCOMES = ("CHANGE", "DEFAULT HOLDS", "FOR THE AUTHOR", "NO COMPARISON")
COLS = ["size_kib", "network", "host", "default", "default_s", "default_copies", "preferred", "preferred_s",
        "preferred_copies", "preferred_spec", "preferred_marks", "naming", "also_named", "time_gap_pct",
        "bytes_gap_pct", "faster_of_10", "lighter_of_10", "verdict", "outcome", "flags", "gossipsub_s", "gossipsub_copies"]


def report(res, sets, gss, out_csv=None):
    """Prints the reading. -> False when a point is refused (the CSV, if asked for, then not written), else True."""
    table, refused, by_outcome = [], [], {}
    print(f"note: {NOTE}")
    for point in sorted(set(res) | set(sets)):
        pi = res.get(point)
        size, net = point
        print(f"\n== {size} KiB, {net} (host {pi['host'] if pi else sets[point]['host']})")
        r = judge(pi, point, sets.get(point), gss.get(point))
        if "refused" in r:
            print(f"   REFUSED: {r['refused']}")
            refused.append(f"{size} KiB {net}")
            continue
        S = pi["settings"]
        tol_t, tol_b = noise(size)
        print(f"   noise allowance here: time {float(tol_t) * 100:.0f} %, bytes {float(tol_b) * 100:.0f} %; "
              f"clear: on at least {CLEAR} of {len(SEEDS)} seeds and beyond it")
        print("   the set at ten seeds, by the median of ten:")
        for i, s in enumerate(r["ok"], 1):
            print(f"     {i}. {fig(S, s)} [{'; '.join(r['roles'][s])}]")
        for s in r["not_ok"]:
            d = S[s]
            print(f"     not ok, out of the ranking: {fronts.name(s)} [{d['status']}, {len(SEEDS) - len(d['lack'])} of "
                  f"{len(SEEDS)} seeds" + (f", failed on {d['failed_seeds']}" if d["failed_seeds"] else "")
                  + f"]{marks(d)} [{'; '.join(r['roles'][s])}]")
        for a, b, v in r["pairs"]:
            print(f"   {fronts.name(a)} against {fronts.name(b)}: {vtext(v)}")
        g = r["gossipsub"]
        gtxt = ("", "")
        if g:
            gd = g["g"]
            if not g["fresh"]:
                print(f"   gossipsub, the whole message: seeds {sorted(gss[point])} only, not run in stage 3: no comparison")
            elif gd["status"] == "ok":
                cp = gd["mib"] / pi["comp_mib"] if pi["comp_mib"] else None
                gtxt = (f"{gd['time']:.4f}", f"{cp:.2f}" if cp is not None else "")
                print(f"   gossipsub, the whole message (a reference): {gd['time']:.4f} s, "
                      + (f"{cp:.2f} copies" if cp is not None else f"{gd['mib']:.4f} MiB")
                      + (f" PAST 3 s in {gd['past_3s']} cells (worst warm payload {gd['at_3s'][0]} of {gd['at_3s'][1]})" if gd["past_3s"] else ""))
                if g["base"]:
                    print(f"     against the default {fronts.name(r['base'])}: {vtext(g['base'])}")
                if g.get("pref"):
                    print(f"     against the preferred {fronts.name(r['pref'])}: {vtext(g['pref'])}")
            else:
                print(f"   gossipsub, the whole message: {gd['status'].upper()} at ten seeds"
                      + (f", failed on {gd['failed_seeds']}" if gd["failed_seeds"] else ""))
        if r["best"] is None:
            print("   NO BEST: no selected setting is ok at ten seeds")
        else:
            best, nb = r["best"], r["nb"]
            print(f"   the best (the fastest selected setting by the median of ten): {fronts.name(best)}")
            top = r["ok"][0]
            if top != best:
                # the key that put it first: time, then bytes, then the knobs
                how = {"p99_s": "faster by the median of ten", "mib": "as fast by the median of ten and lighter",
                       None: "as fast and as light by the median of ten, first by the knobs"}[decided(S, top, best, ("p99_s", "mib"))]
                print(f"     {how}, not selected: {fronts.name(top)}")
            if nb is None:
                print(f"   NOT COMPARED: none of its {r['n_nbs']} neighbours among the cells is ok at ten seeds; "
                      "the best is preferred alone")
            else:
                head = f"against its best neighbour {fronts.name(nb)} ({r['n_okn']} of its {r['n_nbs']} neighbours ok at ten seeds)"
                if r["naming"] == "alone":
                    print(f"   NAMED ALONE: {head}: {vtext(r['vnb'])}")
                else:
                    print(f"   BOTH NAMED: {head}: {vtext(r['vnb'])}; PREFERRED: {fronts.name(r['pref'])} ({r['pref_why']})")
            for n in r["notes"]:
                print(f"     note: {n}")
            for s in r["named"]:
                v = r["vs_base"][s]
                who = f"{fronts.name(s)}" + (" (preferred)" if s == r["pref"] and len(r["named"]) > 1 else "")
                if v == "is":
                    print(f"   {who} is the default")
                elif isinstance(v, str):
                    print(f"   {who}: the default {fronts.name(r['base'])} is {v}: no comparison")
                else:
                    print(f"   {who} against the default {fronts.name(r['base'])}: {vtext(v)}")
        oc, why = r["outcome"]
        p = r["pref"]
        pm = marks(S[p]).strip() if p else ""
        print(f"   FOR THE TEXT: {oc}: {why}" + (f"; the preferred setting's marks: {pm}" if pm else ""))
        for f in r["flags"]:
            print(f"   FOR THE AUTHOR: {f}")
        by_outcome.setdefault(oc, []).append(f"{size} KiB {net}" + (" (flagged)" if r["flags"] else ""))
        b = r["base"]
        bd = S[b]
        v = r["vs_base"].get(p) if p else None
        v = v if isinstance(v, dict) else None
        table.append({
            "size_kib": size, "network": net, "host": pi["host"], "default": fronts.name(b),
            "default_s": f"{bd['time']:.4f}" if "time" in bd else "", "default_copies": f"{bd['copies']:.2f}" if bd.get("copies") is not None else "",
            "preferred": fronts.name(p) if p else "", "preferred_s": f"{S[p]['time']:.4f}" if p else "",
            "preferred_copies": f"{S[p]['copies']:.2f}" if p and S[p].get("copies") is not None else "",
            "preferred_spec": S[p]["spec"] if p else "", "preferred_marks": pm, "naming": r["naming"],
            "also_named": "; ".join(fronts.name(s) for s in r["named"] if s != p),
            "time_gap_pct": f"{float(v['tg']) * 100:.2f}" if v else "", "bytes_gap_pct": f"{float(v['bg']) * 100:.2f}" if v else "",
            "faster_of_10": v["f"] if v else "", "lighter_of_10": v["l"] if v else "", "verdict": words(v) if v else "",
            "outcome": oc, "flags": " | ".join(r["flags"]), "gossipsub_s": gtxt[0], "gossipsub_copies": gtxt[1]})
    print(f"\n{len(table)} points read, {len(refused)} refused" + (": " + "; ".join(refused) if refused else ""))
    print("point | the default | the preferred (spec) | named | against the default: time, bytes (faster, lighter of 10) | outcome")
    for t in table:
        pref = (f"{t['preferred']} ({t['preferred_s']} s, {t['preferred_copies']} copies; {t['preferred_spec']})"
                + (f" {t['preferred_marks']}" if t["preferred_marks"] else "")) if t["preferred"] else "no best"
        print(f"{t['size_kib']} KiB {t['network']} | {t['default_s']} s, {t['default_copies']} copies | {pref} | {t['naming']}"
              + (f" with {t['also_named']}" if t["also_named"] else "")
              + (f" | {t['time_gap_pct']} %, {t['bytes_gap_pct']} % ({t['faster_of_10']}, {t['lighter_of_10']}): {t['verdict']}" if t["verdict"] else " | -")
              + f" | {t['outcome']}" + (" (flagged)" if t["flags"] else ""))
    for oc in OUTCOMES:
        pts = by_outcome.get(oc, [])
        print(f"{oc}: {len(pts)}" + (": " + "; ".join(pts) if pts else ""))
    if refused:
        if out_csv:
            print(f"CSV NOT WRITTEN: {len(refused)} points refused (a file already at that path is left as it was)")
        return False
    if out_csv:
        with contextlib.ExitStack() as stack:
            fh = out_csv if hasattr(out_csv, "write") else stack.enter_context(open(out_csv, "w", newline=""))
            w = csv.DictWriter(fh, COLS)
            w.writeheader()
            w.writerows(table)
    return True


def strays(rows, exp):
    """Rows of the ten seeds that are no cell of the lists."""
    return sorted(r["log"] for r in rows if int(r["seed"]) in SEEDS and r["log"] not in exp)


def gossipsub_cells(rows):
    out = {}
    for r in rows:
        if r["protocol"] == "gossipsub" and int(r["seed"]) in SEEDS:
            out.setdefault((int(r["size_kib"]), r["network"]), {})[int(r["seed"])] = r
    return out


def selftest():
    def cell(size, net, seed, r, unit, t, b, code=None, **kw):
        code = code or fronts.rule_code(size, unit, 1)
        k = -(-size // unit)
        row = {"protocol": "seacast", "network": net, "size_kib": str(size), "seed": str(seed), "nodes": "500",
               "push_r": str(r), "unit_kib": str(unit), "k": str(k), "n": str(k if code in ("unc", "plain") else 2 * k),
               "code": code, "rsx": "1", "r_fast": fronts.rule_rfast(r), "ask_ms": "200", "target_ms": "20", "proj": "2",
               "fault": "", "loss": "", "disc": "arm", "offer_bound": "group", "counted": "1", "chunk_b": str(int(unit * 727)),
               "comp_b": str(int(size * 727)), "bin_md5": "a" * 32, "passed": "True", "p99_s": f"{t}", "mib": f"{b}",
               "dc_rx_mib": "", "other_rx_mib": "", "recorded_warm": "1000", "refused_warm": "0", "censored_warm": "0",
               "honest_at_3s": "499/499", "at_3s": "499/499", "log": f"x{size}{net}{seed}r{r}u{unit}{code}",
               "host": "A" if net == "all-home" else "B"}
        row.update(kw)
        return row

    def ten(size, net, r, unit, t, b, code=None, seeds=SEEDS, fail=(), **kw):
        """t, b: one value, or one per seed of SEEDS; fail: the seeds whose cell did not pass"""
        ts = t if isinstance(t, tuple) else (t,) * len(SEEDS)
        bs = b if isinstance(b, tuple) else (b,) * len(SEEDS)
        return [cell(size, net, x, r, unit, ts[i], bs[i], code, **dict(kw, passed="False" if x in fail else "True"))
                for i, x in enumerate(SEEDS) if x in seeds]

    def gs(size, net, t, b, seeds=SEEDS, fail=()):
        return [dict(c, protocol="gossipsub", log=f"gs{size}{net}-{c['seed']}") for c in ten(size, net, 0, 16, t, b, seeds=seeds, fail=fail)]

    k = lambda r, u, code="leo8": (r, u, code, 1, fronts.rule_rfast(r), "200", "20", "2", "", "", "arm", "group")  # noqa: E731
    sets = {}

    def role(size, net, s, *rs):
        sets.setdefault((size, net), {"host": "A" if net == "all-home" else "B", "roles": {}})["roles"][s] = list(rs)

    # A (allowance 10 %, 8 %): the best is clearly faster than its neighbour: NAMED ALONE; CHANGE (clearly heavier);
    # a neighbour with seed 7 only; gossipsub close in time to the preferred and clearly heavier
    rows = ten(32, "all-home", 4, 16, 1.00, 1.00) + ten(32, "all-home", 8, 4, 0.70, 1.40) + ten(32, "all-home", 6, 4, 0.80, 1.30)
    rows += [cell(32, "all-home", 7, 8, 8, 0.90, 1.50)] + gs(32, "all-home", 0.75, 1.60)
    role(32, "all-home", k(8, 4), "the fastest")
    role(32, "all-home", k(6, 4), "the lighter point", "the fastest's best neighbour")
    role(32, "all-home", k(4, 16), "the base")
    # B: the best is clearly faster than the default but close to its neighbour; the lighter neighbour is close in time
    # to the default and clearly heavier: the best alone clears the bar and is preferred: CHANGE; the count
    # alone would name the best alone; gossipsub failed
    rows += ten(64, "all-home", 4, 16, 1.00, 1.00) + ten(64, "all-home", 8, 4, 0.88, 1.50) + ten(64, "all-home", 6, 4, 0.93, 1.30)
    rows += gs(64, "all-home", 0.9, 1.6, fail=(12,))
    role(64, "all-home", k(8, 4), "the fastest")
    role(64, "all-home", k(6, 4), "the fastest's best neighbour")
    role(64, "all-home", k(4, 16), "the base")
    # C (allowance 6 %, 3 %): the default is the best; faster than its neighbour on 7 of 10 only, by a median beyond the
    # allowance: BOTH NAMED; the default is the lighter: DEFAULT HOLDS; gossipsub with the default preferred
    rows += ten(1024, "all-home", 2, 16, 0.60, 1.00) + ten(1024, "all-home", 3, 16, (0.70,) * 7 + (0.55,) * 3, 1.20)
    rows += gs(1024, "all-home", 0.5, 2.0)
    role(1024, "all-home", k(2, 16), "the fastest", "the base")
    role(1024, "all-home", k(3, 16), "the fastest's best neighbour")
    # D: a neighbour that was not selected is clearly faster than the best (MISSED) and than the default; the best is
    # close in time to the default and clearly lighter: both clear the bar, the lighter (the best) is preferred:
    # CHANGE by bytes; gossipsub of seed 7 only
    rows += ten(2048, "dcb20", 2, 16, 0.90, 2.00) + ten(2048, "dcb20", 2, 32, 0.85, 1.90) + ten(2048, "dcb20", 3, 32, 0.75, 2.40)
    rows += gs(2048, "dcb20", 1.0, 3.0, seeds=(7,))
    role(2048, "dcb20", k(2, 32), "the fastest")
    role(2048, "dcb20", k(3, 32), "the fastest's best neighbour")
    role(2048, "dcb20", k(2, 16), "the base")
    # E: a listed cell is missing: REFUSED
    rows += ten(512, "dcb20", 3, 16, 0.50, 1.00) + ten(512, "dcb20", 4, 8, 0.40, 1.20)
    role(512, "dcb20", k(4, 8), "the fastest")
    role(512, "dcb20", k(3, 16), "the base")
    # F (allowance 10 %, 8 %): the neighbour failed on seed 12, with a refusal under the group bound: NOT COMPARED;
    # the best is close in time to the default and clearly heavier: DEFAULT HOLDS
    rows += ten(256, "dcb20", 4, 16, 0.30, 1.00) + ten(256, "dcb20", 4, 4, 0.29, 1.10)
    rows += ten(256, "dcb20", 4, 8, 0.295, 1.05, fail=(12,), refused_warm="3")
    role(256, "dcb20", k(4, 4), "the fastest")
    role(256, "dcb20", k(4, 8), "the fastest's best neighbour")
    role(256, "dcb20", k(4, 16), "the base")
    # G: a setting outside the set with stage 3's seeds: REFUSED
    rows += ten(128, "all-home", 4, 16, 0.30, 1.00) + ten(128, "all-home", 6, 8, 0.25, 1.20) + ten(128, "all-home", 8, 8, 0.24, 1.30)
    role(128, "all-home", k(6, 8), "the fastest")
    role(128, "all-home", k(4, 16), "the base")
    # H: the set names a setting with no cells: REFUSED; (I) a point with cells and no set: REFUSED
    rows += ten(4096, "all-home", 2, 16, 1.50, 7.00, "plain")
    role(4096, "all-home", k(2, 16, "plain"), "the base")
    role(4096, "all-home", k(2, 32), "the fastest")
    rows += ten(256, "all-home", 4, 16, 0.30, 1.00)
    # J (6 %, 3 %): the lighter point is the best, the default its best neighbour; NAMED ALONE; CHANGE
    rows += ten(512, "all-home", 3, 16, 1.00, 1.00) + ten(512, "all-home", 4, 8, 1.02, 1.30) + ten(512, "all-home", 3, 8, 0.90, 1.10)
    rows += ten(512, "all-home", 4, 16, 0.97, 1.20)
    role(512, "all-home", k(4, 8), "the fastest")
    role(512, "all-home", k(3, 8), "the lighter point")
    role(512, "all-home", k(4, 16), "the fastest's best neighbour")
    role(512, "all-home", k(3, 16), "the base")
    # K (10 %, 8 %): both named, the neighbour preferred and clearly faster than the default, close in bytes: CHANGE,
    # PREFERRED NOT SELECTED
    rows += ten(128, "dcb20", 4, 16, 1.00, 1.00) + ten(128, "dcb20", 6, 4, 0.80, 1.30) + ten(128, "dcb20", 4, 4, 0.82, 1.05)
    role(128, "dcb20", k(6, 4), "the fastest")
    role(128, "dcb20", k(4, 4), "the fastest's best neighbour")
    role(128, "dcb20", k(4, 16), "the base")
    # L (6 %, 3 %): NOT COMPARED; the best is clearly slower than the default and close in bytes: DEFAULT HOLDS; PAST 3 s
    rows += ten(1024, "dcb20", 2, 16, 0.50, 1.00)
    rows += [dict(c, at_3s="480/499") if c["seed"] == "13" else c for c in ten(1024, "dcb20", 2, 64, 0.60, 0.99)]
    role(1024, "dcb20", k(2, 64), "the fastest")
    role(1024, "dcb20", k(2, 16), "the base")
    # M: the default and the selected setting both failed: NO COMPARISON; (N) the default ok, the selected failed: NO BEST
    rows += ten(2048, "all-home", 2, 16, 0.9, 2.0, fail=(9,)) + ten(2048, "all-home", 2, 32, 0.8, 2.0, fail=(11,))
    role(2048, "all-home", k(2, 32), "the fastest")
    role(2048, "all-home", k(2, 16), "the base")
    rows += ten(4096, "dcb20", 2, 16, 1.1, 2.0, "plain") + ten(4096, "dcb20", 2, 32, 0.9, 2.0, fail=(15,))
    role(4096, "dcb20", k(2, 32), "the fastest")
    role(4096, "dcb20", k(2, 16, "plain"), "the base")
    # P: gossipsub run in stage 3 lacks seed 16: SHORT; Q: a set setting lacks seed 16: SHORT; R: a set without rows
    rows += ten(32, "dcb20", 4, 16, 1.0, 1.0) + gs(32, "dcb20", 0.9, 1.5, seeds=SEEDS[:-1])
    role(32, "dcb20", k(4, 16), "the fastest", "the base")
    rows += ten(64, "dcb20", 4, 16, 1.0, 1.0) + ten(64, "dcb20", 6, 8, 0.8, 1.2, seeds=SEEDS[:-1]) + gs(64, "dcb20", 0.9, 1.5)
    role(64, "dcb20", k(6, 8), "the fastest")
    role(64, "dcb20", k(4, 16), "the base")
    role(16, "all-home", k(4, 16), "the fastest", "the base")
    # U (10 %, 8 %): two selected settings tied in time by the exact median of ten (a float median would rank the
    # heavier first): the lighter is the best; V: the two named equal in bytes by the exact median of ten (a float
    # median would make the slower one lighter): the faster preferred
    rows += ten(8, "all-home", 4, 16, 1.0, 1.0)
    rows += ten(8, "all-home", 6, 4, (0.05,) * 4 + (0.1, 0.2) + (0.3,) * 4, 1.10)
    rows += ten(8, "all-home", 4, 4, (0.05,) * 4 + (0.15, 0.15) + (0.3,) * 4, 1.20)
    role(8, "all-home", k(6, 4), "the fastest")
    role(8, "all-home", k(4, 4), "the lighter point", "the fastest's best neighbour")
    role(8, "all-home", k(4, 16), "the base")
    rows += ten(16, "dcb20", 4, 16, 1.0, 1.0) + ten(16, "dcb20", 6, 4, 0.50, (1.0,) * 4 + (1.1, 1.3) + (1.5,) * 4)
    rows += ten(16, "dcb20", 4, 4, 0.52, 1.20)
    role(16, "dcb20", k(6, 4), "the fastest")
    role(16, "dcb20", k(4, 4), "the fastest's best neighbour")
    role(16, "dcb20", k(4, 16), "the base")
    # W (10 %, 8 %): CHANGE to a best with no neighbour among the cells: NO NEIGHBOUR TEST
    rows += ten(8, "dcb20", 4, 16, 1.0, 1.0) + ten(8, "dcb20", 6, 64, 0.5, 1.0)
    role(8, "dcb20", k(6, 64), "the fastest")
    role(8, "dcb20", k(4, 16), "the base")
    # X (10 %, 8 %): the best clearly lighter and clearly slower than the default: DEFAULT HOLDS; MISSED by the default
    rows += ten(4, "dcb20", 4, 16, 1.0, 1.0) + ten(4, "dcb20", 6, 2, 1.2, 0.8)
    role(4, "dcb20", k(6, 2), "the fastest")
    role(4, "dcb20", k(4, 16), "the base")
    # Y (10 %, 8 %): the lighter point is the best, close to its neighbour (the fastest), both close in time to the
    # default, the fastest clearly heavier: neither clears the bar: DEFAULT HOLDS; stage 2's neighbour role holder, not a neighbour of the best, clears the bar: SPLIT,
    # and it is clearly faster than the best: MISSED
    rows += ten(4, "all-home", 4, 16, 1.00, 1.00) + ten(4, "all-home", 6, 4, 0.97, 1.10) + ten(4, "all-home", 4, 4, 0.96, 1.05)
    rows += ten(4, "all-home", 6, 8, 0.85, 1.30)
    role(4, "all-home", k(6, 4), "the fastest")
    role(4, "all-home", k(4, 4), "the lighter point")
    role(4, "all-home", k(6, 8), "the fastest's best neighbour")
    role(4, "all-home", k(4, 16), "the base")
    exp = {r["log"]: (int(r["size_kib"]), r["network"], int(r["seed"])) for r in rows}
    exp["never-ran.log"] = (512, "dcb20", 12)
    assert strays(rows, exp) == [] and strays(rows + [cell(32, "dcb20", 12, 4, 8, 0.1, 0.2)], exp) == ["x32dcb2012r4u8leo8"]

    # the verdict at ten seeds, in exact fractions
    def mk(t, b="1.0", seeds=SEEDS, fail=()):
        ts = t if isinstance(t, tuple) else (t,) * len(SEEDS)
        bs = b if isinstance(b, tuple) else (b,) * len(SEEDS)
        return {"cells": {x: {"passed": "False" if x in fail else "True", "p99_s": ts[i], "mib": bs[i]}
                          for i, x in enumerate(SEEDS) if x in seeds}}
    Sx = {("a",): mk("0.94"), ("b",): mk("1.0"), ("c",): mk("0.9399"),
          ("p",): mk(("0.9",) * 8 + ("1.1",) * 2), ("q",): mk(("0.9",) * 7 + ("1.1",) * 3),
          ("m",): mk(("0.9",) * 5 + ("0.98",) * 5), ("t",): mk("1.0", "1.0"),
          ("g",): mk("1.0", "0.97"), ("h",): mk("1.0", "0.9699"), ("i",): mk("0.5", "0.5", SEEDS[:-1]),
          ("a10",): mk("0.9"), ("c10",): mk("0.8999"), ("g8",): mk("1.0", "0.92"), ("h8",): mk("1.0", "0.9199"),
          ("lb",): mk("1.0", ("0.9",) * 8 + ("1.1",) * 2), ("lc",): mk("1.0", ("0.9",) * 7 + ("1.1",) * 3),
          ("w",): mk(("0.5",) * 7 + ("1.0",) * 3), ("x",): mk("0.5", fail=(12,))}

    def vx(p, q, size=512):
        return verdict((p,), (q,), Sx, size)
    assert vx("a", "b")["faster"] is False and vx("a", "b")["f"] == 10 and vx("a", "b")["tg"] == Fraction(6, 100)
    assert vx("c", "b")["faster"] is True and vx("a", "b", 256)["faster"] is False
    assert vx("p", "b")["faster"] is True and vx("p", "b")["f"] == 8 and vx("p", "b")["tg"] == Fraction(1, 10)   # 8 of 10
    assert vx("q", "b")["faster"] is False and vx("q", "b")["f"] == 7 and vx("q", "b")["tg"] == Fraction(1, 10)  # 7 of 10
    assert vx("m", "b")["tg"] == Fraction(6, 100) and vx("m", "b")["faster"] is False        # the mean of the middle two
    assert vx("m", "b")["ff"] == 7 and vx("m", "b")["fn"] == 7 and vx("m", "b")["ftg"] == Fraction(2, 100)   # seeds 10 to 16
    assert (vx("t", "b")["f"], vx("b", "t")["f"], vx("t", "b")["l"]) == (0, 0, 0) and words(vx("t", "b")) == "close"   # ties
    assert vx("g", "b")["lighter"] is False and vx("h", "b")["lighter"] is True and vx("g", "b", 256)["lighter"] is False
    assert vx("i", "b")["n"] == 9 and not vx("i", "b")["faster"] and not vx("i", "b")["lighter"]   # nine seeds: never clear
    assert vx("x", "b")["n"] == 9 and vx("x", "b")["f"] == 9 and not vx("x", "b")["faster"]          # a failed cell: nine
    assert vx("a10", "b", 256)["faster"] is False and vx("c10", "b", 256)["faster"] is True          # 10 % exactly, below 512
    assert vx("g8", "b", 256)["lighter"] is False and vx("h8", "b", 256)["lighter"] is True          # 8 % exactly, below 512
    assert vx("lb", "b")["lighter"] is True and vx("lc", "b")["lighter"] is False and vx("lc", "b")["l"] == 7   # bytes 8 and 7
    assert vx("w", "b")["f"] == 7 and vx("w", "b")["tg"] == Fraction(1, 2) and not vx("w", "b")["faster"]       # 7 wins, 3 ties
    assert vx("b", "c")["slower"] is True and vx("b", "a")["slower"] is False and vx("b", "p")["slower"] is True
    assert all(vx(p, q)[w] == vx(q, p)[r] for p in "abcpqmtgh" for q in "abcpqmtgh"
               for w, r in (("faster", "slower"), ("lighter", "heavier")))

    gss = gossipsub_cells(rows)
    info, res = fronts.analyse(rows, list(SEEDS), expect=exp)

    def j(p):
        return judge(res.get(p), p, sets.get(p), gss.get(p))

    def cnt(v):
        return (v["f"], v["l"], v["n"])
    a = j((32, "all-home"))
    assert a["best"] == k(8, 4) and a["nb"] == k(6, 4) and a["naming"] == "alone" and a["pref"] == k(8, 4), a
    assert (a["n_okn"], a["n_nbs"]) == (1, 2) and cnt(a["vnb"]) == (10, 0, 10) and a["vnb"]["tg"] == Fraction(1, 8), a
    assert a["outcome"][0] == "CHANGE" and a["flags"] == [] and a["ok"] == [k(8, 4), k(6, 4), k(4, 16)], a
    assert cnt(a["gossipsub"]["pref"]) == (0, 0, 10) and words(a["gossipsub"]["pref"]) == "clearly heavier", a["gossipsub"]
    b = j((64, "all-home"))
    assert b["naming"] == "both" and b["pref"] == k(8, 4) and b["flags"] == [], b
    assert b["outcome"] == ("CHANGE", "the preferred setting is clearly faster than the default, clearly heavier"), b
    assert b["pref_why"] == "the only one of the two that clears the bar against the default", b
    assert b["gossipsub"]["base"] is None and "pref" not in b["gossipsub"], b["gossipsub"]
    c = j((1024, "all-home"))
    assert c["best"] == k(2, 16) and c["naming"] == "both" and c["pref"] == k(2, 16) and cnt(c["vnb"]) == (7, 10, 10), c
    assert c["vnb"]["tg"] == Fraction(1, 7) and c["outcome"] == ("DEFAULT HOLDS", "the preferred setting is the default"), c
    assert c["vs_base"][k(2, 16)] == "is" and words(c["vs_base"][k(3, 16)]) == "clearly heavier" and c["flags"] == [], c
    assert c["gossipsub"]["pref"] is None and words(c["gossipsub"]["base"]) == "clearly faster and clearly heavier", c
    d = j((2048, "dcb20"))
    assert d["best"] == k(2, 32) and d["nb"] == k(3, 32) and (d["n_okn"], d["n_nbs"]) == (2, 2) and d["pref"] == k(2, 32), d
    assert words(d["vnb"]) == "clearly slower and clearly lighter" and d["pref_why"] == "the lighter; both clear the bar against the default", d
    assert d["outcome"] == ("CHANGE", "the preferred setting is clearly lighter than the default and close in time"), d
    assert d["flags"] == ["MISSED: R=3 unit=32K leo8, not selected, is clearly faster than the best"], d["flags"]
    assert d["gossipsub"]["fresh"] is False and d["gossipsub"]["base"] is None, d["gossipsub"]
    assert j((512, "dcb20")) == {"refused": "MISSING: 1 listed cells are not in the rows"}
    f = j((256, "dcb20"))
    assert f["naming"] == "not compared" and f["nb"] is None and f["not_ok"] == [k(4, 8)] and f["pref"] == k(4, 4), f
    assert f["outcome"] == ("DEFAULT HOLDS", "the preferred setting is close in time to the default, clearly heavier"), f
    assert j((128, "all-home"))["refused"] == "OUTSIDE: cells of seeds 10 to 16 of a setting outside the set: R=8 unit=8K leo8 rfast=8"
    assert j((4096, "all-home"))["refused"] == "ABSENT: the set's R=2 unit=32K leo8 has no cells"
    assert j((256, "all-home"))["refused"] == "NO SET: stage 2 chose no settings for this point"
    jj = j((512, "all-home"))
    assert jj["best"] == k(3, 8) and jj["nb"] == k(3, 16) and jj["naming"] == "alone" and jj["ok"][0] == k(3, 8), jj
    assert (jj["n_okn"], jj["n_nbs"]) == (2, 2) and jj["outcome"] == ("CHANGE", "the preferred setting is clearly faster than "
                                                                     "the default, clearly heavier") and jj["flags"] == [], jj
    kk = j((128, "dcb20"))
    assert kk["naming"] == "both" and kk["pref"] == k(4, 4) and kk["outcome"] == ("CHANGE", "the preferred setting is clearly "
                                                                                 "faster than the default, close in bytes"), kk
    assert kk["flags"] == ["PREFERRED NOT SELECTED: the change goes to R=4 unit=4K leo8, the best's neighbour, not a setting "
                           "stage 2 selected"], kk["flags"]
    ll = j((1024, "dcb20"))
    assert ll["naming"] == "not compared" and ll["outcome"] == ("DEFAULT HOLDS", "the default is clearly faster than the "
                                                               "preferred setting, which is close in bytes"), ll
    assert ll["flags"] == ["MISSED: the default R=2 unit=16K leo8 is clearly faster than the best"], ll["flags"]
    assert j((2048, "all-home"))["outcome"] == ("NO COMPARISON", "the default is failed at ten seeds; no selected setting is ok")
    nn = j((4096, "dcb20"))
    assert nn["outcome"] == ("FOR THE AUTHOR", "no selected setting is ok at ten seeds") and nn["naming"] == "no best", nn
    assert j((32, "dcb20"))["refused"] == "SHORT: gossipsub lacks seeds [16]"
    assert j((64, "dcb20"))["refused"] == "SHORT: R=6 unit=8K leo8 lacks seeds [16]"
    assert j((16, "all-home"))["refused"] == "NO ROWS: the set names this point, the rows have none"
    uu = j((8, "all-home"))
    assert uu["best"] == k(6, 4) and uu["notes"][0].startswith("the best is tied in time with R=4 unit=4K leo8"), uu
    assert fronts.order(res[(8, "all-home")]["settings"])(k(4, 4)) < fronts.order(res[(8, "all-home")]["settings"])(k(6, 4))  # floats
    vv = j((16, "dcb20"))
    assert vv["pref"] == k(6, 4) and len(vv["notes"]) == 2 and vv["notes"][1] == ("the two are equal in bytes by the "
                                                                                  "median of ten; the faster is preferred"), vv
    assert vv["pref_why"] == "the faster of two equal in bytes; both clear the bar against the default", vv
    fm = {s: st.median(float(c["mib"]) for c in res[(16, "dcb20")]["settings"][s]["cells"].values()) for s in (k(6, 4), k(4, 4))}
    assert fm[k(6, 4)] > fm[k(4, 4)], fm                       # floats would have preferred the slower one
    xx = j((4, "dcb20"))
    assert xx["outcome"] == ("DEFAULT HOLDS", "the default is clearly faster than the preferred setting, which is clearly "
                                              "lighter"), xx
    assert xx["flags"] == ["MISSED: the default R=4 unit=16K leo8 is clearly faster than the best"], xx["flags"]
    yy = j((4, "all-home"))
    assert yy["best"] == k(4, 4) and yy["nb"] == k(6, 4) and yy["pref"] == k(4, 4) and yy["ok"][0] == k(6, 8), yy
    assert yy["outcome"] == ("DEFAULT HOLDS", "the preferred setting is close in time to the default"), yy
    assert yy["pref_why"] == "the lighter; neither clears the bar against the default", yy
    assert yy["flags"] == ["SPLIT: R=6 unit=8K leo8, not named, clears the bar against the default; the outcome follows "
                           "the named settings", "MISSED: R=6 unit=8K leo8, not selected, is clearly faster than the best"], yy
    ww = j((8, "dcb20"))
    assert ww["naming"] == "not compared" and ww["outcome"] == ("CHANGE", "the preferred setting is clearly faster than the "
                                                               "default, close in bytes"), ww
    assert ww["flags"] == ["NO NEIGHBOUR TEST: the change goes to a best with no neighbour ok at ten seeds"], ww["flags"]
    A = (32, "all-home")
    hb = {"host": "B", "roles": sets[A]["roles"]}
    assert judge(res[A], A, hb)["refused"].startswith("HOST")
    wrong = {"host": "A", "roles": {k(8, 4): ["the fastest"], k(6, 4): ["the base"], k(4, 16): ["the fastest's best neighbour"]}}
    assert judge(res[A], A, wrong)["refused"] == "BASE: the set's base is R=6 unit=4K leo8; the cells' base is R=4 unit=16K leo8"
    typo = {"host": "A", "roles": {k(8, 4): ["the fastest"], k(6, 4): ["the lighter pint"], k(4, 16): ["the base"]}}
    assert judge(res[A], A, typo)["refused"] == "ROLES: unknown roles 'the lighter pint'"
    two = {"host": "A", "roles": {k(8, 4): ["the fastest"], k(6, 4): ["the fastest"], k(4, 16): ["the base [failed]"]}}
    assert judge(res[A], A, two)["refused"] == ("ROLES: counts fastest 2, lighter point 0, base 1, fastest's best neighbour 0")
    # a base's status selection.py never writes; a role twice on a setting; a setting with no role of the filter
    for rs, why in (({k(4, 16): ["the base [typo]"]}, "unknown roles 'the base [typo]'"),
                    ({k(6, 4): ["the lighter point", "the lighter point"]}, "a role twice on R=6 unit=4K leo8"),
                    ({k(4, 16): ["the base", "the base [short]"]}, "a role twice on R=4 unit=16K leo8"),
                    ({k(6, 4): ["option: the corner"]}, "no role of the filter (selected, base, fastest-neighbour) on R=6 "
                                                        "unit=4K leo8")):
        bad = {"host": "A", "roles": dict(sets[A]["roles"]) | rs}
        assert judge(res[A], A, bad)["refused"] == "ROLES: " + why, (rs, judge(res[A], A, bad))
    # gossipsub left out at a size where stage 3 ran it: its seeds 10 to 16 with their lists, or all of it
    for drop, why in ((FRESH, "SHORT: gossipsub lacks seeds [10, 11, 12, 13, 14, 15, 16]"), (SEEDS, "SHORT: gossipsub has no rows")):
        keep = [r for r in rows if not (r["protocol"] == "gossipsub" and (int(r["size_kib"]), r["network"]) == A
                                        and int(r["seed"]) in drop)]
        r2 = fronts.analyse(keep, list(SEEDS), expect={r["log"]: exp[r["log"]] for r in keep})[1]
        assert judge(r2[A], A, sets[A], gossipsub_cells(keep).get(A)) == {"refused": why}, why
    # apart from the report: (64 KiB all-home) the default failed, an ok best, gossipsub ok: NO
    # COMPARISON keeps MISSED and gossipsub against the preferred; (16 KiB all-home) the named settings both close in
    # time to the default, one clearly heavier; the lighter point, not named, clears the bar by bytes alone: SPLIT
    rows2 = ten(64, "all-home", 4, 16, 1.0, 1.0, fail=(12,)) + ten(64, "all-home", 6, 4, 0.80, 1.30)
    rows2 += ten(64, "all-home", 8, 4, 0.60, 1.50) + gs(64, "all-home", 0.9, 1.6)
    rows2 += ten(16, "all-home", 4, 16, 1.00, 1.00) + ten(16, "all-home", 6, 4, 0.97, 1.10) + ten(16, "all-home", 6, 8, 0.98, 1.05)
    rows2 += ten(16, "all-home", 2, 16, 1.02, 0.85)
    # the knobs deciding: (8 KiB all-home) the two selected and the best's neighbour equal in time and bytes, and
    # a neighbour role holder as fast and lighter, not selected, above the best; (4 KiB all-home) a setting as fast
    # and as light as the best, first by the knobs, not selected
    rows2 += ten(8, "all-home", 4, 16, 1.0, 1.0) + ten(8, "all-home", 4, 4, 0.5, 1.2) + ten(8, "all-home", 6, 4, 0.5, 1.2)
    rows2 += ten(8, "all-home", 8, 8, 0.5, 1.1)
    rows2 += ten(4, "all-home", 4, 16, 1.0, 1.0) + ten(4, "all-home", 6, 4, 0.5, 1.2) + ten(4, "all-home", 4, 4, 0.5, 1.2)
    sets2 = {(64, "all-home"): {"host": "A", "roles": {k(6, 4): ["the fastest"], k(8, 4): ["the fastest's best neighbour"],
                                                      k(4, 16): ["the base"]}},
             (16, "all-home"): {"host": "A", "roles": {k(6, 4): ["the fastest"], k(2, 16): ["the lighter point"],
                                                      k(6, 8): ["the fastest's best neighbour"], k(4, 16): ["the base"]}},
             (8, "all-home"): {"host": "A", "roles": {k(4, 4): ["the fastest"], k(6, 4): ["the lighter point"],
                                                     k(8, 8): ["the fastest's best neighbour"], k(4, 16): ["the base"]}},
             (4, "all-home"): {"host": "A", "roles": {k(6, 4): ["the fastest"], k(4, 4): ["the fastest's best neighbour"],
                                                     k(4, 16): ["the base"]}}}
    res2 = fronts.analyse(rows2, list(SEEDS), expect={r["log"]: (int(r["size_kib"]), r["network"], int(r["seed"])) for r in rows2})[1]
    gss2 = gossipsub_cells(rows2)
    P2, P3 = (64, "all-home"), (16, "all-home")
    nc = judge(res2[P2], P2, sets2[P2], gss2.get(P2))
    assert nc["outcome"] == ("NO COMPARISON", "the default is failed at ten seeds") and nc["best"] == k(6, 4), nc
    assert nc["nb"] == k(8, 4) and nc["pref"] == k(6, 4) and nc["pref_why"] == "the lighter", nc
    assert nc["flags"] == ["MISSED: R=8 unit=4K leo8 rfast=8, not selected, is clearly faster than the best"], nc["flags"]
    assert nc["gossipsub"]["base"] is None and words(nc["gossipsub"]["pref"]) == "clearly slower and clearly heavier", nc
    assert cnt(nc["gossipsub"]["pref"]) == (0, 0, 10), nc["gossipsub"]
    sp = judge(res2[P3], P3, sets2[P3], gss2.get(P3))
    assert sp["best"] == k(6, 4) and sp["nb"] == k(6, 8) and sp["naming"] == "both" and sp["pref"] == k(6, 8), sp
    assert sp["pref_why"] == "the lighter; neither clears the bar against the default", sp
    assert sp["outcome"] == ("DEFAULT HOLDS", "the preferred setting is close in time to the default"), sp
    assert words(verdict(k(2, 16), k(4, 16), res2[P3]["settings"], 16)) == "clearly lighter", sp
    assert sp["flags"] == [f"SPLIT: {fronts.name(k(2, 16))}, not named, clears the bar against the default; the outcome "
                           "follows the named settings"], sp["flags"]
    P4, P5 = (8, "all-home"), (4, "all-home")
    kn = judge(res2[P4], P4, sets2[P4], gss2.get(P4))
    assert kn["ok"][0] == k(8, 8) and kn["best"] == k(4, 4) and kn["nb"] == k(6, 4) and kn["pref"] == k(4, 4), kn
    assert kn["notes"] == ["the best is tied in time with R=6 unit=4K leo8 by the median of ten; equal in bytes too: the "
                           "knobs rank it first", "the two are equal in bytes by the median of ten; equal in time too: the "
                           "knobs decide"], kn["notes"]
    assert kn["pref_why"] == "the first by the knobs, the two equal in bytes and in time; both clear the bar against the default", kn
    k5 = judge(res2[P5], P5, sets2[P5], gss2.get(P5))
    assert k5["ok"][0] == k(4, 4) and k5["best"] == k(6, 4) and k5["pref"] == k(4, 4) and k5["outcome"][0] == "CHANGE", k5
    assert k5["flags"] == ["PREFERRED NOT SELECTED: the change goes to R=4 unit=4K leo8, the best's neighbour, not a "
                           "setting stage 2 selected"], k5["flags"]
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        assert report(res2, sets2, gss2) is True
    t2 = buf2.getvalue()
    for want in ("     faster by the median of ten, not selected: R=8 unit=4K leo8 rfast=8",
                 "     as fast by the median of ten and lighter, not selected: R=8 unit=8K leo8 rfast=8",
                 "     as fast and as light by the median of ten, first by the knobs, not selected: R=4 unit=4K leo8",
                 "   FOR THE TEXT: NO COMPARISON: the default is failed at ten seeds",
                 "   FOR THE AUTHOR: MISSED: R=8 unit=4K leo8 rfast=8, not selected, is clearly faster than the best",
                 "     against the preferred R=6 unit=4K leo8: faster on 0 of 10",
                 "   R=6 unit=4K leo8 (preferred): the default R=4 unit=16K leo8 is failed: no comparison",
                 "NO COMPARISON: 1: 64 KiB all-home (flagged)"):
        assert want in t2, (want, t2)
    # the published set files (stage 2's output, in data/tuning/stage2): their shape
    real = load_set([os.path.join(HERE, "..", "..", "data", "tuning", "stage2", f"stage3-{h}.csv") for h in ("B", "A")])
    assert len(real) == 16 and all(check_roles(v["roles"]) is None for v in real.values())
    assert sorted(sum(len(v["roles"]) for v in real.values() if v["host"] == h) for h in ("B", "A")) == [25, 29]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert report(res, sets, gss) is False                    # a refusal fails the run without --csv too
    buf, out_all = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert report(res, sets, gss, out_all) is False
    text = buf.getvalue()
    assert out_all.getvalue() == "" and "CSV NOT WRITTEN: 7 points refused" in text, text
    for want in (
            "note: gossipsub's whole message is a reference outside the rules: unsigned, with the author's peer id",
            "   noise allowance here: time 10 %, bytes 8 %; clear: on at least 8 of 10 seeds and beyond it",
            "     1. R=8 unit=4K leo8 rfast=8 (0.7000 s, 1.4000 MiB, 63.10 copies; spec UNIT+R_FAST) [the fastest]",
            "     2. R=6 unit=4K leo8 (0.8000 s, 1.3000 MiB, 58.59 copies; spec UNIT) [the lighter point; the fastest's best neighbour]",
            "   R=8 unit=4K leo8 rfast=8 against R=6 unit=4K leo8: faster on 10 of 10 (median +12.50 %), lighter on 0 of 10 "
            "(median -7.69 %): clearly faster; on seeds 10 to 16 (7): faster on 7 (median +12.50 %), lighter on 0",
            "   NAMED ALONE: against its best neighbour R=6 unit=4K leo8 (1 of its 2 neighbours ok at ten seeds)",
            "   R=8 unit=4K leo8 rfast=8 against the default R=4 unit=16K leo8: faster on 10 of 10 (median +30.00 %), lighter on 0 "
            "of 10 (median -40.00 %): clearly faster and clearly heavier",
            "   FOR THE TEXT: CHANGE: the preferred setting is clearly faster than the default, clearly heavier",
            "   gossipsub, the whole message (a reference): 0.7500 s, 72.12 copies",
            "     against the default R=4 unit=16K leo8: faster on 10 of 10 (median +25.00 %), lighter on 0 of 10 (median -60.00 %): "
            "clearly faster and clearly heavier",
            "     against the preferred R=8 unit=4K leo8 rfast=8: faster on 0 of 10 (median -7.14 %), lighter on 0 of 10 "
            "(median -14.29 %): clearly heavier",
            "   gossipsub, the whole message: FAILED at ten seeds, failed on [12]",
            "   BOTH NAMED: against its best neighbour R=6 unit=4K leo8 (1 of its 1 neighbours ok at ten seeds): faster on 10 of 10 "
            "(median +5.38 %), lighter on 0 of 10 (median -15.38 %): clearly heavier; on seeds 10 to 16 (7): faster on 7 "
            "(median +5.38 %), lighter on 0; PREFERRED: R=8 unit=4K leo8 rfast=8 (the only one of the two that clears the bar "
            "against the default)",
            "     note: the best is faster than its neighbour on 10 of 10 seeds, within the allowance: by the count alone it "
            "would be named alone",
            "   R=8 unit=4K leo8 rfast=8 (preferred) against the default R=4 unit=16K leo8: faster on 10 of 10 (median +12.00 %), "
            "lighter on 0 of 10 (median -50.00 %): clearly faster and clearly heavier",
            "   R=6 unit=4K leo8 against the default R=4 unit=16K leo8: faster on 10 of 10 (median +7.00 %), lighter on 0 "
            "of 10 (median -30.00 %): clearly heavier",
            "   FOR THE AUTHOR: SPLIT: R=6 unit=8K leo8, not named, clears the bar against the default; the outcome follows the "
            "named settings",
            "   FOR THE TEXT: CHANGE: the preferred setting is clearly lighter than the default and close in time",
            "   FOR THE TEXT: DEFAULT HOLDS: the default is clearly faster than the preferred setting, which is clearly lighter",
            "   FOR THE AUTHOR: MISSED: the default R=4 unit=16K leo8 is clearly faster than the best",
            "     faster by the median of ten, not selected: R=6 unit=8K leo8",
            "   BOTH NAMED: against its best neighbour R=3 unit=16K leo8 (1 of its 1 neighbours ok at ten seeds): faster on 7 of 10 "
            "(median +14.29 %), lighter on 10 of 10 (median +16.67 %): clearly lighter; on seeds 10 to 16 (7): faster on 4 "
            "(median +14.29 %), lighter on 7; PREFERRED: R=2 unit=16K leo8 (the lighter; neither clears the bar against the default)",
            "   R=2 unit=16K leo8 (preferred) is the default",
            "   FOR THE TEXT: DEFAULT HOLDS: the preferred setting is the default",
            "   the best (the fastest selected setting by the median of ten): R=2 unit=32K leo8",
            "     faster by the median of ten, not selected: R=3 unit=32K leo8",
            "   BOTH NAMED: against its best neighbour R=3 unit=32K leo8 (2 of its 2 neighbours ok at ten seeds): faster on 0 of 10 "
            "(median -13.33 %), lighter on 10 of 10 (median +20.83 %): clearly slower and clearly lighter",
            "   FOR THE AUTHOR: MISSED: R=3 unit=32K leo8, not selected, is clearly faster than the best",
            "   gossipsub, the whole message: seeds [7] only, not run in stage 3: no comparison",
            "     not ok, out of the ranking: R=4 unit=8K leo8 [failed, 10 of 10 seeds, failed on [12]] REFUSED UNDER THE GROUP "
            "BOUND: 27 of 9027 warm announcements in 9 cells [the fastest's best neighbour]",
            "   NOT COMPARED: none of its 1 neighbours among the cells is ok at ten seeds; the best is preferred alone",
            "   FOR THE TEXT: DEFAULT HOLDS: the default is clearly faster than the preferred setting, which is close in bytes; "
            "the preferred setting's marks: PAST 3 s in 1 cells (worst warm payload 480 of 499)",
            "   FOR THE AUTHOR: PREFERRED NOT SELECTED: the change goes to R=4 unit=4K leo8, the best's neighbour",
            "   FOR THE TEXT: NO COMPARISON: the default is failed at ten seeds; no selected setting is ok",
            "   NO BEST: no selected setting is ok at ten seeds",
            "     note: the best is tied in time with R=4 unit=4K leo8 by the median of ten; the lighter ranks first",
            "   REFUSED: MISSING: 1 listed cells are not in the rows",
            "   REFUSED: NO ROWS: the set names this point, the rows have none",
            "15 points read, 7 refused: 16 KiB all-home; 32 KiB dcb20; 64 KiB dcb20; 128 KiB all-home; 256 KiB all-home; "
            "512 KiB dcb20; 4096 KiB all-home",
            "32 KiB all-home | 1.0000 s, 45.07 copies | R=8 unit=4K leo8 rfast=8 (0.7000 s, 63.10 copies; UNIT+R_FAST) | alone | "
            "30.00 %, -40.00 % (10, 0): clearly faster and clearly heavier | CHANGE",
            "64 KiB all-home | 1.0000 s, 22.54 copies | R=8 unit=4K leo8 rfast=8 (0.8800 s, 33.80 copies; UNIT+R_FAST) | both "
            "with R=6 unit=4K leo8 | 12.00 %, -50.00 % (10, 0): clearly faster and clearly heavier | CHANGE",
            "1024 KiB all-home | 0.6000 s, 1.41 copies | R=2 unit=16K leo8 (0.6000 s, 1.41 copies; -) | both with R=3 unit=16K "
            "leo8 | - | DEFAULT HOLDS",
            "1024 KiB dcb20 | 0.5000 s, 1.41 copies | R=2 unit=64K leo8 (0.6000 s, 1.39 copies; UNIT+MAX_SEGMENT_SIZE) PAST 3 s in "
            "1 cells (worst warm payload 480 of 499) | not compared | -20.00 %, 1.00 % (0, 10): clearly slower | DEFAULT HOLDS (flagged)",
            "2048 KiB all-home |  s,  copies | no best | no best | - | NO COMPARISON",
            "4096 KiB dcb20 | 1.1000 s, 0.70 copies | no best | no best | - | FOR THE AUTHOR",
            "CHANGE: 8: 8 KiB all-home; 8 KiB dcb20 (flagged); 16 KiB dcb20; 32 KiB all-home; 64 KiB all-home; 128 KiB dcb20 "
            "(flagged); 512 KiB all-home; 2048 KiB dcb20 (flagged)",
            "DEFAULT HOLDS: 5: 4 KiB all-home (flagged); 4 KiB dcb20 (flagged); 256 KiB dcb20; 1024 KiB all-home; 1024 KiB dcb20 (flagged)",
            "FOR THE AUTHOR: 1: 4096 KiB dcb20",
            "NO COMPARISON: 1: 2048 KiB all-home"):
        assert want in text, (want, text)
    complete = {p: v for p, v in res.items() if p in ((32, "all-home"), (64, "all-home"), (1024, "all-home"), (2048, "dcb20"),
                                                      (256, "dcb20"), (1024, "dcb20"))}
    csets = {p: sets[p] for p in complete}
    out_sel, said = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(said):
        assert report(complete, csets, gss, out_sel) is True
    got = list(csv.DictReader(io.StringIO(out_sel.getvalue())))
    assert [(r["size_kib"], r["network"], r["outcome"], r["naming"]) for r in got] == [
        ("32", "all-home", "CHANGE", "alone"), ("64", "all-home", "CHANGE", "both"), ("256", "dcb20", "DEFAULT HOLDS", "not compared"),
        ("1024", "all-home", "DEFAULT HOLDS", "both"), ("1024", "dcb20", "DEFAULT HOLDS", "not compared"),
        ("2048", "dcb20", "CHANGE", "both")], got
    assert got[0]["gossipsub_s"] == "0.7500" and got[0]["time_gap_pct"] == "30.00" and got[3]["verdict"] == "", got
    assert got[4]["preferred_marks"] == "PAST 3 s in 1 cells (worst warm payload 480 of 499)" and got[4]["flags"] == (
        "MISSED: the default R=2 unit=16K leo8 is clearly faster than the best") and got[0]["preferred_marks"] == "", got
    # the input's order does not change the reading
    rev = fronts.analyse(list(reversed(rows)), list(SEEDS), expect=exp)[1]
    gr = gossipsub_cells(list(reversed(rows)))
    assert all(judge(rev.get(p), p, sets.get(p), gr.get(p)) == j(p) for p in set(res) | set(sets))
    print("selftest: the verdict at ten seeds (8 of 10 and 7 of 10 on time and bytes, the exact boundaries at 6, 10, 3 and "
          "8 %, the median of ten as the mean of the middle two, seeds 10 to 16 apart, ties, wins with ties, nine seeds, a "
          "failed cell, antisymmetric), the best among the selected (the lighter point as best, an exact tie in time), its "
          "best neighbour (the default among them) and their count, named alone, both named with the lighter preferred (a "
          "tie in bytes, the count-alone note), not compared, the preferred among those that clear the bar (one, both, "
          "neither), the outcomes (change by time with the best and with the neighbour, change by bytes, default holds as "
          "the default, as close, as clearly slower and as clearly slower and lighter, no best, no comparison with its best "
          "and flags kept), the wording that follows the key that decided (bytes equal by the exact median and not by "
          "floats; time and bytes equal, the knobs deciding, in the preference, the tie notes and the ranking), the flags (split by a setting not named, by time and by bytes alone, the other selected setting "
          "among them; missed by a setting and by the default; preferred not selected; no neighbour test), marks, "
          "gossipsub (against the default and the preferred, failed, not run in stage 3, left out where stage 3 ran it), "
          "the refusals (missing, no rows, no set, host, roles with a base's status, a role twice and no role of the "
          "filter, absent, short, outside, base), the committed set files' shape, strays, the table, the exit and the CSV "
          "withheld and written with the preferred setting's marks, the input's order: ok")


def main():
    a = sys.argv[1:]
    if a == ["--selftest"]:
        return selftest()
    files, expect, setp, out_csv = [], [], [], None
    while a:
        x = a.pop(0)
        if x == "--expect":
            expect.append(a.pop(0))
        elif x == "--set":
            setp.append(a.pop(0))
        elif x == "--csv":
            out_csv = a.pop(0)
        elif x.startswith("--"):
            sys.exit(__doc__)
        else:
            files.append(x)
    if not files or not expect or not setp:
        sys.exit(__doc__)
    rows, exp = fronts.load(files), fronts.load_expect(expect)
    bad = strays(rows, exp)
    if bad:
        sys.exit(f"{len(bad)} rows of seeds {SEEDS[0]} to {SEEDS[-1]} are no cell of the lists given: " + "; ".join(bad[:5]))
    info, res = fronts.analyse(rows, list(SEEDS), 500, exp)
    print(f"seeds {SEEDS[0]} to {SEEDS[-1]} (stage 3's set chosen on 7 to 9); {info['ignored']} rows of other seeds not "
          f"used; SEACAST binary md5 {info['md5'] or '-'}; \"clearly\" faster or lighter: on at least {CLEAR} of "
          f"{len(SEEDS)} seeds, paired, and beyond the noise allowance")
    if not report(res, load_set(setp), gossipsub_cells(rows), out_csv):
        sys.exit(1)


if __name__ == "__main__":
    main()
