# Transactions in today's full blocks

The post's bullet on gas compares the transfers with 7,740 B signatures that a 60M-gas block holds,
about 113, with "a median of about 390 transactions in today's full blocks (the blocks at least 95%
full over a day)". That median is counted here, from a day of mainnet blocks.

`full_blocks.py` reads a range of blocks from an Ethereum node's JSON-RPC (an IPC socket or an
http(s) URL), with `eth_getBlockByNumber`, and counts each block's transactions:

```sh
python3 full_blocks.py ENDPOINT 26369901 26377100
```

[`full-blocks-26369901-26377100.txt`](full-blocks-26369901-26377100.txt) is its output, counted on
2026-11-09 from a geth node: the 7,200 blocks 26369901 to 26377100, from 2026-11-08 11:37 UTC to
2026-11-09 11:41 UTC (a Sunday into a Monday). Run again on 2026-11-17 over the same blocks, the
script gave the same output, byte for byte.

- The gas limit was about 60M (59.77M to 60.06M).
- Full blocks, with gas used at least 95% of the block's limit, are 424 of the 7,200 (6%). Their
  transactions: median 389, 10th percentile 206, 90th 690, at most 1,889.
- All blocks: median 244 transactions, 10th percentile 119, 90th 405; the median block is 49% full.
- Blocks over the 50% target are 3,457 (48%), with a median of 300 transactions.

A percentile is the sorted counts' element at index ⌊p·n⌋; the median is Python's
`statistics.median`.
