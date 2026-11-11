### Capacity: privacy tx/s held on top of 15 signature tx/s, with a random proposer

At seeds 100 / 101 / 102 / 103, one value where all four agree. '≥': the highest rung run held (seed 100 ran to 96, seeds 101–103 to 72). The every-node and 25% columns are a random proposer's (proposer_mode=random); the one-builder columns are node 0's, as in designs-fixed-proposer.md: that builder proposes by construction.

**six-object block**

| design | every node, 100 nodes | every node, 1,000 nodes | one builder, 100 nodes | one builder, 1,000 nodes | 25% aggregators, 100 nodes | 25% aggregators, 1,000 nodes |
|---|---|---|---|---|---|---|
| 1 push | 54 | ≥96 / ≥72 / ≥72 / ≥72 | 3 / 3 / 3 / 6 | 3 / 3 / 3 / 6 | 6 | 6 |
| 2 pull | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 9 | 9 | 18 / 27 / 18 / 18 | 18 |
| 3 keep | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 9 | 9 | 36 / 36 / 36 / 27 | 54 / 54 / 36 / 54 |
| 4 coverage | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 9 / 6 / 9 / 9 | 6 | 36 | 36 / 36 / 36 / 54 |
| 5 geth today | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 9 | 9 | 36 | ≥96 / ≥72 / ≥72 / ≥72 |

**501-object block**

| design | every node, 100 nodes | every node, 1,000 nodes | one builder, 100 nodes | one builder, 1,000 nodes | 25% aggregators, 100 nodes | 25% aggregators, 1,000 nodes |
|---|---|---|---|---|---|---|
| 1 push | 54 | ≥96 / ≥72 / ≥72 / ≥72 | 3 | 3 | 6 | 3 / 6 / 6 / 6 |
| 2 pull | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 12 / 9 / 9 / 9 | 9 | 27 / 27 / 27 / 18 | 18 |
| 3 keep | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 12 | 12 / 9 / 9 / 12 | 36 | 54 / 54 / 36 / 54 |
| 4 coverage | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 12 | 6 | 36 | 36 / 36 / 36 / 54 |
| 5 geth today | ≥96 / ≥72 / ≥72 / ≥72 | ≥96 / ≥72 / ≥72 / ≥72 | 12 | 12 | 36 / 54 / 36 / 54 | ≥96 / ≥72 / ≥72 / ≥72 |

