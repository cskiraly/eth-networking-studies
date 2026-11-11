### Capacity: privacy tx/s held on top of 15 signature tx/s

At seeds 100 / 101 / 102 / 103, one value where all four agree. '≥': the highest rung run held (seed 100 ran to 96, seeds 101–103 to 72).

**six-object block**

| design | every node, 100 nodes | every node, 1,000 nodes | one builder, 100 nodes | one builder, 1,000 nodes | 25% aggregators, 100 nodes | 25% aggregators, 1,000 nodes |
|---|---|---|---|---|---|---|
| 1 push | 36 / 54 / 54 / 54 | ≥96 / ≥72 / ≥72 / ≥72 | 3 / 3 / 3 / 6 | 3 / 3 / 3 / 6 | 6 / 3 / 3 / 6 | 6 |
| 2 pull | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 9 | 9 | 18 / 18 / 12 / 18 | 12 / 18 / 18 / 18 |
| 3 keep | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 9 | 9 | 36 / 36 / 18 / 36 | 27 / 54 / 54 / ≥72 |
| 4 coverage | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 9 / 6 / 9 / 9 | 6 | 36 / 36 / 27 / 36 | 36 / 36 / 36 / 54 |
| 5 geth today | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 9 | 9 | 36 / 54 / 36 / 36 | ≥96 / ≥72 / ≥72 / ≥72 |

**501-object block**

| design | every node, 100 nodes | every node, 1,000 nodes | one builder, 100 nodes | one builder, 1,000 nodes | 25% aggregators, 100 nodes | 25% aggregators, 1,000 nodes |
|---|---|---|---|---|---|---|
| 1 push | 54 | ≥96 / ≥72 / ≥72 / ≥72 | 3 | 3 | 6 | 6 |
| 2 pull | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 12 / 9 / 9 / 9 | 9 | 18 / 27 / 12 / 27 | 12 / 18 / 18 / 18 |
| 3 keep | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 12 | 12 / 9 / 9 / 12 | 36 / 36 / 27 / 36 | 27 / 54 / 54 / ≥72 |
| 4 coverage | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 12 | 6 | 36 | 54 / 54 / 36 / 54 |
| 5 geth today | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 12 | 12 | 36 | ≥96 / ≥72 / ≥72 / ≥72 |

### Today's load (15 signature tx/s, p = 0), six-object block: mean over seeds 100–103 (range)

**Upload per node, Mbit/s**

| design | every node, 100 nodes | every node, 1,000 nodes | one builder, 100 nodes | one builder, 1,000 nodes | 25% aggregators, 100 nodes | 25% aggregators, 1,000 nodes |
|---|---|---|---|---|---|---|
| 1 push | 11.18 (11.15–11.21) | 11.16 (11.14–11.19) | 1.45 | 1.37 | 10.53 (10.33–10.67) | 10.48 (10.28–10.67) |
| 2 pull | 10.68 (10.67–10.71) | 10.72 (10.71–10.73) | 0.38 | 0.30 | 10.19 (10.07–10.32) | 10.24 (10.20–10.30) |
| 3 keep | 10.48 (10.47–10.50) | 10.36 (10.33–10.38) | 0.38 | 0.30 | 10.39 (10.36–10.45) | 10.42 (10.40–10.44) |
| 4 coverage | 6.23 (6.15–6.31) | 6.36 (6.33–6.44) | 0.25 (0.25–0.26) | 0.26 | 2.44 (2.42–2.47) | 2.64 (2.59–2.67) |
| 5 geth today | 10.73 (10.70–10.75) | 10.80 (10.79–10.83) | 0.66 (0.65–0.66) | 0.57 | 10.02 (9.93–10.16) | 10.05 (10.00–10.14) |

**Delay, slots of 12 s**

