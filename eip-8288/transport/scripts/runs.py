"""Run records by name, for the transport tables' scripts.

Each cell's run is the standard output of its command in a ../configs/<series>.tsv, saved in one run
directory as <name>.jsonl; its last line is the run's JSON record. A name says what the cell is:

    <design>-<sharing>-n<nodes>-p<privacy tx/s>-<objects>obj-<proposer>[-<control>]-s<seed>

- design: push, pull, keep, coverage, geth (designs 1 to 5);
- sharing: every (every node aggregates), builder (one builder proves everything and proposes
  every block), quarter (a quarter of the nodes aggregate, placed at random);
- objects: 6 or 501, the most objects a block takes;
- proposer: fixed (node 0, made an aggregator, proposes every slot; with one builder, the builder),
  random (a node drawn each slot, the sharing's own aggregators), or other (a quarter aggregating:
  the first-ranked of its own aggregators at the seed, fixed as the proposer of every slot);
- control, on the fixed proposer: timeout5s (designs 2 and 4 with a 5 s request timeout),
  timeout500ms (design 5 with 500 ms), feeorder (a fold's inputs ranked by fee per proving cost),
  fastprover (proving 1,000 times faster), sig7740 (7,740 B signatures), sigtps2 (2 signature tx/s
  instead of 15, no privacy load).

A missing run reads as None, and the tables print it as missing.
"""
import json
import pathlib

DESIGNS = ("push", "pull", "keep", "coverage", "geth")
SHARINGS = ("every", "builder", "quarter")


def name(design, sharing, nodes, load, objects, proposer="fixed", control=None, seed=100):
    tail = f"-{control}" if control else ""
    return f"{design}-{sharing}-n{nodes}-p{load}-{objects}obj-{proposer}{tail}-s{seed}"


class Runs:
    """The runs of one directory, each read once, on first use."""

    def __init__(self, directory):
        self.directory = pathlib.Path(directory)
        if not self.directory.is_dir():
            raise SystemExit(f"no run directory {self.directory}")
        self.records = {}

    def get(self, *key, **settings):
        stem = name(*key, **settings)
        if stem not in self.records:
            path = self.directory / f"{stem}.jsonl"
            self.records[stem] = (json.loads(path.read_text().splitlines()[-1])
                                  if path.exists() else None)
        return self.records[stem]

    def used(self):
        """The names of the runs read so far that were there."""
        return sorted(stem for stem, record in self.records.items() if record is not None)


def arguments(description):
    """The run directory, and --used FILE to list the runs a table read."""
    import argparse
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("runs", help="the run directory")
    parser.add_argument("--used", metavar="FILE", help="write the names of the runs read here")
    return parser.parse_args()


def write_used(runs, path):
    if path:
        pathlib.Path(path).write_text("".join(f"{stem}\n" for stem in runs.used()))
