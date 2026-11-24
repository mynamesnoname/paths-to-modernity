# Scripts Graph — codebase structure and implementation status

Read this reference when inspecting, generating, or maintaining a repository's
code-structure dependency graph under `_aiHumanInteract/scripts/`.

## Authority and provenance

The source of truth for the Scripts Graph is **the project's actual source code
and configuration files**. Generated views (`graph.json`, `graph.md`,
`graph.canvas`, and the Studio's Scripts lens) are strictly derived outputs;
never hand-edit generated graph files as a parallel authority.

Keep edge provenance explicit across three categories:

1. **`observed` (static analysis)** — deterministically extracted from syntax
   trees and module declarations (`imports`, `invokes`, `CLI entrypoint`).
2. **`declared` (cross-graph links)** — explicitly linked from Plan Graph
   `links.code` / `links.tests` (`implemented_by` / `planned_target`) or
   Knowledge Debt `script_refs`.
3. **`inferred` (annotated architecture)** — optional human or agent role notes
   recorded in `_aiHumanInteract/scripts/annotations.json` with a stated
   `evidence` note; never presented as static AST facts.

## Static extraction model

Inspired by modular dependency analyzers (`pydeps`, `grimp`), static call-graph
tools (`pyan3`), and repository symbol maps (`repomap`), the scanner extracts:

- **Python (`.py`) via two-pass `ast` analysis:**
  - module docstring, LOC, CLI/main entrypoints (`if __name__ == "__main__"`),
    top-level classes and functions;
  - relative and intra-repository `import` / `from ... import ...` resolution
    (`imports` edges);
  - cross-module symbol invocations (`invokes` edges).
- **Web / Script files (`.js`, `.ts`, `.tsx`, `.jsx`, `.vue`, `.sh`, `.html`):**
  - ES module `import` / `require` / `<script src>` / Vue component imports;
  - shell script `python -m <module>` or script invocations.
- **Planned-but-unwritten targets:**
  - file paths referenced in active Plan Graph `links.code` / `links.tests` that
    do not yet exist on disk appear with status `planned_missing`, making the gap
    between planned pragmatic work and current scripts immediately visible.
- **Structural diagnostics:**
  - **PageRank / Hub centrality** to surface core architectural modules first in
    compact summaries and recovery portraits;
  - **Cycle detection** (`cyclic_imports`) to flag circular module dependencies.

## Repository layout

```text
_aiHumanInteract/
  scripts/
    annotations.json     Optional human/agent role annotations (only editable file)
    structure/
      graph.json         Machine-readable module nodes, symbols, edges, cycles, hubs
      graph.md           Markdown summary table and Mermaid module diagram
      graph.canvas       JSON Canvas view
```

Schema identifier: `paths-to-modernity-scripts-graph-v1`.
