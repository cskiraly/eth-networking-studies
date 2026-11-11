#!/usr/bin/env python3
"""The figures of the post and of First Questions version 11, from the runs.

    python3 -I figures.py extract SERIES DIR...   # the runs -> data/*.csv
    python3 -I figures.py draw                    # data/*.csv -> *.svg

Each DIR holds the runs of one series, a `configs/<series>.tsv` of the record's interval,
cycle-prices or leanvm part: a run is `<cell>.jsonl`, what the cell's command printed. A reader
reads every run in DIR whose name fits the series. The series, and the data files they make:

    capacity EVERY_NODE NO_FLOOD ONE_BUILDER    capacity-n.csv
                                                (capacity-every-node, -no-flood, -one-builder)
    scaling SCALING THROUGHPUT INTERVAL_CYCLES  scaling-3000.csv, throughput.csv
    leaf-multiplicity DIR                       scaling-n.csv
    partial-aggregation DIR                     partial-aggregation.csv
    interval-cycles DIR                         interval-cycles.csv
    privacy-1000 DIR                            privacy-frontier-1000.csv, with interval-cycles.csv
    privacy-40 TICK TICKLESS                    privacy-frontier.csv (privacy-40, -40-tickless)
    interval INTERVAL_303MS INTERVAL_871MS      interval.csv, and latency.csv from the first
    designs TABLE                               designs.csv, from the transport part's
                                                designs-random-proposer.md
    leanvm-16-threads RESULTS                   leanvm-16-threads.csv
    leanvm-threads RESULTS                      leanvm-threads.csv

`interval` takes each run's settings from its own record; the others read them from the
cell's name, as its config names it. Rerun on the stored runs, every file in
data/ comes out byte for byte, and `draw` redraws every figure here byte for byte from them.
"""

import csv
import json
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIGURES = HERE

# ---------------------------------------------------------------- extract


def _runs(directory, pattern):
    """(match, path) for each run in a directory whose file name fits the pattern, by name."""
    for name in sorted(os.listdir(directory)):
        m = pattern.match(name)
        if m:
            yield m, os.path.join(directory, name)


def _record(path):
    """A run's record: the first line of its file."""
    with open(path) as handle:
        return json.loads(handle.readline())


def _classify(fracs):
    """A cell's class over its seeds: held if every seed included at least 95% of its
    transactions, collapsed if every seed included less than 60%."""
    if all(f >= 0.95 for f in fracs):
        return "held"
    if all(f < 0.60 for f in fracs):
        return "collapsed"
    return "marginal"


def _capacity(classes):
    """Highest privacy rate held, at 30 tx/s, with every lower one held; and whether a higher
    one failed."""
    capacity, bound = 0.0, False
    for share in sorted(classes):
        if share == 0.0:
            continue
        if classes[share] != "held":
            bound = True
            break
        capacity = 30 * share
    return capacity, bound


# The fold timings by their presets and proving budget, as the post names them.
INTERVAL_DESIGNS = {("eip_faithful+aggregation_interval=1000", 1000.0): "ticked-b1000",
                    ("eip_faithful+aggregation_interval=2000", 2000.0): "ticked2000-b2000",
                    ("eip_faithful+aggregation_trigger=when_ready", 2000.0): "tickless-b2000"}


def _interval_cells(directories, pick):
    """{(design, share, tps, factor): {seed: pick(metrics)}} over the fold-timing runs on
    calibration v2, each run's settings from its own record. A run's metrics line is about
    5 MB, so only what pick returns is kept."""
    cells = {}
    for directory in directories:
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".jsonl"):
                continue
            record = _record(os.path.join(directory, name))
            w = record["workload"]
            design = INTERVAL_DESIGNS[(w["presets"], float(w["proving_budget"]))]
            seeds = cells.setdefault((design, float(w["privacy_share"]), int(w["tps"]),
                                      int(w["leanstark_factor"])), {})
            if int(record["seed"]) in seeds:
                sys.exit(f"{directory}/{name}: seed {record['seed']} twice")
            seeds[int(record["seed"])] = pick(record["metrics"])
    return {key: dict(sorted(seeds.items())) for key, seeds in cells.items()}


def extract_interval(dirs_303, dirs_871):
    """The fold timings on calibration v2, at both anchors (the ms of a 2-to-1 fold): each
    cell's class over its seeds, its worst and best seed's share included, and its mean CPU
    and uplink use over the load window."""
    rows = []
    for anchor, directories in ((303, dirs_303), (871, dirs_871)):
        cells = _interval_cells(directories, lambda m: (
            m["included_txs"] / m["arrived_txs"], m["load_utilisation"]["cpu_utilisation"],
            m["load_utilisation"]["egress_utilisation"]))
        for (design, share, tps, factor), seeds in sorted(cells.items()):
            runs = list(seeds.values())
            fracs = [r[0] for r in runs]
            rows.append(dict(anchor_ms=anchor, design=design, share=share, tps=tps,
                             factor=factor, seeds=len(runs), cls=_classify(fracs),
                             included_min=round(min(fracs), 4), included_max=round(max(fracs), 4),
                             cpu=round(statistics.fmean(r[1] for r in runs), 3),
                             egress=round(statistics.fmean(r[2] for r in runs), 3)))
    write("interval.csv", rows)


def extract_latency(dirs_303):
    """Inclusion latency over the fold timings at 1,000 nodes on the fast prover, with one
    nested proof per privacy witness."""
    def pick(m):
        ages = {o["age_ms"]: o["all"] for o in m["fixed_age_outcomes"]}
        slot = m["slot_length"] / 1000
        return (slot * m["delay_mean_slots"], slot * m["delay_p95_slots"],
                ages[12000.0]["included_fraction"], ages[24000.0]["included_fraction"])
    rows = []
    for (design, share, tps, factor), seeds in sorted(_interval_cells(dirs_303, pick).items()):
        if factor != 1:
            continue
        runs = list(seeds.values())
        rows.append(dict(design=design, share=share, tps=tps, seeds=len(runs),
                         delay_mean_s=round(statistics.fmean(r[0] for r in runs), 3),
                         delay_p95_s=round(statistics.fmean(r[1] for r in runs), 3),
                         within_12s=round(statistics.fmean(r[2] for r in runs), 4),
                         within_24s=round(statistics.fmean(r[3] for r in runs), 4)))
    write("latency.csv", rows)


# The transport readers' capacity table: per design, privacy tx/s held on top of 15 tx/s of
# signatures, seeds 100-103, with a random proposer each slot wherever one was run. One
# builder's columns have the builder propose, as it does by construction.
TRANSPORT_COLUMNS = [("every", 100), ("every", 1000), ("builder", 100), ("builder", 1000),
                     ("quarter", 100), ("quarter", 1000)]


def _transport_tables(path):
    """{(block, design, participation, nodes): [(value, at_top) for seeds 100-103]}."""
    cells, block = {}, None
    for line in open(path):
        if line.startswith("### ") and not line.startswith("### Capacity"):
            block = None
        elif line.startswith("**six-object block**"):
            block = 6
        elif line.startswith(("**500-object block**", "**501-object block**")):
            block = 501   # block_budget 500 counts folds: 501 objects
        elif block and re.match(r"^\| [1-5] ", line):
            fields = [f.strip() for f in line.strip().strip("|").split("|")]
            design = int(fields[0].split()[0])
            for (participation, nodes), field in zip(TRANSPORT_COLUMNS, fields[1:]):
                values = [v.strip() for v in field.split("/")]
                values = values * 4 if len(values) == 1 else values
                assert len(values) == 4, (path, line)
                cells[(block, design, participation, nodes)] = [
                    (int(v.lstrip("≥")), v.startswith("≥")) for v in values]
    return cells


def extract_designs(table):
    """The five designs' capacities, privacy tx/s held on top of 15 signature tx/s."""
    cells = _transport_tables(table)
    rows = []
    for (block, design, participation, nodes), seeds in sorted(cells.items()):
        for seed, (value, at_top) in zip(range(100, 104), seeds):
            rows.append(dict(block=block, design=design, participation=participation,
                             nodes=nodes, seed=seed, capacity=value, at_top=int(at_top)))
    write("designs.csv", rows)


LEAF = re.compile(r"^leaf-multiplicity-(tick1000|tickless2000)-n(\d+)-seed(\d+)\.jsonl$")


def _pct(value, spec):
    """A share as a table prints it, read back: format(0.1234, '6.1%') -> 12.3."""
    return float(format(value, spec).strip().rstrip("%"))


def extract_leaf_multiplicity(directory):
    """Leaf multiplicity against N: per design and node count, how many nodes fold each
    signature and each privacy witness into a leaf, the repeat share of proving, CPU,
    inclusion and delay, means over seeds, at a table's precision."""
    cells = {}
    for m, path in _runs(directory, LEAF):
        with open(path) as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                metrics, folds = record["metrics"], record["metrics"]["leaf_folds"]
                cells.setdefault((m.group(1), record["workload"]["nodes"]), []).append(dict(
                    pq=folds["by_kind"]["pq"]["multiplicity"]["mean"],
                    priv=folds["by_kind"]["privacy"]["multiplicity"]["mean"],
                    repeat=folds["total"]["repeat_service_share"],
                    cpu=metrics["cpu_utilisation"],
                    incl=metrics["included"] / metrics["arrived"], delay=metrics["delay"]))
    rows = []
    for (design, nodes), runs in sorted(cells.items()):
        mean = lambda k: statistics.fmean(r[k] for r in runs)
        rows.append(dict(design=design, nodes=nodes,
                         sig_folders=float(format(mean("pq"), "5.1f")),
                         privacy_folders=float(format(mean("priv"), "5.1f")),
                         repeat_share=round(_pct(mean("repeat"), "6.1%") / 100, 4),
                         cpu=int(_pct(mean("cpu"), "4.0%")) / 100,
                         included=_pct(mean("incl"), "5.1%") / 100,
                         delay_slots=float(format(mean("delay"), "5.2f")), seeds=len(runs)))
    write("scaling-n.csv", rows)


