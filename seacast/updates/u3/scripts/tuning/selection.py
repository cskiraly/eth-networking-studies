#!/usr/bin/env python3
"""Stage 2's selection: what goes on to stage 3, per point, by the reading fixed before stage 2's launch. It
reads fronts.py's analysis and adds what fronts.py does not print. The rules marked "the author's" below are
the author's decisions.

    python3 selection.py --expect LIST.dry... [--roles ROLE,... [--csv OUT.csv]] HOST=cells.csv...
    python3 selection.py --selftest

ROLE: selected, base, fastest-neighbour, lighter-neighbour, corner (the roles of stage 3's set, below).

The cells: read.py's rows of stage 1, the grow batch and stage 2 for each host, all of seeds 7, 8 and 9 (stage 1
and the grow batch ran seed 7 only). --expect names every list's .dry file of those runs and is required. Every
row of seeds 7 to 9 must be a cell of the lists (else the run stops: a stray row could make a setting ok);
a point with a listed cell that is not in the rows gets no selection (MISSING). fronts.analyse's checks
hold (one node count, one SEACAST binary, one host a point, one cell a setting and seed). Statuses, kinds,
the base, the front, neighbours and the marks are fronts.py's.

Per point (payload size, network), over the ok grid settings, by their medians over the three seeds:
  - every comparison of A with B, paired by seed, prints its counts (faster, lighter on n of 3 seeds), its
    median per-seed gaps (time 1 - t_A / t_B, bytes 1 - b_A / b_B; positive where A is faster or lighter) and
    a verdict (the author's): "clearly faster" ("clearly lighter") where A is faster (lighter) on all 3 seeds
    and the gap is beyond stage 1's noise allowance (time 6 % from 512 KiB up and 10 % below; bytes 3 % and
    8 %); "clearly slower" ("clearly heavier") where B is clearly faster (lighter) than A by B's own gap, so
    that the verdicts are antisymmetric; else "close" on that axis. The gap is relative to the other setting of
    the pair, a little stricter than fronts.carry()'s measure relative to the front's (6 % here is 6.4 %
    there, 10 % is 11.1 %, 3 % is 3.1 %, 8 % is 8.7 %). Gaps print to two decimals. Stage 2
    concludes only on clear verdicts. All three seeds took part in this pick; the
    counts on seeds 8 and 9 exclude only stage 1's carry, which was made on seed 7. The verdict independent of
    the pick is stage 3's, on seeds 10 to 16;
  - the fastest: the front's fastest by the median (fronts.order: time, then bytes, then the knobs). It is
    selected. Printed: its verdict against the runner-up (the next ok grid setting by the median), and its
    close rivals (the ok grid settings it is not clearly faster than). "The fastest" is a median's word;
  - the lighter point (the author's): of the front's other settings, those clearly lighter than the fastest;
    of these, the fastest by the median. Where none is, the point sends the fastest alone, the front's other
    settings are named with their verdicts, and the front's next point by time with a lower byte median is
    printed as "lighter by the median only", not selected;
  - each selected setting against the base and against its best neighbour (fronts.py's: the fastest ok
    neighbour by stage 2's medians), with the verdict over three seeds and the counts on seeds 8 and 9; every
    other ok neighbour too, and "the best of k ok of m neighbours" where some are not ok;
  - the point's state. OPEN (the author's): the fastest is not clearly faster than the base or than its best
    neighbour; stage 3's ten seeds decide it with the cells already chosen. NOT COMPARED: the fastest has no ok
    neighbour, so neither stage 2 nor stage 3's set can test it against one. Else concluded: clearly faster
    than its best neighbour, and than the base where the base is ok and not itself; a base that is not ok is
    named "no comparison" (the author's);
  - stage 3's settings at the point, by role (the author's choice: selected, the base, the fastest's best
    neighbour; --roles selected,base,fastest-neighbour): selected (the fastest, the lighter point); the base;
    the fastest's best neighbour; also printed, not chosen: the lighter point's best neighbour, and the corner
    (each uncoded setting that would be on the front, with its ok coded twin). The totals print the cumulative
    count of distinct settings role by role, a setting counted once at its first role;
  - the grid's growth (the study plan's words: "Stage 2's three seeds show whether R = 8 or 2 KiB really beat their
    inner neighbours; the grid grows later only where they do"). Every grid setting at R = 8 or in 2 KiB
    chunks, whatever its status, against its inner neighbour (R = 6, the same chunk size and code; 4 KiB chunks, the same R, the code by the code rule):
      GROWS (by time, by bytes, or both; the author's: either axis): on the three-seed front and clearly
        faster or clearly lighter;
      does not grow: tested, and close on both axes, or not on the three-seed front;
      NOT TESTED, with the reason: the point has no selection (a listed cell missing), the setting or its
        inner neighbour is not ok, or the neighbour has no cell.
    Front settings on another edge of the grid (fronts.py's geometric edge, but for a one-chunk setting at the
    largest chunk size, where no larger chunk exists) are named as outside the words;
  - the corner: each uncoded setting that would be on the front, against the fastest and against its coded
    twin (the same R and chunk size, the code rule's Leopard code);
  - grid settings that are not ok for a reason other than lacking stage 2's seeds (failed, censored, or short
    with a cell of seed 8 or 9) are named, also at a point without a selection; settings with seed 7 only are
    those stage 1 did not carry;
  - gossipsub's whole message where the point has it, also at a point without a selection.
--roles keeps of stage 3's set only the settings that hold one of the roles named (the author's choice) and
prints that set's size by host. --csv, which needs --roles, writes those settings with their roles and marks,
one row a setting and point; it is not written when a point has no selection (stage 3's list needs every
point), and the run then exits nonzero.
"""
import contextlib
import csv
import io
import statistics as st
import sys
from fractions import Fraction

import fronts

SEEDS = (7, 8, 9)
SELECTED_ON = (7,)
FRESH = tuple(x for x in SEEDS if x not in SELECTED_ON)
ROLES = ("selected", "the base", "the fastest's best neighbour", "option: the lighter point's best neighbour",
         "option: the corner")


def pair(a, b, S, seeds=SEEDS):
    """-> (faster, lighter, n) of a against b, paired by seed (fronts.paired)."""
    return fronts.paired(a, b, S, list(seeds))


def noise(size):
    """Stage 1's noise allowance (time, bytes), as fronts.carry() has it: time 6 % and bytes 3 % from 512 KiB
    up, time 10 % and bytes 8 % below (the repeat noise of four runs of one cell)."""
    return (Fraction("0.06"), Fraction("0.03")) if size >= 512 else (Fraction("0.10"), Fraction("0.08"))


