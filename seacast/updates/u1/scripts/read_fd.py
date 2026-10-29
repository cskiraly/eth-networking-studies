#!/usr/bin/env python3
"""Figure 4's two numbers from cell logs: read_fd.py LOG... [--csv NETWORK,PROTOCOL]

Per log (one cell, six payloads): p99 is the median over warm payloads 2-6 of each payload's p99 on
its summary line; MiB is the median over the same payloads of the "link rx/node" line that follows
it, / 2^20. A cell counts only if every payload's summary line shows every receiver complete. With --csv the rows are seacast_compare.csv's
(network, protocol, seed, p99_s, mib, connections); without, a table with the per-payload values.
"""
import re
import statistics
import sys

SUMMARY = re.compile(r" (whole|segmented|phase|ecrs|fulldas) +(\d+)/(\d+) .*?p99 ([\d.]+)(m?s) ")
LINKRX = re.compile(r"link rx/node (\d+)B")
MESSAGE = re.compile(r"=== message (\d+)/(\d+)")
SEED = re.compile(r"_seed(\d+)")
DEGREE = re.compile(r"\[degree (\d+),")


def read(path):
    msgs = {}
    cur = None
    degree = None
    with open(path, errors="replace") as f:
        for line in f:
            m = MESSAGE.search(line)
            if m:
                cur = int(m.group(1))
                msgs[cur] = {}
                continue
            if cur is None:
                continue
            s = SUMMARY.search(line)
            if s and "p99" not in msgs[cur]:
                v = float(s.group(4))
                msgs[cur]["p99"] = v / 1000 if s.group(5) == "ms" else v
                msgs[cur]["ok"] = s.group(2) == s.group(3)
                d = DEGREE.search(line)
                if d:
                    degree = int(d.group(1))
                continue
            r = LINKRX.search(line)
            if r and "p99" in msgs[cur] and "rx" not in msgs[cur]:
                msgs[cur]["rx"] = int(r.group(1))
    warm = [msgs[k] for k in range(2, 7) if k in msgs]
    # Every payload complete, the cold one included; the figures read the warm ones.
    complete = len(warm) == 5 and all(v.get("ok") and "rx" in v for v in msgs.values())
    p99 = statistics.median(w["p99"] for w in warm) if complete else None
    mib = statistics.median(w["rx"] for w in warm) / 2**20 if complete else None
    return {"msgs": msgs, "complete": complete, "p99": p99, "mib": mib, "degree": degree}


def main(argv):
    csv = None
    if "--csv" in argv:
        i = argv.index("--csv")
        csv = argv[i + 1].split(",")
        argv = argv[:i] + argv[i + 2:]
    for path in argv:
        r = read(path)
        seed = SEED.search(path)
        seed = seed.group(1) if seed else "?"
        if csv:
            if not r["complete"]:
                print(f"# {path}: incomplete", file=sys.stderr)
                continue
            print(f"{csv[0]},{csv[1]},{seed},{r['p99']:.4f},{r['mib']:.4f},{r['degree']}")
            continue
        per = " ".join(f"{k}:{v.get('p99', float('nan')):.3f}s/{v.get('rx', 0) / 2**20:.2f}MiB{'' if v.get('ok') else '!'}" for k, v in sorted(r["msgs"].items()))
        head = f"p99 {r['p99']:.4f} s, {r['mib']:.4f} MiB" if r["complete"] else "INCOMPLETE"
        print(f"{path}: seed {seed}: {head}; {per}")


if __name__ == "__main__":
    main(sys.argv[1:])