PRIVACY_40 = re.compile(r"^privacy-40-(tick|tickless)-a(\d+)-f([\d.]+)-v9\.195-tps30-s([\d.]+)"
                        r"-seed(\d+)\.jsonl$")


def extract_privacy_40(tick, tickless):
    """Privacy capacity against the prover at 40 nodes and 30 tx/s: the highest privacy rate
    held with every lower one held, for the EIP's tick and tickless, by anchor and leanSTARK
    factor, over 4 seeds."""
    designs = {"tick": "eip_tick", "tickless": "tickless"}
    cells = {}
    for directory in (tick, tickless):
        for m, path in _runs(directory, PRIVACY_40):
            if m.group(3) not in ("1", "2"):
                continue
            metrics = _record(path)["metrics"]
            key = (designs[m.group(1)], int(m.group(2)), int(m.group(3)))
            cells.setdefault(key, {}).setdefault(float(m.group(4)), []).append(
                metrics["included_txs"] / metrics["arrived_txs"])
    order = {d: i for i, d in enumerate(("eip_tick", "tickless"))}
    rows = []
    for (design, anchor, factor), shares in sorted(cells.items(),
                                                   key=lambda kv: (order[kv[0][0]],) + kv[0][1:]):
        capacity, bound = _capacity({share: _classify(fracs) for share, fracs in shares.items()})
        rows.append(dict(design=design, anchor_ms=anchor, factor=factor, capacity=capacity,
                         bound=int(bound)))
    write("privacy-frontier.csv", rows)


# Interval-cycles: the fold-timing comparison priced by leanVM 990b935's cycle counts.
CYCLES = re.compile(r"^interval-cycles-(tick1000|tick2000|tickless)-f(\d)-tps(\d+)-s([\d.]+)"
                    r"-seed(\d+)\.jsonl$")
CYCLES_DESIGNS = {"tick1000": "ticked-b1000", "tick2000": "ticked2000-b2000",
                  "tickless": "tickless-b2000"}


def _cycles_point(record):
    m = record["metrics"]
    total = m["selection_decisions"]["total"]
    stops = total["budget_stops"]
    return dict(frac=m["included_txs"] / m["arrived_txs"], included=m["included_txs"],
                cpu=m["load_utilisation"]["cpu_utilisation"],
                late24=[o for o in m["fixed_age_outcomes"]
                        if o["age_ms"] == 24000.0][0]["late"]["included_fraction"],
                delay_s=m["delay_mean_slots"] * m["slot_length"] / 1000,
                peer=(stops.get("peer_aggregates", 0) + stops.get("both", 0)) / total["decisions"],
                leaf=stops.get("fee_leaves", 0) / total["decisions"])


def extract_interval_cycles(directory):
    """The fold timings priced by cycle counts, 8 seeds: each cell's class (with its seed
    count where it has fewer than eight), the range of transactions included, and its mean
    CPU, late cohort within 24 s and delay, at a table's precision."""
    cells = {}
    for m, path in _runs(directory, CYCLES):
        key = (CYCLES_DESIGNS[m.group(1)], int(m.group(2)), int(m.group(3)), float(m.group(4)))
        with open(path) as handle:
            for line in handle:
                cells.setdefault(key, []).append(_cycles_point(json.loads(line)))
    rows = []
    for design in ("ticked-b1000", "ticked2000-b2000", "tickless-b2000"):
        for share in (0.0, 0.2, 0.5):
            for tps in (10, 20, 30, 45, 60):
                for factor in (1, 2):
                    points = cells.get((design, factor, tps, share))
                    if not points:
                        break
                    cls = _classify([p["frac"] for p in points])
                    if len(points) != 8:
                        cls = f"{cls}?{len(points)}"
                    mean = lambda k: statistics.fmean(p[k] for p in points)
                    rows.append(dict(design=design, share=share, tps=tps, factor=factor, cls=cls,
                                     included_min=min(p["included"] for p in points),
                                     included_max=max(p["included"] for p in points),
                                     born=tps * 60, cpu=float(format(mean("cpu"), ">4.2f")),
                                     late24=float(format(mean("late24"), ">5.2f")),
                                     delay_s=float(format(mean("delay_s"), ">5.1f"))))
    write("interval-cycles.csv", rows)


PRIVACY_1000 = re.compile(r"^privacy-1000-(tick|tickless)-a(\d+)-f(\d)-s([\d.]+)-seed(\d+)\.jsonl$")


def extract_privacy_1000(directory):
    """Privacy capacity at 1,000 nodes and 30 tx/s: the slower provers from their runs, the
    fast one from interval-cycles (shares 0.2 and 0.5 only, so a held 0.5 reads as "at least
    15")."""
    designs = {"tick": "eip_tick", "tickless": "tickless"}
    cells = {}
    for m, path in _runs(directory, PRIVACY_1000):
        metrics = _record(path)["metrics"]
        key = (designs[m.group(1)], int(m.group(2)), int(m.group(3)))
        cells.setdefault(key, {}).setdefault(float(m.group(4)), []).append(
            metrics["included_txs"] / metrics["arrived_txs"])
    fast = {"ticked-b1000": "eip_tick", "tickless-b2000": "tickless"}
    for r in read("interval-cycles.csv"):
        if r["design"] in fast and int(r["tps"]) == 30 and float(r["share"]) > 0:
            key = (fast[r["design"]], 303, int(r["factor"]))
            # interval-cycles keeps the class over 8 seeds; its worst seed stands for them.
            cells.setdefault(key, {})[float(r["share"])] = r["cls"]
    rows = []
    for (design, anchor, factor), shares in sorted(cells.items()):
        classes = {share: v if isinstance(v, str) else _classify(v) for share, v in shares.items()}
        capacity, bound = _capacity(classes)
        rows.append(dict(design=design, anchor_ms=anchor, factor=factor, capacity=capacity,
                         bound=int(bound), nodes=1000,
                         seeds=8 if anchor == 303 else min(len(v) for v in shares.values())))
    write("privacy-frontier-1000.csv", rows)


PARTIAL = re.compile(r"^partial-(a[\d.]+)(?:-(best|all))?(?:-(relayprop|lean))?-(sig30|p15)"
                     r"-seed(\d+)\.jsonl$")


def extract_partial(directory):
    """Partial aggregation at 1,000 nodes: per cell, means over seeds.

    CPU and uplink figures are over the load window, from `load_utilisation`'s per-node
    arrays split by `relay_node_ids`. (`roles` divides by the whole run, drain included.)
    """
    cells = {}
    for m, path in _runs(directory, PARTIAL):
        share, rule, variant, load, _ = m.groups()
        metrics = _record(path)["metrics"]
        relays = set(metrics["relay_node_ids"])
        window = metrics["load_utilisation"]
        nodes = range(len(window["cpu_utilisation_by_node"]))
        aggs = [n for n in nodes if n not in relays]
        rel = sorted(relays)
        role = metrics["roles"]
        cells.setdefault((variant or "main", load, float(share[1:]), rule or "-"), []).append(dict(
            included=metrics["included_txs"] / metrics["arrived_txs"],
            agg_cpu=statistics.fmean(window["cpu_utilisation_by_node"][n] for n in aggs),
            agg_cpu_max=max(window["cpu_utilisation_by_node"][n] for n in aggs),
            relay_egress=statistics.fmean(window["egress_utilisation_by_node"][n] for n in rel)
            if rel else -1.0,
            relay_wrapper_mb=role["relay"]["wrapper_bytes_sent_per_node_second"] / 1e6
            if rel else -1.0,
            agg_wrapper_mb=role["aggregator"]["wrapper_bytes_sent_per_node_second"] / 1e6,
            born_relay=role["relay"]["included"] / role["relay"]["born"]
            if role["relay"]["born"] else -1.0,
            delay_s=12 * metrics["delay_mean_slots"],
            children=metrics["fold_width"]["children_mean"]))
    rows = []
    for (variant, load, share, rule), runs in sorted(cells.items()):
        avg = lambda f: round(statistics.fmean(r[f] for r in runs), 4)
        rows.append(dict(variant=variant, load=load, aggregator_share=share, rule=rule,
                         seeds=len(runs),
                         included_min=round(min(r["included"] for r in runs), 4),
                         agg_cpu=avg("agg_cpu"),
                         agg_cpu_max=round(max(r["agg_cpu_max"] for r in runs), 4),
                         relay_egress=avg("relay_egress"), relay_wrapper_mb=avg("relay_wrapper_mb"),
                         agg_wrapper_mb=avg("agg_wrapper_mb"), born_relay=avg("born_relay"),
                         delay_s=avg("delay_s"), children=avg("children")))
    write("partial-aggregation.csv", rows)


def _run_row(path):
    metrics = _record(path)["metrics"]
    ages = {o["age_ms"]: o["all"] for o in metrics["fixed_age_outcomes"]}
    steady = [b for b in metrics["block_observations"] if 2 <= b["slot"] <= 5]
    slot = metrics["slot_length"] / 1000
    return dict(included=metrics["included_txs"] / metrics["arrived_txs"],
                cpu=metrics["load_utilisation"]["cpu_utilisation"],
                egress=metrics["load_utilisation"]["egress_utilisation"],
                delay_s=slot * metrics["delay_mean_slots"],
                within_12s=ages[12000.0]["included_fraction"],
                block_share=statistics.fmean(b["included_txs"] for b in steady)
                / (metrics["arrived_txs"] / 5),
                blocks_full=statistics.fmean(1.0 if b["budget_full_with_live_backlog"] else 0.0
                                             for b in steady))