def verdict(a, b, S, size, seeds=SEEDS):
    """a against b, paired by seed: counts, the median per-seed gaps (time: 1 - t_a / t_b; bytes: 1 - b_a / b_b;
    positive where a is faster or lighter), and the verdicts: clearly faster (lighter) when a is faster
    (lighter) on every one of the stage's seeds and the gap is beyond the noise allowance. Exact fractions of
    the rows' decimal strings, so that a gap of exactly the allowance is not beyond it."""
    f, l, n = pair(a, b, S, seeds)
    rf, rl, _ = pair(b, a, S, seeds)
    xs = [x for x in seeds if x in S[a]["cells"] and x in S[b]["cells"]
          and S[a]["cells"][x]["passed"] == "True" and S[b]["cells"][x]["passed"] == "True"]

    def gap(u, w, col):
        return st.median(1 - Fraction(S[u]["cells"][x][col]) / Fraction(S[w]["cells"][x][col]) for x in xs) if xs else None
    tg, bg = gap(a, b, "p99_s"), gap(a, b, "mib")
    tol_t, tol_b = noise(size)
    full = n == len(seeds) == len(SEEDS)
    return {"f": f, "l": l, "n": n, "tg": tg, "bg": bg,
            "faster": full and f == n and tg > tol_t, "lighter": full and l == n and bg > tol_b,
            # a clear loss is b clearly faster (lighter) than a, by b's own gap: the verdicts are antisymmetric
            "slower": full and rf == n and gap(b, a, "p99_s") > tol_t, "heavier": full and rl == n and gap(b, a, "mib") > tol_b}


def vtext(v):
    """'faster on 3 of 3 (median +7.12 %), lighter on 0 of 3 (median -12.30 %): clearly faster and clearly heavier'"""
    if v["tg"] is None:
        return "no seed with both cells passed"
    t = "clearly faster" if v["faster"] else "clearly slower" if v["slower"] else ""
    b = "clearly lighter" if v["lighter"] else "clearly heavier" if v["heavier"] else ""
    return (f"faster on {v['f']} of {v['n']} (median {float(v['tg']) * 100:+.2f} %), lighter on {v['l']} of {v['n']} "
            f"(median {float(v['bg']) * 100:+.2f} %): " + (" and ".join(x for x in (t, b) if x) or "close"))


def ok_neighbours(s, S):
    """-> (the ok neighbours by the median, all neighbours) of s."""
    nbs = fronts.neighbours(s, S)
    return sorted((c for c in nbs if S[c]["status"] == "ok"), key=fronts.order(S)), nbs


def inner(s, S):
    """-> [(axis, the inner neighbour or None)] for a setting at R = 8 or in 2 KiB chunks."""
    nbs = fronts.neighbours(s, S)
    out = []
    if s[0] == 8:
        c = [n for n in nbs if n[0] == 6 and n[1] == s[1]]
        assert len(c) <= 1, (s, c)
        out.append(("R", c[0] if c else None))
    if s[1] == 2:
        c = [n for n in nbs if n[1] == 4 and n[0] == s[0]]
        assert len(c) <= 1, (s, c)
        out.append(("chunk size", c[0] if c else None))
    return out


def seeds_of(d):
    return len(SEEDS) - len(d["lack"])


def growth(pi, size):
    """-> [(setting, axis, inner, the verdict dict or None, the growth verdict)] for every grid setting at R = 8
    or 2 KiB. GROWS only on a clear win (time or bytes, beyond the noise allowance)."""
    S = pi["settings"]
    out = []
    for s in sorted((s for s, d in S.items() if d["kind"] == "grid" and (s[0] == 8 or s[1] == 2)),
                    key=lambda c: tuple(str(x) for x in c)):
        d = S[s]
        if pi["missing"]:
            # the front lacks the missing cells' settings: a verdict that rests on the front cannot be made
            out.append((s, "-", None, None, f"NOT TESTED: the point has no selection ({len(pi['missing'])} listed cells missing)"))
            continue
        if d["status"] != "ok":
            out.append((s, "-", None, None, f"NOT TESTED: it is {d['status']} ({seeds_of(d)} of {len(SEEDS)} seeds)"))
            continue
        for axis, inn in inner(s, S):
            if inn is None:
                out.append((s, axis, None, None, "NOT TESTED: no inner neighbour among the cells"))
            elif S[inn]["status"] != "ok":
                out.append((s, axis, inn, None, f"NOT TESTED: the inner neighbour is {S[inn]['status']} "
                                                f"({seeds_of(S[inn])} of {len(SEEDS)} seeds)"))
            else:
                vd = verdict(s, inn, S, size)
                win = [w for w, c in (("time", vd["faster"]), ("bytes", vd["lighter"])) if c]
                if s not in pi["front"]:
                    v = "does not grow: not on the three-seed front"
                elif win:
                    v = "GROWS by " + " and ".join(win)
                else:
                    v = "does not grow: close"
                out.append((s, axis, inn, vd, v))
    return out


def other_edges(pi):
    """Front settings on the grid's geometric edge (fronts.py's) that are not at R = 8 or 2 KiB; a one-chunk
    setting (K = 1) at the largest chunk size is no edge (no larger chunk exists: edge_growth.py's floor);
    none at a point without a selection."""
    S = pi["settings"]
    grid = [s for s in S if S[s]["kind"] == "grid"]
    if not grid or pi["missing"]:
        return []
    rmax, umin, umax = max(x[0] for x in grid), min(x[1] for x in grid), max(x[1] for x in grid)
    return [s for s in sorted(pi["front"], key=fronts.order(S))
            if (s[0] == rmax or s[1] == umin or (s[1] == umax and S[s]["k"] > 1)) and not (s[0] == 8 or s[1] == 2)]


def not_ok(S, with_base=False):
    """Grid settings not ok for a reason other than lacking stage 2's seeds (seed 7 only: stage 1 did not carry them).
    The base is left out where the comparisons name its status, and kept at a point without a selection."""
    return [s for s, d in sorted(S.items(), key=lambda kv: tuple(str(x) for x in kv[0]))
            if d["kind"] == "grid" and d["status"] != "ok" and (with_base or not d["base"])
            and (d["base"] or d["status"] != "short" or any(x in d["cells"] for x in FRESH))]


ROLE_NAMES = dict(zip(("selected", "base", "fastest-neighbour", "lighter-neighbour", "corner"), ROLES))


def has_role(rs, role):
    """Whether a setting's roles hold a role of ROLES (a base with a status, the corner's coded twin included)."""
    return any(r in ("the fastest", "the lighter point") if role == "selected" else r.startswith(role) for r in rs)


