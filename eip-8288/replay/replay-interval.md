| run | stands for | config (series: cell) | outcome | exact leaves | to 1e-12 | included, stored / rerun |
| --- | --- | --- | --- | --- | --- | --- |
| `interval-845ms` | the 1,000 ms tick at the 845 ms anchor, where three nested proofs fit one fold | `interval-845ms`: `interval-845ms-tick1000-f1-tps10-s0.2-seed100` | identical | 736247 | 0 | 435/600 / 435/600 |
| `nodes-10000-303ms` | the fold timings at 10,000 nodes, at the 303 ms anchor | `nodes-10000-303ms`: `nodes-10000-303ms-tick2000-f2-tps10-s0.5-seed100` | identical | 7281790 | 0 | 600/600 / 600/600 |
| `nodes-10000-871ms` | the fold timings at 10,000 nodes, at the 871 ms anchor | `nodes-10000-871ms`: `nodes-10000-871ms-tick2000-f1-tps10-s0.5-seed100` | identical | 7295565 | 0 | 576/600 / 576/600 |
| `nodes-10000-signatures-7740b` | 7,740-byte signatures at 10,000 nodes | `nodes-10000-signatures-7740b`: `nodes-10000-signatures-7740b-tick2000-f1-tps10-s0-seed100` | identical | 7276982 | 0 | 600/600 / 600/600 |
| `nodes-10000-845ms` | the 845 ms anchor at 10,000 nodes | `nodes-10000-845ms`: `nodes-10000-845ms-tick1000-f1-tps10-s0.2-seed100` | identical | 7300389 | 0 | 407/600 / 407/600 |
| `nodes-10000-bind-no-budget` | what binds at 871 ms, at 10,000 nodes: no proving budget | `nodes-10000-bind-no-budget`: `nodes-10000-bind-no-budget-tick1000-f1-tps10-s0.2-seed100` | identical | 7302916 | 0 | 367/600 / 367/600 |
| `nodes-10000-bind-capacity` | what binds at 871 ms, at 10,000 nodes: the 303 ms anchor with 871 ms's fold widths | `nodes-10000-bind-capacity`: `nodes-10000-bind-capacity-tick1000-f1-tps10-s0.2-seed100` | identical | 7297051 | 0 | 465/600 / 465/600 |
| `nodes-10000-bind-uplink` | what binds at 871 ms, at 10,000 nodes: ten times the uplink | `nodes-10000-bind-uplink`: `nodes-10000-bind-uplink-tick1000-f1-tps10-s0.2-seed100` | identical | 7276909 | 0 | 483/600 / 483/600 |
