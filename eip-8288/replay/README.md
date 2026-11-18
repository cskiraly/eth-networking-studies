# The replay at version 2.5

The record's runs ran on development commits of the simulator that version 2.5 squashes, so
those commits aren't published. To show that version 2.5 gives what they gave, stored runs were
run again on version 2.5's simulator code, one for each kind of result. Each rerun's record was
compared with the stored run's, number by number (every leaf of its JSON): exact, rounding
(within a relative 1e-12, the rounding of a sum taken in another order), or a real difference.
The run's configuration (`workload` and `variant`) was compared the same way.

There were two replays: one of 25 runs for the record's first version, and one of 17 runs for
the series its second version added.

## The first replay: 25 runs

One for each kind of result in the post and in First Questions version 11.

**All 25 reproduce:** every count equal, no real difference. 19 match exactly. 6 match to
rounding: their stored runs came from Python 3.11, whose floats can differ from 3.12's in their
last digits.

`replay.md` and `replay.csv` have one row per run:
- `config`: the run's line in the record's configs, its series and cell;
- `stands for`: the result or figure it is the replay's cell for;
- `exact leaves` and `to 1e-12`: how many of the stored record's numbers came back exactly, and
  to rounding (the CSV also counts `differing_leaves`, 0 in every row). Numbers only the rerun
  has, from measurements added since, aren't compared;
- `compared_apart` (in the CSV): a block compared on its own. The leaf-multiplicity run's
  `leaf_folds` was recorded by an earlier state of that measurement. All 429 of its stored
  numbers come back exactly, and version 2.5 records 211 more beside them;
- `included`: transactions included of those that arrived, stored and rerun.

## The second replay: 17 runs

The second version added 784 runs to [`../interval/`](../interval/), in 8 series (the 845 ms anchor,
and the fold timings at 10,000 nodes with their controls on what binds), and 154 to
[`../transport/`](../transport/), in 5 series (the designs at 10,000 nodes, and pull with one
builder at 7,740 B). They too ran on development commits that version 2.5 squashes. (The second
version's runs of seeds 104–107 ran later, on the last of those commits, whose tree is version
2.5's.) One stored run of each new interval series was run again (a seed-100 run with privacy
load, or with 7,740 B signatures where the series has none), and one of each new kind of transport
result.

**All 17 reproduce exactly:** every count equal, and every number the stored run recorded came back
exactly, none only to rounding: 736,247 and 742,790 numbers in the two runs at 1,000 nodes, and 7.28
to 7.42 million in each at 10,000. The stored runs and the reruns came from Python 3.12 or 3.13. The
interval reruns record one measurement the stored runs predate, `reproving`; it isn't compared.

`replay-interval.md` and `replay-transport.md`, with their CSVs, have one row per run, in the
first replay's columns.
