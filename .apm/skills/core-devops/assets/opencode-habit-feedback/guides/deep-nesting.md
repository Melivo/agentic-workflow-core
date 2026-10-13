The code below nests deeper than the threshold.

Core guidance: **S00 – proportionale Grund- und Abschlussprüfung** in
`.apm/skills/core-architecture/references/design-baseline.md` (separation of
responsibilities, small interfaces).

Improvement goal: flatten via early returns and by extracting guard logic the
caller actually needs; keep the public contract unchanged.

Re-verification: re-run the sensor on the file and the task's tests; document
both in the task result.
