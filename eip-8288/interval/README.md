# The aggregation interval, the prover and the signature size

The runs behind the post's interval section, its signature-size bullet and its latency line, and
behind First Questions version 11's section 4 and its holds-grid and latency figures: the
fold-timing comparison on calibration v2 (`--calibration leanvm-990b935-timed --proof-size
fold`), 1,000 nodes (10,000 in the `nodes-10000-` series) on a degree-6 mesh, 25 Mbit/s uplinks,
12 s slots.

The runs ran on development commits of the simulator that version 2.5 squashes, on Python 3.12
or 3.13. Every interval run that [`../replay/`](../replay/) ran again on version 2.5, one of each
series but `bind-no-budget` and `bind-capacity`, gave every number back exactly. Seeds 104–107 of
`interval-845ms` and the `bind-` series ran on the last of those commits, whose tree is version
2.5's.

## configs/

One line per run: `cell`, `seed`, and the `bench.mainnet` command, run from the simulator's
checkout. Each run writes one record to stdout; save it as `<cell>.jsonl`, one directory per
series.

| series | runs | what it is |
| --- | --- | --- |
| `interval-303ms` | 600 | three designs (`tick1000`, the 1,000 ms tick with a 1,000 ms proving budget; `tick2000`, the 2,000 ms tick, and `tickless`, folding when ready, with 2,000 ms) × 10, 20, 30, 45 and 60 tx/s × privacy share 0, 0.2 and 0.5 × leanSTARK factor 1 and 2 (2 only with privacy) × seeds 100–107, at the 303 ms anchor (leanVM's benchmark machine) |
| `interval-871ms` | 600 | the same at `--anchor-ms 871` (four cores of a Ryzen 9 8945HS) |
| `signatures-7740b` | 120 | the all-signature cells of `interval-303ms` with 7,740-byte signatures (`--sig-witness-bytes 7740`) |
| `bind-no-budget` | 24 | what binds at 871 ms: the 1,000 ms tick, a fifth private, 10, 20 and 45 tx/s, seeds 100–107, with no proving budget |
| `bind-capacity` | 24 | the same at the 303 ms anchor with the budget that keeps 871 ms's fold widths (347.876 ms = 1,000 × 303 / 871) |
| `bind-uplink` | 24 | the same at 871 ms with ten times the uplink (`--uplink-mbps 250`) |
| `interval-845ms` | 24 | the 1,000 ms tick, a fifth private, 10, 20 and 45 tx/s, seeds 100–107, at `--anchor-ms 845` (the four cores' median pass; 871 ms is their mean): three nested proofs fit one 1,000 ms fold there, two at 871 ms |
| `nodes-10000-303ms` | 348 | `interval-303ms` with `--nodes 10000`, seeds 100–103; seeds 104–107 too for the 1,000 ms tick at 10, 20 and 30 tx/s without privacy and at 60 tx/s at every share and factor, and for the other two designs at 20 and 30 tx/s without privacy |
| `nodes-10000-871ms` | 316 | `interval-871ms` with `--nodes 10000`, seeds 100–103; seeds 104–107 too for the 1,000 ms and the 2,000 ms tick at a fifth private, 10 and 20 tx/s |
| `nodes-10000-signatures-7740b` | 60 | `signatures-7740b` with `--nodes 10000`, seeds 100–103 |
| `nodes-10000-845ms` | 12 | `interval-845ms` with `--nodes 10000`, seeds 100–103 |
| `nodes-10000-bind-no-budget`, `nodes-10000-bind-capacity`, `nodes-10000-bind-uplink` | 12 each | the three `bind-` series with `--nodes 10000`, seeds 100–103 |

Each `nodes-10000-` command differs from its 1,000-node command only in `--nodes`.

A 1,000-node run takes up to about 15 minutes on one core of that Ryzen, and peaks below
1 GiB. A 10,000-node run took 5–15 times as long (15 minutes to 3 hours on one server core)
and peaked at 13.3 GiB.

## scripts/ and data/

`scripts/w_tables.py` reads the records (any file names: it identifies each run from its own
record) and writes the tables in `data/`:

```sh
python3 scripts/w_tables.py compare data/interval-871ms-vs-303ms 303ms 871ms runs/interval-303ms runs/interval-871ms
python3 scripts/w_tables.py compare data/signatures-7740b-vs-2560b 2560b 7740b runs/interval-303ms runs/signatures-7740b
python3 scripts/w_tables.py control data/what-binds-871ms runs/interval-871ms runs/interval-303ms runs/bind-no-budget runs/bind-capacity runs/bind-uplink
python3 scripts/w_tables.py compare data/interval-871ms-vs-845ms 871ms 845ms runs/interval-871ms runs/interval-845ms
python3 scripts/w_tables.py compare data/nodes-1000-vs-10000-303ms 1000 10000 runs/interval-303ms runs/nodes-10000-303ms
python3 scripts/w_tables.py compare data/nodes-1000-vs-10000-871ms 1000 10000 runs/interval-871ms runs/nodes-10000-871ms
python3 scripts/w_tables.py compare data/nodes-1000-vs-10000-signatures-7740b 1000 10000 runs/signatures-7740b runs/nodes-10000-signatures-7740b
python3 scripts/w_tables.py compare data/nodes-1000-vs-10000-845ms 1000 10000 runs/interval-845ms runs/nodes-10000-845ms
python3 scripts/w_tables.py compare data/nodes-1000-vs-10000-bind-no-budget 1000 10000 runs/bind-no-budget runs/nodes-10000-bind-no-budget
python3 scripts/w_tables.py compare data/nodes-1000-vs-10000-bind-capacity 1000 10000 runs/bind-capacity runs/nodes-10000-bind-capacity
python3 scripts/w_tables.py compare data/nodes-1000-vs-10000-bind-uplink 1000 10000 runs/bind-uplink runs/nodes-10000-bind-uplink
python3 scripts/w_tables.py compare data/nodes-10000-interval-871ms-vs-303ms 303ms 871ms runs/nodes-10000-303ms runs/nodes-10000-871ms
python3 scripts/w_tables.py compare data/nodes-10000-signatures-7740b-vs-2560b 2560b 7740b runs/nodes-10000-303ms runs/nodes-10000-signatures-7740b
python3 scripts/w_tables.py control data/nodes-10000-what-binds-871ms runs/nodes-10000-871ms runs/nodes-10000-303ms runs/nodes-10000-bind-no-budget runs/nodes-10000-bind-capacity runs/nodes-10000-bind-uplink
python3 scripts/w_tables.py compare data/nodes-10000-interval-871ms-vs-845ms 871ms 845ms runs/nodes-10000-871ms runs/nodes-10000-845ms
```

- `interval-871ms-vs-303ms`: per design, share, rate and factor, the class at each anchor (held:
  every seed includes at least 95% of the transactions that arrived; collapsed: every seed below
  60%; marginal otherwise), the worst seed, CPU and uplink utilisation, mean delay and the paired
  delay difference, and the budget stops at 871 ms.
- `signatures-7740b-vs-2560b`: the same for the signature size.
- `what-binds-871ms`: each arm beside the 871 ms runs (and arm B beside the 303 ms runs), seed by
  seed, on every seed that all five sets have.
- `interval-871ms-vs-845ms`: the 1,000 ms tick's privacy cells at the 845 ms anchor beside the same
  runs at 871 ms, as `interval-871ms-vs-303ms`.
- `nodes-1000-vs-10000-*`: each 10,000-node series beside the same cells and seeds at 1,000
  nodes, as `interval-871ms-vs-303ms`.
- `nodes-10000-*`: `interval-871ms-vs-303ms`, `signatures-7740b-vs-2560b`, `what-binds-871ms` and
  `interval-871ms-vs-845ms` from the 10,000-node runs (every seed all their sets share: 100–103
  for `what-binds`).

Each table was made by this script from the runs listed in configs/, and each equals, row for row,
the table the post's numbers were read from.
