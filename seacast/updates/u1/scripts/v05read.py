#!/usr/bin/env python3
"""Read SEACAST's cell logs as Figures 4 and 5 read them, plus what version 0.5's rules did.

    python3 v05read.py LOG...            one row per log
    python3 v05read.py --csv LOG...      the same as CSV

Per cell, over the warm payloads (2-6), as the figures' CSVs (data/seacast_compare.csv,
data/seacast_elastic_all.csv):
  p99_s   the median over warm payloads of each payload's time for 99 % of the nodes to hold enough
          chunks (its `<rate>Mbps L=... phase` result line), as the figures' CSVs have it; the
          `messages:` summary line's warm median can differ by a millisecond (unrounded values);
  mib     the median over warm payloads of `link rx/node`, what each downlink took in by the
          network's completion, in MiB (it includes what still waited in a downlink then);
  sock_mib  the same for `socket rx/node`, what had reached the sockets ("-" in logs without
          that line).
Also, medians over the warm payloads: broken promises and peers parked, offer-table retries, honest
ids asked and pushes, cancelled and projected at dispatch, and each counter of version 0.5's rules
from the `v0.5 this message:` line (absent on cells run without SEGMENT_V05).
"""
import argparse
import os
import re
import statistics as st
import sys

V05_KEYS = ["at_write", "lost", "unpushed", "owed", "owed_sent", "answers_owed", "lr_armed", "lr_asks",
            "lr_parked", "beyond_list", "closed", "ledger", "expired", "discards"]


def tag_fields(path):
    b = os.path.basename(path)
    up = re.search(r"_u(\d+)_", b)
    seed = re.search(r"seed(\d+)", b)
    net = "dcb20" if "_dcb20_" in b else "dc20" if "_dc20_" in b else "all-home"
    x = re.search(r"_m6_(?:dcb20_|dc20_)?(.+?)_s0a_", b)
    return {"net": net, "up": int(up.group(1)) if up else 50, "seed": int(seed.group(1)) if seed else -1,
            "xtag": x.group(1) if x else "?"}


def read(path):
    msgs = []  # per message: dict
    cur = None
    p99 = None
    p99s = []  # per payload, in order, from the result lines
    passed = False
    with open(path, errors="replace") as fh:
        for line in fh:
            m = re.search(r"=== message (\d+)/(\d+)", line)
            if m:
                cur = {"msg": int(m.group(1))}
                msgs.append(cur)
                continue
            if "--- PASS: TestQ6RealisticMesh" in line:
                passed = True
            m = re.search(r"\d+Mbps L=\S+\s+n=\d+ \S+\s+\d+/\d+ .* p99 (\d+(?:\.\d+)?)(ms|s) ", line)
            if m:
                p99s.append(float(m.group(1)) / (1000 if m.group(2) == "ms" else 1))
            m = re.search(r"messages: M=\d+ .*warm \(2\.\.\d+\) median \[min\.\.max\]: p50 \d+ \[[^]]*\] p90 \d+ \[[^]]*\] p99 (\d+)", line)
            if m:
                p99 = int(m.group(1)) / 1000
            if cur is None:
                continue
            m = re.search(r"link rx/node (\d+)B", line)
            if m:
                cur["linkrx"] = int(m.group(1))
            m = re.search(r"socket rx/node (\d+)B", line)
            if m:
                cur["sockrx"] = int(m.group(1))
            m = re.search(r"commitment enforcement this message: (\d+) broken promises, (\d+) peers parked; offer-table retries (\d+)", line)
            if m:
                cur["breaks"], cur["parks"], cur["retries"] = map(int, m.groups())
            m = re.search(r"requests@3000ms \[honest \d+\]: ids asked (\d+) .* pushes (\d+);", line)
            if m:
                cur["asked"], cur["pushes"] = map(int, m.groups())
            m = re.search(r"outbound@3000ms \[honest \d+\]: .* cancelled at dispatch (\d+), .* projected (\d+)", line)
            if m:
                cur["cancelled"], cur["projected"] = map(int, m.groups())
            if "v0.5 this message:" in line:
                nums = [int(x) for x in re.findall(r"(?<![\w.])(\d+)(?![\w.])", line.split("v0.5 this message:")[1])]
                for k, v in zip(V05_KEYS, nums):
                    cur["v05_" + k] = v
    if len(p99s) >= 2:
        p99 = st.median(p99s[1:])  # warm payloads, 2 on
    return msgs, p99, passed


def warm_median(msgs, key):
    vals = [m[key] for m in msgs if m["msg"] >= 2 and key in m]
    return st.median(vals) if vals else None


def row(path):
    msgs, p99, passed = read(path)
    r = tag_fields(path)
    r.update({"passed": passed, "msgs": len(msgs), "p99_s": p99})
    lr = warm_median(msgs, "linkrx")
    r["mib"] = lr / 1048576 if lr is not None else None
    sr = warm_median(msgs, "sockrx")
    r["sock_mib"] = sr / 1048576 if sr is not None else None
    for k in ["breaks", "parks", "retries", "asked", "pushes", "cancelled", "projected"] + ["v05_" + k for k in V05_KEYS]:
        r[k] = warm_median(msgs, k)
    r["log"] = os.path.basename(path)
    return r


COLS = ["net", "up", "xtag", "seed", "passed", "msgs", "p99_s", "mib", "sock_mib", "breaks", "parks", "retries", "asked",
        "pushes", "cancelled", "projected"] + ["v05_" + k for k in V05_KEYS]


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.4f}" if v < 100 else f"{v:.0f}"
    return str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("logs", nargs="+")
    a = ap.parse_args()
    rows = [row(p) for p in a.logs]
    sep = "," if a.csv else "\t"
    print(sep.join(COLS))
    for r in rows:
        print(sep.join(fmt(r[c]) for c in COLS))


if __name__ == "__main__":
    main()