def select(pi, size):
    """-> a dict with the point's selection, or {"refused": why, "out_of": [...]}."""
    S = pi["settings"]
    if pi["missing"]:
        return {"refused": f"MISSING: {len(pi['missing'])} listed cells are not in the rows", "out_of": not_ok(S, True)}
    key = fronts.order(S)
    fr = sorted(pi["front"], key=key)
    if not fr:
        return {"refused": "NO FRONT: no ok grid setting", "out_of": not_ok(S, True)}
    fastest = fr[0]
    grid_ok = sorted((s for s, d in S.items() if d["status"] == "ok" and d["kind"] == "grid"), key=key)
    assert grid_ok[0] == fastest, (grid_ok[0], fastest)
    runner = grid_ok[1] if len(grid_ok) > 1 else None
    # the ok grid settings the fastest is not clearly faster than: its close rivals
    rivals = [(s, v) for s in grid_ok[1:] for v in [verdict(fastest, s, S, size)] if not v["faster"]]
    # the lighter point: clearly lighter than the fastest, the fastest of those
    lighter = next((s for s in fr[1:] if verdict(s, fastest, S, size)["lighter"]), None)
    # the front's next point by time with a lower byte median (an exact twin of the fastest is not lighter)
    median_only = None if lighter else next((s for s in fr[1:] if S[s]["mib"] < S[fastest]["mib"]), None)
    others = [(s, verdict(s, fastest, S, size)) for s in fr[1:] if s != lighter]
    picked = [fastest] + ([lighter] if lighter else [])
    bases = sorted((s for s, d in S.items() if d["base"]), key=lambda c: tuple(str(x) for x in c))
    comps, best, open_ = [], {}, []
    for s in picked:
        for b in bases:
            if b == s:
                comps.append((s, "base", b, "is"))
            elif S[b]["status"] != "ok":
                comps.append((s, "base", b, S[b]["status"]))
            else:
                v = verdict(s, b, S, size)
                comps.append((s, "base", b, (v, pair(s, b, S, FRESH))))
                if s == fastest and not v["faster"]:
                    open_.append(f"close to the base {fronts.name(b)}")
        okn, nbs = ok_neighbours(s, S)
        best[s] = okn[0] if okn else None
        if okn:
            v = verdict(s, okn[0], S, size)
            comps.append((s, f"best neighbour (the best of {len(okn)} ok of {len(nbs)} neighbours)" if len(okn) < len(nbs)
                          else "best neighbour", okn[0], (v, pair(s, okn[0], S, FRESH))))
            if s == fastest and not v["faster"]:
                open_.append(f"close to its best neighbour {fronts.name(okn[0])}")
        else:
            comps.append((s, "best neighbour", None, None))
        for c in okn[1:]:
            comps.append((s, "other ok neighbour", c, (verdict(s, c, S, size), pair(s, c, S, FRESH))))
        for c in nbs:
            if S[c]["status"] != "ok":
                comps.append((s, "neighbour", c, f"{S[c]['status']} ({seeds_of(S[c])} of {len(SEEDS)} seeds)"))
    corner = []
    for s in sorted((s for s, d in S.items() if d["would_front"]), key=key):
        twin = [c for c in S if c[:2] == s[:2] and c[3:] == s[3:] and S[c]["kind"] == "grid" and c[2] in ("leo8", "leo16")]
        tw = twin[0] if twin and S[twin[0]]["status"] == "ok" else None
        corner.append((s, verdict(s, fastest, S, size), tw, verdict(s, tw, S, size) if tw else None,
                       None if tw else (f"its coded twin is {S[twin[0]]['status']}" if twin else "no coded twin among the cells")))
    # the point's state (stage 2 concludes only on clear verdicts): open where a measured
    # comparison of the fastest is close; not compared where the fastest has no ok neighbour (stage 3's set then
    # holds none either); else concluded
    okn_f, nbs_f = ok_neighbours(fastest, S)
    nb_flag = f" (the best of {len(okn_f)} ok of {len(nbs_f)} neighbours)" if okn_f and len(okn_f) < len(nbs_f) else ""
    state = "open" if open_ else "not compared" if best[fastest] is None else "concluded"
    stage3 = {}   # setting -> [roles], in ROLES' order of first appearance
    for s, role in [(fastest, "the fastest"), (lighter, "the lighter point")]:
        if s:
            stage3.setdefault(s, []).append(role)
    for b in bases:
        stage3.setdefault(b, []).append("the base" + ("" if S[b]["status"] == "ok" else f" [{S[b]['status']}]"))
    if best[fastest]:
        stage3.setdefault(best[fastest], []).append("the fastest's best neighbour")
    if lighter and best[lighter]:
        stage3.setdefault(best[lighter], []).append("option: the lighter point's best neighbour")
    for s, _, tw, *_ in corner:
        stage3.setdefault(s, []).append("option: the corner")
        if tw:
            stage3.setdefault(tw, []).append("option: the corner (its coded twin)")
    by_role = []   # the cumulative distinct settings, role by role; a setting counts once, at its first role
    seen = set()
    for role in ROLES:
        seen |= {s for s, rs in stage3.items() if has_role(rs, role)}
        by_role.append(len(seen))
    out_of = not_ok(S)
    return {"fastest": fastest, "runner": runner, "runner_v": verdict(fastest, runner, S, size) if runner else None,
            "rivals": rivals, "lighter": lighter, "median_only": median_only, "others": others, "open": open_,
            "state": state, "nb_flag": nb_flag, "best_nb": best[fastest],
            "comps": comps, "stage3": stage3, "by_role": by_role, "corner": corner, "bases": bases, "out_of": out_of}


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
    return (f"{fronts.name(s)} ({d['time']:.4f} s, {d['mib']:.4f} MiB{cp})" if "time" in d else fronts.name(s)) + marks(d)


def counts(v):
    vd, (f2, l2, m2) = v
    return f"{vtext(vd)}; on seeds {','.join(str(x) for x in FRESH)} ({m2}): faster on {f2}, lighter on {l2}"


