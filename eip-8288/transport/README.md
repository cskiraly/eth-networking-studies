# The transport designs: how transactions and proofs travel

The runs behind the post's and First Questions version 11's numbers on the five transport designs
(push, pull, keep, coverage, geth's rules), under the three ways to share the work (every
node aggregating, one builder, a quarter of the nodes aggregating), at 100, 1,000 and 10,000
nodes, on seeds 100 to 107, at calibration v2 prices (leanVM 990b935's folds, timed). The post's
first record had 100 and 1,000 nodes on seeds 100 to 103. The second added 10,000 nodes (today's
load, and the steps around each 1,000-node edge), pull with one builder at 7,740 B at 100 and
1,000 nodes, and seeds 104 to 107.

- **Code:** stark-mempool-sim v2.5, this record's pin. Seeds 100 to 103 were run on a commit
  whose simulator code is v2.5's, where only tests and docs differ, and seeds 104 to 107 on v2.5's
  own tree. Run on Python 3.12. One stored run of
  each kind the second record added was run again on v2.5 and compared number by number: see the
  record's `replay/`.
- **`configs/`:** one TSV per series, `cell`, `seed`, `command`. Run each command from the
  stark-mempool-sim checkout's root, and keep its standard output as `<cell>.jsonl`, all in one
  directory. Write it through a temporary file and rename it when the run finishes: the scripts
  count a run when its `<cell>.jsonl` exists, and read its last line.
- **`scripts/`:** each takes that directory and writes one file of `data/`, byte for byte:
  `python3 scripts/designs_fixed_proposer.py RUNS > data/designs-fixed-proposer.md`. `runs.py`
  explains the cell names; `--used FILE` lists the runs a table read.
- **`data/`:** the tables. Design 5, geth's rules, is `5 geth` in the three `.txt` tables.

| table | what it holds | series it reads |
| --- | --- | --- |
| `designs-fixed-proposer.md` | capacity by design, setting and size, each seed, one fixed proposer; upload and delay per node at today's load; 7,740 B signatures; 2 signature tx/s | `designs-fixed-proposer`, `signatures-7740-bytes`, `signatures-2-per-second` |
| `designs-random-proposer.md` | capacity with a random proposer (every node, a quarter aggregating); one builder as above | `designs-random-proposer`, `designs-fixed-proposer` |
| `controls.txt` | seed 100's controls: request timeouts of 5 s and 500 ms, design 4's fold order by fee per proving cost, one builder proving 1,000 times faster | `request-timeout-5s`, `request-timeout-500ms`, `fold-order-fee-per-proving-cost`, `prover-1000-times-faster`, `designs-fixed-proposer` |
| `proposer-every-node.txt` | every node aggregating, a random proposer against the fixed one, cell by cell | `designs-random-proposer`, `designs-fixed-proposer` |
| `proposer-other-aggregator.txt` | a quarter aggregating, designs 2 and 5: node 0, another aggregator fixed as the proposer, and a random proposer, cell by cell at node 0's edges, and the steps each held per series | `fixed-proposer-other-aggregator`, `designs-fixed-proposer`, `designs-random-proposer` |
| `today-one-builder.md` | one builder at today's load, pull and geth's rules, 2,560 B and 7,740 B signatures, at 100, 1,000 and 10,000 nodes, each seed: inclusion, upload of the other nodes and of the builder, delay, the builder's CPU | `designs-fixed-proposer`, `designs-10000-nodes`, `signatures-7740-bytes`, `signatures-7740-bytes-10000-nodes`, `pull-signatures-7740-bytes` |
| `designs-10000-nodes.md` | capacity at 10,000 nodes against 1,000; every step run at 10,000 nodes beside the same cell at 1,000; every node's upload at 15 and 2 signature tx/s; one builder proving 1,000 times faster | `designs-10000-nodes`, `designs-fixed-proposer`, `designs-random-proposer`, `signatures-2-per-second`, `signatures-2-per-second-10000-nodes`, `prover-1000-times-faster`, `prover-1000-times-faster-10000-nodes` |

A capacity is the highest step of privacy load, on top of 15 signature tx/s, at which a run
includes at least 95% of its transactions by its end (five 12 s slots of load and two to drain),
with every lower step run held. Seed 100 ran the whole ladder with one fixed proposer; the other
seeds ran the steps around each edge, and steps not run are taken as held. Seeds 104 to 107 first
ran every step that seeds 101 to 103 ran in their series. Then, wherever a seed's edge fell
outside those steps, they ran the step below or above, until every edge was closed: a step held
with a failed step directly above it, or 72 held. At 10,000 nodes only each 1,000-node edge and
the step above it ran, and the next step down or up where the edge moved.

Upload: the first five tables count a node's messages over the whole 84 s run. The two the second
record added count them over the 60 s of load, as the post does (`load_traffic`), and
`today-one-builder.md` leaves the builder out of the other nodes' mean: it uploads about 11 Mbit/s,
and its weight in a mean over every node falls tenfold with each tenfold in nodes.
