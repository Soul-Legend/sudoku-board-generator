# Architecture Documentation

## System Overview

This tool generates Sudoku puzzles of configurable size (any N×N where N is a perfect square), exports them to PDF, and persists all generated puzzles in a SQLite database to guarantee uniqueness across runs.

The codebase is structured as a Python package under `src/sudoku/` with 8 modules. Entry points are a Click-based CLI (`cli.py`) and a `__main__.py` for `python -m sudoku` invocation.

```
src/sudoku/
├── __init__.py
├── __main__.py       → python -m sudoku entry
├── cli.py            → CLI + interactive menus
├── config.py         → difficulty constants
├── generator.py      → board generation strategies
├── models.py         → data models
├── pdf_builder.py    → PDF rendering
├── puzzle_maker.py   → clue removal logic
├── repository.py     → SQLite persistence
└── solver.py         → constraint solver
```

---

## Module Dependency Graph

```
cli.py
 ├── generator.py
 │    ├── solver.py
 │    │    └── models.py
 │    └── models.py
 ├── puzzle_maker.py
 │    ├── solver.py
 │    ├── config.py
 │    └── models.py
 ├── repository.py
 │    └── models.py
 ├── pdf_builder.py
 │    └── models.py
 └── config.py
```

All modules depend on `models.py`. No circular dependencies exist.

---

## Module Reference

### models.py

Defines immutable data types used across the system.

**`BoardSize`** — Validated constraint on the grid dimension. Enforces that `n` is a perfect square ≥ 4. Provides computed properties `box_rows`, `box_cols` (both equal to `√n`), and `total_cells` (`n²`).

**`Board`** — Frozen dataclass wrapping a NumPy `int32` array of shape `(n, n)`. Values are `0` (empty) or `1..n` (filled). Key operations:

| Method/Property | Description |
|---|---|
| `canonical_string` | Row-major, comma-separated serialization. Deterministic. |
| `sha256` | SHA-256 hex digest of `canonical_string`. Used as deduplication key. |
| `is_complete()` | True if no zeros in the grid. |
| `is_valid()` | Checks all rows, columns, and boxes for duplicate non-zero values. |
| `from_string(s, size)` | Inverse of `canonical_string`. Reconstructs the grid. |
| `copy()` | Returns a new `Board` with a copied grid array. |

`__eq__` compares `size` + element-wise grid equality. `__hash__` delegates to `canonical_string`.

**`Difficulty`** — Enum with values `easy`, `medium`, `hard`, `expert`.

**`Puzzle`** — Associates a `puzzle_board` (with blanks) and its `solution_board`. Validates that both boards have the same size. Exposes `sha256` (delegated to puzzle board), `clue_count`, and `blank_count`.

**`PuzzleRecord`** — Mutable container pairing a `Puzzle` with a database `id` and `created_at` timestamp.

### solver.py

Implements a backtracking Sudoku solver with constraint propagation.

**`Solver.__init__(size)`** — Precomputes `n`, `box_r`, `box_c`, and the set of all valid values `{1..n}`.

**`_get_candidates(grid, row, col)`** — Collects all non-zero values in the cell's row, column, and box, then returns `{1..n} - used`. This is the constraint propagation step; it prunes invalid values before branching.

**`_find_best_empty(grid)`** — Scans all empty cells, computes candidates for each, and returns the cell with the fewest candidates (Minimum Remaining Values heuristic). Returns `None` if:
- No empty cells exist (solved state)
- An empty cell has zero candidates (dead end)

These two cases are distinguished by checking `np.any(grid == 0)` in the caller.

**`_backtrack(grid)`** — Recursive depth-first search. Picks the MRV cell, tries each candidate in order, recurses, and backtracks on failure. Modifies the grid in-place.

**`_count_backtrack(grid, counter, limit)`** — Same structure as `_backtrack` but increments a counter instead of returning on the first solution, and short-circuits at `limit`.

**Public API:**