def report(res, out_csv=None, roles=None):
    """Prints the selection; with roles (a list of ROLES), keeps only stage 3's settings holding one of them and
    prints that set's size. -> False when a CSV was asked for and withheld, else True."""
    n = len(SEEDS)
    rows, totals, grows, untested, done, refused, chosen, states = [], {}, [], [], [], [], {}, {}
    for point, pi in res.items():
        size, net = point
        S = pi["settings"]
        print(f"\n== {size} KiB, {net} (host {pi['host']})")
        g = pi["gossipsub"]
        if g and g["status"] == "ok":
            cp = f"{g['mib'] / pi['comp_mib']:.2f} copies" if pi["comp_mib"] else f"{g['mib']:.4f} MiB"
            print(f"   gossipsub, the whole message: {g['time']:.4f} s, {cp}"
                  + (f" PAST 3 s in {g['past_3s']} cells (worst warm payload {g['at_3s'][0]} of {g['at_3s'][1]})" if g["past_3s"] else ""))
        elif g:
            print(f"   gossipsub, the whole message: {g['status'].upper()}")
        sel = select(pi, size)
        for s in sel["out_of"]:
            d = S[s]
            print(f"   not ok, out of the ranking: {fronts.name(s)} [{d['status']}, {seeds_of(d)} of {n} seeds"
                  + (f", failed on {d['failed_seeds']}" if d["failed_seeds"] else "") + "]")
        if "refused" in sel:
            print(f"   NO SELECTION: {sel['refused']}")
            refused.append(f"{size} KiB {net}")
            continue
        done.append(point)
        fa = sel["fastest"]
        tol_t, tol_b = noise(size)
        print(f"   noise allowance here: time {float(tol_t) * 100:.0f} %, bytes {float(tol_b) * 100:.0f} %")
        line = f"   the fastest by the median: {fig(S, fa)}"
        if sel["runner"]:
            line += f"; against the runner-up {fronts.name(sel['runner'])}: {vtext(sel['runner_v'])}"
        else:
            line += "; the only ok grid setting"
        print(line)
        if sel["rivals"]:
            print(f"     close rivals, the fastest not clearly faster than {len(sel['rivals'])} other ok grid settings: "
                  + "; ".join(f"{fronts.name(s)} ({vtext(v)})" for s, v in sel["rivals"]))
        elif sel["runner"]:
            print("     clearly faster than every other ok grid setting")
        if sel["lighter"]:
            print(f"   the lighter point: {fig(S, sel['lighter'])}: against the fastest: {vtext(verdict(sel['lighter'], fa, S, size))}")
        else:
            print("   the lighter point: NONE clearly lighter than the fastest")
            if sel["median_only"]:
                print(f"     the front's next point by time, lighter by the median only (not selected): {fig(S, sel['median_only'])}: "
                      f"against the fastest: {vtext(verdict(sel['median_only'], fa, S, size))}")
        for s, v in sel["others"]:
            if s != sel["median_only"]:
                print(f"     the front's other setting {fronts.name(s)}: against the fastest: {vtext(v)}")
        for s, label, o, v in sel["comps"]:
            who = "the fastest" if s == fa else "the lighter point"
            if label == "neighbour":
                print(f"   {who}: its neighbour {fronts.name(o)} is {v}: no comparison")
            elif o is None:
                print(f"   {who}: NO OK NEIGHBOUR among the cells: stage 3's neighbour test has no cells")
            elif v == "is":
                print(f"   {who} is the base")
            elif isinstance(v, str):
                print(f"   {who}: the base {fronts.name(o)} is {v}: no comparison")
            else:
                print(f"   {who} against the {label} {fronts.name(o)}: {counts(v)}")
        if not sel["bases"]:
            print("   NO BASE at this point")
        bnote = "".join(f"; the base {fronts.name(b)} is {S[b]['status']}: no comparison" for b in sel["bases"] if S[b]["status"] != "ok")
        if sel["state"] == "open":
            print("   OPEN (stage 3's ten seeds decide): the fastest is " + "; ".join(sel["open"]) + sel["nb_flag"] + bnote)
        elif sel["state"] == "not compared":
            print("   NOT COMPARED: the fastest has no ok neighbour among the cells, and stage 3's set holds none" + bnote)
        else:
            what = [f"its best neighbour {fronts.name(sel['best_nb'])}{sel['nb_flag']}"]
            what += [f"the base {fronts.name(b)}" for b in sel["bases"] if S[b]["status"] == "ok" and b != fa]
            print("   concluded: the fastest is clearly faster than " + " and ".join(what)
                  + ("; it is the base" if fa in sel["bases"] else "") + bnote)
        states.setdefault(sel["state"], []).append(f"{size} KiB {net}")
        for s, v, tw, tv, why in sel["corner"]:
            txt = f"   corner: {fig(S, s)} would be on the front; against the fastest: {vtext(v)}"
            txt += f"; against its coded twin {fronts.name(tw)}: {vtext(tv)}" if tw else f"; {why}"
            print(txt)
        st3 = sel["stage3"]
        print(f"   stage 3 here, by role ({' / '.join(ROLES)}): {' -> '.join(str(x) for x in sel['by_role'])} settings: "
              + "; ".join(f"{fronts.name(s)}{marks(S[s])} ({', '.join(r)})" for s, r in st3.items()))
        t = totals.setdefault(pi["host"], [0] * len(ROLES))
        for i, x in enumerate(sel["by_role"]):
            t[i] += x
        for s, r in st3.items():
            if roles is not None and not any(has_role(r, role) for role in roles):
                continue
            d = S[s]
            chosen[pi["host"]] = chosen.get(pi["host"], 0) + 1
            rows.append([size, net, pi["host"], *s, d["status"], "; ".join(r), d.get("past_3s", ""),
                         d["refused"] if d.get("refused_mark") else ""])
    for point, pi in res.items():
        for s, axis, inn, c, v in growth(pi, point[0]):
            head = f"   growth, {point[0]} KiB {point[1]}: {fronts.name(s)}"
            if c:
                print(f"{head} against its inner neighbour {fronts.name(inn)} ({axis}): {vtext(c)}: {v}")
            else:
                print(f"{head}" + (f" ({axis})" if axis != "-" else "") + f": {v}" + (f": {fronts.name(inn)}" if inn else ""))
            if v.startswith("GROWS"):
                grows.append(f"{point[0]} KiB {point[1]}: {fronts.name(s)} ({axis}, {v[len('GROWS '):]})")
            elif v.startswith("NOT TESTED"):
                untested.append(f"{point[0]} KiB {point[1]}: {fronts.name(s)}" + (f" ({axis})" if axis != "-" else ""))
        for s in other_edges(pi):
            print(f"   on another edge, outside the author's words (R = 8 and 2 KiB): {point[0]} KiB {point[1]}: {fronts.name(s)}")
    print(f"\n{len(done)} points selected, {len(refused)} without a selection" + (": " + "; ".join(refused) if refused else "")
          + (" (THE TOTALS BELOW ARE PARTIAL)" if refused else ""))
    for label, key in (("open (stage 3's ten seeds decide)", "open"), ("not compared (no ok neighbour)", "not compared"),
                       ("concluded", "concluded")):
        pts = states.get(key, [])
        print(f"{label}: {len(pts)}" + (": " + "; ".join(pts) if pts else ""))
    for h, t in sorted(totals.items()):
        print(f"stage 3's settings, host {h}, cumulative by role ({' / '.join(ROLES)}): {' -> '.join(str(x) for x in t)}")
    print("the grid grows at: " + ("; ".join(grows) or "nowhere"))
    print("not tested: " + ("; ".join(untested) or "none"))
    if roles is not None:
        print(f"stage 3's chosen set (roles: {' / '.join(roles)}): "
              + ", ".join(f"host {h}: {c} settings" for h, c in sorted(chosen.items())) + f"; {sum(chosen.values())} in all")
    if out_csv and refused:
        print(f"CSV NOT WRITTEN: {len(refused)} points without a selection; stage 3's list needs every point "
              "(a file already at that path is left as it was)")
        return False
    if out_csv:
        with contextlib.ExitStack() as stack:
            fh = out_csv if hasattr(out_csv, "write") else stack.enter_context(open(out_csv, "w", newline=""))
            w = csv.writer(fh)
            w.writerow(["size_kib", "network", "host", *fronts.KEY, "status", "roles", "past_3s_cells", "refused_warm_group"])
            w.writerows(rows)
    return True


