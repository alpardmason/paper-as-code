# Reports Agent Guide

Reports are standardized evaluation artifacts.

When writing a report:

- Use `templates/report.md` as the required structure.
- Base every claim on the source context.
- Apply the active Codex evaluation profile together with current workspace context.
- Give a deeper academic summary that helps the reader understand the idea without immediately reading the original paper.
- Assign ⭐, ⭐⭐, or ⭐⭐⭐ only after evaluating usefulness.
- Explain practical implementation relevance.
- Use the active tag taxonomy to label the object in metadata/frontmatter when topic clusters are clear.
- Respect human-provided rating floors from external intake; Codex may promote a rating after
  analysis but should not silently degrade it.
- Use Obsidian wiki links in `## Related Work and Connections` for related reports, notes, and concepts when the relationship is meaningful.
- Recommend related sources as next actions when existing workspace context suggests missing background, competing methods, or follow-up work.
- Avoid filler prose and mechanical template completion.

The CLI may create report stubs, but Codex must write the actual report content through reasoning.
Run report validation after imports or material report edits.