| Method | Returns |
|---|---|
| `solve(board)` | Solved `Board` or `None` if unsolvable |
| `count_solutions(board, limit=2)` | Number of solutions, capped at `limit` |
| `has_unique_solution(board)` | `True` iff exactly 1 solution exists |

### generator.py

Defines `GenerationStrategy` (abstract base class) and two concrete implementations.

**`ShuffleStrategy.generate(size)`**:
1. Constructs a seed grid using the formula `(r * box_c + r // box_r + c) % n + 1`. This always produces a valid complete board.
2. Calls `_shuffle_grid()` which applies 6 randomization operations:
   - Shuffle rows within each band (group of `box_r` consecutive rows)
   - Shuffle columns within each stack (group of `box_c` consecutive columns)
   - Shuffle the order of bands
   - Shuffle the order of stacks
   - Apply a random digit permutation (relabel all 1s→X, all 2s→Y, etc.)
   - Randomly transpose the grid (50% chance)

Each operation preserves Sudoku validity. The composition generates boards from a space of `(box_r!)^box_r × (box_c!)^box_c × box_r! × box_c! × n! × 2` possibilities. For 9×9, this is `(3!)^3 × (3!)^3 × 3! × 3! × 9! × 2 ≈ 1.2 billion` distinct boards from a single seed.

Time complexity: O(n²) per board.

**`BacktrackingStrategy.generate(size)`**:
Fills the grid cell by cell (row-major order) using randomized candidate selection. On conflict, backtracks. Uses `Solver._get_candidates()` for constraint checking.

Time complexity: Variable, typically O(n²) for small sizes but can be significantly slower for large grids.

### puzzle_maker.py

**`PuzzleMaker.make_puzzle(solution, difficulty)`**:

1. Validates that the input board is complete and valid.
2. Computes the target clue count from `config.clue_count_range()`.
3. Creates a shuffled list of all cell coordinates.
4. Iteratively removes cells:
   - Temporarily sets a cell to 0.
   - Calls `Solver.has_unique_solution()` on the resulting board.
   - If uniqueness holds, keeps the removal. Otherwise, restores the value.
5. Stops when the target number of removals is reached or all cells have been attempted.

The uniqueness check is the bottleneck. For each cell removal, the solver must verify that exactly 1 solution exists, which involves running `_count_backtrack` with `limit=2`. For a 9×9 board, this typically takes 0.5–5ms per cell depending on the board state. For harder difficulties (more removals), later removals take longer because the search space is larger.

### config.py

Defines `DIFFICULTY_CLUE_RATIOS`: a mapping from `Difficulty` to `(min_ratio, max_ratio)` of cells to keep as clues.

| Difficulty | Ratio | 9×9 clues | 4×4 clues | 16×16 clues |
|---|---|---|---|---|
| Easy | 0.44–0.56 | 35–45 | 7–8 | 112–143 |
| Medium | 0.33–0.43 | 26–34 | 5–6 | 84–110 |
| Hard | 0.27–0.32 | 21–25 | 4–5 | 69–81 |
| Expert | 0.21–0.26 | 17–21 | 3–4 | 53–66 |

`clue_count_range(n, difficulty)` computes `(min_clues, max_clues)` by scaling ratios to the total cell count `n²`.

### repository.py

**`PuzzleRepository`** wraps a SQLite connection with the following schema:

```sql
CREATE TABLE puzzles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hash        TEXT    UNIQUE NOT NULL,
    size        INTEGER NOT NULL,
    difficulty  TEXT    NOT NULL,
    puzzle      TEXT    NOT NULL,     -- canonical_string of puzzle_board
    solution    TEXT    NOT NULL,     -- canonical_string of solution_board
    created_at  TEXT    NOT NULL      -- ISO 8601 timestamp
);
CREATE INDEX idx_puzzles_hash ON puzzles(hash);
CREATE INDEX idx_puzzles_size ON puzzles(size);
```

Uses WAL journal mode for concurrent read performance.

**Key operations:**