def _summarise(cells, name, keys):
    rows = []
    for key, runs in sorted(cells.items()):
        row = dict(zip(keys, key))
        row["seeds"] = len(runs)
        row["included_min"] = round(min(r["included"] for r in runs), 4)
        for field in ("cpu", "egress", "delay_s", "within_12s", "block_share", "blocks_full"):
            row[field] = round(statistics.fmean(r[field] for r in runs), 4)
        rows.append(row)
    write(name, rows)


SCALING = re.compile(r"^(scaling|throughput)-n(\d+)-(tick|tickless)-tps(\d+)-s([\d.]+)"
                     r"-seed(\d+)\.jsonl$")
SCALING_CYCLES = re.compile(r"^interval-cycles-(tick1000|tickless)-f1-tps(\d+)-s(0|0\.2)"
                            r"-seed(\d+)\.jsonl$")


def extract_scaling(scaling_dir, throughput_dir, cycles_dir):
    """100 to 3,000 nodes at 30 tx/s, and 100-200 tx/s at 1,000 nodes, priced by cycle counts.
    The 1,000-node cells at 30 and 60 tx/s are interval-cycles' (same code, seeds and flags)."""
    scaling, throughput = {}, {}
    for directory in (scaling_dir, throughput_dir):
        for m, path in _runs(directory, SCALING):
            step, nodes, design, tps, share, _ = m.groups()
            target = scaling if step == "scaling" else throughput
            target.setdefault((design, int(nodes), int(tps), float(share)), []).append(
                _run_row(path))
    for m, path in _runs(cycles_dir, SCALING_CYCLES):
        design = "tick" if m.group(1) == "tick1000" else "tickless"
        tps, share = int(m.group(2)), float(m.group(3))
        row = _run_row(path)
        if tps == 30:
            scaling.setdefault((design, 1000, 30, share), []).append(row)
        if tps in (30, 60):
            throughput.setdefault((design, 1000, tps, share), []).append(row)
    _summarise(scaling, "scaling-3000.csv", ("design", "nodes", "tps", "share"))
    _summarise(throughput, "throughput.csv", ("design", "nodes", "tps", "share"))


def extract_leanvm_16_threads(results):
    """leanVM 990b935's leaves and folds on a Ryzen 9 8945HS at 16 threads: per shape, the
    median proving time over its accepted runs."""
    groups = {}
    for r in csv.DictReader(open(results)):
        key = (int(r["rate"]), r["kind"], int(r["n"]), int(r["k"]))
        groups.setdefault(key, []).append(r)
    rows = []
    for (rate, kind, n, k), g in sorted(groups.items()):
        accepted = [r for r in g if r["accepted"] == "1"] or g
        rows.append(dict(rate=rate, kind=kind, children=n, sigs_per_leaf=k,
                         prove_s=statistics.median(float(r["prove_s"]) for r in accepted),
                         repeats=len(accepted),
                         cycles=int(g[0]["cycles"]),
                         committed=round(2 ** float(g[0]["committed_log2"])),
                         proof_kib=float(g[0]["proof_kib"]),
                         peak_gib=statistics.median(float(r["peak_gib"]) for r in g)))
    write("leanvm-16-threads.csv", rows)


def extract_leanvm_threads(results):
    """leanVM's README 2-to-1 fold on a Ryzen 9 8945HS, by thread count."""
    rows = [dict(threads=int(r["threads"]), prove_s=float(r["prove_s"]),
                 cycles=int(r["cycles"]), proof_kib=float(r["proof_kib"]),
                 accepted=int(r["accepted"]))
            for r in csv.DictReader(open(results))]
    write("leanvm-threads.csv", sorted(rows, key=lambda r: r["threads"]))


def extract_capacity(every_node, no_flood, one_builder):
    """Capacity against network size: every node aggregating, with raw transactions pushed
    to every node or kept at their entry node (`relay_policy=wrapper_only`), and one builder
    aggregating, the fixed proposer, with relays that forward no proof; its CPU is the
    builder's own. 15 tx/s of signatures plus p privacy tx/s under the EIP tick on the fast
    prover, priced by cycle counts."""
    series = (("every_node", every_node, "every-node"), ("every_node_no_flood", no_flood, "no-flood"),
              ("builder_only", one_builder, "one-builder"))
    cells = {}
    for design, directory, prefix in series:
        pattern = re.compile(rf"^{prefix}-n(\d+)-p(\d+)-seed(\d+)\.jsonl$")
        for m, path in _runs(directory, pattern):
            row = _run_row(path)
            if design == "builder_only":
                record = _record(path)
                relays = set(record["variant"]["relay_node_ids"])
                by_node = record["metrics"]["load_utilisation"]["cpu_utilisation_by_node"]
                (builder,) = [node for node in range(len(by_node)) if node not in relays]
                row["cpu"] = by_node[builder]
            cells.setdefault((design, int(m.group(1)), int(m.group(2))), []).append(row)
    rows = []
    for (design, nodes, p), runs in sorted(cells.items()):
        fracs = [r["included"] for r in runs]
        rows.append(dict(design=design, nodes=nodes, p=p, tps=15 + p, seeds=len(runs),
                         included_min=round(min(fracs), 4), included_max=round(max(fracs), 4),
                         cls=_classify(fracs),
                         **{field: round(statistics.fmean(r[field] for r in runs), 4)
                            for field in ("cpu", "egress", "delay_s", "block_share")}))
    write("capacity-n.csv", rows)


def write(name, rows):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", newline="") as handle:
        writer = csv.DictWriter(handle, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"data/{name}: {len(rows)} rows")


def read(name):
    return list(csv.DictReader(open(os.path.join(DATA, name))))


# ---------------------------------------------------------------- draw


STYLE = """
:root{--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--axis:#c3c2b7;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--held:#e3f1e3;--held-ink:#1f5f1f;--marg:#fbf0d6;
--marg-ink:#7a5600;--coll:#f7e1e0;--coll-ink:#8e2626;--today:#0b0b0b}
@media (prefers-color-scheme: dark){:root{--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;
--muted:#898781;--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--held:#1f3321;
--held-ink:#9fd69f;--marg:#3a3018;--marg-ink:#f0cf7a;--coll:#3d2222;--coll-ink:#f0a3a3;
--today:#f0efec}}
text{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;fill:var(--ink)}
.bg{fill:var(--surface)}
.title{font-size:16px;font-weight:600}
.sub{font-size:12px;fill:var(--ink2)}
.head{font-size:13px;font-weight:600}
.lab{font-size:12px;fill:var(--ink2)}
.ax{font-size:11px;fill:var(--muted);font-variant-numeric:tabular-nums}
.val{font-size:12px;font-variant-numeric:tabular-nums;font-weight:600}
.grid{stroke:var(--grid);stroke-width:1}
.axis{stroke:var(--axis);stroke-width:1}
.s1{stroke:var(--s1);fill:none;stroke-width:2}
.s2{stroke:var(--s2);fill:none;stroke-width:2}
.s3{stroke:var(--s3);fill:none;stroke-width:2}
.m3{fill:var(--s3);stroke:var(--surface);stroke-width:2}
.dash{stroke-dasharray:5 4}
.m1{fill:var(--s1);stroke:var(--surface);stroke-width:2}
.m2{fill:var(--s2);stroke:var(--surface);stroke-width:2}
.mo1{fill:var(--surface);stroke:var(--s1);stroke-width:2}
.mo2{fill:var(--surface);stroke:var(--s2);stroke-width:2}
.ref{stroke:var(--muted);stroke-width:1;stroke-dasharray:2 3}
.fit{stroke:var(--muted);stroke-width:1.5;stroke-dasharray:6 4;fill:none}
.bar{fill:var(--s1)}
.held{fill:var(--held)} .marginal{fill:var(--marg)} .collapsed{fill:var(--coll)}
.t-held{fill:var(--held-ink)} .t-marginal{fill:var(--marg-ink)} .t-collapsed{fill:var(--coll-ink)}
.today{fill:none;stroke:var(--today);stroke-width:1.5;stroke-dasharray:4 3}
.frontier{fill:none;stroke:var(--ink);stroke-width:2.5;stroke-linecap:round}
.range{stroke-width:6;stroke-linecap:round;opacity:.3}
"""


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, cls="lab", anchor="start", extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}"{extra}>{esc(s)}</text>'


def svg(name, w, h, title, desc, body):
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" '
           f'height="{h}" role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title>'
           f'<desc id="d">{esc(desc)}</desc><style>{STYLE}</style>'
           f'<rect class="bg" width="{w}" height="{h}" rx="8"/>' + "".join(body) + "</svg>\n")
    os.makedirs(FIGURES, exist_ok=True)
    with open(os.path.join(FIGURES, name), "w") as handle:
        handle.write(out)
    print(name)


def fmt(v):
    return f"{v:,.0f}" if v >= 100 else (f"{v:g}")