def strays(rows, exp):
    """Rows of the stage's seeds that are no cell of the lists."""
    return sorted(r["log"] for r in rows if int(r["seed"]) in SEEDS and r["log"] not in exp)


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

    def grid(size, net, specs, seeds=SEEDS):
        """specs: (r, unit, (t7, t8, t9), (b7, b8, b9), code) -> rows at the seeds"""
        return [cell(size, net, seed, r, u, ts[i], bs[i], code) for r, u, ts, bs, code in specs
                for i, seed in enumerate(SEEDS) if seed in seeds]

    k = lambda r, u, code="leo8": (r, u, code, 1, fronts.rule_rfast(r), "200", "20", "2", "", "", "arm", "group")  # noqa: E731
    # A: a lighter point; the fastest beats the runner-up on 3 of 3 but not the fifth by the median
    rows = grid(1024, "all-home", [
        (2, 16, (0.60, 0.61, 0.62), (1.30, 1.30, 1.30), None),     # the base, the lightest
        (3, 16, (0.55, 0.56, 0.57), (1.50, 1.50, 1.50), None),     # front: the lighter point
        (4, 16, (0.50, 0.50, 0.50), (1.80, 1.80, 1.80), None),     # front: the fastest
        (4, 32, (0.51, 0.51, 0.51), (1.82, 1.82, 1.82), None),     # the runner-up, beaten; the fastest's best neighbour
        (3, 32, (0.40, 0.58, 0.58), (1.90, 1.90, 1.90), None),     # fifth by the median, faster than the fastest on seed 7
        (6, 16, (0.52, 0.52, 0.52), (2.20, 2.20, 2.20), None),     # beaten
        (2, 16, (0.40, 0.40, 0.40), (1.00, 1.00, 1.00), "unc")])   # the corner; its twin is the base
    rows += [cell(1024, "all-home", 7, 1, 16, 0.9, 1.2), cell(1024, "all-home", 8, 1, 16, 0.9, 1.2, passed="False")]  # failed on seed 8
    rows += grid(1024, "all-home", [(4, 8, (0.53, 0.53, 0.53), (1.85, 1.85, 1.85), None)], seeds=(7, 8))  # short with seed 8: a neighbour
    rows += [cell(1024, "all-home", 7, 1, 32, 0.9, 1.1)]           # seed 7 only: not carried, not named
    # B: the runner-up is not beaten on 3 of 3; R = 8 does not beat R = 6; an R = 8 off the front
    rows += grid(1024, "dcb20", [
        (2, 16, (0.70, 0.70, 0.70), (1.30, 1.30, 1.30), None),     # the base
        (8, 16, (0.50, 0.52, 0.49), (2.50, 2.50, 2.50), None),     # the fastest by the median
        (6, 16, (0.51, 0.51, 0.51), (2.30, 2.30, 2.30), None),     # the runner-up, the lighter point, R = 8's inner neighbour
        (8, 32, (0.60, 0.60, 0.60), (2.60, 2.60, 2.60), None),     # faster than R = 6 at 32 KiB on 3 of 3, but off the front
        (6, 32, (0.65, 0.65, 0.65), (2.40, 2.40, 2.40), None)])
    # C: no lighter point on 3 of 3; an exact twin of the fastest; 2 KiB beats 4 KiB by time (the grid grows); PAST 3 s
    rows += grid(512, "all-home", [
        (3, 16, (0.40, 0.40, 0.40), (1.00, 1.20, 1.00), None),     # the base
        (3, 4, (0.35, 0.36, 0.35), (1.05, 1.30, 1.05), None),      # lighter by the median, on 2 of 3 seeds only
        (4, 2, (0.30, 0.31, 0.30), (1.10, 1.10, 1.10), None)])     # the fastest's exact twin (leo16); no 4 KiB inner neighbour
    rows += [cell(512, "all-home", s, 3, 2, t, 1.10, at_3s="480/499" if s == 8 else "499/499")
             for s, t in zip(SEEDS, (0.30, 0.31, 0.30))]            # the fastest (leo16 by the code rule)
    # D: a listed cell is missing: no selection, no growth verdict; gossipsub is printed all the same, with its PAST 3 s
    rows += grid(256, "all-home", [
        (4, 16, (0.2, 0.2, 0.2), (0.5, 0.5, 0.5), None),
        (8, 16, (0.15, 0.15, 0.15), (0.7, 0.7, 0.7), None),        # would GROW by time against R = 6
        (6, 16, (0.18, 0.18, 0.18), (0.6, 0.6, 0.6), None)])
    rows += [dict(cell(256, "all-home", s, 0, 16, 0.3, 0.9), protocol="gossipsub", log=f"gs256{s}",
                  at_3s="470/499" if s == 9 else "499/499") for s in SEEDS]
    # E (allowance below 512 KiB: time 10 %, bytes 8 %): the fastest is the base and has no ok neighbour; 4 KiB is
    # lighter than the base on 3 of 3 but by 5 % only (close); 2 KiB is clearly lighter (20 %) and beats 4 KiB by
    # bytes only (15.8 %): the grid grows; a refusal under the group bound on the lighter point
    rows += grid(256, "dcb20", [
        (4, 16, (0.30, 0.30, 0.30), (1.00, 1.00, 1.00), None),     # the base, the fastest
        (4, 4, (0.33, 0.33, 0.33), (0.95, 0.95, 0.95), None)])     # front, close to the base on bytes
    rows += [cell(256, "dcb20", s, 4, 2, 0.35, 0.80, refused_warm="5" if s == 9 else "0") for s in SEEDS]  # the lighter point, marked
    # F: R = 8 whose inner neighbour has seed 7 only; another R = 8 that is short
    rows += grid(128, "all-home", [
        (4, 16, (0.30, 0.30, 0.30), (1.00, 1.00, 1.00), None),     # the base
        (8, 8, (0.20, 0.20, 0.20), (1.50, 1.50, 1.50), None)])     # the fastest
    rows += [cell(128, "all-home", 7, 6, 8, 0.25, 1.3), cell(128, "all-home", 7, 8, 4, 0.19, 1.6)]
    # G: R = 8 beats R = 6 by time and bytes; a setting at both edges with no inner neighbours; a one-chunk lightest
    rows += grid(64, "dcb20", [
        (4, 16, (0.20, 0.20, 0.20), (0.50, 0.50, 0.50), None),     # the base
        (8, 16, (0.10, 0.10, 0.10), (0.40, 0.40, 0.40), None),     # the fastest
        (6, 16, (0.15, 0.15, 0.15), (0.45, 0.45, 0.45), None),
        (8, 2, (0.30, 0.30, 0.30), (0.60, 0.60, 0.60), None),      # R = 8 and 2 KiB, off the front
        (1, 64, (0.50, 0.50, 0.50), (0.30, 0.30, 0.30), None)])    # K = 1: the lighter point, no edge
    # H: NO FRONT; the only setting, the base, failed on seed 8 and is named
    rows += [cell(32, "all-home", s, 4, 16, 0.1, 0.2, passed="False" if s == 8 else "True") for s in SEEDS]
    # I (allowance 6 %, 3 %): the fastest is close to the base (3.61 %) and to its neighbour (2.44 %): OPEN on both;
    # R = 8 faster than R = 6 on 3 of 3 but within the allowance: does not grow
    rows += grid(2048, "dcb20", [
        (2, 16, (0.83, 0.83, 0.83), (3.00, 3.00, 3.00), None),     # the base
        (8, 16, (0.80, 0.80, 0.80), (3.50, 3.50, 3.50), None),     # the fastest
        (6, 16, (0.82, 0.82, 0.82), (3.30, 3.30, 3.30), None)])    # the lighter point (5.71 % lighter), the neighbour
    exp = {r["log"]: (int(r["size_kib"]), r["network"], int(r["seed"])) for r in rows}
    exp["never-ran.log"] = (256, "all-home", 9)
    assert strays(rows, exp) == [] and strays(rows + [cell(32, "dcb20", 8, 4, 16, 0.1, 0.2)], exp) == ["x32dcb208r4u16leo8"]
    # the verdict in exact fractions: a gap of exactly the allowance is not beyond it (floats would say 6.000...05 %)
    Sx = {(n,): {"cells": {x: {"passed": "True", "p99_s": t, "mib": b} for x in ss}}
          for n, t, b, ss in (("a", "0.94", "1.0", SEEDS), ("b", "1.0", "1.0", SEEDS), ("c", "0.9399", "1.0", SEEDS),
                              ("d", "0.47", "1.0", SEEDS), ("e", "0.5", "1.0", SEEDS), ("g", "1.0", "0.97", SEEDS),
                              ("h", "1.0", "0.9699", SEEDS), ("i", "0.1", "0.1", (7, 8)))}

    def vx(p, q, size=512):
        return verdict((p,), (q,), Sx, size)
    assert vx("a", "b")["faster"] is False and vx("a", "b")["f"] == 3 and vx("a", "b")["tg"] == Fraction(6, 100)
    assert vx("c", "b")["faster"] is True and vx("d", "e")["faster"] is False and vx("a", "b", 256)["faster"] is False
    assert vx("b", "c")["slower"] is True and vx("b", "a")["slower"] is False            # antisymmetric, the boundary too
    assert all(vx(p, q)[w] == vx(q, p)[r] for p in "abcdegh" for q in "abcdegh"
               for w, r in (("faster", "slower"), ("lighter", "heavier")))
    assert vx("g", "b")["lighter"] is False and vx("h", "b")["lighter"] is True and vx("g", "b", 256)["lighter"] is False
    assert vx("i", "b")["n"] == 2 and vx("i", "b")["faster"] is False and vx("i", "b")["lighter"] is False   # two seeds

    def cnt(v):
        return (v["f"], v["l"], v["n"]) if v else None

    def gr(p):
        return [(s, ax, i, cnt(v), w) for s, ax, i, v, w in growth(res[p], p[0])]
    info, res = fronts.analyse(rows, list(SEEDS), expect=exp)
    a = select(res[(1024, "all-home")], 1024)
    assert a["fastest"] == k(4, 16) and a["runner"] == k(4, 32) and cnt(a["runner_v"]) == (3, 3, 3), a
    assert not a["runner_v"]["faster"] and not a["runner_v"]["lighter"], a["runner_v"]          # 2.0 % and 1.1 %: close
    assert [s for s, _ in a["rivals"]] == [k(4, 32), k(6, 16), k(3, 32)], a["rivals"]          # R=3 at 16 KiB: clear, 10.7 %
    assert a["lighter"] == k(3, 16) and a["median_only"] is None, a["lighter"]
    assert a["open"] == ["close to its best neighbour R=4 unit=32K leo8"] and a["state"] == "open", a["open"]
    assert a["nb_flag"] == " (the best of 3 ok of 4 neighbours)", a["nb_flag"]
    i = select(res[(2048, "dcb20")], 2048)
    assert i["state"] == "open" and i["open"] == ["close to the base R=2 unit=16K leo8",
                                                  "close to its best neighbour R=6 unit=16K leo8"], i["open"]
    assert i["lighter"] == k(6, 16) and i["by_role"] == [2, 3, 3, 3, 3], i
    assert gr((2048, "dcb20")) == [(k(8, 16), "R", k(6, 16), (3, 0, 3), "does not grow: close")]
    assert list(a["stage3"]) == [k(4, 16), k(3, 16), k(2, 16), k(4, 32), k(2, 16, "unc")], list(a["stage3"])
    assert a["stage3"][k(4, 16)] == ["the fastest", "option: the lighter point's best neighbour"], a["stage3"]
    assert a["stage3"][k(2, 16)] == ["the base", "option: the corner (its coded twin)"], a["stage3"]
    assert a["by_role"] == [2, 3, 4, 4, 5], a["by_role"]
    assert a["corner"][0][0] == k(2, 16, "unc") and a["corner"][0][2] == k(2, 16) and cnt(a["corner"][0][3]) == (3, 3, 3), a["corner"]
    assert a["out_of"] == [k(1, 16), k(4, 8)], a["out_of"]          # failed, and short with a seed-8 cell; seed 7 only is not named
    assert other_edges(res[(1024, "all-home")]) == []
    b = select(res[(1024, "dcb20")], 1024)
    assert b["fastest"] == k(8, 16) and cnt(b["runner_v"]) == (2, 0, 3) and b["lighter"] == k(6, 16), b   # 8.0 % lighter: clear
    assert b["stage3"][k(6, 16)] == ["the lighter point", "the fastest's best neighbour"], b["stage3"]
    assert b["by_role"] == [2, 3, 3, 3, 3] and [s for s, _ in b["rivals"]] == [k(6, 16)], b
    assert b["open"] == ["close to its best neighbour R=6 unit=16K leo8"], b["open"]
    c = select(res[(512, "all-home")], 512)
    assert c["fastest"] == k(3, 2, "leo16") and c["lighter"] is None and c["median_only"] == k(3, 4), c   # not the exact twin
    assert c["runner"] == k(4, 2, "leo16") and cnt(c["runner_v"]) == (0, 0, 3), c
    assert [(s, cnt(v)) for s, v in c["others"]] == [(k(4, 2, "leo16"), (0, 0, 3)), (k(3, 4), (0, 2, 3)), (k(3, 16), (0, 2, 3))], c["others"]
    assert list(c["stage3"]) == [k(3, 2, "leo16"), k(3, 16), k(4, 2, "leo16")] and c["by_role"] == [1, 2, 3, 3, 3], c
    assert c["open"] == ["close to its best neighbour R=4 unit=2K leo16"], c["open"]        # the exact twin
    assert other_edges(res[(512, "all-home")]) == [k(3, 16)]
    d = select(res[(256, "all-home")], 256)
    assert "refused" in d and d["out_of"] == [] and other_edges(res[(256, "all-home")]) == []
    e = select(res[(256, "dcb20")], 256)
    assert e["fastest"] == k(4, 16) and e["lighter"] == k(4, 2) and ((k(4, 16), "best neighbour", None, None) in e["comps"]), e
    assert e["stage3"][k(4, 16)] == ["the fastest", "the base"] and e["by_role"] == [2, 2, 2, 3, 3], e
    assert e["stage3"][k(4, 4)] == ["option: the lighter point's best neighbour"] and e["open"] == [], e   # 5 %: not the lighter point
    assert e["state"] == "not compared" and select(res[(128, "all-home")], 128)["state"] == "not compared", e
    assert other_edges(res[(256, "dcb20")]) == [k(4, 16), k(4, 4)]
    g = select(res[(64, "dcb20")], 64)
    assert g["fastest"] == k(8, 16) and g["lighter"] == k(1, 64) and not g["rivals"] and g["by_role"] == [2, 3, 4, 4, 4], g
    assert g["open"] == [] and g["state"] == "concluded" and g["nb_flag"] == "" and select(res[(128, "all-home")], 128)["open"] == []
    assert other_edges(res[(64, "dcb20")]) == []                     # the one-chunk setting is no edge
    assert gr((1024, "dcb20")) == [(k(8, 16), "R", k(6, 16), (2, 0, 3), "does not grow: close"),
                                   (k(8, 32), "R", k(6, 32), (3, 0, 3), "does not grow: not on the three-seed front")]
    assert gr((512, "all-home")) == [(k(3, 2, "leo16"), "chunk size", k(3, 4), (3, 1, 3), "GROWS by time"),
                                     (k(4, 2, "leo16"), "chunk size", None, None, "NOT TESTED: no inner neighbour among the cells")]
    assert gr((256, "dcb20")) == [(k(4, 2), "chunk size", k(4, 4), (0, 3, 3), "GROWS by bytes")]
    assert gr((256, "all-home")) == [(k(8, 16), "-", None, None, "NOT TESTED: the point has no selection (1 listed cells missing)")]
    assert gr((128, "all-home")) == [(k(8, 4), "-", None, None, "NOT TESTED: it is short (1 of 3 seeds)"),
                                     (k(8, 8), "R", k(6, 8), None, "NOT TESTED: the inner neighbour is short (1 of 3 seeds)")]
    assert gr((64, "dcb20")) == [(k(8, 16), "R", k(6, 16), (3, 3, 3), "GROWS by time and bytes"),
                                 (k(8, 2), "R", None, None, "NOT TESTED: no inner neighbour among the cells"),
                                 (k(8, 2), "chunk size", None, None, "NOT TESTED: no inner neighbour among the cells")]
    h = select(res[(32, "all-home")], 32)
    assert h["refused"].startswith("NO FRONT") and h["out_of"] == [k(4, 16)], h
    buf, out_all = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert report(res, out_all) is False
    text = buf.getvalue()
    assert out_all.getvalue() == "" and "CSV NOT WRITTEN: 2 points without a selection" in text
    complete = {p: v for p, v in res.items() if p not in ((256, "all-home"), (32, "all-home"))}

    def csv_rows(roles):
        out_sel, said = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(said):
            assert report(complete, out_sel, [ROLE_NAMES[r] for r in roles]) is True
        return list(csv.DictReader(io.StringIO(out_sel.getvalue()))), said.getvalue()
    out, said = csv_rows(list(ROLE_NAMES))
    assert len(out) == 5 + 3 + 3 + 3 + 2 + 4 + 3 and "host A: 10 settings, host B: 13 settings; 23 in all" in said, (len(out), said)
    sub, said = csv_rows(["selected", "base", "fastest-neighbour"])               # stage 3's set, in ROLES' order
    assert len(sub) == 4 + 3 + 3 + 2 + 2 + 4 + 3 and "host A: 9 settings, host B: 12 settings; 21 in all" in said, (len(sub), said)
    sub, said = csv_rows(["selected", "corner"])                                  # a choice out of ROLES' order
    assert len(sub) == 4 + 2 + 1 + 2 + 2 + 2 + 2 and "host A: 7 settings, host B: 8 settings; 15 in all" in said, (len(sub), said)
    assert {r["roles"] for r in sub if r["size_kib"] == "1024" and r["network"] == "all-home"} == {
        "the fastest; option: the lighter point's best neighbour", "the lighter point", "the base; option: the corner (its coded twin)",
        "option: the corner"}
    assert {r["past_3s_cells"] for r in out if r["unit_kib"] == "2" and r["size_kib"] == "512" and r["push_r"] == "3"} == {"1"}
    assert {r["refused_warm_group"] for r in out if r["unit_kib"] == "2" and r["size_kib"] == "256"} == {"5"}
    for want in ("against the runner-up R=4 unit=32K leo8: faster on 3 of 3 (median +1.96 %), lighter on 3 of 3 (median +1.10 %): close",
                 "close rivals, the fastest not clearly faster than 3 other ok grid settings: R=4 unit=32K leo8",
                 "R=3 unit=32K leo8 (faster on 2 of 3 (median +13.79 %), lighter on 3 of 3 (median +5.26 %): clearly lighter)",
                 "clearly faster than every other ok grid setting",
                 "the lighter point: NONE clearly lighter than the fastest",
                 "lighter by the median only (not selected): R=3 unit=4K leo8",
                 "the fastest against the base R=2 unit=16K leo8: faster on 3 of 3 (median +18.03 %), lighter on 0 of 3 (median -38.46 %): "
                 "clearly faster and clearly heavier; on seeds 8,9 (2): faster on 2, lighter on 0",
                 "the fastest against the best neighbour (the best of 3 ok of 4 neighbours) R=4 unit=32K leo8",
                 "the fastest: its neighbour R=4 unit=8K leo8 is short (2 of 3 seeds): no comparison",
                 "the lighter point against the other ok neighbour R=3 unit=32K leo8: faster on 2 of 3 (median +1.72 %), lighter on 3 of 3 "
                 "(median +21.05 %): clearly lighter; on seeds 8,9 (2): faster on 2, lighter on 2",
                 "the fastest is the base", "the fastest: NO OK NEIGHBOUR among the cells",
                 "OPEN (stage 3's ten seeds decide): the fastest is close to its best neighbour R=4 unit=32K leo8 "
                 "(the best of 3 ok of 4 neighbours)",
                 "OPEN (stage 3's ten seeds decide): the fastest is close to the base R=2 unit=16K leo8; close to its best "
                 "neighbour R=6 unit=16K leo8",
                 "NOT COMPARED: the fastest has no ok neighbour among the cells, and stage 3's set holds none",
                 "concluded: the fastest is clearly faster than its best neighbour R=6 unit=16K leo8 and the base R=4 unit=16K leo8",
                 "noise allowance here: time 10 %, bytes 8 %", "noise allowance here: time 6 %, bytes 3 %",
                 "R=3 unit=2K leo16 (0.3000 s, 1.1000 MiB, 3.10 copies) PAST 3 s in 1 cells (worst warm payload 480 of 499)",
                 "R=4 unit=2K leo8 (0.3500 s, 0.8000 MiB, 4.51 copies) REFUSED UNDER THE GROUP BOUND: 5 of 3005 warm announcements in 1 cells",
                 "R=4 unit=2K leo8 REFUSED UNDER THE GROUP BOUND: 5 of 3005 warm announcements in 1 cells (the lighter point)",
                 "gossipsub, the whole message: 0.3000 s, 5.07 copies PAST 3 s in 1 cells (worst warm payload 470 of 499)",
                 "NO SELECTION: MISSING: 1 listed cells",
                 "against its coded twin R=2 unit=16K leo8: faster on 3 of 3 (median +34.43 %), lighter on 3 of 3 (median +23.08 %): "
                 "clearly faster and clearly lighter",
                 "not ok, out of the ranking: R=1 unit=16K leo8 [failed, 2 of 3 seeds, failed on [8]]",
                 "not ok, out of the ranking: R=4 unit=8K leo8 [short, 2 of 3 seeds]",
                 "growth, 256 KiB dcb20: R=4 unit=2K leo8 against its inner neighbour R=4 unit=4K leo8 (chunk size): faster on 0 of 3 "
                 "(median -6.06 %), lighter on 3 of 3 (median +15.79 %): clearly lighter: GROWS by bytes",
                 "open (stage 3's ten seeds decide): 4: 512 KiB all-home; 1024 KiB all-home; 1024 KiB dcb20; 2048 KiB dcb20\n"
                 "not compared (no ok neighbour): 2: 128 KiB all-home; 256 KiB dcb20\nconcluded: 1: 64 KiB dcb20",
                 "growth, 128 KiB all-home: R=8 unit=8K leo8 rfast=8 (R): NOT TESTED: the inner neighbour is short (1 of 3 seeds): R=6 unit=8K leo8",
                 "growth, 256 KiB all-home: R=8 unit=16K leo8 rfast=8: NOT TESTED: the point has no selection (1 listed cells missing)",
                 "on another edge, outside the author's words (R = 8 and 2 KiB): 512 KiB all-home: R=3 unit=16K leo8",
                 "7 points selected, 2 without a selection: 32 KiB all-home; 256 KiB all-home (THE TOTALS BELOW ARE PARTIAL)",
                 "not ok, out of the ranking: R=4 unit=16K leo8 [failed, 3 of 3 seeds, failed on [8]]\n   NO SELECTION: NO FRONT",
                 "stage 3's settings, host B, cumulative by role (selected / the base / the fastest's best neighbour / "
                 "option: the lighter point's best neighbour / option: the corner): 8 -> 11 -> 12 -> 13 -> 13",
                 "stage 3's settings, host A, cumulative by role (selected / the base / the fastest's best neighbour / "
                 "option: the lighter point's best neighbour / option: the corner): 5 -> 7 -> 9 -> 9 -> 10",
                 "the grid grows at: 64 KiB dcb20: R=8 unit=16K leo8 rfast=8 (R, by time and bytes); 256 KiB dcb20: R=4 unit=2K leo8 "
                 "(chunk size, by bytes); 512 KiB all-home: R=3 unit=2K leo16 (chunk size, by time)",
                 "not tested: 64 KiB dcb20: R=8 unit=2K leo8 rfast=8 (R); 64 KiB dcb20: R=8 unit=2K leo8 rfast=8 (chunk size); "
                 "128 KiB all-home: R=8 unit=4K leo8 rfast=8; 128 KiB all-home: R=8 unit=8K leo8 rfast=8 (R); "
                 "256 KiB all-home: R=8 unit=16K leo8 rfast=8; 512 KiB all-home: R=4 unit=2K leo16 (chunk size)"):
        assert want in text, (want, text)
    # the input's order does not change the selection
    rev = fronts.analyse(list(reversed(rows)), list(SEEDS), expect=exp)[1]
    assert all(select(rev[p], p[0]) == select(res[p], p[0]) and growth(rev[p], p[0]) == growth(res[p], p[0]) for p in res)
    print("selftest: the verdicts (clear wins and losses, antisymmetric, the exact boundary on time and bytes, two seeds), "
          "the fastest, the runner-up and its close rivals, the clearly lighter point or none, the median-only point past an "
          "exact twin, comparisons, neighbours and their flag, the point's state (open by the base and by the neighbour, not "
          "compared, concluded), stage 3 by role with the corner's twin, growth on a clear win (time, bytes, both, close, off the "
          "front, not tested, at a refused point), other edges and the one-chunk floor, marks, gossipsub at a refused point, "
          "strays, the CSV withheld and written, the input's order: ok")