| design | every node, 100 nodes | every node, 1,000 nodes | one builder, 100 nodes | one builder, 1,000 nodes | 25% aggregators, 100 nodes | 25% aggregators, 1,000 nodes |
|---|---|---|---|---|---|---|
| 1 push | 0.59 (0.58–0.60) | 0.62 (0.61–0.63) | 0.56 (0.54–0.59) | 0.57 (0.56–0.60) | 0.58 (0.57–0.61) | 0.60 (0.58–0.62) |
| 2 pull | 0.72 (0.71–0.74) | 0.86 (0.85–0.87) | 0.61 (0.59–0.63) | 0.65 (0.64–0.67) | 0.69 (0.67–0.73) | 0.77 (0.75–0.79) |
| 3 keep | 0.85 (0.83–0.88) | 1.02 (1.00–1.03) | 0.61 (0.59–0.63) | 0.65 (0.64–0.67) | 0.73 (0.70–0.77) | 0.86 (0.85–0.87) |
| 4 coverage | 0.85 (0.83–0.89) | 1.03 (1.02–1.05) | 1.28 (1.25–1.34) | 1.69 (1.68–1.70) | 1.06 (1.03–1.08) | 1.30 (1.27–1.33) |
| 5 geth today | 0.66 (0.65–0.68) | 0.77 (0.76–0.79) | 0.58 (0.56–0.60) | 0.60 (0.59–0.63) | 0.61 (0.59–0.64) | 0.65 (0.64–0.68) |

### 7,740 B signatures at today's load, against 2,560 B (same seed): change, mean over seeds (range)

| design | setting | nodes | upload, Mbit/s per node | delay, slots | lowest inclusion |
|---|---|---|---|---|---|
| 1 push | every node | 100 | +2.29 (+2.27–+2.31) | +0.02 (+0.02–+0.03) | 100.0% |
| 1 push | every node | 1,000 | +2.30 (+2.28–+2.32) | +0.05 (+0.04–+0.05) | 100.0% |
| 1 push | one builder | 100 | +2.22 (+2.22–+2.23) | +0.00 | 100.0% |
| 1 push | one builder | 1,000 | +2.22 | +0.00 | 100.0% |
| 1 push | 25% aggregators | 100 | +2.20 (+2.15–+2.23) | +0.00 (+0.00–+0.01) | 100.0% |
| 1 push | 25% aggregators | 1,000 | +2.26 (+2.22–+2.29) | +0.01 | 100.0% |
| 4 coverage | every node | 100 | +0.00 | +0.00 | 100.0% |
| 4 coverage | every node | 1,000 | +0.00 | +0.00 | 100.0% |
| 4 coverage | one builder | 100 | +0.39 | +0.00 | 100.0% |
| 4 coverage | one builder | 1,000 | +0.40 | +0.00 | 100.0% |
| 4 coverage | 25% aggregators | 100 | +0.06 (+0.06–+0.07) | -0.00 (-0.02–+0.01) | 100.0% |
| 4 coverage | 25% aggregators | 1,000 | -0.02 (-0.06–+0.02) | -0.01 (-0.02–+0.02) | 100.0% |
| 5 geth today | every node | 100 | +0.12 (+0.09–+0.16) | +0.15 (+0.13–+0.17) | 100.0% |
| 5 geth today | every node | 1,000 | -0.08 (-0.12–-0.04) | +0.21 (+0.18–+0.24) | 100.0% |
| 5 geth today | one builder | 100 | +0.14 (+0.14–+0.15) | +0.17 (+0.17–+0.18) | 100.0% |
| 5 geth today | one builder | 1,000 | +0.16 | +0.25 (+0.25–+0.27) | 100.0% |
| 5 geth today | 25% aggregators | 100 | +0.62 (+0.51–+0.69) | +0.21 (+0.20–+0.22) | 100.0% |
| 5 geth today | 25% aggregators | 1,000 | +0.61 (+0.52–+0.68) | +0.35 (+0.33–+0.36) | 100.0% |

### 2 signature tx/s, every node aggregating, 1,000 nodes, p = 0: mean over seeds (range)

| design | upload, Mbit/s per node | delay, slots | lowest inclusion |
|---|---|---|---|
| 1 push | 8.51 (7.55–8.90) | 0.57 (0.55–0.59) | 100.0% |
| 4 coverage | 1.88 (1.86–1.92) | 0.94 (0.92–0.99) | 100.0% |