def draw_w():
    rows = [r for r in read("interval.csv") if r["factor"] == "1"]
    cell = {(int(r["anchor_ms"]), r["design"], float(r["share"]), int(r["tps"])): r for r in rows}
    designs = [("ticked-b1000", "EIP-8288: 1,000 ms tick"), ("ticked2000-b2000", "2,000 ms tick"),
               ("tickless-b2000", "Tickless (fold when ready, ≤ 2 s)")]
    provers = [(303, "The fast prover: a 2-to-1 fold in 303 ms"),
               (871, "Four Ryzen cores: a 2-to-1 fold in 871 ms")]
    shares = [(0.0, "no privacy"), (0.2, "a fifth private"), (0.5, "half private")]
    rates = [10, 20, 30, 45, 60]
    cw, ch, gap, x0, pgap = 44, 34, 2, 128, 26
    pw = len(rates) * (cw + gap) - gap
    w = x0 + 3 * pw + 2 * pgap + 20
    body = [text(20, 28, "Which designs keep up, at 1,000 nodes", "title"),
            text(20, 48, "Share included on the worst of 8 seeds (%, rounded down). Raw "
                 "transactions pushed to every node; a privacy witness costs one nested proof.",
                 "sub"),
            text(x0 - 8, 100, "tx/s", "ax", "end")]
    for i, (design, label) in enumerate(designs):
        px = x0 + i * (pw + pgap)
        body.append(text(px, 80, label, "head"))
        for j, tps in enumerate(rates):
            body.append(text(px + j * (cw + gap) + cw / 2, 100, str(tps), "ax", "middle"))
    y = 130
    for anchor, prover in provers:
        body.append(text(20, y, prover, "head"))
        top = y + 12
        for i, (design, label) in enumerate(designs):
            px = x0 + i * (pw + pgap)
            for k, (share, share_label) in enumerate(shares):
                for j, tps in enumerate(rates):
                    r = cell[(anchor, design, share, tps)]
                    worst = 100 * float(r["included_min"])
                    cx, cy = px + j * (cw + gap), top + k * (ch + gap)
                    body.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="4" '
                                f'class="{r["cls"]}"><title>{esc(label)}, {anchor} ms fold, '
                                f'{tps} tx/s, {share_label}: {r["cls"]}, worst seed {worst:.1f}% '
                                f'included, CPU {float(r["cpu"]):.0%}</title></rect>')
                    body.append(text(cx + cw / 2, cy + ch / 2 + 4, f"{math.floor(worst):.0f}",
                                     f"val t-{r['cls']}", "middle"))
            body.append(f'<rect x="{px - 3}" y="{top - 3}" width="{2 * (cw + gap) + 4}" '
                        f'height="{ch + 6}" rx="6" class="today"/>')
        for k, (_, share_label) in enumerate(shares):
            body.append(text(x0 - 12, top + k * (ch + gap) + ch / 2 + 4, share_label, "lab",
                             "end"))
        y = top + 3 * (ch + gap) + 32
    ly = y - 8
    legend = [("held", "held: ≥ 95% on every seed"), ("marginal", "marginal"),
              ("collapsed", "collapsed: < 60% on every seed")]
    lx = 20
    for cls, label in legend:
        body.append(f'<rect x="{lx}" y="{ly - 11}" width="14" height="14" rx="3" class="{cls}"/>')
        body.append(text(lx + 20, ly, label))
        lx += 34 + 7 * len(label)
    body.append(f'<rect x="{lx}" y="{ly - 11}" width="24" height="14" rx="4" class="today"/>')
    body.append(text(lx + 30, ly, "today's mainnet: about 15–20 tx/s, none private"))
    svg("holds-grid.svg", w, ly + 20, "Which designs keep up, at 1,000 nodes",
        "Six grids of privacy share by transaction rate: one column per fold timing, one row per "
        "prover, calibration v2 prices. On the fast prover every cell holds. On four Ryzen "
        "cores every fold timing holds every rate without privacy. With privacy the EIP's "
        "1,000 ms tick holds nothing, its worst seeds including 9-61%; the 2,000 ms tick holds "
        "a fifth private at 10 and 20 tx/s; tickless holds those and half private at 10 tx/s; "
        "nothing private holds at 45 or 60 tx/s.", body)


def log_scale(lo, hi, a, b):
    return lambda v: a + (math.log(v) - math.log(lo)) / (math.log(hi) - math.log(lo)) * (b - a)


def lin_scale(lo, hi, a, b):
    return lambda v: a + (v - lo) / (hi - lo) * (b - a)


def ytitle(body, x, py, ph, label):
    """A vertical axis title, centred on the plot and reading upwards."""
    y = py + ph / 2
    body.append(f'<text x="{x:.1f}" y="{y:.1f}" class="ax" text-anchor="middle" '
                f'transform="rotate(-90 {x:.1f} {y:.1f})">{esc(label)}</text>')


def marker_class(cls):
    return "m3" if "s3" in cls else "m1" if "s1" in cls else "m2"


def line_panel(body, px, py, pw, ph, title, xs, xticks, ylo, yhi, yticks, series, xfmt=str,
               log=True, xlabel=None, ylabel=None):
    sx = (log_scale if log else lin_scale)(xs[0], xs[-1], px, px + pw)
    sy = lin_scale(ylo, yhi, py + ph, py)
    body.append(text(px, py - 14, title, "head"))
    for t in yticks:
        body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" '
                    f'class="{"axis" if t == ylo else "grid"}"/>')
        body.append(text(px - 6, sy(t) + 4, fmt(t), "ax", "end"))
    if ylabel:
        ytitle(body, px - 34, py, ph, ylabel)
    for t in xticks:
        body.append(text(sx(t), py + ph + 16, xfmt(t), "ax", "middle"))
    if xlabel:
        body.append(text(px + pw / 2, py + ph + 34, xlabel, "ax", "middle"))
    for cls, points, label, label_dy in series:
        d = " ".join(f"{'M' if i == 0 else 'L'}{sx(x):.1f},{sy(y):.1f}"
                     for i, (x, y) in enumerate(points))
        body.append(f'<path d="{d}" class="{cls}"/>')
        mcls = marker_class(cls)
        for x, y in points:
            body.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4.5" class="{mcls}">'
                        f'<title>{esc(label or "")} {xfmt(x)}: {y:g}</title></circle>')
        if label:
            x, y = points[-1]
            body.append(text(sx(x) + 8, sy(y) + 4 + label_dy, label, "lab"))
    return sx, sy


def legend_row(body, x, y, items):
    for cls, label in items:
        body.append(f'<line x1="{x}" x2="{x + 22}" y1="{y - 4}" y2="{y - 4}" class="{cls}"/>')
        body.append(f'<circle cx="{x + 11}" cy="{y - 4}" r="4.5" class="{marker_class(cls)}"/>')
        body.append(text(x + 30, y, label))
        x += 46 + 7 * len(label)


def draw_scaling():
    rows = read("scaling-n.csv")
    by = {}
    for r in rows:
        by.setdefault(r["design"], []).append(r)
    nodes = [40, 100, 300, 1000]
    nf = lambda v: f"{v:,}"
    w, ph, pw = 880, 170, 210
    body = [text(20, 28, "What grows with the number of nodes", "title"),
            text(20, 48, "15 tx/s, a fifth private, raw transactions flooded, 2 seeds per point; "
                 "every run included all. leanVM-b's weights, a nested proof at 151.5 ms.", "sub")]
    legend_row(body, 20, 76, [("s1", "EIP-8288: 1,000 ms tick"),
                              ("s2", "Tickless (≤ 2 s)")])
    py = 122
    tick, tickless = by["tick1000"], by["tickless2000"]
    pts = lambda rs, f: [(int(r["nodes"]), f(r)) for r in rs]
    line_panel(body, 60, py, pw, ph, "Mean inclusion delay (s)", nodes, nodes, 0, 14,
               [0, 4, 8, 12], [("s1", pts(tick, lambda r: 12 * float(r["delay_slots"])), None, 0),
                               ("s2", pts(tickless, lambda r: 12 * float(r["delay_slots"])), None, 0)],
               nf, xlabel="nodes (log scale)", ylabel="mean delay (s)")
    body.append(text(60 + pw / 2, py + ph - 56, "the two designs overlap:", "lab", "middle"))
    body.append(text(60 + pw / 2, py + ph - 40, "+3 s for 25× the nodes", "lab", "middle"))
    line_panel(body, 345, py, pw, ph, "CPU busy, per node (%)", nodes, nodes, 0, 100,
               [0, 25, 50, 75, 100],
               [("s1", pts(tick, lambda r: 100 * float(r["cpu"])), None, 0),
                ("s2", pts(tickless, lambda r: 100 * float(r["cpu"])), None, 0)],
               nf, xlabel="nodes (log scale)", ylabel="CPU busy (%)")
    body.append(text(345 + pw / 2, py + 26, "flat in the number of nodes", "lab", "middle"))
    line_panel(body, 630, py, pw - 20, ph, "Nodes proving each privacy input (%)", nodes,
               nodes, 0, 30, [0, 10, 20, 30],
               [("s1", pts(tick, lambda r: 100 * float(r["privacy_folders"]) / int(r["nodes"])),
                 None, 0),
                ("s2", pts(tickless,
                           lambda r: 100 * float(r["privacy_folders"]) / int(r["nodes"])),
                 None, 0)],
               nf, xlabel="nodes (log scale)", ylabel="share of nodes (%)")
    svg("scaling-n.svg", w, py + ph + 52, "What grows with the number of nodes",
        "Three panels against node count 40 to 1,000. Mean inclusion delay rises from about "
        "9.5 to 12.5 s under both designs. CPU per node is flat, 58-59% under the tick and "
        "75-76% tickless. The share of nodes that prove each privacy witness themselves falls, "
        "from 28% to 14% under the tick and 17% to 5.5% tickless.", body)


