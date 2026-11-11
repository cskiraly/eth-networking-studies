#!/usr/bin/env python3
"""The fold-timing comparison's tables: the aggregation interval, the prover and the signature size.

    python3 w_tables.py compare OUT LABEL_A LABEL_B DIR_A[,DIR_A...] DIR_B[,DIR_B...]
    python3 w_tables.py control OUT DIR_871 DIR_303 DIR_ARM_A DIR_ARM_B DIR_ARM_D

Each directory holds `bench.mainnet --json` records, one run per file (`*.jsonl`), as the commands
in configs/ write them. A run is identified by its own record: the design by its preset, then
the rate, privacy share, leanSTARK factor and seed.

compare: two sets of runs cell by cell, paired by seed. A is the reference and B the variant.
For each set, the class (held: every seed includes at least 95% of the transactions that arrived;
collapsed: every seed below 60%; marginal otherwise) and the worst seed's inclusion. Then the
means of CPU and egress (uplink) utilisation over the load window for both sets, mean inclusion
delay in seconds for both, the paired delay difference (mean over seeds of B minus A), and B's
budget stops in the peer and leaf loops (shares of selection decisions), the share of the late
cohort included within 24 s, and the mean recursive proof in KiB.

control: what binds the 1,000 ms tick at the 871 ms anchor. Arm A has no proving budget; arm B
the 303 ms anchor with the budget that keeps 871 ms's fold widths; arm D ten times the uplink.
Each arm beside the 871 ms runs, and arm B also beside the 303 ms runs with the whole budget, at
a fifth private, 10, 20 and 45 tx/s, seeds 100-103: inclusion per seed, the class, and the means
of CPU, egress, peer- and leaf-loop stops, root claim (fold width) and delay.

Both write OUT.txt (the table) and OUT.csv (one row a cell).
"""
import csv
import glob
import json
import os
import statistics
import sys

DESIGNS = {"eip_faithful+aggregation_interval=1000": "tick1000",
           "eip_faithful+aggregation_interval=2000": "tick2000",
           "eip_faithful+aggregation_trigger=when_ready": "tickless"}
ORDER = ("tick1000", "tick2000", "tickless")
RATES = (10, 20, 30, 45, 60)
SHARES = (0.0, 0.2, 0.5)


def point(record):
    """One run's numbers."""
    m = record["metrics"]
    decisions = m["selection_decisions"]["total"]
    stops = decisions["budget_stops"]
    late = [o for o in m["fixed_age_outcomes"] if o["age_ms"] == 24000.0][0]
    return {
        "frac": m["included_txs"] / m["arrived_txs"],
        "cpu": m["load_utilisation"]["cpu_utilisation"],
        "egress": m["load_utilisation"]["egress_utilisation"],
        "delay_s": m["delay_mean_slots"] * m["slot_length"] / 1000,
        "peer": (stops.get("peer_aggregates", 0) + stops.get("both", 0)) / decisions["decisions"],
        "leaf": stops.get("fee_leaves", 0) / decisions["decisions"],
        "late24": late["late"]["included_fraction"],
        "width": m["plan_root_claim_mean"],
        "kib": m.get("proof_kib_mean", 0.0),
    }


def load(directories):
    """Runs by (design, factor, tps, share, seed)."""
    runs = {}
    for directory in directories:
        for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
            with open(path) as handle:
                record = json.loads(handle.readline())
            w = record["workload"]
            key = (DESIGNS[w["preset"]], str(int(w["leanstark_factor"])), int(w["tps"]),
                   float(w["privacy_share"]), int(record["seed"]))
            if key in runs:
                raise SystemExit(f"{key} appears twice: {path}")
            runs[key] = point(record)
    return runs


def classify(points):
    if all(p["frac"] >= 0.95 for p in points):
        return "held"
    if all(p["frac"] < 0.60 for p in points):
        return "collapsed"
    return "marginal"


