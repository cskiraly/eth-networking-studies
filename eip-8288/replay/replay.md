| run | stands for | config (series: cell) | outcome | exact leaves | to 1e-12 | included, stored / rerun |
| --- | --- | --- | --- | --- | --- | --- |
| `interval-cycles-1000ms` | the 1,000 ms tick at cycle prices (versions 9-11) | `interval-cycles`: `interval-cycles-tick1000-f1-tps10-s0-seed100` | identical | 723650 | 0 | 600/600 / 600/600 |
| `interval-cycles-2000ms` | the 2,000 ms tick at cycle prices | `interval-cycles`: `interval-cycles-tick2000-f1-tps10-s0-seed100` | identical | 723650 | 0 | 600/600 / 600/600 |
| `capacity-n100` | capacity against network size (capacity-n) | `capacity-every-node`: `every-node-n100-p9-seed100` | identical | 85459 | 17 | 1440/1440 / 1440/1440 |
| `capacity-no-flood-n100` | raw transactions kept at the node they enter (capacity-n) | `capacity-no-flood`: `no-flood-n100-p18-seed100` | identical | 88969 | 12 | 1980/1980 / 1980/1980 |
| `scaling-n100` | 100 to 3,000 nodes at 30 tx/s (scaling-3000) | `scaling`: `scaling-n100-tick-tps30-s0.2-seed100` | identical | 88329 | 13 | 1800/1800 / 1800/1800 |
| `leaf-multiplicity-n100` | how many nodes fold each witness, against network size (scaling-n) | `leaf-multiplicity`: `leaf-multiplicity-tick1000-n100-seed100` | identical | 77427 | 0 | 900/900 / 900/900 |
| `partial-10pct-best` | 10% aggregators forwarding their best proof (partial-aggregation) | `partial-aggregation`: `partial-a0.1-best-p15-seed100` | identical | 730961 | 0 | 881/900 / 881/900 |
| `frontier-40` | prover speed and privacy capacity (privacy-frontier) | `privacy-40`: `privacy-40-tick-a303-f1-v9.195-tps30-s0.25-seed0` | identical | 37797 | 0 | 1800/1800 / 1800/1800 |
| `one-builder-cycles` | one builder at cycle prices | `capacity-one-builder`: `one-builder-n100-p3-seed100` | identical | 82151 | 12 | 1072/1080 / 1072/1080 |
| `frontier-1000-tickless` | the privacy frontier at 1,000 nodes, tickless | `privacy-1000`: `privacy-1000-tickless-a606-f1-s0.1-seed100` | identical | 524542 | 0 | 1793/1800 / 1793/1800 |
| `interval-303ms` | the 1,000 ms tick on calibration v2, 303 ms (holds-grid, latency) | `interval-303ms`: `interval-303ms-tick1000-f1-tps45-s0.2-seed100` | identical | 754766 | 0 | 2700/2700 / 2700/2700 |
| `interval-871ms` | the 1,000 ms tick at the 871 ms anchor (holds-grid) | `interval-871ms`: `interval-871ms-tick1000-f1-tps30-s0.2-seed100` | identical | 743815 | 0 | 544/1800 / 544/1800 |
| `signatures-7740b` | 7,740-byte signatures | `signatures-7740b`: `signatures-7740b-tick1000-f1-tps45-s0-seed100` | identical | 753924 | 0 | 2700/2700 / 2700/2700 |
| `bind-uplink` | what binds at 871 ms: ten times the uplink | `bind-uplink`: `bind-uplink-tick1000-f1-tps45-s0.2-seed100` | identical | 750837 | 0 | 509/2700 / 509/2700 |
| `design1-push-25pct` | design 1, push, 25% aggregators, random proposer (designs) | `designs-random-proposer`: `push-quarter-n100-p6-6obj-random-s100` | identical | 85786 | 0 | 1202/1260 / 1202/1260 |
| `design2-pull-25pct` | design 2, pull, 25% aggregators, random proposer (designs) | `designs-random-proposer`: `pull-quarter-n100-p18-6obj-random-s100` | identical | 93119 | 0 | 1967/1980 / 1967/1980 |
| `design3-keep-25pct` | design 3, keep, 25% aggregators, random proposer (designs) | `designs-random-proposer`: `keep-quarter-n100-p36-6obj-random-s100` | identical | 101492 | 0 | 2950/3060 / 2950/3060 |
| `design4-coverage-25pct` | design 4, coverage, 25% aggregators, random proposer (designs) | `designs-random-proposer`: `coverage-quarter-n100-p36-6obj-random-s100` | identical | 103105 | 0 | 3016/3060 / 3016/3060 |
| `design5-geth-25pct` | design 5, geth today, 25% aggregators, random proposer (designs) | `designs-random-proposer`: `geth-quarter-n100-p36-6obj-random-s100` | identical | 101173 | 0 | 3017/3060 / 3017/3060 |
| `design2-pull-one-builder` | design 2, pull, one builder | `designs-fixed-proposer`: `pull-builder-n100-p9-6obj-fixed-s100` | identical | 88137 | 0 | 1397/1440 / 1397/1440 |
| `one-builder-fast-prover` | one builder with a prover a thousand times faster | `capacity-one-builder-fast-prover`: `one-builder-fast-prover-n100-p6-seed100` | identical | 83591 | 12 | 1183/1260 / 1183/1260 |
| `partial-25pct-all` | a relay as proposer, 25% aggregators, relays forwarding every proof | `partial-aggregation-follow-ups`: `partial-a0.25-all-relayprop-sig30-seed104` | identical | 736866 | 20 | 1792/1800 / 1792/1800 |
| `block-12-objects` | a 12-object block | `capacity-every-node-blocks-12`: `every-node-blocks-12-n100-p12-seed100` | identical | 86961 | 0 | 1255/1620 / 1255/1620 |
| `bigger-blocks-1000` | bigger blocks at 1,000 nodes | `throughput-blocks`: `throughput-blocks-12-tick-tps100-s0.0-seed100` | identical | 770990 | 0 | 6000/6000 / 6000/6000 |
| `frontier-40-tickless` | the privacy frontier at 40 nodes, tickless | `privacy-40-tickless`: `privacy-40-tickless-a303-f1-v9.195-tps30-s0.25-seed0` | identical | 29015 | 0 | 1800/1800 / 1800/1800 |