def draw_privacy():
    """Factor 1, 1,000 nodes against 40: network size helps only the fast prover."""
    big = {(r["design"], int(r["anchor_ms"])): r for r in read("privacy-frontier-1000.csv")
           if r["factor"] == "1"}
    small = {(r["design"], int(r["anchor_ms"])): r for r in read("privacy-frontier.csv")
             if r["factor"] == "1"}
    anchors = [303, 606, 1212]
    xl = {303: ("fast: 303 ms", "an M4 Max"), 606: ("2× slower", "8-core Ryzen, all cores"),
          1212: ("4× slower", "Ryzen on 2 cores is 4.7×")}
    w, px, py, pw, ph = 780, 70, 132, 470, 250
    sx = lambda a: px + anchors.index(a) / 2 * pw
    sy = lin_scale(0, 16, py + ph, py)
    body = [text(20, 28, "Prover speed sets privacy capacity (priced by cycle counts)", "title"),
            text(20, 48, "Highest privacy rate included on every seed, at 30 tx/s in all; a privacy "
                 "witness costs one nested proof. Arrows: held at the", "sub"),
            text(20, 66, "highest rate tried. Raw transactions flooded. 1,000 nodes: 8 seeds on the "
                 "fast prover, 4 on the slower ones; 40 nodes: 4.", "sub")]
    legend_x = 20
    for cls, label in (("s1", "EIP tick, 1,000 nodes"), ("s1 dash", "EIP tick, 40 nodes"),
                       ("s2", "tickless, 1,000 nodes"), ("s2 dash", "tickless, 40 nodes")):
        body.append(f'<line x1="{legend_x}" x2="{legend_x + 26}" y1="92" y2="92" class="{cls}"/>')
        body.append(text(legend_x + 32, 96, label))
        legend_x += 44 + 7 * len(label)
    for t in (0, 4, 8, 12, 16):
        body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" '
                    f'class="{"axis" if t == 0 else "grid"}"/>')
        body.append(text(px - 8, sy(t) + 4, fmt(t), "ax", "end"))
    ytitle(body, px - 36, py, ph, "privacy tx/s carried")
    for v, label in ((6, "a fifth of 30 tx/s"), (15, "half of 30 tx/s")):
        body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="ref"/>')
        body.append(text(px + pw + 8, sy(v) + 4, label, "ax"))
    for a in anchors:
        body.append(text(sx(a), py + ph + 18, xl[a][0], "ax", "middle"))
        body.append(text(sx(a), py + ph + 33, xl[a][1], "ax", "middle"))
    body.append(text(px + pw / 2, py + ph + 54, "prover speed (a 2→1 fold's time)", "ax", "middle"))
    series = [(big, "eip_tick", "s1", "m1", "EIP tick, 1,000 nodes"),
              (small, "eip_tick", "s1 dash", "mo1", "EIP tick, 40 nodes"),
              (big, "tickless", "s2", "m2", "tickless, 1,000 nodes"),
              (small, "tickless", "s2 dash", "mo2", "tickless, 40 nodes")]
    for table, design, cls, mcls, label in series:
        pts = [(a, float(table[(design, a)]["capacity"]), table[(design, a)]["bound"] == "1")
               for a in anchors]
        d = " ".join(f"{'M' if i == 0 else 'L'}{sx(a):.1f},{sy(v):.1f}"
                     for i, (a, v, _) in enumerate(pts))
        body.append(f'<path d="{d}" class="{cls}"/>')
        for a, v, bound in pts:
            tip = f"{label}, {xl[a][0]}: {v:g} privacy tx/s" + ("" if bound else " or more")
            body.append(f'<circle cx="{sx(a):.1f}" cy="{sy(v):.1f}" r="4.5" class="{mcls}">'
                        f'<title>{esc(tip)}</title></circle>')
            if not bound:
                body.append(f'<path d="M{sx(a):.1f},{sy(v) - 8:.1f} l0,-14 m-5,5 l5,-5 l5,5" '
                            f'class="{cls.split()[0]}"/>')
    body.append(text(sx(303) + 10, sy(7.5) + 4, "7.5 at 40 nodes", "lab"))
    body.append(text(sx(606) + 10, sy(3) - 8, "3", "lab"))
    body.append(text(sx(606) + 10, sy(1.5) + 14, "1.5", "lab"))
    body.append(text(sx(1212) - 10, sy(2.4), "nothing private holds", "lab", "end"))
    body.append(text(sx(303) + 44, sy(15) + 16, "15 or more at 1,000 nodes, both designs", "lab"))
    svg("privacy-frontier.svg", w, py + ph + 70, "Prover speed sets privacy capacity",
        "Privacy capacity at 30 tx/s against prover speed, at 1,000 and 40 nodes. On the fast "
        "prover the EIP tick holds 15 or more privacy tx/s at 1,000 nodes and 7.5 at 40; tickless "
        "15 or more at both. On a 2x slower prover both sizes give the same: 1.5 under the tick "
        "and 3 tickless. On a 4x slower one nothing private holds at either size.", body)


def draw_latency():
    rows = read("latency.csv")
    cell = {(r["design"], float(r["share"]), int(r["tps"])): r for r in rows}
    rates = [10, 20, 30, 45, 60]
    designs = [("ticked-b1000", "s1", "EIP-8288: 1,000 ms tick"), ("ticked2000-b2000", "s3", "2,000 ms tick"),
               ("tickless-b2000", "s2", "Tickless (≤ 2 s)")]
    w, ph, pw = 880, 200, 220
    body = [text(20, 28, "How long a transaction waits for a block", "title"),
            text(20, 48, "Mean time from birth to inclusion; 1,000 nodes, 8 seeds, the fast "
                 "prover; 12 s slots.", "sub"),
            text(20, 64, "Raw transactions pushed to every node; a privacy witness costs one "
                 "nested proof.", "sub")]
    legend_x = 20
    for _, cls, label in designs:
        body.append(f'<line x1="{legend_x}" x2="{legend_x + 22}" y1="90" y2="90" class="{cls}"/>')
        body.append(f'<circle cx="{legend_x + 11}" cy="90" r="4.5" class="m{cls[1]}"/>')
        body.append(text(legend_x + 30, 94, label))
        legend_x += 46 + 7 * len(label)
    py = 140
    for k, (share, title) in enumerate(((0.0, "No privacy"), (0.2, "A fifth private"), (0.5, "Half private"))):
        px = 60 + k * (pw + 70)
        sx = lin_scale(10, 60, px, px + pw)
        sy = lin_scale(0, 18, py + ph, py)
        body.append(text(px, py - 14, title, "head"))
        for t in (0, 6, 12, 18):
            body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" '
                        f'class="{"axis" if t == 0 else "grid"}"/>')
            body.append(text(px - 6, sy(t) + 4, str(t), "ax", "end"))
        ytitle(body, px - 30, py, ph, "mean inclusion delay (s)")
        body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(6):.1f}" y2="{sy(6):.1f}" class="ref"/>')
        if k == 0:
            body.append(text(px + pw, sy(6) + 14, "ideal: next block, 6 s on average", "ax", "end"))
        for t in rates:
            body.append(text(sx(t), py + ph + 16, str(t), "ax", "middle"))
        body.append(text(px + pw / 2, py + ph + 34, "tx/s", "ax", "middle"))
        for design, cls, label in designs:
            pts = [(t, float(cell[(design, share, t)]["delay_mean_s"]),
                    float(cell[(design, share, t)]["within_12s"])) for t in rates]
            d = " ".join(f"{'M' if i == 0 else 'L'}{sx(t):.1f},{sy(v):.1f}" for i, (t, v, _) in enumerate(pts))
            body.append(f'<path d="{d}" class="{cls}"/>')
            for t, v, within in pts:
                body.append(f'<circle cx="{sx(t):.1f}" cy="{sy(v):.1f}" r="4" class="m{cls[1]}">'
                            f'<title>{esc(label)}, {esc(title.lower())}, {t} tx/s: mean {v:.1f} s, '
                            f'{within:.0%} within 12 s</title></circle>')
    svg("latency.svg", w, py + ph + 52, "How long a transaction waits for a block",
        "Mean inclusion delay against transaction rate at 1,000 nodes on the fast prover, in three "
        "panels by privacy share. Without privacy the EIP tick rises from 7.1 to 9.5 s, the "
        "2,000 ms tick from 7.1 to 8.0 s, and tickless sits at 12.2-13.3 s. With privacy every "
        "design waits 9.9-14.2 s. The ideal, inclusion in the next block, averages 6 s.", body)


