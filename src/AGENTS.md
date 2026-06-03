# Source Code Agent Guide

`src/` contains the PaC Python implementation.

Code standards:

- Python 3.12.
- Public functions and methods must be typed.
- Use `pathlib.Path`.
- Keep CLI handlers thin and move behavior into tested functions.
- Use Pydantic models for metadata validation.
- Return structured results that are easy to serialize as JSON.

The CLI is an agent API. Avoid hidden side effects and interactive prompts.
