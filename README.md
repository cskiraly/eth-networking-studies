# eth-networking-studies

One commit of this repository pins every piece of code behind one published networking
study: the client branch the measurements ran on, the library forks it built against, and
the measurement instruments. Each publication is a tag. Check out a tag, run
`git submodule update --init`, and every directory is at the commit the study used.

The four oldest tags were made in September 2026 from the posts' dates: those posts linked
repositories, not commits, so each directory is at the last commit on the linked branch before
the post went up, and each section says where that leaves a gap.

To cite a study, cite its publication and name this repository's tag for the code; each section
ends with a ready-made citation and its BibTeX. `CITATION.cff` describes the repository itself.

| tag | publication |
| --- | --- |
| `fulldas` | [FullDAS: towards massive scalability with 32MB blocks and beyond](https://ethresear.ch/t/fulldas-towards-massive-scalability-with-32mb-blocks-and-beyond/19529), 2024-05-11 |
| `discv5-crawler` | [Crawling the Ethereum discv5 network, fast](https://ethresear.ch/t/crawling-the-ethereum-discv5-network-fast/20962), 2024-11-12 |
| `batch-publishing` | [Improving DAS performance with GossipSub Batch Publishing](https://ethresear.ch/t/improving-das-performance-with-gossipsub-batch-publishing/21713), 2025-02-10 |
| `pppt` | [PPPT: Fighting the GossipSub Overhead with Push-Pull Phase Transition](https://ethresear.ch/t/pppt-fighting-the-gossipsub-overhead-with-push-pull-phase-transition/22118), 2025-04-09 |
| `rowdas` | [EIP-8371: RowDAS, distributed blobspace reconstruction](https://ethereum-magicians.org/t/eip-8371-rowdas-distributed-blobspace-reconstruction/29320), 2026-08-31 |
| `segmentation-part2` | [Wen fast payload broadcast? Segment, code, push, pull, and everything in between](https://ethresear.ch/t/wen-fast-payload-broadcast-segment-code-push-pull-and-everything-in-between/25913) and [EIP-8411: what segmented payload diffusion is made of](https://ethresear.ch/t/eip-8411-what-segmented-payload-diffusion-is-made-of/26025), 2026-09-17 |
| `shadow-crosscheck` | the two-simulator cross-check of the segmentation results under Shadow, 2026-09 (post and report forthcoming) |

## `shadow-crosscheck`

The segmentation results rerun cell by cell under the [Shadow](https://shadow.github.io/)
simulator, over QUIC and over TCP, beside their in-process twins; and the same node run as one
process per Linux network namespace on the real kernel stack, with the links shaped by the
kernel's traffic control.

| directory | repository | commit | role |
| --- | --- | --- | --- |
| `prysm/` | [cskiraly/prysm](https://github.com/cskiraly/prysm), branch `payload-segmentation-snapshot` | `c4d72f7959` | the research tree the cells ran (`af6e41eb7d` without its notes, plus the previous snapshot's `testing/segstudy`): the Shadow node `TestShadowNode` and the topology export in `beacon-chain/p2p/segmentintegrationtest`, the arm catalogue and cell scripts for both substrates in `testing/shadowstudy`, the two library forks vendored under `third_party/`. The real-stack cells ran the node with its dial deadline and handshake bound taken from the cell (`0871156c89`), which this commit carries on the snapshot |
| `eth-networking-lab/` | [cskiraly/eth-networking-lab](https://github.com/cskiraly/eth-networking-lab) | `f108f3b` | the Shadow tooling in `shadowsim/`: topology to Shadow config, the stall watchdog, the record extractor, the pairing; and the namespace backend (`nsrun.py`, `nsmesh.py`, `nsextract.py`, `nsunpriv.sh`), which runs the same node on the real Linux network stack. The Shadow cells ran at `0a29198`, the real-stack cells at this commit |
| `shadow/` | [shadow/shadow](https://github.com/shadow/shadow), release 3.3.0 | `5a05740ba` | the simulator |
| `shadow-patches/` | this repository | | three patches the cells' Shadow carried: hosts get their upload rate from `bandwidth_up` (fixed upstream in `28cca3873`, unreleased), `sched_getaffinity` no longer checks that the tid belongs to a known thread and answers for the calling thread (Go's cgo start-up passes glibc's native main-thread tid, which Shadow did not know), UDP `setsockopt` accepts the don't-fragment and receive-TOS requests quic-go makes |

At this tag the other submodules of the earlier publications do not exist: both forks are
vendored inside `prysm/third_party/` at the commits `segmentation-part2` pinned. `prysm/go.mod`
replaces `eth-networking-lab` with `../eth-networking-lab`, which is the sibling directory here.

`build.sh` builds the patched Shadow and the node binary. One cell on each substrate, from
`prysm/testing/shadowstudy/` (details in its README and in the lab's `shadowsim/tools/README.md`):

```sh
git checkout shadow-crosscheck && git submodule update --init && ./build.sh
export STUDY=$PWD/prysm/testing/shadowstudy BIN=$PWD/bin/segshadow.test RES=$PWD/results
$STUDY/cell.sh shadow  atuned_32k 7 quic 500 p1m            # Shadow over QUIC
$STUDY/cell.sh shadow  atuned_32k 7 tcp  500 p1m            # Shadow over TCP
$STUDY/cell.sh harness atuned_32k 7 quic 500 p1m            # the in-process twin
QDISC=round-robin $STUDY/cell.sh shadow wholend 7 tcp 500 p1m   # the fair-share queue cell
python3 -B eth-networking-lab/shadowsim/tools/compare.py --shadow results --harness results
```

`cell.sh` writes every record into `RES`, Shadow and twin alike, and `compare.py` pairs the
Shadow records in a directory with the harness records in it. A 500-node cell needs about
10 GB of memory and a few minutes. Identical inputs and seeds do not guarantee identical Shadow
results, even within a session; treat each run as a sample and compare medians over paired
seeds, as the lab's tools guide explains.

The same cells on the real network stack, at 100 nodes: one process per node in its own
network namespace, virtual links at the topology's rates and delays, the uplink queue a FIFO
or fq_codel. No root is needed, only a kernel with unprivileged user namespaces and the
`iproute2` tools; the machine's CPU is shared by every node, so the records carry the host's
load and a cell counts as a network measurement only when the host had headroom while the
payload spread (the lab's guide, under Validity).

```sh
python3 -B eth-networking-lab/shadowsim/tools/nsmesh.py --study $STUDY --binary $BIN \
  --sizes 100 --delay-scope neighbours --out mesh100     # plans: three arms × two transports × two queues
eth-networking-lab/shadowsim/tools/nsunpriv.sh mesh100/run-all.sh   # builds, runs three times, extracts
python3 -B eth-networking-lab/shadowsim/tools/compare.py --backend shadow=results \
  --backend harness=results --backend netns=mesh100 \
  --queue-agnostic harness   # ratios to Shadow; --reference-backend harness pairs the fq_codel cells with the harness
```

**Cite as.** The post and the technical report are forthcoming; their citations are added here when they are up. Code: <https://github.com/cskiraly/eth-networking-studies>, tag `shadow-crosscheck`.

## `segmentation-part2`

Part 1 published no code and deferred to Part 2. Part 2 linked two Prysm trees and two fork
branches, all pinned here.

| directory | repository | commit | role |
| --- | --- | --- | --- |
| `prysm/` | [cskiraly/prysm](https://github.com/cskiraly/prysm), branch `payload-segmentation-snapshot`, tag `followup-part1` | `070d401b34` | the research tree the figures were measured on: variants A, B, C and the rest in `beacon-chain/p2p/segmentintegrationtest`, the fleet scripts and extractors in `testing/segstudy`, the in-process instruments in `testing/gossipsim` |
| `prysm-variant-a/` | [cskiraly/prysm](https://github.com/cskiraly/prysm), branch `variant-a` | `4f53d9d543` | the clean implementation of variant A: segmentation, Merkle commitment, erasure coding, as a reviewable series on `develop` |
| `go-libp2p-pubsub/` | [cskiraly/go-libp2p-pubsub](https://github.com/cskiraly/go-libp2p-pubsub), branch `segments-snapshot`, tag `followup-part1` | `16ca04274f` | the research fork the snapshot builds against: phase forwarding, the IWANT discipline, the experiment machinery |
| `go-libp2p-pubsub-variant-a/` | [cskiraly/go-libp2p-pubsub](https://github.com/cskiraly/go-libp2p-pubsub), branch `variant-a` | `8e0db63ecb` | the fork changes variant A needs, as a clean series |
| `simnet/` | [cskiraly/simnet](https://github.com/cskiraly/simnet), branch `burst-window` | `816b7ffb26` | `LinkSettings.BurstWindow` |
| `eth-networking-lab/` | [cskiraly/eth-networking-lab](https://github.com/cskiraly/eth-networking-lab) | `42eaad1` | the standalone equivalent of `testing/gossipsim` as of the day before publication; the measurements ran on the copy inside `prysm/` |

The snapshot's `go.mod` replaces both libraries with the exact fork commits pinned here; the
`variant-a` series replaces only go-libp2p-pubsub and uses upstream simnet. A build inside either
tree uses its pins without further configuration. How the figures were
produced is in `prysm/testing/segstudy/README.md`.

```sh
git clone --recurse-submodules https://github.com/cskiraly/eth-networking-studies
cd eth-networking-studies && git checkout segmentation-part2 && git submodule update --init
cd prysm && cat testing/segstudy/README.md
```

**Cite as.** Csaba Kiraly, "Wen fast payload broadcast? Segment, code, push, pull, and everything in between", ethresear.ch, 4 September 2026, <https://ethresear.ch/t/wen-fast-payload-broadcast-segment-code-push-pull-and-everything-in-between/25913>. Code: <https://github.com/cskiraly/eth-networking-studies>, tag `segmentation-part2`.

<details><summary>BibTeX</summary>

```bibtex
@misc{kiraly2026segmentation1,
  author       = {Kiraly, Csaba},
  title        = {Wen fast payload broadcast? {Segment}, code, push, pull, and everything in between},
  howpublished = {ethresear.ch},
  year         = {2026},
  month        = sep,
  url          = {https://ethresear.ch/t/wen-fast-payload-broadcast-segment-code-push-pull-and-everything-in-between/25913},
  note         = {Code: \url{https://github.com/cskiraly/eth-networking-studies}, tag segmentation-part2}
}
```
</details>

**Cite as.** Csaba Kiraly, "EIP-8411: what segmented payload diffusion is made of", ethresear.ch, 17 September 2026, <https://ethresear.ch/t/eip-8411-what-segmented-payload-diffusion-is-made-of/26025>. Code: <https://github.com/cskiraly/eth-networking-studies>, tag `segmentation-part2`.

<details><summary>BibTeX</summary>

```bibtex
@misc{kiraly2026segmentation2,
  author       = {Kiraly, Csaba},
  title        = {{EIP-8411}: what segmented payload diffusion is made of},
  howpublished = {ethresear.ch},
  year         = {2026},
  month        = sep,
  url          = {https://ethresear.ch/t/eip-8411-what-segmented-payload-diffusion-is-made-of/26025},
  note         = {Code: \url{https://github.com/cskiraly/eth-networking-studies}, tag segmentation-part2}
}
```
</details>

## `rowdas`

| directory | repository | commit | role |
| --- | --- | --- | --- |
| `prysm/` | [cskiraly/prysm](https://github.com/cskiraly/prysm), branch `rowdas` | `2cec8fe20a` | RowDAS behind `--row-das`; the harness `beacon-chain/p2p/rowintegrationtest` and the in-process instruments `testing/gossipsim` |
| `go-libp2p-pubsub/` | [cskiraly/go-libp2p-pubsub](https://github.com/cskiraly/go-libp2p-pubsub), branch `rowdas-partial-messages` | `115d7f6949` | `SetPartialInterest`, `RegisterPartial`, `PublishAction.OnSent`, the experiment machinery |
| `simnet/` | [cskiraly/simnet](https://github.com/cskiraly/simnet), branch `burst-window` | `816b7ffb26` | `LinkSettings.BurstWindow` |
| `eth-networking-lab/` | [cskiraly/eth-networking-lab](https://github.com/cskiraly/eth-networking-lab) | `2167ef4` | the instruments extracted from `testing/gossipsim` as a standalone module, published alongside; the study ran the copy inside Prysm |

At this tag the `prysm-variant-a/` and `go-libp2p-pubsub-variant-a/` directories do not exist.
The experiments are Go tests under `prysm/beacon-chain/p2p/rowintegrationtest`; the
changelog fragment `prysm/changelog/cskiraly_rowdas.md` summarises the change.

```sh
git checkout rowdas && git submodule update --init
cd prysm && go test -count=1 -run 'TestR' ./beacon-chain/p2p/rowintegrationtest/
```

**Cite as.** Csaba Kiraly, "RowDAS (EIP-8371): Distributed Blob Reconstruction, measured", ethresear.ch, 3 September 2026, <https://ethresear.ch/t/rowdas-eip-8371-distributed-blob-reconstruction-measured/25897>. Code: <https://github.com/cskiraly/eth-networking-studies>, tag `rowdas`. The EIP itself is discussed at <https://ethereum-magicians.org/t/eip-8371-rowdas-distributed-blobspace-reconstruction/29320>.

<details><summary>BibTeX</summary>

```bibtex
@misc{kiraly2026rowdas,
  author       = {Kiraly, Csaba},
  title        = {{RowDAS} ({EIP-8371}): distributed blob reconstruction, measured},
  howpublished = {ethresear.ch},
  year         = {2026},
  month        = sep,
  url          = {https://ethresear.ch/t/rowdas-eip-8371-distributed-blob-reconstruction-measured/25897},
  note         = {Code: \url{https://github.com/cskiraly/eth-networking-studies}, tag rowdas}
}
```
</details>

## `pppt`

[PPPT: Fighting the GossipSub Overhead with Push-Pull Phase Transition](https://ethresear.ch/t/pppt-fighting-the-gossipsub-overhead-with-push-pull-phase-transition/22118)
linked the Nim DAS simulator only, whose `main` had not moved since `batch-publishing`. The
push-pull strategies themselves are on the `gossipsub-push-pull` branch of the nim-libp2p fork,
which the post did not link; its commit with the PPPT strategies was pushed on 2025-04-15, six
days after the post went up on 2025-04-09, and is pinned here as the closest public code.

| directory | repository | commit | role |
| --- | --- | --- | --- |
| `das-simulator-nim/` | [cskiraly/das-simulator-nim](https://github.com/cskiraly/das-simulator-nim), branch `main` | `4ba1a698e` | the Nim DAS simulator, unchanged since `batch-publishing` |
| `nim-libp2p/` | [cskiraly/nim-libp2p](https://github.com/cskiraly/nim-libp2p), branch `gossipsub-push-pull` | `073bc48cf` | the push-pull strategies including PPPT (`073bc48cf`), IDONTWANT disabled for the experiments (`60185c6a3`), the hop count in the message and the pending-IWANT tracking they build on (`86624760a` to `7b3a5ec46`) |

Build as in `fulldas`, with the simulator's vendored copy pointed at `nim-libp2p/`.

```sh
git checkout pppt && git submodule update --init --recursive
git -C nim-libp2p log --oneline 507242370..HEAD
```

**Cite as.** Csaba Kiraly, "PPPT: Fighting the GossipSub Overhead with Push-Pull Phase Transition", ethresear.ch, 9 April 2025, <https://ethresear.ch/t/pppt-fighting-the-gossipsub-overhead-with-push-pull-phase-transition/22118>. Code: <https://github.com/cskiraly/eth-networking-studies>, tag `pppt`.

<details><summary>BibTeX</summary>

```bibtex
@misc{kiraly2025pppt,
  author       = {Kiraly, Csaba},
  title        = {{PPPT}: fighting the {GossipSub} overhead with push-pull phase transition},
  howpublished = {ethresear.ch},
  year         = {2025},
  month        = apr,
  url          = {https://ethresear.ch/t/pppt-fighting-the-gossipsub-overhead-with-push-pull-phase-transition/22118},
  note         = {Code: \url{https://github.com/cskiraly/eth-networking-studies}, tag pppt}
}
```
</details>

## `batch-publishing`

[Improving DAS performance with GossipSub Batch Publishing](https://ethresear.ch/t/improving-das-performance-with-gossipsub-batch-publishing/21713)
linked the two DAS simulators and the `batch-publish` branch of the author's nim-libp2p fork;
the author's comment under the post linked the branch's two commits over `507242370`. The
simulators are at the last commits on their linked branches before the post went up on
2025-02-10, which are still their tips.

| directory | repository | commit | role |
| --- | --- | --- | --- |
| `das-research/` | [logos-storage/das-research](https://github.com/logos-storage/das-research), branch `master` | `c53043bab` | the Python DAS simulator, unchanged since `fulldas` |
| `das-simulator-nim/` | [cskiraly/das-simulator-nim](https://github.com/cskiraly/das-simulator-nim), branch `main` | `4ba1a698e` | the Nim DAS simulator with the FullDAS branch merged, the Shadow configuration templated and Shadow's memory manager in use (2024-09-10). Its vendored nim-libp2p is still `ee5eda960`, older than the branch below |
| `nim-libp2p/` | [cskiraly/nim-libp2p](https://github.com/cskiraly/nim-libp2p), branch `batch-publish` | `ba11226b1` | `batchPublish` in `libp2p/protocols/pubsub/gossipsub.nim`: `ea8c22314` factors the publish path, `ba11226b1` adds the batch call (2025-02-07) |

Build as in `fulldas`; to run the simulator against the batch-publish branch, point its vendored
copy at `nim-libp2p/`.

```sh
git checkout batch-publishing && git submodule update --init --recursive
git -C nim-libp2p log --oneline 507242370..HEAD
```

**Cite as.** Csaba Kiraly, "Improving DAS performance with GossipSub Batch Publishing", ethresear.ch, 10 February 2025, <https://ethresear.ch/t/improving-das-performance-with-gossipsub-batch-publishing/21713>. Code: <https://github.com/cskiraly/eth-networking-studies>, tag `batch-publishing`.

<details><summary>BibTeX</summary>

```bibtex
@misc{kiraly2025batchpublishing,
  author       = {Kiraly, Csaba},
  title        = {Improving {DAS} performance with {GossipSub} batch publishing},
  howpublished = {ethresear.ch},
  year         = {2025},
  month        = feb,
  url          = {https://ethresear.ch/t/improving-das-performance-with-gossipsub-batch-publishing/21713},
  note         = {Code: \url{https://github.com/cskiraly/eth-networking-studies}, tag batch-publishing}
}
```
</details>

## `discv5-crawler`

[Crawling the Ethereum discv5 network, fast](https://ethresear.ch/t/crawling-the-ethereum-discv5-network-fast/20962)
linked one repository and no commit. The pin is the last commit on `master` before the post
went up on 2024-11-12, committed five minutes earlier.

| directory | repository | commit | role |
| --- | --- | --- | --- |
| `fast-ethereum-crawler/` | [cskiraly/fast-ethereum-crawler](https://github.com/cskiraly/fast-ethereum-crawler), branch `master` | `0a031926a` | `dcrawl`: the crawler built on nim-eth's discv5, its faster exploration of the node-ID space, the crawl loop with its cycle and discovery-file options, and the post-processing plots. Its own submodules vendor the author's fork of [status-im/nim-eth](https://github.com/status-im/nim-eth) and the Nimbus build system |

The crawler's README has the build (`make update`, then `make`) and the `run.sh` options.

```sh
git checkout discv5-crawler && git submodule update --init --recursive
cat fast-ethereum-crawler/README.md
```

**Cite as.** Csaba Kiraly, "Crawling the Ethereum discv5 network, fast", ethresear.ch, 12 November 2024, <https://ethresear.ch/t/crawling-the-ethereum-discv5-network-fast/20962>. Code: <https://github.com/cskiraly/eth-networking-studies>, tag `discv5-crawler`.

<details><summary>BibTeX</summary>

```bibtex
@misc{kiraly2024crawler,
  author       = {Kiraly, Csaba},
  title        = {Crawling the {Ethereum} {discv5} network, fast},
  howpublished = {ethresear.ch},
  year         = {2024},
  month        = nov,
  url          = {https://ethresear.ch/t/crawling-the-ethereum-discv5-network-fast/20962},
  note         = {Code: \url{https://github.com/cskiraly/eth-networking-studies}, tag discv5-crawler}
}
```
</details>

## `fulldas`

[FullDAS: towards massive scalability with 32MB blocks and beyond](https://ethresear.ch/t/fulldas-towards-massive-scalability-with-32mb-blocks-and-beyond/19529)
linked two simulators and no commits. Each directory is at the last commit on the linked
branch before the post went up on 2024-05-11.

| directory | repository | commit | role |
| --- | --- | --- | --- |
| `das-research/` | [logos-storage/das-research](https://github.com/logos-storage/das-research) (linked as `codex-storage/das-research`, since renamed), branch `master` | `c53043bab` | the Python DAS simulator: the abstract, large-scale model of a 2D erasure-coded block spreading over row and column subnets, with custody, sampling and the parameter sweeps that produce the summary figures. `master` has not moved since 2024-03-29; the repository's `develop` branch stood at `04004ed`, 64 commits ahead, on the same day |
| `das-simulator-nim/` | [cskiraly/das-simulator-nim](https://github.com/cskiraly/das-simulator-nim), branch `main` | `0e2810a11` | the Nim DAS simulator: a nim-libp2p test node with row and column topics, cross-forwarding, simulated erasure coding and reconstruction, run under Shadow. It vendors the author's nim-libp2p fork as its own submodule (`shadow/vendor/nim-libp2p` at `ee5eda960`, the partial-publish work) |

Neither simulator has a build script here. `das-research/README.md` describes the Python
environment and the study files, `das-simulator-nim/README.md` the Shadow build; the vendored
fork needs a recursive submodule update.

```sh
git checkout fulldas && git submodule update --init --recursive
cat das-research/README.md das-simulator-nim/README.md
```

**Cite as.** Csaba Kiraly, "FullDAS: towards massive scalability with 32MB blocks and beyond", ethresear.ch, 11 May 2024, <https://ethresear.ch/t/fulldas-towards-massive-scalability-with-32mb-blocks-and-beyond/19529>. Code: <https://github.com/cskiraly/eth-networking-studies>, tag `fulldas`.

<details><summary>BibTeX</summary>

```bibtex
@misc{kiraly2024fulldas,
  author       = {Kiraly, Csaba},
  title        = {{FullDAS}: towards massive scalability with 32{MB} blocks and beyond},
  howpublished = {ethresear.ch},
  year         = {2024},
  month        = may,
  url          = {https://ethresear.ch/t/fulldas-towards-massive-scalability-with-32mb-blocks-and-beyond/19529},
  note         = {Code: \url{https://github.com/cskiraly/eth-networking-studies}, tag fulldas}
}
```
</details>