def draw_partial():
    rows = [r for r in read("partial-aggregation.csv") if r["variant"] == "main"]
    cell = {(r["load"], float(r["aggregator_share"]), r["rule"]): r for r in rows}
    shares = [1.0, 0.75, 0.5, 0.25, 0.1]
    series = [("sig30", "best", "s1", "m1"), ("sig30", "all", "s2", "m2"),
              ("p15", "best", "s1 dash", "mo1"), ("p15", "all", "s2 dash", "mo2")]
    names = {"sig30": "30 tx/s, signatures only", "p15": "15 tx/s, a fifth private"}
    w, ph, pw = 880, 190, 210
    worst = min(float(r["included_min"]) for r in rows)
    body = [text(20, 28, "What happens when fewer nodes aggregate", "title"),
            text(20, 48, f"1,000 nodes, the EIP's 1,000 ms tick, 4 seeds, raw transactions flooded, "
                 f"priced by cycle counts. Every cell included at least {worst:.1%} on every seed.",
                 "sub")]
    legend_x = 20
    for cls, label in (("s1", "forward the best proof"), ("s2", "forward every proof")):
        body.append(f'<line x1="{legend_x}" x2="{legend_x + 26}" y1="74" y2="74" class="{cls}"/>')
        body.append(text(legend_x + 32, 78, label))
        legend_x += 48 + 7 * len(label)
    for cls, label in (("axis", "solid: " + names["sig30"]), ("axis dash", "dashed: " + names["p15"])):
        body.append(f'<line x1="{legend_x}" x2="{legend_x + 26}" y1="74" y2="74" class="{cls}" '
                    f'style="stroke:var(--ink2);stroke-width:2"/>')
        body.append(text(legend_x + 32, 78, label))
        legend_x += 48 + 7 * len(label)
    py = 124
    panels = [("Aggregator CPU (%)", "agg_cpu", 100, (0, 25, 50, 75, 100), shares, lambda v: 100 * v),
              ("Relay uplink busy (%)", "relay_egress", 100, (0, 25, 50, 75, 100), shares[1:], lambda v: 100 * v),
              ("Mean inclusion delay (s)", "delay_s", 14, (0, 4, 8, 12), shares, lambda v: v)]
    for k, (title, field, hi, ticks, xs, conv) in enumerate(panels):
        px = 60 + k * (pw + 80)
        sx = lambda share: px + shares.index(share) / (len(shares) - 1) * pw
        sy = lin_scale(0, hi, py + ph, py)
        body.append(text(px, py - 14, title, "head"))
        for t in ticks:
            body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" '
                        f'class="{"axis" if t == 0 else "grid"}"/>')
            body.append(text(px - 6, sy(t) + 4, str(t), "ax", "end"))
        ytitle(body, px - 34, py, ph, title[0].lower() + title[1:])
        for share in shares:
            body.append(text(sx(share), py + ph + 16, f"{share:.0%}", "ax", "middle"))
        body.append(text(px + pw / 2, py + ph + 34, "nodes that aggregate", "ax", "middle"))
        for load, rule, cls, mcls in series:
            pts = []
            for share in xs:
                r = cell.get((load, share, rule)) or cell.get((load, share, "-"))
                pts.append((share, conv(float(r[field]))))
            d = " ".join(f"{'M' if i == 0 else 'L'}{sx(x):.1f},{sy(v):.1f}" for i, (x, v) in enumerate(pts))
            body.append(f'<path d="{d}" class="{cls}"/>')
            for x, v in pts:
                body.append(f'<circle cx="{sx(x):.1f}" cy="{sy(v):.1f}" r="4" class="{mcls}"><title>'
                            f'{esc(names[load])}, forward {rule if x < 1 else "(no relays)"}, '
                            f'{x:.0%} aggregate: {v:.1f}</title></circle>')
    svg("partial-aggregation.svg", w, py + ph + 52, "What happens when fewer nodes aggregate",
        "Three panels against the share of nodes that aggregate, 100% down to 10%. Aggregator CPU "
        "falls as aggregators get fewer: from 47% to 25% at 30 tx/s of signatures, and from 72% to "
        "54-56% at 15 tx/s with a fifth private. Relays forwarding every proof run their uplinks "
        "94-98% busy, those forwarding the best one about 60% at 30 tx/s. Mean delay at 30 tx/s "
        "falls to 7.4 s when relays forward the best proof and rises to 10.2 s when they forward "
        "every proof; at 15 tx/s with privacy it stays near 11.5-12 s.", body)


def draw_scaling3000():
    rows = read("scaling-3000.csv")
    cell = {(r["design"], int(r["nodes"]), int(r["tps"]), float(r["share"])): r for r in rows}
    nodes = [100, 300, 1000, 3000]
    loads = [(30, 0.0, "30 tx/s, signatures only"), (15, 0.2, "15 tx/s, a fifth private"),
             (30, 0.2, "30 tx/s, a fifth private")]
    designs = [("tick", "s1", "m1", "EIP-8288: 1,000 ms tick"), ("tickless", "s2", "m2", "Tickless (≤ 2 s)")]
    seeds = sorted({int(r["seeds"]) for r in rows})
    w, ph, pw = 880, 190, 220
    body = [text(20, 28, "Delay grows slowly with the network", "title"),
            text(20, 48, f"100 to 3,000 nodes, raw transactions flooded, priced by cycle counts, "
                 f"{seeds[0] if seeds[0] == seeds[-1] else f'{seeds[0]}–{seeds[-1]}'} seeds a "
                 "point. Every point included everything; per-node CPU stayed flat.", "sub")]
    legend_row(body, 20, 76, [(cls, label) for _, cls, _, label in designs])
    py = 124
    for k, (tps, share, title) in enumerate(loads):
        px = 60 + k * (pw + 70)
        sx = log_scale(100, 3000, px, px + pw)
        sy = lin_scale(0, 18, py + ph, py)
        body.append(text(px, py - 14, title, "head"))
        for t in (0, 6, 12, 18):
            body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" '
                        f'class="{"axis" if t == 0 else "grid"}"/>')
            body.append(text(px - 6, sy(t) + 4, str(t), "ax", "end"))
        ytitle(body, px - 30, py, ph, "mean inclusion delay (s)")
        body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(6):.1f}" y2="{sy(6):.1f}" class="ref"/>')
        if k == 0:
            body.append(text(px + pw, sy(6) + 14, "ideal: next block, 6 s", "ax", "end"))
        for n in nodes:
            body.append(text(sx(n), py + ph + 16, f"{n:,}", "ax", "middle"))
        body.append(text(px + pw / 2, py + ph + 34, "nodes (log scale)", "ax", "middle"))
        for design, cls, mcls, label in designs:
            pts = [(n, float(cell[(design, n, tps, share)]["delay_s"]),
                    float(cell[(design, n, tps, share)]["cpu"])) for n in nodes]
            d = " ".join(f"{'M' if i == 0 else 'L'}{sx(n):.1f},{sy(v):.1f}" for i, (n, v, _) in enumerate(pts))
            body.append(f'<path d="{d}" class="{cls}"/>')
            for n, v, cpu in pts:
                body.append(f'<circle cx="{sx(n):.1f}" cy="{sy(v):.1f}" r="4" class="{mcls}"><title>'
                            f'{esc(label)}, {esc(title)}, {n:,} nodes: mean {v:.1f} s, CPU {cpu:.0%}'
                            f'</title></circle>')
    svg("scaling-3000.svg", w, py + ph + 52, "Delay grows slowly with the network",
        "Mean inclusion delay against node count from 100 to 3,000 at three load points. Under the "
        "EIP tick it rises from 7.6 to 8.8 s with signatures only, from 10.1 to 12.9 s at 15 tx/s with a "
        "fifth private, and from 11.7 to 14.4 s at 30 tx/s with a fifth private; tickless rises from "
        "9.5 to 12.8 s with signatures only. Every point included every transaction, and per-node CPU "
        "stayed flat.", body)


def draw_capacity():
    rows = [r for r in read("capacity-n.csv") if r["design"] in ("every_node", "builder_only")]
    cell = {(r["design"], int(r["nodes"]), int(r["p"])): r for r in rows}
    designs = [(d, label) for d, label in (("every_node", "Every node aggregates (EIP-8288)"),
                                           ("builder_only", "One builder aggregates"))
               if any(r["design"] == d for r in rows)]
    nodes = sorted({int(r["nodes"]) for r in rows})
    rates = sorted({int(r["p"]) for r in rows}, reverse=True)
    seeds = sorted({int(r["seeds"]) for r in rows})
    cw, ch, gap, x0, y0, pgap = 72, 30, 2, 92, 140, 40
    pw = len(nodes) * (cw + gap) - gap
    ph = len(rates) * (ch + gap) - gap
    w = max(x0 + len(designs) * pw + (len(designs) - 1) * pgap + 24, 700)
    seed_text = f"{seeds[0]}" if seeds[0] == seeds[-1] else f"{seeds[0]}–{seeds[-1]}"
    body = [text(20, 28, "More nodes carry more privacy transactions", "title"),
            text(20, 48, "Share of transactions included on the worst seed (%), under the EIP's "
                 "1,000 ms tick,", "sub"),
            text(20, 64, "with 15 tx/s of signatures plus the privacy rate on the left. Priced by "
                 "leanVM 990b935's cycle counts;", "sub"),
            text(20, 80, "a privacy witness costs one nested proof; raw transactions reach every "
                 f"node. {seed_text} seeds per cell.", "sub")]
    ytitle(body, 36, y0, ph, "privacy tx/s, on top of 15 tx/s of signatures")
    for k, rate in enumerate(rates):
        body.append(text(x0 - 10, y0 + k * (ch + gap) + ch / 2 + 4, str(rate), "lab", "end"))
    for i, (design, label) in enumerate(designs):
        px = x0 + i * (pw + pgap)
        body.append(text(px, y0 - 34, label, "head"))
        for j, n in enumerate(nodes):
            body.append(text(px + j * (cw + gap) + cw / 2, y0 - 12, f"{n:,}", "ax", "middle"))
        body.append(text(px + pw / 2, y0 + ph + 20, "nodes", "ax", "middle"))
        frontier = []
        for j, n in enumerate(nodes):
            held = [rate for rate in rates if (design, n, rate) in cell]
            level = len(rates)
            for k in range(len(rates) - 1, -1, -1):
                r = cell.get((design, n, rates[k]))
                if r is None:
                    continue
                if r["cls"] != "held":
                    break
                level = k
            frontier.append(level if held else None)
            for k, rate in enumerate(rates):
                r = cell.get((design, n, rate))
                cx, cy = px + j * (cw + gap), y0 + k * (ch + gap)
                if r is None:
                    continue
                worst = 100 * float(r["included_min"])
                body.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="4" '
                            f'class="{r["cls"]}"><title>{esc(label)}, {n:,} nodes, {rate} privacy '
                            f'tx/s: {r["cls"]}, {worst:.1f}–{100 * float(r["included_max"]):.1f}% '
                            f'included, {"builder" if design == "builder_only" else "mean"} CPU '
                            f'{float(r["cpu"]):.0%}, mean delay {float(r["delay_s"]):.1f} s'
                            f'</title></rect>')
                body.append(text(cx + cw / 2, cy + ch / 2 + 4, f"{math.floor(worst):.0f}",
                                 f"val t-{r['cls']}", "middle"))
        d = []
        for j, level in enumerate(frontier):
            if level is None:
                continue
            y = y0 + level * (ch + gap) - gap / 2
            x1, x2 = px + j * (cw + gap) - gap / 2, px + j * (cw + gap) + cw + gap / 2
            d.append(f"{'M' if not d else 'L'}{max(x1, px):.1f},{y:.1f} L{min(x2, px + pw):.1f},{y:.1f}")
        body.append(f'<path d="{" ".join(d)}" class="frontier"/>')
    ly = y0 + ph + 48
    lx = 20
    for cls, label in (("held", "held: ≥ 95% on every seed"), ("marginal", "marginal"),
                       ("collapsed", "collapsed: < 60% on every seed")):
        body.append(f'<rect x="{lx}" y="{ly - 11}" width="14" height="14" rx="3" class="{cls}"/>')
        body.append(text(lx + 20, ly, label))
        lx += 34 + 7 * len(label)
    body.append(f'<line x1="{lx}" x2="{lx + 24}" y1="{ly - 4}" y2="{ly - 4}" class="frontier"/>')
    body.append(text(lx + 30, ly, "capacity"))
    capacities = []
    for n in nodes:
        held = [rate for rate in sorted(rates) if ("every_node", n, rate) in cell]
        best = 0
        for rate in held:
            if cell[("every_node", n, rate)]["cls"] != "held":
                break
            best = rate
        capacities.append(f"{best} at {n:,}")
    svg("capacity-n.svg", w, ly + 20, "More nodes carry more privacy transactions",
        "A grid of privacy rate against node count under the EIP tick, with 15 tx/s of signatures. "
        "The highest privacy rate held on every seed, with every lower rate held, rises with the "
        "network: " + ", ".join(capacities) + " nodes."
        + (" A second grid shows one builder that aggregates everything." if len(designs) > 1 else ""),
        body)


