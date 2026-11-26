#!/usr/bin/env python3
"""Stage 3's lists, from stage 2's selection.

    python3 make_lists.py        writes s3-small-<machine>.txt, s3-large-<machine>.txt and known-<machine>.txt
                                 beside this script

The settings: ../stage2/stage3-<machine>.csv (selection.py --roles selected,base,fastest-neighbour), at seeds
10 to 16, with gossipsub's whole message at 32 and 64 KiB. Each SEACAST line is the line its setting ran with
in stage 2 (../grow/s2-*-<machine>.txt,
the seed-8 line, which must exist and equal carry_cost.cell_line's for the setting), with only the seed changed;
so every knob is what ran. Lines are run1.sh's sixteen fields. s3-small: 32 to 512 KiB, gossipsub at 32 and 64
KiB; s3-large: 1 to 4 MiB; seed-major, sizes ascending, the CSV's order within a size, gossipsub last at its
size.

known-<machine>.txt, the repeat known answer: stage 2's base cell at 32 KiB, seed 8, and gossipsub's at 32 KiB,
seed 8, run again; their rows must fall within the repeat noise (time 10 %, bytes 8 % below 512 KiB) of stage
2's. It catches a changed binary or host between the stages; it is read apart and never enters the fronts.

The record publishes this script for GOSSIPSUB_SIZES, which best.py imports; main() also needs stage 2's
launch lists (s2-*.txt), which are not published.
"""
import csv
import os

import fronts
import carry_cost

HERE = os.path.dirname(os.path.abspath(__file__))

NET = {"A": "home", "B": "dcb20"}
SEEDS = range(10, 17)
GOSSIPSUB_SIZES = (32, 64)


def main():
    for h, net in NET.items():
        ran = {}
        for lane in ("small", "large"):
            for ln in open(os.path.join(HERE, "..", "grow", f"s2-{lane}-{h}.txt")):
                f = ln.split()
                if f[0] == "seacast" and f[3] == "8":
                    ran[" ".join(f)] = f
        rows = list(csv.DictReader(open(os.path.join(HERE, "..", "stage2", f"stage3-{h}.csv"))))
        settings = []   # (size, fields of the seed-8 line)
        for r in rows:
            size, s = int(r["size_kib"]), (r["push_r"], r["unit_kib"], r["code"])
            assert r["host"] == h and r["status"] == "ok", r
            assert (r["rsx"], r["ask_ms"], r["target_ms"], r["proj"], r["fault"], r["loss"], r["offer_bound"]) == \
                ("1", "200", "20", "2", "", "", "group") and r["r_fast"] == fronts.rule_rfast(int(r["push_r"])), r
            line = carry_cost.cell_line(net, size, 8, s)
            assert line in ran, ("not a line stage 2 ran", line)
            settings.append((size, ran[line]))
        assert len({(z, " ".join(f)) for z, f in settings}) == len(settings) == len(rows)
        out = {"small": [], "large": []}
        for seed in SEEDS:
            for size in sorted({z for z, _ in settings}):
                lane = "small" if size <= 512 else "large"
                out[lane] += [" ".join(f[:3] + [str(seed)] + f[4:]) for z, f in settings if z == size]
                if size in GOSSIPSUB_SIZES:
                    out[lane].append(carry_cost.gossipsub_line(net, size, seed))
        base32 = [r for r in rows if int(r["size_kib"]) == 32 and "the base" in r["roles"]]
        assert len(base32) == 1, base32
        known = [carry_cost.cell_line(net, 32, 8, (base32[0]["push_r"], base32[0]["unit_kib"], base32[0]["code"])),
                 carry_cost.gossipsub_line(net, 32, 8)]
        assert known[0] in ran
        n_g = len(SEEDS) * len(GOSSIPSUB_SIZES)
        assert len(out["small"]) + len(out["large"]) == len(rows) * len(SEEDS) + n_g
        for name, v in (("s3-small", out["small"]), ("s3-large", out["large"]), ("known", known)):
            assert len(v) == len(set(v)), name
            with open(os.path.join(HERE, f"{name}-{h}.txt"), "w") as fh:
                fh.write("\n".join(v) + "\n")
        print(f"{h} ({net}): {len(rows)} settings x {len(SEEDS)} seeds + {n_g} gossipsub: s3-small {len(out['small'])}, "
              f"s3-large {len(out['large'])}; known {len(known)}")


if __name__ == "__main__":
    main()