def write_csv(out, rows):
    with open(out + ".csv", "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: f"{v:.4f}" if isinstance(v, float) else v for k, v in r.items()})


def compare(out, label_a, label_b, dirs_a, dirs_b):
    a, b = load(dirs_a.split(",")), load(dirs_b.split(","))
    rows = []
    for design in ORDER:
        for share in SHARES:
            for factor in ("1", "2"):
                for tps in RATES:
                    seeds = sorted(k[4] for k in b if k[:4] == (design, factor, tps, share) and k in a)
                    if not seeds:
                        continue
                    pa = [a[(design, factor, tps, share, s)] for s in seeds]
                    pb = [b[(design, factor, tps, share, s)] for s in seeds]
                    mean = lambda points, key: statistics.fmean(p[key] for p in points)
                    rows.append({
                        "design": design, "share": share, "tps": tps, "factor": factor, "seeds": len(seeds),
                        f"class_{label_a}": classify(pa), f"worst_{label_a}": min(p["frac"] for p in pa),
                        f"class_{label_b}": classify(pb), f"worst_{label_b}": min(p["frac"] for p in pb),
                        f"cpu_{label_a}": mean(pa, "cpu"), f"cpu_{label_b}": mean(pb, "cpu"),
                        f"egress_{label_a}": mean(pa, "egress"), f"egress_{label_b}": mean(pb, "egress"),
                        f"delay_{label_a}": mean(pa, "delay_s"), f"delay_{label_b}": mean(pb, "delay_s"),
                        "delay_paired_diff": statistics.fmean(y["delay_s"] - x["delay_s"] for x, y in zip(pa, pb)),
                        f"peer_stops_{label_b}": mean(pb, "peer"), f"leaf_stops_{label_b}": mean(pb, "leaf"),
                        f"late24_{label_b}": mean(pb, "late24"), f"proof_kib_{label_b}": mean(pb, "kib"),
                    })
    write_csv(out, rows)
    with open(out + ".txt", "w") as text:
        text.write(f"A = {label_a}, B = {label_b}\n\n")
        text.write(f"{'design':10} {'share':>5} {'tps':>3} f  n  {'A':9} {'A worst':>7}  {'B':9} {'B worst':>7}  "
                   f"{'cpu A>B':>9} {'egress A>B':>10}  {'delay A>B':>11} {'paired':>6}  {'peer':>4} {'leaf':>4} "
                   f"{'late24':>6} {'KiB':>5}\n")
        last = None
        for r in rows:
            if last and (r["design"], r["share"]) != last:
                text.write("\n")
            last = (r["design"], r["share"])
            text.write(
                f"{r['design']:10} {r['share']:>5} {r['tps']:>3} {r['factor']} {r['seeds']:>2}  "
                f"{r[f'class_{label_a}']:9} {r[f'worst_{label_a}']:>7.3f}  {r[f'class_{label_b}']:9} "
                f"{r[f'worst_{label_b}']:>7.3f}  {r[f'cpu_{label_a}']:.2f}>{r[f'cpu_{label_b}']:.2f} "
                f"{r[f'egress_{label_a}']:.2f}>{r[f'egress_{label_b}']:.2f}  {r[f'delay_{label_a}']:>5.1f}>{r[f'delay_{label_b}']:<5.1f} "
                f"{r['delay_paired_diff']:>+6.2f}  {r[f'peer_stops_{label_b}']:>4.2f} {r[f'leaf_stops_{label_b}']:>4.2f} "
                f"{r[f'late24_{label_b}']:>6.2f} {r[f'proof_kib_{label_b}']:>5.1f}\n")
    print(f"{len(rows)} cells -> {out}.txt, {out}.csv")


def control(out, dir_871, dir_303, dir_a, dir_b, dir_d):
    def runs(directory):
        return {(k[2], k[4]): v for k, v in load([directory]).items()
                if k[0] == "tick1000" and k[1] == "1" and k[3] == 0.2}

    sets = {"871": runs(dir_871), "303": runs(dir_303), "A": runs(dir_a), "B": runs(dir_b), "D": runs(dir_d)}
    seeds = (100, 101, 102, 103)
    rows, lines = [], []
    for arm, refs in (("B", ("871", "303")), ("D", ("871",)), ("A", ("871",))):
        lines.append(f"arm {arm} against {', '.join(refs)}")
        lines.append(f"{'tps':>3} {'set':4} {'class':9} {'seed 100':>8} {'101':>6} {'102':>6} {'103':>6}  "
                     f"{'cpu':>4} {'egress':>6} {'peer':>4} {'leaf':>4} {'width':>6} {'delay':>6}")
        for tps in (10, 20, 45):
            for name in (arm,) + refs:
                pts = [sets[name][(tps, s)] for s in seeds]
                mean = lambda k: statistics.fmean(p[k] for p in pts)
                rec = {"arm": arm, "tps": tps, "set": name, "class": classify(pts),
                       **{f"incl_{s}": p["frac"] for s, p in zip(seeds, pts)},
                       "cpu": mean("cpu"), "egress": mean("egress"), "peer_stops": mean("peer"),
                       "leaf_stops": mean("leaf"), "root_claim": mean("width"), "delay_s": mean("delay_s")}
                rows.append(rec)
                lines.append(f"{tps:>3} {name:4} {rec['class']:9} "
                             + " ".join(f"{p['frac']:>{8 if i == 0 else 6}.3f}" for i, p in enumerate(pts))
                             + f"  {rec['cpu']:>4.2f} {rec['egress']:>6.2f} {rec['peer_stops']:>4.2f} "
                             f"{rec['leaf_stops']:>4.2f} {rec['root_claim']:>6.1f} {rec['delay_s']:>6.1f}")
            lines.append("")
    with open(out + ".txt", "w") as text:
        text.write("\n".join(lines) + "\n")
    write_csv(out, rows)
    print(f"{len(rows)} rows -> {out}.txt, {out}.csv")


if __name__ == "__main__":
    command, args = sys.argv[1], sys.argv[2:]
    {"compare": compare, "control": control}[command](*args)
