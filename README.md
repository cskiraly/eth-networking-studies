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
