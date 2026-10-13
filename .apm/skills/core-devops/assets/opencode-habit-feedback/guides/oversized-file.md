The original line-count sensor reports an oversized file.

Core guidance: use **M02 – Wissenseigentum und Grenzen** in
`.apm/skills/core-architecture/references/boundaries-and-abstractions.md`.
This is a reference to the canonical method, not a second rule source.

Improvement goal: identify genuinely separate responsibilities and their
public contracts; do not mechanically split at a line threshold or hide
related behaviour in an unrelated utils module. A line metric alone is not
a quality or behaviour-preservation proof.

Re-verification: repeat the original file-scoped sensor/mapper run, keep
all not_scanned gaps visible, and preserve consumer behaviour with the
confirmed task safety net. Coaching does not authorise new tasks or fixes.
