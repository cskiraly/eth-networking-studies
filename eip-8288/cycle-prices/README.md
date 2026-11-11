# Earlier runs, priced by cycle counts

Before calibration v2 the simulator priced a proof by leanVM 990b935's cycle counts: a nested
proof at 151.5 ms on the fast prover, against v2's 108.2 ms. These runs are the post's and First
Questions version 11's results on those prices, which both say so where they cite them. Every cell
used `--calibration leanvm-990b935` but `leaf-multiplicity`, which ran on the default, leanVM-b's
weights, at the 303 ms anchor.

- **Code:** the cells ran between 31 October and 2 November 2026, on development commits that
  version 2.4 squashes. `leaf-multiplicity` ran on an earlier state of its leaf-fold measurement;
  version 2.4 gives the same numbers, and more beside them. The replay at version 2.5 reproduced
  a cell of each kind ([`../replay/`](../replay/)). Some cells ran on Python 3.11,
  whose floats can differ from 3.12's in their last digits; the replay says which.
- **`configs/`:** one TSV per series, `cell`, `seed`, `command`. Run each command from the
  stark-mempool-sim checkout's root and keep its standard output as `<cell>.jsonl`, one directory
  per series. `python3 -B -u` is how the cells were started; the interpreter flags change nothing.
- **Readers:** the series behind a figure are read by [`../figures/figures.py`](../figures/); its
  docstring says which series each data file reads. The other series are cited in the text from
  each run's record (`metrics`), the first line of its `<cell>.jsonl`.

| series | cells | what it varies | behind |
| --- | --- | --- | --- |
| `capacity-every-node` | 112 | every node aggregating, raw transactions pushed to every node: 15 signature tx/s plus p privacy tx/s, 100 to 3,000 nodes, the EIP's tick on the fast prover, seeds 100–103, at the load steps around each capacity's edge | Figure capacity-n; the post's "push held 9 at 100 nodes and 15 at 1,000" and the growth with network size |
| `capacity-no-flood` | 128 | as above, with raw transactions kept at the node they enter (`relay_policy=wrapper_only`) | Figure capacity-n; the growth with raw transactions kept at their entry node |
| `capacity-one-builder` | 64 | one node aggregating, the proposer; the others relay and forward no proof | Figure capacity-n and capacity-relay; "push held it at 3" |
| `capacity-one-builder-fast-prover` | 64 | as above with a prover a thousand times faster (`--anchor-ms 0.303`) | "a prover a thousand times faster didn't change that" |
| `capacity-every-node-blocks-12` | 60 | every node aggregating with 12-object blocks (`block_budget=11`), 100 and 300 nodes | Version 11, section 2: "It isn't block space" |
| `scaling` | 160 | 100, 300 and 3,000 nodes at 30 tx/s, none or a fifth private, and 100 to 3,000 nodes at 15 tx/s with a fifth private, the EIP's tick and tickless, 8 seeds; the 1,000-node cells at 30 tx/s are `interval-cycles`' | Figure scaling-3000; per-node CPU and delay against network size |
| `throughput` | 72 | 100, 150 and 200 tx/s at 1,000 nodes, none, 5% or a fifth private, both fold timings, 4 seeds | Version 11, section 5's table |
| `throughput-blocks` | 64 | 60 to 200 tx/s at 1,000 nodes with 12- and 24-object blocks | Version 11, section 5: bigger blocks |
| `partial-aggregation` | 144 | 100, 75, 50, 25 or 10% of 1,000 nodes aggregating, relays forwarding their best proof or every proof, at 30 signature tx/s and at 15 tx/s with a fifth private; a relay as proposer; a leaner wrapper encoding | Figure partial-aggregation; the post's "Not every node has to aggregate" |
| `partial-aggregation-follow-ups` | 128 | tickless with relays; a relay proposer at 10%; a relay proposer at 25% on 28 networks (seeds 104–131) | "collapsed on exactly the 5 networks of 28"; version 11's "Tickless works with relays too" |
| `privacy-1000` | 176 | privacy capacity at 1,000 nodes and 30 tx/s on slower provers (606 and 1,212 ms), the EIP's tick and tickless, one or two nested proofs per privacy witness | Figure privacy-frontier |
| `privacy-40` | 376 | privacy capacity at 40 nodes and 30 tx/s, the EIP's tick, anchors 303, 606 and 1,212 ms, 0.75, 1 or 2 nested proofs per privacy witness; verification at 7.5 and 12 ms; 15 tx/s | Figure privacy-frontier |
| `privacy-40-tickless` | 192 | as above for tickless with a 2,000 ms budget, 1 or 2 nested proofs | Figure privacy-frontier |
| `leaf-multiplicity` | 16 | 40 to 1,000 nodes at 15 tx/s with a fifth private, both fold timings, seeds 100–101 | Figure scaling-n |
| `interval-cycles` | 600 | the three fold timings (the EIP's 1,000 ms tick, a 2,000 ms tick, tickless) at 1,000 nodes, 10–60 tx/s, none, a fifth or half private, one or two nested proofs, seeds 100–107 | Figure privacy-frontier's fast prover; the 1,000-node cells of scaling-3000 and section 5's table |

Left out: partial aggregation with raw transactions announced and fetched. It ran on a fetcher with
faults since repaired, and neither document uses it.
