# leanVM 990b935's proving times on a Ryzen 9 8945HS

The timings behind First Questions version 11's section 6 (its figures cpu-model and cores):
leanVM [`990b935`](https://github.com/leanEthereum/leanVM/commit/990b935263dc7f793f280914f262ca7955ddc3e0),
built with `cargo build --release` (leanVM's own `.cargo/config.toml` sets `-C target-cpu=native`),
on an 8-core, 16-thread Ryzen 9 8945HS with 92 GiB. Calibration v2's own timings, pinned to 1, 2
and 4 cores, are in [`../calibration/`](../calibration/).

- **`configs/`:** one line per run, the command as it ran (`leanvm` is the built binary).
  - `leanvm-16-threads`: leaves of 16 and 512 leanSPHINCS signatures, and folds of 2, 4 and 8
    children over such leaves, at log-inv-rate 2 and 1 (rates 1/4 and 1/2).
  - `leanvm-threads`: leanVM's README 2-to-1 fold (900 leanXMSS signatures per leaf) by thread
    count.
- **`data/`:** each run's measurements as its runner recorded them, one row per try: the
  proving time leanVM prints (`prove_s`, with its ± in `prove_pm`), cycles, committed size, proof
  size, peak memory, and the CPU other processes used before and during the run, in cores
  (`foreign_before`, `foreign_during`). A try during which other processes used two cores or more
  was retried, up to three tries; `accepted` marks a try that exited cleanly below that bound.
- `leanvm-16-threads` ran every shape four times. The prefixes `t16`, `t8`, `t4` and `t2` in its
  names and its `threads` column are the thread counts its runner asked for, but the runner set
  `RAYON_NUM_THREADS`, which leanVM 990b935 ignores: it reads `LEANVM_NUM_THREADS`. Every run used
  leanVM's default, all 16 threads, so the four are repeats of one setting. `leanvm-threads` set
  `LEANVM_NUM_THREADS`, as its commands say.
- [`../figures/figures.py`](../figures/) reads these files:
  - `extract leanvm-16-threads data/leanvm-16-threads.csv`: the median time over each shape's
    accepted tries, or over all its tries where none was accepted;
  - `extract leanvm-threads data/leanvm-threads.csv`.
