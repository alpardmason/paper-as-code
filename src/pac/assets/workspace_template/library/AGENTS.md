# Library Agent Guide

`library/` is the YAML source of truth.

Use:

- `library/intake/` for intake records.
- `library/objects/` for research object records.
- `library/sources/` for source records.

Metadata must be valid YAML and conform to the Pydantic schemas in the PaC engine. Prefer explicit status fields over inferred workflow state. Do not put generated search data here.
