# The figures

The post's figures are in `post/`, as uploaded: PNGs of these SVGs rasterized at twice their size
with headless Chromium, on white. The exception is `aggregation.png`, a diagram drawn by hand
(`post/aggregation.svg`). First Questions version 11 shows the SVGs themselves.

`figures.py` makes them from the runs in two steps:
- `python3 -I figures.py extract SERIES DIR...` reads the runs into `data/*.csv`;
- `python3 -I figures.py draw` draws every SVG here from `data/`.

Its docstring lists the series each data file reads. Rerun on the stored runs, every data file
came out byte for byte, and `draw` redraws every SVG byte for byte from them.

| figure | data | series | shown in |
| --- | --- | --- | --- |
| `holds-grid` Which designs keep up, at 1,000 nodes | `interval.csv` | `interval-303ms`, `interval-871ms` | the post; version 11, section 1 |
| `latency` How long a transaction waits for a block | `latency.csv` | `interval-303ms` | the post; section 7 |
| `designs` How raw transactions travel decides capacity once only some nodes aggregate | `designs.csv` | transport's `designs-random-proposer.md` | the post; section 3 |
| `partial-aggregation` What happens when fewer nodes aggregate | `partial-aggregation.csv` | `partial-aggregation` | the post; section 3 |
| `capacity-n` More nodes carry more privacy transactions | `capacity-n.csv` | `capacity-every-node`, `capacity-no-flood`, `capacity-one-builder` | section 2 |
| `capacity-relay` Aggregating nodes carry more as the network grows; one builder doesn't | `capacity-n.csv` | as above | section 2 |
| `scaling-3000` Delay grows slowly with the network | `scaling-3000.csv` | `scaling`, `interval-cycles` | section 2 |
| `scaling-n` What grows with the number of nodes | `scaling-n.csv` | `leaf-multiplicity` | section 2 |
| `privacy-frontier` Prover speed sets privacy capacity | `privacy-frontier.csv`, `privacy-frontier-1000.csv` | `privacy-40`, `privacy-40-tickless`, `privacy-1000`, `interval-cycles` | section 4 |
| `cpu-model` What a proof's time follows | `leanvm-16-threads.csv` | `leanvm-16-threads` | section 6 |
| `cores` What a node's cores buy | `leanvm-threads.csv` | `leanvm-threads` | section 6 |

Two data files have no figure: `throughput.csv` is the table of version 11's section 5 (series
`throughput` and `interval-cycles`), and `interval-cycles.csv` holds `interval-cycles`' cells, which
`privacy-frontier-1000.csv` reads for its fast prover.

The series are in [`../interval/`](../interval/) (`interval-*`),
[`../transport/`](../transport/), [`../cycle-prices/`](../cycle-prices/) and
[`../leanvm/`](../leanvm/).
