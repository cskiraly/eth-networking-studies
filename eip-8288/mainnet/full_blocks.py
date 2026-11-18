#!/usr/bin/env python3
"""Transactions per block in a range of mainnet blocks, for all blocks and for full ones.

    python3 full_blocks.py ENDPOINT FIRST LAST

ENDPOINT is an Ethereum node's JSON-RPC: the path of its IPC socket, or an http(s) URL. Reads each
block with eth_getBlockByNumber (without transaction bodies) and prints, for all blocks, for full
ones (gas used at least 95% of the block's gas limit) and for those over the 50% target: the median,
10th and 90th percentile and maximum of the transaction count, and the same of gas used. Python's
standard library only.
"""
import datetime
import json
import socket
import statistics
import sys
import urllib.request


def rpc(endpoint):
    if endpoint.startswith(('http://', 'https://')):
        def call(method, params):
            body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
            req = urllib.request.Request(endpoint, body.encode(), {'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)['result']
        return call
    s = socket.socket(socket.AF_UNIX)
    s.connect(endpoint)
    dec = json.JSONDecoder()
    buf = ''

    def call(method, params):
        nonlocal buf
        s.sendall(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode())
        while True:
            b = buf.lstrip()
            try:
                obj, end = dec.raw_decode(b)
                buf = b[end:]
                return obj['result']
            except json.JSONDecodeError:
                buf += s.recv(1 << 20).decode()
    return call


def q(a, p):
    return a[min(len(a) - 1, int(p * len(a)))]


def summ(name, rs):
    if not rs:
        print(name, 'none')
        return
    tx = sorted(r[2] for r in rs)
    g = sorted(r[3] for r in rs)
    print(f'{name}: n={len(rs)} tx median={statistics.median(tx):.0f} p10={q(tx, .1)} p90={q(tx, .9)} '
          f'max={tx[-1]} | gasUsed median={statistics.median(g) / 1e6:.1f}M p10={q(g, .1) / 1e6:.1f}M '
          f'p90={q(g, .9) / 1e6:.1f}M')


def main():
    endpoint, first, last = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    call = rpc(endpoint)
    rows = []   # number, timestamp, transactions, gas used, gas limit
    for n in range(first, last + 1):
        b = call('eth_getBlockByNumber', [hex(n), False])
        rows.append((n, int(b['timestamp'], 16), len(b['transactions']), int(b['gasUsed'], 16),
                     int(b['gasLimit'], 16)))

    def ts(t):
        return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    print(f'blocks {rows[0][0]}..{rows[-1][0]} ({len(rows)}), {ts(rows[0][1])} .. {ts(rows[-1][1])}')
    print('gasLimit values:', sorted(set(r[4] for r in rows)))
    summ('all', rows)
    summ('full (>=95% of limit)', [r for r in rows if r[3] >= .95 * r[4]])
    summ('over target (>50%)', [r for r in rows if r[3] > .5 * r[4]])
    fill = sorted(r[3] / r[4] for r in rows)
    print(f'fill median={statistics.median(fill) * 100:.0f}% p90={q(fill, .9) * 100:.0f}%')


if __name__ == '__main__':
    main()
