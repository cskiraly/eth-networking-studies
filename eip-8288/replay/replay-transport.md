| run | stands for | config (series: cell) | outcome | exact leaves | to 1e-12 | included, stored / rerun |
| --- | --- | --- | --- | --- | --- | --- |
| `design3-keep-every-node-10000` | every node aggregating at 15 signature tx/s, 10,000 nodes | `designs-10000-nodes`: `keep-every-n10000-p0-6obj-fixed-s101` | identical | 7289693 | 0 | 900/900 / 900/900 |
| `design4-coverage-every-node-2tps-10000` | every node aggregating at 2 signature tx/s, 10,000 nodes | `signatures-2-per-second-10000-nodes`: `coverage-every-n10000-p0-6obj-fixed-sigtps2-s101` | identical | 7355736 | 0 | 120/120 / 120/120 |
| `design3-keep-every-node-p72-10000` | every node aggregating at 72 privacy tx/s, 10,000 nodes | `designs-10000-nodes`: `keep-every-n10000-p72-6obj-fixed-s100` | identical | 7317264 | 0 | 5220/5220 / 5220/5220 |
| `design4-coverage-25pct-10000` | design 4, coverage, 25% aggregators, random proposer, 10,000 nodes | `designs-10000-nodes`: `coverage-quarter-n10000-p36-6obj-random-s101` | identical | 7424922 | 0 | 3060/3060 / 3060/3060 |
| `design2-pull-one-builder-today-10000` | design 2, pull, one builder at today's load, 10,000 nodes | `designs-10000-nodes`: `pull-builder-n10000-p0-6obj-fixed-s103` | identical | 7340175 | 0 | 900/900 / 900/900 |
| `design2-pull-one-builder-7740b-10000` | the same with 7,740-byte signatures, 10,000 nodes | `signatures-7740-bytes-10000-nodes`: `pull-builder-n10000-p0-6obj-fixed-sig7740-s100` | identical | 7340173 | 0 | 900/900 / 900/900 |
| `design2-pull-one-builder-p6-10000` | design 2, pull, one builder at its edge, 10,000 nodes | `designs-10000-nodes`: `pull-builder-n10000-p6-6obj-fixed-s103` | identical | 7406696 | 0 | 1260/1260 / 1260/1260 |
| `design2-pull-fast-prover-10000` | one builder with a prover a thousand times faster, 10,000 nodes | `prover-1000-times-faster-10000-nodes`: `pull-builder-n10000-p12-6obj-fixed-fastprover-s102` | identical | 7423990 | 0 | 1500/1620 / 1500/1620 |
| `design2-pull-one-builder-7740b-1000` | design 2, pull, one builder at today's load, 7,740-byte signatures, 1,000 nodes | `pull-signatures-7740-bytes`: `pull-builder-n1000-p0-6obj-fixed-sig7740-s100` | identical | 742790 | 0 | 900/900 / 900/900 |
