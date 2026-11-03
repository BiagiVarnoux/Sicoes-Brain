## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.

Updating the graph (Git hooks are the primary mechanism):
- The git hooks (`post-commit`, `post-checkout`, `post-merge`, `post-rewrite`) rebuild the AST graph automatically after each commit and when switching branches. Do NOT run `graphify update .` after every code edit — the commit hook already does it, and manual runs between commits only duplicate work. Run `graphify update .` by hand only to recover from a known-failed hook (e.g. the hook printed an error), never as a routine post-edit step.
- When there are uncommitted changes (`git status` is not clean), treat the graph as possibly stale: it reflects the last commit, not the working tree. Before trusting a query about code you just touched, contrast the graph's answer with the actual current file, and prefer reading the real lines for anything inside the uncommitted diff.
- SQL migrations and the DB schema are first-class: when reasoning about data flow, always include the schema community (e.g. `monitor/schema.sql` → `convocatorias_radar`, `convocatoria_specs`, `erp_*`) in the analysis, and do not treat a schema/migration change as "just a doc." After a migration lands, let the commit hook rebuild; if the schema change is large, verify the rebuild with `graphify hook status` and a quick `graphify query` against the changed table.
- Documentation and semantic/concept changes (READMEs, COMO_CORRER.md, rationale, design notes) are NOT picked up by the AST-only git hooks. After a meaningful doc or concept change, refresh them manually with `/graphify . --update` (semantic re-extraction).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