def capacities(rows, design):
    """Per node count: the highest p held with every lower p held, and the next p tried above
    it (None when every p tried held)."""
    out = {}
    for n in sorted({int(r["nodes"]) for r in rows if r["design"] == design}):
        tried = sorted((int(r["p"]), r["cls"]) for r in rows
                       if r["design"] == design and int(r["nodes"]) == n)
        held, above = 0, None
        for p, cls in tried:
            if cls != "held":
                above = p
                break
            held = p
        out[n] = (held, above)
    return out


def draw_capacity_relay():
    rows = read("capacity-n.csv")
    designs = [(d, cls, label) for d, cls, label in (
        ("every_node", "s1", "Flood: every raw transaction pushed to every node"),
        ("every_node_no_flood", "s2", "No flood: raw transactions stay at their entry node"),
        ("builder_only", "s3", "One builder aggregates (flood)"))
        if any(r["design"] == d for r in rows)]
    seeds = sorted({int(r["seeds"]) for r in rows})
    seed_text = f"{seeds[0]}" if seeds[0] == seeds[-1] else f"{seeds[0]}–{seeds[-1]}"
    nodes = [100, 300, 1000, 3000]
    nf = lambda v: f"{v:,}"
    px, py, pw, ph = 76, 124 + 18 * len(designs), 520, 260
    body = [text(20, 28, "Aggregating nodes carry more as the network grows; one builder doesn't",
                 "title"),
            text(20, 48, "Capacity: the highest privacy rate included at ≥ 95% on every seed, with "
                 "every lower rate held,", "sub"),
            text(20, 64, "on top of 15 tx/s of signatures, under the EIP's 1,000 ms tick. The bar "
                 "reaches the next rate", "sub"),
            text(20, 80, f"tried, which wasn't held. Priced by leanVM 990b935's cycle counts; "
                 f"{seed_text} seeds per cell.", "sub")]
    for k, (_, cls, label) in enumerate(designs):
        legend_row(body, 20, 106 + 18 * k, [(cls, label)])
    series = []
    caps = {}
    for design, cls, label in designs:
        caps[design] = capacities(rows, design)
        series.append((cls, [(n, caps[design][n][0]) for n in nodes if n in caps[design]],
                       None, 0))
    sx, sy = line_panel(body, px, py, pw, ph, "", nodes, nodes, 0, 80, [0, 20, 40, 60, 80],
                        series, nf, xlabel="nodes (log scale)",
                        ylabel="privacy tx/s held")
    for design, cls, label in designs:
        for n, (held, above) in caps[design].items():
            if above is None:
                continue
            body.append(f'<line x1="{sx(n):.1f}" x2="{sx(n):.1f}" y1="{sy(held):.1f}" '
                        f'y2="{sy(above):.1f}" class="{cls} range"><title>{esc(label)}, {n:,} '
                        f'nodes: {held} held, {above} not</title></line>')
        n = nodes[-1]
        held = caps[design][n][0]
        body.append(text(sx(n) + 10, sy(held) + 4, f"{held}", "val"))
    ratio = [caps["every_node_no_flood"][n][0] / caps["every_node"][n][0] for n in nodes
             if "every_node_no_flood" in caps and n in caps["every_node_no_flood"]]
    builder = (" One builder that proves everything holds "
               + ", ".join(sorted({f"{caps['builder_only'][n][0]}" for n in nodes
                                   if n in caps["builder_only"]}))
               + " at every size." if "builder_only" in caps else "")
    svg("capacity-relay.svg", px + pw + 60, py + ph + 52,
        "Aggregating nodes carry more as the network grows; one builder doesn't",
        "Capacity against node count, 100 to 3,000 nodes, under the EIP tick with 15 tx/s of "
        "signatures, priced by leanVM 990b935's cycle counts. With every raw transaction pushed "
        "to every node it rises from "
        + ", ".join(f"{caps['every_node'][n][0]}" for n in nodes)
        + " privacy tx/s; with raw transactions kept at their entry node, from "
        + (", ".join(f"{caps['every_node_no_flood'][n][0]}" for n in nodes) if ratio else "")
        + f" ({min(ratio):.0f}–{max(ratio):.0f} times as much)." + builder if ratio else "", body)


def draw_designs():
    """Capacity by design, under the three ways to share the work, six-object blocks. Seeds 101-103
    ran to 72 and seed 100 to 96, so a capacity is shown up to 72, with an arrow where a seed held
    the top of its ladder."""
    rows = [r for r in read("designs.csv") if r["block"] == "6"]
    cells = {}
    for r in rows:
        cells.setdefault((int(r["design"]), r["participation"], int(r["nodes"])), []).append(
            (min(int(r["capacity"]), 72), r["at_top"] == "1" or int(r["capacity"]) >= 72))
    designs = ["1, push", "2, pull", "3, keep", "4, coverage", "5, geth today"]
    panels = [("every", "Every node aggregates"), ("quarter", "A quarter aggregate"),
              ("builder", "One builder proves everything")]
    sizes = [(100, "s2", -7, "100 nodes"), (1000, "s1", 7, "1,000 nodes")]
    x0, pw, pgap, rh = 112, 226, 34, 40
    w = x0 + 3 * pw + 2 * pgap + 20
    body = [text(20, 28, "How raw transactions travel decides capacity once only some nodes "
                 "aggregate", "title"),
            text(20, 48, "Privacy tx/s held on top of 15 signature tx/s, range over 4 seeds; the "
                 "EIP's 1,000 ms tick, the fast prover, six-object blocks.", "sub"),
            text(20, 64, "A node drawn at random proposes each slot; one builder proposes every "
                 "block.", "sub")]
    legend_row(body, 20, 92, [(cls, label) for _, cls, _, label in sizes])
    body.append('<path d="M262,83.5 L269,88 L262,92.5 Z" class="m1"/>')
    body.append(text(278, 92, "held at 72, the top rate every seed ran (seed 100 ran to 96)"))
    py = 132
    ph = len(designs) * rh
    for k, (participation, title) in enumerate(panels):
        px = x0 + k * (pw + pgap)
        sx = log_scale(2.4, 90, px, px + pw)
        body.append(text(px, py - 12, title, "head"))
        for t in (3, 6, 9, 12, 18, 27, 36, 54, 72):  # the load ladder's steps
            body.append(f'<line x1="{sx(t):.1f}" x2="{sx(t):.1f}" y1="{py}" y2="{py + ph}" '
                        f'class="grid"/>')
            body.append(text(sx(t), py + ph + 16, str(t), "ax", "middle"))
        body.append(text(px + pw / 2, py + ph + 34, "privacy tx/s held (log scale)", "ax",
                         "middle"))
        for i, design in enumerate(designs):
            cy = py + i * rh + rh / 2
            if k == 0:
                body.append(text(x0 - 14, cy + 4, design, "lab", "end"))
            for nodes, cls, dy, label in sizes:
                seeds = cells[(i + 1, participation, nodes)]
                lo, hi = min(v for v, _ in seeds), max(v for v, _ in seeds)
                top = any(t for _, t in seeds)
                shown = (f"at least {hi}" if lo == hi else f"{lo} to at least {hi}") if top \
                    else (f"{lo}" if lo == hi else f"{lo}–{hi}")
                y = cy + dy
                tip = (f"<title>{esc(design)}, {esc(title.lower())}, {label}: {shown} "
                       "privacy tx/s</title>")
                if hi > lo:
                    body.append(f'<line x1="{sx(lo):.1f}" x2="{sx(hi):.1f}" y1="{y:.1f}" '
                                f'y2="{y:.1f}" class="{cls} range">{tip}</line>')
                for v in sorted({lo, hi}):
                    body.append(f'<circle cx="{sx(v):.1f}" cy="{y:.1f}" r="4.5" '
                                f'class="{marker_class(cls)}">{tip}</circle>')
                if top:
                    ax = sx(hi) + 7
                    body.append(f'<path d="M{ax:.1f},{y - 4.5:.1f} L{ax + 7:.1f},{y:.1f} '
                                f'L{ax:.1f},{y + 4.5:.1f} Z" class="{marker_class(cls)}"/>')
    svg("designs.svg", w, py + ph + 52,
        "How raw transactions travel decides capacity once only some nodes aggregate",
        "Privacy capacity of the five transport designs at 100 and 1,000 nodes, under three ways "
        "to share the work. With every node aggregating, every design holds at least 72 privacy "
        "tx/s at 1,000 nodes, and push 54 at 100. With a quarter of the nodes aggregating, at "
        "1,000 nodes, push holds 6, pull 18, keep and coverage 36-54, and geth's relay at least "
        "72. One builder holds 6-9 in every design but push, which holds 3-6.",
        body)


