# The aggregation interval, the prover and the signature size

The runs behind the post's interval section, its signature-size bullet and its latency line, and
behind First Questions version 11's section 4 and its holds-grid and latency figures: the
fold-timing comparison on calibration v2 (`--calibration leanvm-990b935-timed --proof-size
fold`), 1,000 nodes on a degree-6 mesh, 25 Mbit/s uplinks, 12 s slots.

## configs/

One line per run: `cell`, `seed`, and the `bench.mainnet` command, run from the simulator's
checkout. Each run writes one record to stdout; save it as `<cell>.jsonl`, one directory per
series.

| series | runs | what it is |
| --- | --- | --- |
| `interval-303ms` | 600 | three designs (`tick1000`, the 1,000 ms tick with a 1,000 ms proving budget; `tick2000`, the 2,000 ms tick, and `tickless`, folding when ready, with 2,000 ms) × 10, 20, 30, 45 and 60 tx/s × privacy share 0, 0.2 and 0.5 × leanSTARK factor 1 and 2 (2 only with privacy) × seeds 100–107, at the 303 ms anchor (leanVM's benchmark machine) |
| `interval-871ms` | 600 | the same at `--anchor-ms 871` (four cores of a Ryzen 9 8945HS) |
| `signatures-7740b` | 120 | the all-signature cells of `interval-303ms` with 7,740-byte signatures (`--sig-witness-bytes 7740`) |
| `bind-no-budget` | 12 | what binds at 871 ms: the 1,000 ms tick, a fifth private, 10, 20 and 45 tx/s, seeds 100–103, with no proving budget |
| `bind-capacity` | 12 | the same at the 303 ms anchor with the budget that keeps 871 ms's fold widths (347.876 ms = 1,000 × 303 / 871) |
| `bind-uplink` | 12 | the same at 871 ms with ten times the uplink (`--uplink-mbps 250`) |

A 1,000-node run takes up to about 15 minutes on one core of that Ryzen, and peaks below
1 GiB.

## scripts/ and data/

`scripts/w_tables.py` reads the records (any file names: it identifies each run from its own
record) and writes the tables in `data/`:

```sh
python3 scripts/w_tables.py compare data/interval-871ms-vs-303ms 303ms 871ms runs/interval-303ms runs/interval-871ms
python3 scripts/w_tables.py compare data/signatures-7740b-vs-2560b 2560b 7740b runs/interval-303ms runs/signatures-7740b
python3 scripts/w_tables.py control data/what-binds-871ms runs/interval-871ms runs/interval-303ms runs/bind-no-budget runs/bind-capacity runs/bind-uplink
```

- `interval-871ms-vs-303ms`: per design, share, rate and factor, the class at each anchor (held:
  every seed includes at least 95% of the transactions that arrived; collapsed: every seed below
  60%; marginal otherwise), the worst seed, CPU and uplink utilisation, mean delay and the paired
  delay difference, and the budget stops at 871 ms.
- `signatures-7740b-vs-2560b`: the same for the signature size.
- `what-binds-871ms`: each arm beside the 871 ms runs (and arm B beside the 303 ms runs), seed by
  seed.

Each table was made by this script from the runs listed in configs/, and each equals, row for row,
the table the post's numbers were read from.
