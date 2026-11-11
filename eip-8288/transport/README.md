# The transport designs: how transactions and proofs travel

The runs behind the post's and First Questions version 11's numbers on the five transport designs
(push, pull, keep, coverage, geth's relay of today), under the three ways to share the work (every
node aggregating, one builder, a quarter of the nodes aggregating), at 100 and 1,000 nodes, on
seeds 100 to 103, at calibration v2 prices (leanVM 990b935's folds, timed).

- **Code:** stark-mempool-sim v2.5, this record's pin. The stored runs were made on a commit
  whose simulator code is v2.5's; only tests and docs differ. Run on Python 3.12.
- **`configs/`:** one TSV per series, `cell`, `seed`, `command`. Run each command from the
  stark-mempool-sim checkout's root, and keep its standard output as `<cell>.jsonl`, all in one
  directory. Write it through a temporary file and rename it when the run finishes: the scripts
  count a run when its `<cell>.jsonl` exists, and read its last line.
- **`scripts/`:** each takes that directory and writes one file of `data/`, byte for byte:
  `python3 scripts/designs_fixed_proposer.py RUNS > data/designs-fixed-proposer.md`. `runs.py`
  explains the cell names; `--used FILE` lists the runs a table read.
- **`data/`:** the tables.

| table | what it holds | series it reads |
| --- | --- | --- |
| `designs-fixed-proposer.md` | capacity by design, setting and size, each seed, one fixed proposer; upload and delay per node at today's load; 7,740 B signatures; 2 signature tx/s | `designs-fixed-proposer`, `signatures-7740-bytes`, `signatures-2-per-second` |
| `designs-random-proposer.md` | capacity with a random proposer (every node, a quarter aggregating); one builder as above | `designs-random-proposer`, `designs-fixed-proposer` |
| `controls.txt` | seed 100's controls: request timeouts of 5 s and 500 ms, design 4's fold order by fee per proving cost, one builder proving 1,000 times faster | `request-timeout-5s`, `request-timeout-500ms`, `fold-order-fee-per-proving-cost`, `prover-1000-times-faster`, `designs-fixed-proposer` |
| `proposer-every-node.txt` | every node aggregating, a random proposer against the fixed one, cell by cell | `designs-random-proposer`, `designs-fixed-proposer` |
| `proposer-other-aggregator.txt` | a quarter aggregating, designs 2 and 5: node 0, another aggregator fixed as the proposer, and a random proposer, cell by cell at node 0's edges, and the steps each held per series | `fixed-proposer-other-aggregator`, `designs-fixed-proposer`, `designs-random-proposer` |

A capacity is the highest step of privacy load, on top of 15 signature tx/s, at which a run
includes at least 95% of its transactions by its end (five 12 s slots of load and two to drain),
with every lower step run held. Seed 100 ran the whole ladder with one fixed proposer; the other
runs ran the steps around each edge, and steps not run are taken as held.
