# EIP-8288: the networking side of recursive aggregation, the record

The runs, their configurations and the data behind two texts:
- *EIP-8288: the networking side of recursive aggregation*, ethresear.ch, November 2026;
- its reader page, [EIP-8288 First Questions](https://claude.ai/artifact/18s7FFBBddd3YMFz2kcQHv),
  version 11.

Both report runs of stark-mempool-sim, a discrete-event simulation of
[EIP-8288](https://eips.ethereum.org/EIPS/eip-8288), in a fork of George Kadianakis's repository of
the same name. The pins are the fork's version 2.5, `../stark-mempool-sim/` (tag
`first-questions-v11`), and `../leanVM/` at `990b935`, the leanVM whose folds were timed for the
simulator's prices.

| directory | what it holds |
| --- | --- |
| [`interval/`](interval/) | the three fold timings on calibration v2 at 1,000 nodes: the EIP's 1,000 ms tick, a 2,000 ms tick and tickless, on the fast prover (303 ms) and on four cores of a laptop-class Ryzen (871 ms); 7,740 B signatures; the controls on what binds the tick at 871 ms |
| [`transport/`](transport/) | the five designs for how transactions and proofs travel, under the three ways to share the work, at 100 and 1,000 nodes, with their controls |
| [`calibration/`](calibration/) | calibration v2: leanVM's folds timed on exactly 1, 2 and 4 cores, and the simulator's prices fitted to them |
| [`cycle-prices/`](cycle-prices/) | the earlier runs, priced by leanVM's cycle counts, which both texts label: growth with network size, one builder, partial aggregation, the privacy frontier, 100–200 tx/s |
| [`leanvm/`](leanvm/) | leanVM's timings behind version 11's section 6 |
| [`figures/`](figures/) | every figure of both texts, the data behind each, and the script that makes them from the runs |
| [`replay/`](replay/) | the replay at version 2.5 |

## Which code the runs ran on

The cells ran on development commits of the simulator that version 2.5 squashes into one, so
those commits aren't published. Each part's README says which state of the code its runs had. A
replay of 25 cells on version 2.5's simulator code, one for each kind of result in either text,
reproduced every stored run: every count, and every number the stored run recorded, exactly in 19
and to floating-point rounding (relative 1e-12) in the 6 whose stored runs came from Python 3.11
([`replay/`](replay/)).

## Rerunning a cell

Each part's `configs/` has one TSV per series: `cell`, `seed`, and the command. The simulator
needs only Python's standard library; use Python 3.12, since floats from 3.11 can differ in their
last digits.

```sh
git clone https://github.com/cskiraly/eth-networking-studies
cd eth-networking-studies
git checkout eip-8288-networking
git submodule update --init stark-mempool-sim
cd stark-mempool-sim
python3 -B -u -m bench.mainnet --calibration leanvm-990b935 \
  --presets eip_faithful+aggregation_interval=1000 --proving-budget 1000 --tps 24 \
  --privacy-share 0.375 --leanstark-factor 1 --nodes 100 --degree 6 \
  --outcome-ages-ms 12000,24000 --diffusion --seed-start 100 --seeds 1 --json \
  > every-node-n100-p9-seed100.jsonl
```

That is `cycle-prices/configs/capacity-every-node.tsv`'s cell `every-node-n100-p9-seed100`:
100 nodes, 15 signature tx/s plus 9 privacy tx/s, priced by cycle counts. A run prints one JSON
record, with `workload`, `variant` and `metrics`. Each part's README says how to lay out its runs
for its readers. A run at 1,000 nodes takes up to about 15 minutes on one core and writes about
5 MB; the stored runs, close to 20 GB, aren't in this repository.