| Method | Behavior |
|---|---|
| `exists(hash)` | `SELECT 1 WHERE hash = ?` — O(1) indexed lookup |
| `save(puzzle)` | Checks `exists()`, inserts, commits. Raises `ValueError` on duplicate. |
| `save_batch(puzzles)` | Wraps all inserts in a single transaction. Skips existing hashes silently. |
| `count(size?, difficulty?)` | `SELECT COUNT(*)` with optional filters. |
| `get_all(size?, difficulty?)` | Fetches all rows, deserializes into `PuzzleRecord` objects. |

Constructor takes an optional `db_path`; defaults to `<project_root>/data/sudoku.db`. Creates the directory and tables if they don't exist.

Implements `__enter__`/`__exit__` for use as a context manager.

### pdf_builder.py

**`PdfBuilder`** constructs PDFs using ReportLab's low-level canvas API.

**Constructor parameters:**
- `output_path: Path` — destination file
- `puzzles_per_page: int` — 1, 2, or 4 (validated)
- `include_solutions: bool` — whether to append solution pages after puzzle pages
- `page_size: PageSize` — A4 or Letter

**`build()`** renders puzzle pages first, then solution pages (if enabled). Returns the output path.

**Layout calculation (`_render_pages`):**
- Computes usable area from page dimensions minus margins (15mm).
- Divides into a grid: 1×1, 1×2, or 2×2 based on `puzzles_per_page`.
- Each slot gets a header (puzzle number, size, difficulty) and the grid below it.
- The grid is square; its side length is the minimum of the slot width and (slot height − header height).

**Grid rendering (`_draw_grid`):**
- Fills cell values centered in each cell. Font size is `min(16, cell_size × 0.55)`, floored at 6.
- Given clues (non-zero in `puzzle_board`) render in bold black. On solution pages, solved cells (zero in `puzzle_board`, non-zero in `solution_board`) render in gray.
- Thin lines (0.5pt) between all cells. Thick lines (2pt) at box boundaries. Outer border at 2.5pt.
- For board sizes > 9, digits 10+ are labeled as hex characters (A=10, B=11, ...).

### cli.py

Provides two interaction modes:

**Interactive mode** — Invoked when `sudoku` is run without subcommands or when `sudoku generate` is run without all required flags. Uses `questionary` for select menus and text prompts. The main menu loops between "Generate puzzles", "View statistics", and "Exit".

**Flag mode** — All parameters passed as CLI flags bypass the interactive prompts entirely.

**Generation flow (`_generate_puzzles`):**
1. Creates a `PuzzleMaker` and the selected `GenerationStrategy`.
2. Loops until `count` unique puzzles are generated:
   - Generates a complete board via the strategy.
   - Creates a puzzle via `PuzzleMaker.make_puzzle()`.
   - Checks `repository.exists(puzzle.sha256)`.
   - If new, saves to the database and adds to the result list.
   - If duplicate, increments a retry counter. After 100 consecutive retries, stops with a warning.
3. Displays progress via `rich.progress.Progress`.

**CLI commands:**

| Command | Required flags for non-interactive | Description |
|---|---|---|
| `sudoku` | none | Opens main menu |
| `sudoku generate` | `-s`, `-d`, `-n` | Generates puzzles |
| `sudoku stats` | none | Shows puzzle counts by size and difficulty |

---

## Data Flow

```
User Input (CLI)
      │
      ▼
GenerationStrategy.generate(size) → complete Board
      │
      ▼
PuzzleMaker.make_puzzle(board, difficulty) → Puzzle
      │                                        │
      │  Solver.has_unique_solution()          │
      │  called per cell removal               │
      │                                        ▼
      │                              PuzzleRepository.exists(hash)
      │                                        │
      │                              ┌─────────┴─────────┐
      │                              │ new                │ duplicate
      │                              ▼                    ▼
      │                    Repository.save()         retry generation
      │                              │
      ▼                              ▼
PdfBuilder.add_puzzles(puzzles)
      │
      ▼
PdfBuilder.build() → PDF file on disk
```

---

## Deduplication Mechanism

Each `Board` has a `canonical_string` property: a row-major, comma-separated representation of all cell values (including zeros for blanks). The SHA-256 hash of this string serves as the deduplication key.

