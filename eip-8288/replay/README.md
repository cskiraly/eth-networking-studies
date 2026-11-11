# The replay at version 2.5

The record's runs ran on development commits of the simulator that version 2.5 squashes, so
those commits aren't published. To show that version 2.5 gives what they gave, 25 stored runs
were run again on version 2.5's simulator code, one for each kind of result in the post and in
First Questions version 11. Each rerun's record was compared with the stored run's, number by
number (every leaf of its JSON): exact, rounding (within a relative 1e-12, the rounding of a sum
taken in another order), or a real difference. The run's configuration (`workload` and
`variant`) was compared the same way.

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
