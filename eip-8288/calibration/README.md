# Calibration v2: proving priced by leanVM's timings

`bench.mainnet --calibration leanvm-990b935-timed` prices each proof by time: 25.9 ms a proof,
108.2 ms per nested proof and 1.667 ms per leanSPHINCS signature at the 303 ms anchor, and at
least 303 ms once a proof verifies two nested proofs. `--anchor-ms` scales them all. This part
holds the measurements those prices come from, and the fit.

## The measurements

leanVM at commit `990b935`, built with `cargo build --release`, timed on an AMD Ryzen 9 8945HS (8
cores, 16 hardware threads) on 2026-11-08:

- each run pinned with `taskset` to one hardware thread on each of exactly 1, 2 or 4 cores (CPUs
  4, 4–5 or 4–7, their siblings 12–15 left idle), with `LEANVM_NUM_THREADS` equal to the core
  count, so a 1-core run is strictly sequential;
- `--log-inv-rate 2`, the calibration's, and `--repeat 3` after leanVM's warm-up pass;
- a load gate: other processes' CPU was measured before and during each run, on the machine, on
  the pinned CPUs and on their siblings, and a run over the gate was tried again. After three
  tries it was kept and flagged (`accepted` = 0): one run, the 4-core leaf of 16 signatures.

The shapes, each on 1, 2 and 4 cores (`configs/leanvm-cores.tsv`, 33 runs):

- folds of 2, 4, 8 and 16 children over leaves of 512 leanSPHINCS signatures, and over leaves of
  16 (`recursion --n N --xmss-per-leaf 0 --sphincs-per-leaf K`);
- the README's 2-to-1 over 900 leanXMSS signatures a leaf (`recursion --n 2 --xmss-per-leaf
  900`), the shape of leanVM's 303 ms on an M4 Max, which the simulator's anchor is;
- the leaves themselves (`aggregate --sphincs 512` and `16`).

`data/leanvm-cores.csv` has every run: its proving time (`prove_s`, the mean of the three passes,
which are in `passes`), cycles, committed words, proof size, peak memory, verification time, the
pinned CPUs' clock and the gate's loads. The 2-to-1 takes 2,693, 1,478 and 871 ms on 1, 2 and 4
cores: `--anchor-ms 871` is four of its cores.

## The fit

```sh
python3 scripts/fit_prices.py data/leanvm-cores.csv > data/prices.txt
```

Each shape is put on the 303 ms scale through the 2-to-1 timed on the same cores, then averaged
over the three core counts. The two leaves give a proof's and a signature's cost, and folds of 4,
8 and 16 children over leaves of 512 give a nested proof's, by least squares: 25.88 ms, 108.16 ms
and 1.667 ms. `data/prices.txt` compares the rounded prices with every shape: within 2.5% for
the folds over leaves of 512 and both leaves; 14–19% high for folds of 4 to 16 children over
leaves of 16, and 44% high for their 2-to-1, at the floor. A child is priced at a mempool
aggregate's size, close to the 512-signature leaf, not by its own.
