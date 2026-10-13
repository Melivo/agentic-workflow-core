The functions below exceed the parameter threshold.

Core guidance: apply **M02 – Wissenseigentum und Grenzen** in
`.apm/skills/core-architecture/references/boundaries-and-abstractions.md` (the
canonical method; this guide adds no second methodology).

Improvement goal: identify the domain entity whose fields travel together and
move behaviour onto it, at every call site that passes its fields loose — not
just the one that fired.

Re-verification: re-run `habit-sensors --file <path> | habit-mapper` and show
the finding is gone with no new `incomplete-run`; behaviour is preserved by the
task's existing tests.