The hash is stored in an indexed `UNIQUE` column in SQLite. Lookups are O(1) via the B-tree index. The check is performed on the puzzle board (with blanks), not the solution, because different puzzles can share the same underlying solution.

The deduplication scope is exact match: two puzzles are considered duplicates if and only if their puzzle grids are identical cell-for-cell. Transformations like rotation, reflection, or digit relabeling are not considered.

---

## Complexity Analysis

| Operation | Time Complexity | Notes |
|---|---|---|
| Board generation (shuffle) | O(n²) | Seed construction + 6 permutation passes |
| Board generation (backtracking) | O(n² × branching) | Variable; slower for large n |
| Candidate computation | O(n) | Scans row, column, and box |
| Solver (backtracking + MRV) | Exponential worst case | Practical: <10ms for 9×9 |
| Uniqueness check | 2 × solve time | Runs solver twice (searches for second solution) |
| Puzzle creation (9×9 easy) | ~50–200ms | ~40 cells tested × ~2ms each |
| Puzzle creation (9×9 expert) | ~200–1000ms | ~60 cells tested, more backtracking per check |
| Hash lookup (SQLite) | O(log n) | B-tree index on hash column |
| PDF rendering | O(puzzles × n²) | One pass per cell per puzzle |

---

## Design Decisions

**NumPy for grids** — Board grids are `np.ndarray` rather than nested lists. This enables fast slicing for row/column/box extraction and efficient `count_nonzero` operations. The overhead of NumPy object creation is negligible for the grid sizes involved.

**SHA-256 for deduplication** — Chosen over simpler hashes (e.g., Python's built-in `hash()`) because it's deterministic across processes and sessions. The canonical string serialization ensures that the hash is stable regardless of NumPy array identity.

**SQLite over JSON** — The database needs O(1) deduplication lookups. A JSON file would require loading all records into memory and scanning linearly. SQLite's indexed B-tree provides logarithmic lookups with zero memory overhead for unaccessed records. WAL mode allows concurrent reads during writes.

**Shuffle strategy as default** — The seed-and-permute approach is orders of magnitude faster than backtracking for standard sizes. The backtracking strategy exists as a fallback for cases where the shuffle approach might produce insufficient variety (theoretical concern for very large boards or specific research use cases).

**Frozen dataclasses** — `Board`, `Puzzle`, `BoardSize`, and `Difficulty` are immutable. This prevents accidental mutation after creation and makes them safe to use as dictionary keys and set members.

**Clue removal with uniqueness verification** — Each cell removal is followed by a uniqueness check (count solutions ≤ 2). This guarantees that every generated puzzle has exactly one solution. The check is the dominant cost in puzzle creation. The MRV heuristic in the solver significantly reduces the search space for this check.

---

## Testing Structure

45 unit tests across 6 test modules:

| Module | Tests | Coverage |
|---|---|---|
| `test_models.py` | 11 | BoardSize validation, Board serialization/hashing, Puzzle invariants |
| `test_solver.py` | 6 | 4×4 and 9×9 solving, unsolvable boards, uniqueness detection |
| `test_generator.py` | 6 | Both strategies produce valid complete boards, shuffle produces distinct boards |
| `test_puzzle_maker.py` | 5 | Unique solutions, clue-solution consistency, invalid input rejection |
| `test_repository.py` | 8 | CRUD operations, duplicate handling, batch saves, persistence across instances |
| `test_pdf_builder.py` | 5 | File creation, layout variations (1/2/4 per page), page size, input validation |

All tests use `tmp_path` fixtures for database isolation.

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| numpy | ≥1.24 | Grid storage and operations |
| click | ≥8.1 | CLI framework with flag parsing |
| questionary | ≥2.0 | Interactive terminal menus |
| rich | ≥13.0 | Progress bars, tables, formatted console output |
| reportlab | ≥4.0 | PDF generation |
| typing_extensions | (transitive) | `Self` type for Python 3.10 compatibility |

Dev dependencies: pytest ≥7.0, pytest-cov ≥4.0.
