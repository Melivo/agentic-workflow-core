# Provenance

## Local source

- Source: user-provided local `serena-safety` working-tree snapshot.
- Snapshot and transfer date: 2026-07-21.
- Source type: locally created material as represented by the user.
- Immutable revision: unavailable for this local source.
- Historical package status at import: `UNLICENSED`, personal use only.
- Migrated canonical source: `.apm/skills/gortex-serena-configurator/` in `agentic-workflow-core`.
- Migration source revision: `Melivo/apm-package@0c7838d8072dfd70c702cf2d04734a7241550c3e`.
- On 2026-10-14 Melivo explicitly confirmed the required rights to the complete
  skill, scripts and tests, and authorized licensing this migrated skill under MIT.
- Current package license: MIT; see the accompanying `LICENSE`.

The original import did not grant redistribution rights. The explicit owner
confirmation and MIT grant above supersede that historical restriction for this
skill only; they do not relicense the remaining personal-use collection. The
hashes establish snapshot identity, not ownership. The original inventory below
is retained as historical evidence and is not presented as a current inventory.

## Transfer notes

- Preserved the six inventoried source files byte-for-byte at their original
  relative paths.
- Added this file and `REQUIREMENTS.md` as package-local metadata.
- Excluded every `__pycache__` directory and `*.py[cod]` file.
- Retained no concrete source user-home path and introduced no sibling-skill
  runtime dependency.
- Renamed the packaged skill to `gortex-serena-configurator` and added the
  Gortex-first provider policy after transfer; the inventory below identifies
  the original Serena-focused source snapshot and is intentionally unchanged.

## Source inventory (SHA-256)

```text
e3a1fb05027b13455db2d5519c026d0b347cac9c65c0b4e2cb9b04ec82aa08dc  SKILL.md
cad832f90363413ef183faf0d6896b4ca1f472647ed880b5cce586ea576a23a8  scripts/serena_safety.py
e866b07a80124e470bf2e0901bee0297d008eb12a4ebf28cab7b7e7b7ba10ae5  scripts/test_serena_safety.py
1fe2196def31075334fd0f416a3c4b63cd0d607f9140fea6f525ead4d977ee16  scripts/requirements.txt
9928b354dba1140c5e5cb21542f5dadb4e314e1009c83104731b445a5feb3d70  references/configuration-precedence.md
75da33a6961c0d14194a068aae68baaa74bff2216d20ee920129e391f27d3b04  agents/openai.yaml
```

Inventory SHA-256:
`7a97282e68dc27d1fe64aa0d0f475849488c7fb27f70a6317df0ac9090398513`.

The inventory digest is SHA-256 over the UTF-8 records above in displayed
order, with two ASCII spaces between each file hash and relative path and one
trailing LF per record.