def draw_cores():
    rows = read("leanvm-threads.csv")
    pts = [(int(r["threads"]), 1000 * float(r["prove_s"])) for r in rows]
    w, px, py, pw, ph = 760, 70, 104, 470, 240
    sy = lin_scale(0, 1500, py + ph, py)
    slot = pw / len(pts)
    body = [text(20, 28, "What a node's cores buy", "title"),
            text(20, 48, "leanVM's README 2→1 (900 leanXMSS per leaf, rate 1/4) on a Ryzen 9 8945HS "
                 "(8 cores), by threads given to proving.", "sub"),
            text(20, 66, "Dashed: version 10's three reference provers. The fast one is the M4 "
                 "Max's 303 ms from the same README.", "sub")]
    for t in (0, 500, 1000, 1500):
        body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" '
                    f'class="{"axis" if t == 0 else "grid"}"/>')
        body.append(text(px - 6, sy(t) + 4, f"{t:,}", "ax", "end"))
    ytitle(body, px - 44, py, ph, "2→1 proving time (ms)")
    for v, label in ((303, "fast: M4 Max, 303 ms"), (606, "2× slower, 606 ms"),
                     (1212, "4× slower, 1,212 ms")):
        body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" class="ref"/>')
        body.append(text(px + pw + 8, sy(v) + 4, label, "ax"))
    for i, (threads, ms) in enumerate(sorted(pts, reverse=True)):
        x = px + i * slot + slot * 0.25
        bw = slot * 0.5
        top = sy(ms)
        body.append(f'<path d="M{x:.1f},{sy(0):.1f} V{top + 4:.1f} q0,-4 4,-4 H{x + bw - 4:.1f} '
                    f'q4,0 4,4 V{sy(0):.1f} Z" class="bar"><title>{threads} threads: '
                    f'{ms:.0f} ms, {ms / 303:.1f}× the M4 Max</title></path>')
        body.append(text(x + bw / 2, top - 8, f"{ms:,.0f} ms", "val", "middle"))
        body.append(text(x + bw / 2, sy(0) + 16, f"{threads} threads", "ax", "middle"))
        body.append(text(x + bw / 2, sy(0) + 31, f"{ms / 303:.1f}× M4 Max", "ax", "middle"))
    svg("cores.svg", w, py + ph + 50, "What a node's cores buy",
        "Proving time of leanVM's README 2-to-1 on a Ryzen 9 8945HS: 566 ms on 16 threads and 588 "
        "on 8 (1.9 times the M4 Max's 303 ms), 816 on 4 (2.7 times) and 1,418 on 2 (4.7 times), "
        "beyond version 10's 4 times slower reference prover.", body)


def draw_cpu_model():
    rows = [r for r in read("leanvm-16-threads.csv") if r["rate"] == "2"]
    pts = [(int(r["cycles"]) / 1e6, int(r["committed"]) / 1e6, float(r["prove_s"]), r["kind"])
           for r in rows]
    w, ph, pw = 860, 220, 300
    body = [text(20, 28, "What a proof's time follows", "title"),
            text(20, 48, "leanVM 990b935 on a Ryzen 9 8945HS, 16 threads, rate 1/4: leaves of "
                 "16 and 512 leanSPHINCS, and 2-, 4- and 8-child folds.", "sub")]
    legend_row(body, 20, 76, [("s1", "folds"), ("s2", "leaves")])
    py = 124
    xs = [p[2] for p in pts]
    committed = [p[1] for p in pts]
    n = len(pts)
    mx, my = sum(committed) / n, sum(xs) / n
    b = sum((x - mx) * (y - my) for x, y in zip(committed, xs)) / sum((x - mx) ** 2 for x in committed)
    a = my - b * mx
    for k, (title, idx, hi, ticks, xlabel) in enumerate((
            ("Against cycles: two prices", 0, 2.2, [0, 0.5, 1, 1.5, 2], "VM cycles (millions)"),
            ("Against committed size: one price", 1, 70, [0, 20, 40, 60],
             "committed field elements (millions)"))):
        px = 70 + k * (pw + 110)
        sx = lin_scale(0, hi, px, px + pw)
        sy = lin_scale(0, 1.8, py + ph, py)
        body.append(text(px, py - 14, title, "head"))
        for t in (0, 0.5, 1, 1.5):
            body.append(f'<line x1="{px}" x2="{px + pw}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" '
                        f'class="{"axis" if t == 0 else "grid"}"/>')
            body.append(text(px - 6, sy(t) + 4, f"{t:g}", "ax", "end"))
        ytitle(body, px - 32, py, ph, "proving time (s)")
        for t in ticks:
            body.append(text(sx(t), py + ph + 16, f"{t:g}", "ax", "middle"))
        body.append(text(px + pw / 2, py + ph + 34, xlabel, "ax", "middle"))
        if idx == 1:
            body.append(f'<path d="M{sx(0):.1f},{sy(a):.1f} L{sx(68):.1f},{sy(a + b * 68):.1f}" class="fit"/>')
            body.append(text(sx(2), sy(1.62), f"≈ {a * 1000:.0f} ms + {b * 1000:.1f} ms per million", "lab"))
        else:
            for kind, cls in (("rec", "s1"), ("leaf", "s2")):
                kp = sorted((p[0], p[2]) for p in pts if p[3] == kind)
                d = " ".join(f"{'M' if i == 0 else 'L'}{sx(x):.1f},{sy(y):.1f}" for i, (x, y) in enumerate(kp))
                body.append(f'<path d="{d}" class="{cls}" opacity="0.5"/>')
            body.append(text(sx(0.95) - 8, sy(1.507) - 10, "leaves: 1.6 s per million", "lab", "end"))
            body.append(text(sx(1.65) + 4, sy(1.418) + 26, "folds: 0.8 s per million", "lab"))
        for p in pts:
            cls = "m1" if p[3] == "rec" else "m2"
            body.append(f'<circle cx="{sx(p[idx]):.1f}" cy="{sy(p[2]):.1f}" r="4.5" class="{cls}">'
                        f'<title>{"fold" if p[3] == "rec" else "leaf"}: {p[2]:.3f} s, '
                        f'{p[0]:.2f} M cycles, {p[1]:.1f} M committed</title></circle>')
    svg("cpu-model.svg", w, py + ph + 52, "What a proof's time follows",
        "Proving time against cycles and against committed size. Against cycles, leaves and "
        "folds fall on two lines with prices a factor of two apart. Against committed size, "
        f"all fall on one line, about {a * 1000:.0f} ms plus {b * 1000:.1f} ms per million "
        "committed elements.", body)


EXTRACT = {
    "capacity": (3, extract_capacity),
    "scaling": (3, extract_scaling),
    "leaf-multiplicity": (1, extract_leaf_multiplicity),
    "partial-aggregation": (1, extract_partial),
    "interval-cycles": (1, extract_interval_cycles),
    "privacy-1000": (1, extract_privacy_1000),
    "privacy-40": (2, extract_privacy_40),
    "interval": (2, lambda d303, d871: (extract_interval([d303], [d871]), extract_latency([d303]))),
    "designs": (1, extract_designs),
    "leanvm-16-threads": (1, extract_leanvm_16_threads),
    "leanvm-threads": (1, extract_leanvm_threads),
}


def main(argv):
    if len(argv) > 2 and argv[1] == "extract" and argv[2] in EXTRACT:
        count, extract = EXTRACT[argv[2]]
        if len(argv) - 3 != count:
            sys.exit(f"{argv[2]} takes {count} argument(s)\n\n{__doc__}")
        extract(*argv[3:])
    elif argv[1:] == ["draw"]:
        draw_w()
        draw_scaling()
        draw_privacy()
        draw_cpu_model()
        draw_cores()
        draw_latency()
        draw_partial()
        draw_scaling3000()
        draw_capacity()
        draw_capacity_relay()
        draw_designs()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
