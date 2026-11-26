# SEACAST update 3: SEACAST tuned by payload size, and the specification at version 0.12.0

The record behind version 3 of [SEACAST's living text](../../README.md). The text carries on
[*SEACAST: fast, lean, sampled broadcast for Ethereum, with an executable spec and a formal model*](https://ethresear.ch/t/seacast-fast-lean-sampled-broadcast-for-ethereum-with-an-executable-spec-and-a-formal-model/26167)
(2026). SEACAST's specification and releases: [seacast-spec](https://github.com/cskiraly/seacast-spec).
Version 3 of the text describes its release [v0.12.0](https://github.com/cskiraly/seacast-spec/tree/v0.12.0),
which names its two protocols: SEACAST (`seacast.md`) and SEACAST Lite (`seacast-lite.md`). Its
[changelog](https://github.com/cskiraly/seacast-spec/blob/v0.12.0/CHANGELOG.md) lists what versions
0.10.3 to 0.12.0 changed. In this record, as in the text's measurements, SEACAST is SEACAST Lite, the
protocol the simulator runs.

## 1. SEACAST tuned by payload size

Figure 6 ran SEACAST untuned: the push budget R by the earlier posts' schedule and 16 KiB chunks at every size.
This part tunes R, the chunk size and the code by size, on Figure 6's two networks at eight sizes from 32 KiB to
4 MiB, and ends in one schedule by size for both networks. It measured from 2026-11-17 to 2026-11-22.

### What was tuned, and how

**The cells** are Figure 6's, apart from what this section lists. Each cell is a test run of Prysm's simulation
harness with the pubsub fork's SEACAST on 500 nodes. They ran in virtual time, on the all-home network (every
node at 50 Mbps up and 100 down) on machine A, and on the mixed-bandwidth network, dcb20 (a fifth of the nodes at
1 Gbps, the builder among them), on machine B. Seeds 7 to 16 are Figure 6's. Each gives a network its own graph
and its own placement of nodes in regions, but the ten share nearly one split of the nodes among the regions, as
the [record of update 2](../u2/README.md) explains. Each cell sends six payloads a slot apart. Its time is the
median, over the five payloads after the first, of the time by which 99 % of the nodes can rebuild the payload.
Its bytes are the median, over the same five payloads, of what a node receives on the wire for the payload until
the last node completes, averaged over the nodes. Copies divide those bytes by one number a size: the median, over a
machine's coded SEACAST cells of that size, of K times the chunk length of a cell's first payload, which is its
compressed size to within K bytes. Plain groups and gossipsub's cells have no such value. It is not exactly Figure
6's divisor.

**The default** is Figure 6's setting. It has R = 4 up to 256 KiB, 3 at 512 KiB and 2 above, with R = 6 for the
relays at 1 Gbps; the publisher keeps the base budget. The group is coded, K data chunks and as many parity, in 16 KiB chunks. At 4 MiB it is the plain group
of 256 chunks that the specification sends.

**What differs from Figure 6's cells:**
- **The code.** Groups of at most 128 parity chunks use Leopard Reed–Solomon over GF(2⁸). Larger groups use
  Leopard over GF(2¹⁶): the grid's three shapes of 256 data chunks (1 MiB in 4 KiB chunks, 2 MiB in 8 KiB
  and 4 MiB in 16 KiB), and 4 MiB in 8 KiB chunks (512 data chunks) from the growth below. The tuning's own
  cells of the default also run Leopard GF(2⁸), not Figure 6's GF(2⁸) matrix code. Neither Leopard code is
  the specification's: it defines a systematic Reed–Solomon code over GF(2⁸) with evaluation points 0 to N − 1
  (descriptor version 2), which Figure 6 ran as the GF(2⁸) matrix code. A group has the same shape under
  either. The code changes the bytes on the wire and the CPU, but the harness charges no time for coding (see
  "The codec's CPU" below).
- **The offer bound follows the group.** The pubsub fork remembers at most 256 announcements a peer for chunks a
  node has not received. Under this setting, once a node holds a validated chunk of a group, it remembers up to
  8192 announcements a peer for that group, more than any group here has chunks. The 256 still bound the peer's
  other announcements. Before the tuning, one
  measurement at 4 MiB in 512 chunks, seed 7, compared the bound at 256, at 8192 and following the group. On
  dcb20, the bound at 256 turned away 1.0 % of the announcements. The three bounds' times lie within 2.5 % of
  each other on all-home and within 1.6 % on dcb20, and their bytes within about 1 %.
- **A counter of the offer table's refusals is on.** It changes nothing a node decides. Under the group bound,
  two cells refused announcements: those from a peer that announced most of a group before the node held a
  validated chunk of it, as the rule intends. Both are at seed 7 on dcb20 at 4 MiB, R = 1 under GF(2¹⁶). One
  refused 256 of about 2.0 million in 16 KiB chunks, and the other 320 of about 3.8 million in 8 KiB chunks.
  Neither setting went on to stage 3, and the other 1366 SEACAST cells refused none.
- **Two smaller sizes, 32 and 64 KiB**, join Figure 6's six. The ask discipline is on below 512 KiB, as the
  specification has it (Figure 6's `all` variant).

**The grid** crosses R in 1, 2, 3, 4 and 6 with these chunk sizes (KiB of the uncompressed body; K = ⌈size /
chunk size⌉, as the specification's `build_group`):

| payload | chunk sizes in KiB (K) |
|---|---|
| 32 KiB | 4 (8), 8 (4), 16 (2), 32 (1) |
| 64 KiB | 4 (16), 8 (8), 16 (4), 32 (2) |
| 128 KiB | 4 (32), 8 (16), 16 (8), 32 (4) |
| 256 KiB | 4 (64), 8 (32), 16 (16), 32 (8) |
| 512 KiB | 4 (128), 8 (64), 16 (32), 32 (16) |
| 1 MiB | 4 (256), 8 (128), 16 (64), 32 (32), 64 (16) |
| 2 MiB | 8 (256), 16 (128), 32 (64), 64 (32) |
| 4 MiB | 16 (256, coded), 16 (256, the plain group), 32 (128), 64 (64) |

Where a setting at seed 7 sat on the grid's edge, the grid grew by one step. That added R = 8 (with the fast nodes'
R at 8 too), 2 KiB chunks, 64 KiB chunks at 128, 256 and 512 KiB, 128 KiB chunks at 1, 2 and 4 MiB, and 8 KiB
chunks under GF(2¹⁶) at 4 MiB.
At 32 to 128 KiB, every shape also ran uncoded (the compressed body in K chunks, no parity) and in one chunk,
and gossipsub's whole message ran at 32 and 64 KiB as a reference. The uncoded settings were shown beside the
results and could not be chosen: at seeds 7 to 9 they sit at the light, slow end.

**Not run:** the study's plan also listed one-knob probes (the fast nodes' R, the ask wait, the window target and
parity) and a check under faults. Neither ran. Every cell has the fast nodes' R at 6 (8 with R = 8), the ask wait
at 200 ms and the window target at 20 ms, every coded group has one parity chunk a data chunk, and no cell has a
fault or loss. The plan's third check, on fresh networks, ran on the one schedule ("One schedule for both
networks" below). Its seeds are 1024, 2048 and 3072; every other cell has a seed from 7 to 16.

**Three stages**, one network a machine:
1. **Seed 7: 494 cells**, plus 42 settings grown at the edges. A setting goes on only if it is "ok": no payload
   undelivered, none censored, and every seed present. Per point, up to four settings went on beside the default.
   They were taken in this order: the fastest setting on the time–bytes front over the coded settings, the
   front's lightest, the rest of the front by time, and then the settings within the repeat noise of a front
   setting. The ok neighbours of the fastest were carried too. A neighbour is one grid step away in R or in
   chunk size, with every other knob equal, apart from what the step brings with it: a step in chunk size may
   move between Leopard's GF(2⁸) and GF(2¹⁶), and R = 8 runs the fast nodes' R at 8.
2. **Seeds 8 and 9: 466 cells** (458 SEACAST, 8 gossipsub). At seeds 7 to 9, up to four distinct settings a
   point were chosen for stage 3:
   - the fastest by the median;
   - "the lighter point": the fastest of the settings on the time–bytes front that are lighter than the fastest
     on all three seeds, by more than the noise allowance;
   - the default;
   - the fastest setting's best neighbour.
   In all, 25 settings on all-home and 29 on dcb20.
3. **Seeds 10 to 16: 406 cells** (378 SEACAST, 28 gossipsub at 32 and 64 KiB). The settings were chosen on seeds
   7 to 9, and each comparison is counted twice: on all ten seeds, and on the seven seeds (10 to 16) that took no
   part in the choice.

All 1408 cells of the three stages passed, and so did the 58 cells of the two later runs (54, and 4 repeats). No
SEACAST cell had a censored payload, or one that fewer than 99 % of the nodes completed. The readers found every
listed cell.

**The reading's rules,** fixed before stage 3's cells were read:
- **Clear.** One setting is clearly faster (or lighter) than another when it is faster (or lighter) on at least 8
  of the 10 seeds, paired by seed, and the median of the per-seed gaps 1 − x/x_other in time (or bytes) is beyond
  the noise allowance.
  Otherwise the two are close. Clearly slower or heavier is the same test the other way round. The allowances
  are cutoffs set from reruns of a few cells: in time 10 % below 512 KiB and 6 % from 512 KiB, in bytes 8 % and
  3 %. A later repeat moved one cell's bytes by 9.7 % ("One schedule for both networks" below).
- **The best and the named settings.** The best is the faster of the two settings chosen as the fastest and the
  lighter point, by the median of ten. Its best neighbour is its fastest neighbour that is ok at ten seeds, and
  may be faster than the best. The best is named alone only where it is clearly faster than that neighbour;
  otherwise the two are named, as the two finalists. (At no point was it named alone.)
- **The bar.** A setting clears the bar against the default when it is clearly faster, or clearly lighter and
  not clearly slower.
- **The preferred setting** is the lighter of the named settings that clear the bar. Where neither clears it, the
  reading still reports the lighter of the two as preferred, and the default holds.
- **The outcome.** The text changes from the default where the preferred setting clears the bar, and keeps the
  default otherwise.

**Three points were the author's call,** decided on 2026-11-22 (the one schedule below then changed the second):
- **all-home, 2 MiB: the default is kept.** R = 2 in 32 KiB chunks was not a named setting, but it clears the bar
  by bytes. It is lighter on 10 of 10 seeds, by 5.57 % per seed, and slower on 10 of 10, by 5.90 % per seed,
  just inside the 6 % allowance. By the ratio of the medians it is 6.5 % slower, outside it.
- **dcb20, 128 KiB: the default is kept.** R = 3 in 16 KiB chunks, which was not named either, clears the bar by
  bytes. It is lighter on exactly 8 of 10 seeds, by 8.65 % per seed against an 8 % allowance, and 6.9 % slower,
  inside 10 %. By the ratio of the medians it is 7.0 % lighter, inside the allowance.
- **dcb20, 4 MiB: R = 2 in 32 KiB chunks.** The rule prefers the lighter named setting, 64 KiB chunks. Against it,
  32 KiB chunks are faster on 9 of 10 seeds by 2.98 % and heavier on 9 of 10 by 1.02 % (both close). It would also change the specification's largest
  segment. The author took the fastest, 32 KiB chunks.

### Known answers

**The cells against Figure 6.** Before any tuning cell, each machine reran Figure 6's seed-7 cells for its network
with Figure 6's settings: the GF(2⁸) matrix code, the offer bound at 256 and the 4 MiB variants. The counter of
refusals was on. Bounds were set before the run:
- time within 10 % below 512 KiB, and 6 % (all-home) or 8 % (dcb20) from 512 KiB;
- bytes within 5 % from 512 KiB, and within 7 % below.

The 7 % replaced a first 5 %, which one cell missed (128 KiB on all-home, −5.3 %). Three repeats of that cell and
of 256 KiB then measured the repeat noise of a small payload's bytes: they spread over 7.9 % and 5.7 %, with the
six wire totals equal in every run. All 16 cells pass by the 7 % bound:

| machine | network | protocol | size | Figure 6 | this run | bounds |
|---|---|---|---|---|---|---|
| A | all-home | SEACAST | 128 KiB | 0.3320 s, 0.2909 MiB | 0.3330 s (+0.3 %), 0.2756 MiB (−5.3 %) | 10 %, 7 % |
| A | all-home | SEACAST | 256 KiB | 0.3680 s, 0.5615 MiB | 0.3790 s (+3.0 %), 0.5862 MiB (+4.4 %) | 10 %, 7 % |
| A | all-home | SEACAST | 512 KiB | 0.4570 s, 0.9040 MiB | 0.4570 s (+0.0 %), 0.8803 MiB (−2.6 %) | 6 %, 5 % |
| A | all-home | SEACAST | 1 MiB | 0.6760 s, 1.2819 MiB | 0.6600 s (−2.4 %), 1.2900 MiB (+0.6 %) | 6 %, 5 % |
| A | all-home | SEACAST | 2 MiB | 0.9160 s, 2.5456 MiB | 0.9110 s (−0.5 %), 2.5420 MiB (−0.1 %) | 6 %, 5 % |
| A | all-home | SEACAST, plain | 4 MiB | 1.5500 s, 4.4835 MiB | 1.5520 s (+0.1 %), 4.4795 MiB (−0.1 %) | 6 %, 5 % |
| A | all-home | SEACAST, 32 KiB chunks | 4 MiB | 1.3620 s, 4.5305 MiB | 1.4320 s (+5.1 %), 4.5685 MiB (+0.8 %) | 6 %, 5 % |
| A | all-home | gossipsub | 128 KiB | 0.6700 s, 0.4859 MiB | 0.6510 s (−2.8 %), 0.4655 MiB (−4.2 %) | 10 %, 7 % |
| B | dcb20 | SEACAST | 128 KiB | 0.2850 s, 0.3097 MiB | 0.2740 s (−3.9 %), 0.3170 MiB (+2.4 %) | 10 %, 7 % |
| B | dcb20 | SEACAST | 256 KiB | 0.2960 s, 0.5947 MiB | 0.3070 s (+3.7 %), 0.5868 MiB (−1.3 %) | 10 %, 7 % |
| B | dcb20 | SEACAST | 512 KiB | 0.3620 s, 1.0044 MiB | 0.3620 s (+0.0 %), 0.9867 MiB (−1.8 %) | 8 %, 5 % |
| B | dcb20 | SEACAST | 1 MiB | 0.4750 s, 1.6803 MiB | 0.4750 s (+0.0 %), 1.6695 MiB (−0.6 %) | 8 %, 5 % |
| B | dcb20 | SEACAST | 2 MiB | 0.6530 s, 3.0333 MiB | 0.6510 s (−0.3 %), 3.0338 MiB (+0.0 %) | 8 %, 5 % |
| B | dcb20 | SEACAST, plain | 4 MiB | 1.1340 s, 5.1058 MiB | 1.1380 s (+0.4 %), 5.1021 MiB (−0.1 %) | 8 %, 5 % |
| B | dcb20 | SEACAST, 32 KiB chunks | 4 MiB | 0.9150 s, 5.0545 MiB | 0.9380 s (+2.5 %), 5.1506 MiB (+1.9 %) | 8 %, 5 % |
| B | dcb20 | gossipsub | 128 KiB | 0.5250 s, 0.4664 MiB | 0.4730 s (−9.9 %), 0.4701 MiB (+0.8 %) | 10 %, 7 % |

These are seed 7's cells, so they differ from Figure 6's medians. The one cell of the 16 with refusals is
all-home's 4 MiB in 32 KiB chunks: 87 of 916,880 announcements were refused under the bound of 256, as in
Figure 6.

**Repeats before stage 3.** Before stage 3, each machine reran two of stage 2's cells (32 KiB at seed 8: the
default, and gossipsub). Each repeat lands within about 1.5 % of the first run in time and in bytes:

| machine | cell | stage 2 | the repeat |
|---|---|---|---|
| A | SEACAST, the default | 0.2920 s, 0.0791 MiB | 0.2930 s, 0.0789 MiB |
| A | gossipsub | 0.2770 s, 0.1161 MiB | 0.2760 s, 0.1171 MiB |
| B | SEACAST, the default | 0.2350 s, 0.0806 MiB | 0.2330 s, 0.0808 MiB |
| B | gossipsub | 0.2430 s, 0.1178 MiB | 0.2400 s, 0.1196 MiB |

**The two later runs' repeats.** Before each of the two later runs ("One schedule for both networks" below), its
machine reran two earlier cells with the same binary and knobs:

| run | machine | cell | the first run | the repeat | within 10 %, 7 % |
|---|---|---|---|---|---|
| dcb20 at 32 and 128 KiB | B | R=6 4 KiB, 32 KiB, seed 7 | 0.2220 s, 0.1017 MiB | 0.2140 s, 0.0989 MiB | yes |
| dcb20 at 32 and 128 KiB | B | R=6 4 KiB, 128 KiB, seed 7 | 0.2420 s, 0.3991 MiB | 0.2500 s, 0.3924 MiB | yes |
| fresh networks | A | R=6 4 KiB, 32 KiB, seed 10 | 0.2310 s, 0.1007 MiB | 0.2280 s, 0.1063 MiB | yes |
| fresh networks | A | the default, 32 KiB, seed 10 | 0.2930 s, 0.0813 MiB | 0.2970 s, 0.0741 MiB | time yes; bytes no (9.7 %) |

The miss is discussed under "One schedule for both networks". On machine B the fresh networks' run relied on the
first run's repeat, made the same day with the same binary and settings.

### Results

Medians over seeds 7 to 16. The gaps are the medians of the per-seed gaps against the default, 1 − x/x_default,
so a positive gap means faster or lighter. Beside each gap is the number of the ten seeds on which the setting was
faster or lighter. "Named" lists the two finalists the rules named (above). "The network's own best" is the setting the rules
preferred on that network, apart from dcb20 at 4 MiB (the author's choice). The text carries one schedule for both
networks instead ("One schedule for both networks" below). The table gives the schedule's setting and its gaps
against the default, and each network's own best where it differs.

| size | network | default | named | the schedule (the network's own best, where it differs) | time gap (of 10) | bytes gap (of 10) | outcome |
|---|---|---|---|---|---|---|---|
| 32 KiB | all-home | 0.2890 s, 3.46 copies | R=8 4 KiB (R_FAST 8); R=6 4 KiB | R=6, 4 KiB: 0.2255 s, 4.54 | +21.24 % (10) | −32.97 % (0) | change |
| 64 KiB | all-home | 0.2965 s, 3.30 | R=8 4 KiB (R_FAST 8); R=6 4 KiB | R=6, 4 KiB: 0.2395 s, 4.40 | +19.48 % (10) | −34.06 % (0) | change |
| 128 KiB | all-home | 0.3195 s, 3.12 | R=6 4 KiB; R=8 4 KiB (R_FAST 8) | R=6, 4 KiB: 0.2655 s, 4.49 | +16.16 % (10) | −44.97 % (0) | change |
| 256 KiB | all-home | 0.3555 s, 2.97 | R=4 4 KiB; R=6 4 KiB | the default (R=4 4 KiB: 0.3310 s, 3.49) | (+8.13 % (10)) | (−18.08 % (0)) | default |
| 512 KiB | all-home | 0.4510 s, 2.40 | R=3 8 KiB; R=4 8 KiB | the default (R=3 8 KiB: 0.4335 s, 2.58) | (+3.17 % (10)) | (−8.76 % (0)) | default |
| 1 MiB | all-home | 0.6495 s, 1.83 | R=3 16 KiB; R=3 8 KiB | the default (own best: R=3, 16 KiB: 0.6050 s, 2.33) | (+6.91 % (10)) | (−27.52 % (0)) | default; own best changes |
| 2 MiB | all-home | 0.8725 s, 1.77 | the default; R=3 16 KiB | the default (its own best too, by the author's call) | – | – | default |
| 4 MiB | all-home | 1.5115 s, 1.57 (plain) | R=2 16 KiB GF(2¹⁶); R=2 32 KiB | R=2, 32 KiB: 1.3640 s, 1.60 | +10.56 % (10) | −2.34 % (0) | change |
| 32 KiB | dcb20 | 0.2400 s, 3.50 | R=6 8 KiB; R=6 16 KiB | R=6, 4 KiB: 0.2040 s, 4.53 (own best: R=6, 8 KiB: 0.2120 s, 4.12; +11.59 % (10), −18.57 % (0)) | +14.55 % (10) | −32.02 % (0) | change |
| 64 KiB | dcb20 | 0.2475 s, 3.45 | R=6 4 KiB; R=8 4 KiB (R_FAST 8) | R=6, 4 KiB: 0.2140 s, 4.47 | +13.30 % (10) | −29.00 % (0) | change |
| 128 KiB | dcb20 | 0.2565 s, 3.31 | R=4 8 KiB; R=6 8 KiB | R=6, 4 KiB: 0.2300 s, 4.38 (own best: the default, the author) | +10.33 % (10) | −32.04 % (0) | change |
| 256 KiB | dcb20 | 0.2800 s, 3.12 | R=4 8 KiB; R=6 8 KiB | the default (R=4 8 KiB: 0.2690 s, 3.27) | (+4.35 % (10)) | (−3.42 % (0)) | default |
| 512 KiB | dcb20 | 0.3340 s, 2.65 | R=4 16 KiB; R=4 8 KiB | the default (R=4 16 KiB: 0.3345 s, 2.90) | (−0.45 % (2)) | (−9.89 % (0)) | default |
| 1 MiB | dcb20 | 0.4420 s, 2.34 | R=2 32 KiB; the default | the default (own best: R=2, 32 KiB: 0.4585 s, 2.20) | (−3.38 % (0)) | (+4.85 % (10)) | default; own best changes (lighter) |
| 2 MiB | dcb20 | 0.6255 s, 2.09 | R=2 32 KiB; the default | the default (own best: R=2, 32 KiB: 0.6150 s, 1.99) | (+0.40 % (6)) | (+4.30 % (10)) | default; own best changes (lighter) |
| 4 MiB | dcb20 | 1.1265 s, 1.79 (plain) | R=2 32 KiB; R=2 64 KiB | R=2, 32 KiB: 0.8910 s, 1.76 | +21.71 % (10) | +1.69 % (10) | change (the author's choice) |

Where the schedule keeps the default, the gaps in brackets belong to the network's own best where it differs,
and otherwise to the setting the rules preferred, which did not clear the bar. Every clear gap in the table also
holds on 7 of 7 of the seeds that took no part in the choice: for the schedule's setting at dcb20's 32 and
128 KiB, faster on 7 of 7 by 14.11 % and 10.59 %.

**The specification.** The push budget is each node's own, and since version 0.10.3 `UNIT`, the target chunk
size, is the builder's choice. So the schedule's 4 and 32 KiB chunks, and the own bests' 8 KiB chunks, set `UNIT`
away from its default of 16 KiB; the CSVs' specification column says so. Some of the search's settings exceed the
specification's limits: 64 and 128 KiB chunks exceed `MAX_SEGMENT_SIZE`, 32 KiB, and GF(2¹⁶) groups of more than
256 chunks exceed `MAX_CHUNKS`. R = 8
ran the fast nodes' R at 8 too. Every coded cell ran Leopard, which the specification does not define (see "The
code" above).

**Gossipsub's whole message** at 32 and 64 KiB, as a reference outside the rules. Its messages are unsigned and
carry the author's peer id and a sequence number, and its relays skip the author, as in Figure 6. SEACAST's cells
run Prysm's authorless policy, also unsigned. By our estimate, from the fields' sizes and the copies not sent to
the author, the two policies differ by under about 1 % of gossipsub's bytes. That was not measured, nor was any
effect on time. Gossipsub's gaps, against each SEACAST setting:

| size | network | gossipsub | against the default: time (of 10), bytes | against the schedule: time (of 10), bytes |
|---|---|---|---|---|
| 32 KiB | all-home | 0.2840 s, 5.21 copies | +0.70 % (5), −52.60 %: close in time | −27.96 % (0), −14.06 %: clearly slower |
| 64 KiB | all-home | 0.4065 s, 5.06 | −36.82 % (0), −52.42 %: clearly slower | −71.21 % (0), −13.12 %: clearly slower |
| 32 KiB | dcb20 | 0.2555 s, 5.30 | −6.25 % (1), −51.89 %: close in time | −25.63 % (0), −20.26 %: clearly slower |
| 64 KiB | dcb20 | 0.3400 s, 5.26 | −36.00 % (0), −53.03 %: clearly slower | −58.87 % (0), −18.04 %: clearly slower |

Gossipsub is clearly heavier in every comparison.

### One schedule for both networks

A publisher knows the payload's size and its own uplink, not the makeup of the network. After stage 3's reading,
the author decided on 2026-11-22 that the text carries one schedule by size for both networks, and gives each
network's own best beside it (the Results table above):
- R = 6 in 4 KiB chunks at 32, 64 and 128 KiB;
- the default from 256 KiB to 2 MiB;
- R = 2 in 32 KiB chunks, coded under Leopard GF(2⁸), at 4 MiB.

The schedule was chosen after the results, as what a publisher can know. At 1 and 2 MiB it keeps the default,
because there the trades differ by network:
- At 1 MiB, all-home's R = 3 is 1.11 % slower than the default on dcb20 (faster on 3 of 10 seeds) and uses
  10.46 % more bytes.
- At 1 MiB, dcb20's 32 KiB chunks are 10.22 % slower on all-home (seed 7 only).
- At 2 MiB, 32 KiB chunks are 4.30 % lighter than the default on dcb20 at the same time. On all-home they are
  5.57 % lighter and 5.90 % slower, and the author kept the default there.

These figures come from the published rows (stage 1's and stage 3's), not from a printed reading; so does
gossipsub's row against the schedule at dcb20's 32 KiB above.

**Two runs completed it.** The first started with a repeat of earlier cells on machine B, and the second with one
on machine A. Each repeat was compared with the time and bytes bounds of "The cells against Figure 6" (10 % and
7 % below 512 KiB).

1. **dcb20 at 32 and 128 KiB, seeds 8 to 16 (18 cells on machine B).** Stage 1 had run R = 6 in 4 KiB chunks on
   dcb20 at seed 7 only; stage 2 did not carry it there. Its repeat, the two seed-7 cells, landed within the
   bounds. Against the default at seeds 7 to 16, the setting is faster on 10 of 10 seeds at both sizes:
   - at 32 KiB, by 14.55 % for 32.02 % more bytes;
   - at 128 KiB, by 10.33 % for 32.04 % more bytes. That is just beyond the 10 % allowance.

   At 128 KiB, dcb20's own reading had kept the default, because nothing in its set was clearly faster: R = 6 in
   8 KiB chunks was 7.65 % faster. At 32 KiB, by the medians, the schedule's setting (0.2040 s) is a little faster
   than dcb20's own best (0.2120 s). The two were not compared seed by seed.
2. **Fresh networks: seeds 1024, 2048 and 3072 (36 cells, 18 on each machine).** The schedule's entries that
   differ from the default up to 2 MiB, R = 6 in 4 KiB chunks at 32, 64 and 128 KiB, ran against the default on
   both networks. These seeds split the nodes among the regions in ways that seeds 7 to 16 do not. 4 MiB was not
   in this check. The rule was fixed before the run: an entry is confirmed where it is faster on all three seeds
   and the median per-seed gap is beyond the 10 % allowance. **All six are confirmed:**

   | size | all-home: the default → the schedule | time gap (of 3), bytes gap | dcb20: the default → the schedule | time gap (of 3), bytes gap |
   |---|---|---|---|---|
   | 32 KiB | 0.2620 s, 3.31 → 0.1970 s, 4.37 | +22.52 % (3), −34.10 % | 0.2150 s, 3.49 → 0.1860 s, 4.26 | +13.49 % (3), −15.31 % |
   | 64 KiB | 0.2700 s, 3.21 → 0.2150 s, 4.23 | +19.83 % (3), −32.33 % | 0.2190 s, 3.30 → 0.1960 s, 4.32 | +13.13 % (3), −30.81 % |
   | 128 KiB | 0.2950 s, 2.93 → 0.2450 s, 4.47 | +14.56 % (3), −52.76 % | 0.2380 s, 3.06 → 0.2140 s, 3.98 | +10.08 % (3), −30.09 % |

   The times are medians of the three seeds. The gains are close to those at seeds 7 to 16. Dcb20 at 128 KiB is
   clear only just, here as there: its three seeds gave +10.1, +5.3 and +11.5 %.

   This run's repeat on machine A missed in bytes. It re-ran stage 3's all-home cells at 32 KiB, seed 10.
   - R = 6 in 4 KiB chunks was within: 0.2310 s, 0.1007 MiB in stage 3; 0.2280 s, 0.1063 MiB in the repeat.
   - The default was within in time but not in bytes: 0.2930 s, 0.0813 MiB in stage 3; 0.2970 s, 0.0741 MiB in
     the repeat. Stage 3's run had 9.7 % more bytes, against the 7 % bound.

   The binary and every knob were the same, and both cells' times were within 1.4 %. A cell's bytes are the
   median of its five warm payloads, and those vary within a run. In these two runs they were 91,265, 85,292,
   71,550, 86,836 and 77,904 bytes a node, and 80,990, 77,742, 72,549, 75,589 and 78,781. Across stage 3's seven
   cells of this setting on machine A, the coefficient of variation of the five is 5.6 % at the median and 11.6 %
   at the most. So the miss was read as noise in the bytes of a single run. The run went on, because its rule is
   on time and its bytes gaps on machine A are about 30 % or more.

**What the miss says about the rules:** a bytes gap of about 10 % between two runs of one 32 KiB cell can be
noise. That is more than the 8 % bytes allowance below 512 KiB. No entry of the schedule rests on a bytes
verdict near 8 %. The one verdict near it, dcb20's R = 3 in 16 KiB chunks at 128 KiB (8.65 % lighter on 8 of 10
seeds), is a setting the author turned down.

### Figure 6's tuned line

Version 3 of the living text draws the one schedule in Figure 6, beside update 2's lines, from this record's
cells at seeds 7 to 16 on both networks at eight sizes from 32 KiB to 4 MiB (`schedule-cells-<machine>.csv`,
`figure6.txt`). Update 2's lines started at 128 KiB; at 32 and 64 KiB they come from this version's run of update
2's kit (below).
- **Two runs of the same settings.** From 256 KiB to 2 MiB the schedule is the default. This record ran it with
  its own binary, and update 2 with Figure 6's. The median over the ten networks of each network's change between
  the two runs is within 0.7 % in time and in bytes at each of these sizes.
- **Against ECBroadcast RS** (update 2's cells and, at 32 and 64 KiB, this version's; on the same ten networks):
  the schedule is faster and lighter on every network at each of the eight sizes. The medians of the per-network
  time gains are 19.3 to 33.5 % on all-home and 8.3 to 25.0 % on dcb20. ECBroadcast ran with Figure 4's settings
  at every size and was not tuned.
- **Against today's gossipsub** (the same cells; payloads 40 s apart at 2 and 4 MiB): the schedule is faster on
  every network at each of the eight sizes, and lighter on every network but one. At 32 KiB on all-home at seed
  16, gossipsub's nodes receive 85 bytes fewer: 103,873 against the schedule's 103,958, the medians of payloads 2
  to 6 in the cells' logs. Both rows round them to 0.0991 MiB.
- **Bytes** are in copies of update 2's basis, the median of ECBroadcast's compressed payloads at that size, as
  Figure 6 counts them. This record's tables divide by the median of SEACAST's own compressed payloads, as
  estimated above, which are up to 1.3 % larger (46,912 against 46,321 bytes at 64 KiB; 93,960 against 92,962 at
  128 KiB). So the figure's copies are up to about 1.3 % above the tables'.

### Figure 6 at 32 and 64 KiB

Machine C ran update 2's three arms at 32 and 64 KiB with update 2's kit: its cell script, its settings and its
two binaries (SEACAST at Prysm `589bf05d4b`, md5 3dcd5c49f1c69669b566658bbe82e994; gossipsub and ECBroadcast RS at
`4fd3f2b8d5`, md5 e45b80c32ab5e5b5d7405b04b2ffd529). SEACAST ran with the ask discipline on and the default's
push budget (above). Both networks ran at seeds 7 to 16: 120 cells, all passed. The tuned line at these
sizes comes from this record's schedule cells, as at the other sizes.

**Known answers.** Before the 120 cells, the run repeated update 2's six cells at 128 KiB, seed 7, the three arms
on both networks. The bounds were those of "The cells against Figure 6" below 512 KiB: 10 % in time and 7 % in
bytes. Five cells held. ECBroadcast on all-home missed in bytes, at 0.6529 MiB against update 2's 0.7046 MiB
(−7.3 %; time −2.5 %), with the same compressed payload, 92,962 bytes. Five more runs of that cell gave:

| run | time | bytes | against update 2 |
|---|---|---|---|
| the known answer | 0.3560 s | 0.6529 MiB | −2.5 %, −7.3 % |
| repeat 1 | 0.3510 s | 0.6371 MiB | −3.8 %, −9.6 % |
| repeat 2 | 0.3660 s | 0.7218 MiB | +0.3 %, +2.4 % |
| repeat 3 | 0.3530 s | 0.6611 MiB | −3.3 %, −6.2 % |
| repeat 4 | 0.3630 s | 0.7187 MiB | −0.5 %, +2.0 % |
| repeat 5 | 0.3620 s | 0.7053 MiB | −0.8 %, +0.1 % |

The cell's own spread at one seed, from 9.6 % below update 2's bytes to 2.4 % above them, is wider than the
bound, and update 2's value lies inside it. So the miss is read as the cell's noise, and the rows are used.

**A cross-check.** The tuning ran gossipsub at 32 and 64 KiB too, with the same binary (Code, below), at seeds 7
to 16. Per
network and size, the medians of the two runs agree within 2.4 % in time and 4.3 % in bytes.

### The codec's CPU

The harness charges no virtual time for encoding and decoding. So a setting with more chunks, or under GF(2¹⁶),
looks cheaper in the cells than it would be on a node. The table below measures one group on one thread of
machine C, an AMD EPYC 9254 (Zen 4). It ran Prysm's `BenchmarkCPU` (`container/segments/cpu_bench_test.go`,
which is in the code below), and each cell is the median of 5 repeats of 20 iterations. "Decode" is decoding and
checking from half data and half parity chunks, in ms a group:

| shape | used by | Leopard GF(2⁸) | the library's GF(2⁸) matrix code | the GF(2⁸) matrix code by tables |
|---|---|---|---|---|
| 128 KiB, K = 8 (16 KiB) | the default | 0.16 | 0.12 | 0.70 |
| 128 KiB, K = 32 (4 KiB) | the schedule | 0.34 | 0.33 | 2.57 |
| 1 MiB, K = 64 (16 KiB) | the default (and all-home's own best, which changes only R) | 1.79 | 2.88 | 38.35 |
| 1 MiB, K = 32 (32 KiB) | dcb20's own best | 1.68 | 1.48 | 19.62 |
| 2 MiB, K = 128 (16 KiB) | the default | 3.99 | 14.47 | 151.22 |
| 2 MiB, K = 64 (32 KiB) | dcb20's own best | 3.26 | 4.25 | 74.27 |
| 4 MiB, K = 128 (32 KiB) | the schedule | 7.09 | 17.69 | 292.23 |
| 4 MiB, the plain group of 256 | the default | 0.46 (join only) | | |

The two matrix columns are the specification's code, byte for byte: the first by an optimised library's encoder
(`github.com/klauspost/reedsolomon`), and the second by the research code's own tables (`rs.go`), the
implementation Figure 6's cells ran. The table has no rows
for 32 and 64 KiB or for the one-chunk shapes; at 128 KiB in 4 KiB chunks the decode takes 0.34 ms. With the
Leopard GF(2⁸) code that the cells ran, the largest decoding median is 7.09 ms a node, at 4 MiB. That is under 1 % of the
time at every benchmarked point where the schedule changes (0.80 % of dcb20's 0.891 s at 4 MiB). The
specification's code in the library takes 17.69 ms there, 2.0 % of that time. At 4 MiB the change adds about
6.6 ms of decoding over the plain group's join, against gains of 148 and 236 ms. At 1 and 2 MiB, dcb20's own best,
32 KiB chunks, decodes faster than the default under every code in the table, because there are fewer chunks. A
plain table-driven code decodes the 4 MiB shape in 292 ms, about a third of dcb20's time there; whether it would
undo the coded setting's gain end to end was not measured. **So these results hold for a fast codec, and the
text names the codec.**

## Files

All in `data/tuning/`, `data/small/` and `scripts/tuning/`, beside this record. Machine A ran the all-home network, machine B
dcb20.

- `data/tuning/<stage>/cells-<machine>.csv` for stage1, grow, stage2 and stage3 on machines A and B (247, 247;
  22, 20; 236, 230; 189, 217 rows). There is one row per cell, all in one header of 42 columns:
  - the setting: `protocol`, `network`, `size_kib`, `seed`, `nodes`, `push_r`, `unit_kib`, `k`, `n`, `code`, `rsx`,
    `r_fast`, `ask_ms`, `target_ms`, `proj`, `fault`, `loss`, `disc`, `offer_bound`, `counted`;
  - the sizes: `chunk_b`, `wire_b`, `comp_b`, and the binary's `bin_md5`;
  - the outcome: `passed`, `msgs`, `p99_s` (the time), `mib` (bytes per node), `p99_max_warm_s`, `censored_warm`,
    `at_3s`, `honest_at_3s`, and `dc_rx_mib` and `other_rx_mib` (dcb20's two node classes);
  - the offer table's counter: `recorded_warm`, `refused_warm`, `asks_past_list`, `offers_recorded`,
    `refused_per_peer`, `refused_per_id`, `refused_per_peer_by_group`;
  - `log`, the cell's tag.
- `data/tuning/<stage>/<machine>/*.txt.dry`: each stage's lists, one line a cell with every knob. The readers take
  them with `--expect` to refuse a point where a listed cell is missing. `stage3/<machine>/known.txt.dry` lists
  stage 3's repeats, which the readers do not take.
- `data/tuning/stage2/stage3-<machine>.csv`: the settings chosen for stage 3, with their roles.
- `data/tuning/best-<machine>.txt`, `.csv` (8 rows each): the reading, every comparison with its counts, as the
  published scripts print it. The CSV has each network's own reading, with the rules' preferred setting
  (`preferred`). dcb20's 4 MiB row names 64 KiB chunks there and flags them PREFERRED NOT SELECTED; the author
  chose 32 KiB chunks (section 1). The specification column names the constants a setting sets away from their
  default. `fronts-<machine>.txt`, `.csv`: the ten-seed fronts, every setting with its status, time, bytes and
  specification constants.
- `data/tuning/fill/cells-B.csv` (18 rows: dcb20's R = 6 in 4 KiB chunks at 32 and 128 KiB, seeds 8 to 16) and
  `fill/B/fill.txt.dry`; `data/tuning/fresh/cells-A.csv` and `cells-B.csv` (18 rows each) and
  `fresh/<machine>/fresh.txt.dry`; the later repeats in `known/repeat-fill-B.csv` and `known/repeat-fresh-A.csv`
  (2 each).
- `data/tuning/schedule-<machine>.txt`, `.csv` (8 rows each): the schedule against the default per point, with
  the network's own best beside it. `data/tuning/fresh.txt`: the check on fresh networks.
- `data/tuning/schedule-cells-<machine>.csv` (80 rows each) and `.txt`: the schedule's own cells, one row per
  point and seed (`host`, `network`, `size_kib`, `seed`, `setting`, `passed`, `msgs`, `p99_s`, `mib`, `comp_b`,
  `bin_md5`, `log`), which Figure 6's tuned line draws. The `.txt` holds the known answer: the rows' medians equal
  the schedule's time and copies in `schedule-<machine>.csv` at every point. `data/tuning/figure6.txt`: the tuned
  line against ECBroadcast and against the earlier settings, at Figure 6's eight sizes, with the numbers the living
  text cites.
- `data/small/sizes-small.csv` (120 rows) and `data/small/known-small.csv` (6 rows), in the columns of update 2's
  `sizes.csv`: update 2's three arms at 32 and 64 KiB, and the six known-answer cells at 128 KiB, all on machine C.
  The five repeats of the missed cell are not published; their numbers are in the table above.
- `figures/seacast_sizes.png`: Figure 6 as the living text's version 3 shows it, with the tuned line.
- `data/tuning/known/`, in the same columns as the cells: the 16 known-answer cells (`cells-A.csv`, `cells-B.csv`,
  8 each), the repeat-noise cells (`noise-1-A.csv` to `noise-3-A.csv`, 2 each), the bound's measurement
  (`bound-A.csv`, `bound-B.csv`, 3 each), the 14 trial cells of new shapes (`trials-A.csv`) and stage 3's repeats
  (`repeat-A.csv`, `repeat-B.csv`, 2 each).
- `data/tuning/cpu.csv`: the CPU table (396 cells; `payload_kib`, `k`, `n`, `chunk_bytes`, `group_bytes`,
  `code`, `op`, `median_ms`, `min_ms`, `max_ms`, `repeats`).
- **The scripts** (Python 3, standard library only): `fronts.py`, `best.py`, `selection.py`, `known_answer.py`,
  `schedule.py` and `fresh.py`, and `make_lists.py` and `carry_cost.py`, which `best.py` imports for two
  constants. `schedule.py` and `fresh.py` import `best.py`, and `schedule_cells.py` imports `schedule.py`;
  `figure6.py` stands alone. `scripts/seacast_sizes.py` draws Figure 6 (matplotlib). `fronts.py`, `best.py`,
  `selection.py` and `known_answer.py` each have a self-test (`--selftest`). The stage 3 reading, rebuilt from
  the published files, in bash:

  ```bash
  cd data/tuning
  for m in A B; do
    E=$(for f in stage1/$m/{small,large}.txt.dry grow/$m/*.txt.dry stage2/$m/{small,large}.txt.dry \
                 stage3/$m/{small,large}.txt.dry; do printf -- '--expect %s ' "$f"; done)
    C="$m=stage1/cells-$m.csv $m=grow/cells-$m.csv $m=stage2/cells-$m.csv $m=stage3/cells-$m.csv"
    python3 ../../scripts/tuning/fronts.py --seeds 7,8,9,10,11,12,13,14,15,16 --pairs --select-seeds 7,8,9 \
      $E --csv fronts-$m.csv $C > fronts-$m.txt
    python3 ../../scripts/tuning/best.py $E --set stage2/stage3-$m.csv --csv best-$m.csv $C > best-$m.txt
  done
  ```

  Stage 3's set, from stages 1 and 2, the same way:

  ```bash
  for m in A B; do
    E2=$(for f in stage1/$m/{small,large}.txt.dry grow/$m/*.txt.dry stage2/$m/{small,large}.txt.dry; do
           printf -- '--expect %s ' "$f"; done)
    C2="$m=stage1/cells-$m.csv $m=grow/cells-$m.csv $m=stage2/cells-$m.csv"
    python3 ../../scripts/tuning/selection.py $E2 --roles selected,base,fastest-neighbour \
      --csv stage2/stage3-$m.csv $C2
  done
  ```

  The one schedule against the default, and the check on fresh networks, also from `data/tuning`:

  ```bash
  for m in A B; do
    E=$(for f in stage1/$m/{small,large}.txt.dry grow/$m/*.txt.dry stage2/$m/{small,large}.txt.dry \
                 stage3/$m/{small,large}.txt.dry; do printf -- '--expect %s ' "$f"; done)
    C="$m=stage1/cells-$m.csv $m=grow/cells-$m.csv $m=stage2/cells-$m.csv $m=stage3/cells-$m.csv"
    [ $m = B ] && { E="$E --expect fill/B/fill.txt.dry"; C="$C B=fill/cells-B.csv"; }
    python3 ../../scripts/tuning/schedule.py $E --best best-$m.csv --csv schedule-$m.csv $C > schedule-$m.txt
  done
  python3 ../../scripts/tuning/fresh.py --expect fresh/B/fresh.txt.dry --expect fresh/A/fresh.txt.dry \
    B=fresh/cells-B.csv A=fresh/cells-A.csv > fresh.txt
  ```

  Figure 6's tuned line: the schedule's cells (`schedule_cells.py`, which imports `schedule.py`), the numbers
  against update 2's data (`figure6.py`, whose `--sizes` repeats), and the figure (`scripts/seacast_sizes.py`,
  update 2's script with a repeatable `--csv`, a `--schedule` option, and `--no-variants`, which leaves out update
  2's two open variants; it needs matplotlib). From `data/tuning`, after the commands above:

  ```bash
  for m in A B; do
    E=$(for f in stage1/$m/{small,large}.txt.dry grow/$m/*.txt.dry stage2/$m/{small,large}.txt.dry \
                 stage3/$m/{small,large}.txt.dry; do printf -- '--expect %s ' "$f"; done)
    C="$m=stage1/cells-$m.csv $m=grow/cells-$m.csv $m=stage2/cells-$m.csv $m=stage3/cells-$m.csv"
    [ $m = B ] && { E="$E --expect fill/B/fill.txt.dry"; C="$C B=fill/cells-B.csv"; }
    python3 ../../scripts/tuning/schedule_cells.py $E --best best-$m.csv --check schedule-$m.csv \
      --csv schedule-cells-$m.csv $C > schedule-cells-$m.txt
  done
  python3 ../../scripts/tuning/figure6.py --sizes ../../../u2/data/sizes.csv --sizes ../small/sizes-small.csv \
    schedule-cells-A.csv schedule-cells-B.csv > figure6.txt
  cd ../..
  python3 scripts/seacast_sizes.py --csv ../u2/data/sizes.csv --csv data/small/sizes-small.csv \
    --schedule data/tuning/schedule-cells-A.csv --schedule data/tuning/schedule-cells-B.csv \
    --out figures/seacast_sizes.png --gs-gap 40000 --no-variants
  ```

  The known answer, against the record of update 2's data:
  `python3 ../../scripts/tuning/known_answer.py A=known/cells-A.csv B=known/cells-B.csv --u2 ../../../u2/data/sizes.csv`.
- **Not published:** the cell logs, as in update 2 (`read.py`, which turns them into rows, needs them). The launch
  scripts (`cell.sh`, `tune.sh`, `lane.sh` and their helpers) cite unpublished notes, as in update 2; their
  settings are stated above and in each row.

## Code

The tuning's SEACAST cells ran prysm research commit `28fe390301` (the test binary's md5
`58dff1644574746fd59ce8361db32912`, one binary for every SEACAST cell). Its snapshot is `d0027569e7` on
[`payload-segmentation-snapshot`](https://github.com/cskiraly/prysm/tree/payload-segmentation-snapshot): the research
tree without its notes, with comments that cite unpublished notes rewritten, as in the snapshots of
updates 1 and 2. [eth-networking-lab](https://github.com/cskiraly/eth-networking-lab) is expected beside the tree at `f108f3b`, its
`main`: the revision the tuning's binary was built with, and one the snapshot compiles with.
Gossipsub's reference cells at 32 and 64 KiB ran update 2's gossipsub binary: snapshot `fe605ca7e3` (research
`4fd3f2b8d5`), as in the [record of update 2](../u2/README.md).

The research commit is 15 commits over Figure 6's `589bf05d4b`, with no merges. Its additions:
- **Leopard codes** (`container/segments/leopard.go`): Leopard Reed–Solomon over GF(2¹⁶) as descriptor version 3,
  up to 8192 chunks, and over GF(2⁸) as version 4, up to 256 chunks with at most 128 parity. Both allow 1 to 3
  parity chunks a data chunk. The GF(2⁸) matrix code stays version 2 and the default. The dependency
  `github.com/klauspost/reedsolomon` moves from v1.9.3 to v1.12.5.
- **The GF(2⁸) matrix code's check** (`RecoverAndVerify`) now re-encodes all the parity and checks the root,
  instead of recomputing only the missing chunks. No cell calls it: a cell counts a node complete at K chunks.
- **The harness's new variables**, each unset by default, which keeps `589bf05d4b`'s behaviour:
  - `SEGMENT_RS_CODE` (`gf8`, `leo8`, `leo16`): the code;
  - `SEGMENT_OFFER_PER_PEER` (a number, or `group`): the offer bound;
  - `SEGMENT_OFFER_REFUSALS`: the counter, which only observes.

  The tuning's other knobs are Figure 6's variables: `SEGMENT_A_PHASE_R`, `SEGMENT_A_PHASE_R_FAST`,
  `SEGMENT_FIXED_COUNT`, `SEGMENT_PARITY`, `SEGMENT_COMPRESS_FIRST` and `SEGMENT_PAYLOAD_BYTES`.
- **The pubsub fork** (in the tree at `third_party/go-libp2p-pubsub`, base v0.17.0, and the Bazel patch):
  `WithOfferPeerBound`, `WithOfferPeerBoundByGroup` and `WithOfferOutcomes`, and four tests, two of them
  witnesses of version 0.5's rules. With no option set, the fork bounds and counts as before.
- **The CPU benchmark** `BenchmarkCPU` (`container/segments/cpu_bench_test.go`), with its own variables
  (`SEGMENT_BENCH_*`). It runs in no cell.