def main():
    a = sys.argv[1:]
    if a == ["--selftest"]:
        return selftest()
    files, expect, out_csv, roles = [], [], None, None
    while a:
        x = a.pop(0)
        if x == "--expect":
            expect.append(a.pop(0))
        elif x == "--csv":
            out_csv = a.pop(0)
        elif x == "--roles":
            names = a.pop(0).split(",")
            if not names or any(r not in ROLE_NAMES for r in names) or len(set(names)) != len(names):
                sys.exit(f"--roles takes some of {', '.join(ROLE_NAMES)}, each once")
            roles = [ROLE_NAMES[r] for r in names]
        elif x.startswith("--"):
            sys.exit(__doc__)
        else:
            files.append(x)
    if not files or not expect:
        sys.exit(__doc__)
    if out_csv and roles is None:
        sys.exit("--csv needs --roles: stage 3's list holds only the roles chosen")
    rows, exp = fronts.load(files), fronts.load_expect(expect)
    bad = strays(rows, exp)
    if bad:
        sys.exit(f"{len(bad)} rows of seeds {list(SEEDS)} are no cell of the lists given: " + "; ".join(bad[:5]))
    info, res = fronts.analyse(rows, list(SEEDS), 500, exp)
    print(f"seeds {list(SEEDS)} (stage 1 carried on {list(SELECTED_ON)}); {info['ignored']} rows of other seeds not used; "
          f"SEACAST binary md5 {info['md5'] or '-'}; \"clearly\" faster or lighter: on 3 of 3 seeds, paired, and beyond "
          "the noise allowance")
    if not report(res, out_csv, roles):
        sys.exit(1)


if __name__ == "__main__":
    main()
