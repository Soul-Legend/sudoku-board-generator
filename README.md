# Sudoku Board Generator

Generate unique Sudoku puzzles of any N×N size and export them as formatted PDFs. Every puzzle is guaranteed to have a unique solution, and the tool remembers all previously generated boards to ensure you never get a duplicate.

## Features

- **Any board size** — 4×4, 9×9, 16×16, 25×25, or any N×N where N is a perfect square
- **4 difficulty levels** — Easy, Medium, Hard, Expert
- **Persistent deduplication** — SQLite-backed storage ensures no puzzle is ever repeated across runs
- **PDF export** — Configurable layout (1, 2, or 4 puzzles per page) with solution pages
- **Interactive menus** — Navigate options interactively, or bypass with CLI flags
- **Two generation strategies** — Fast shuffle-based or pure backtracking

## Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (macOS/Linux)
source .venv/bin/activate

# Install
pip install -e ".[dev]"
```

## Usage

### Interactive Mode

Simply run (no arguments → interactive menus):

```bash
sudoku
```

Or start the generate flow directly:

```bash
sudoku generate
```

### Flag Mode (bypass menus)

```bash
# Generate 50 medium 9x9 puzzles, 2 per page, with solutions
sudoku generate -s 9 -d medium -n 50 -p 2 --solutions -o puzzles.pdf

# Generate 10 easy 4x4 mini puzzles
sudoku generate -s 4 -d easy -n 10 -o mini.pdf

# Generate 5 hard 16x16 puzzles, 1 per page, no solutions
sudoku generate -s 16 -d hard -n 5 -p 1 --no-solutions -o large.pdf

# Use backtracking strategy instead of shuffle
sudoku generate -s 9 -d expert -n 20 --strategy backtracking -o expert.pdf
```

### Statistics

```bash
sudoku stats
```

### All Options

```
sudoku generate [OPTIONS]

  -s, --size         Board size (4, 9, 16, 25, ...)
  -d, --difficulty   easy | medium | hard | expert
  -n, --count        Number of puzzles to generate
  -p, --per-page     Puzzles per PDF page: 1, 2, or 4
  --solutions        Include solution pages (default)
  --no-solutions     Exclude solution pages
  -o, --output       Output PDF filename
  --strategy         shuffle (default) or backtracking
  --page-size        a4 (default) or letter
  --db               Custom database path
```

## Architecture

```
src/sudoku/
├── cli.py            # Click CLI + questionary interactive menus
├── models.py         # Board, Puzzle, BoardSize (immutable value objects)
├── generator.py      # ShuffleStrategy, BacktrackingStrategy (Strategy pattern)
├── solver.py         # Constraint propagation + backtracking solver
├── puzzle_maker.py   # Removes clues ensuring unique solution
├── repository.py     # SQLite persistence (Repository pattern)
├── pdf_builder.py    # ReportLab PDF generation (Builder pattern)
└── config.py         # Difficulty ratios and constants
```

### Design Patterns

| Pattern | Component | Purpose |
|---------|-----------|---------|
| Strategy | `generator.py` | Swap generation algorithms |
| Repository | `repository.py` | Abstract persistent storage |
| Builder | `pdf_builder.py` | Step-by-step PDF construction |
| Value Object | `models.py` | Immutable boards with equality/hashing |

## Running Tests

```bash
pytest tests/ -v
```

## How Deduplication Works

1. Each puzzle board is serialized to a canonical string (row-major, comma-separated)
2. A SHA-256 hash is computed from that string
3. The hash is stored in an indexed SQLite column
4. Before accepting any new puzzle, the hash is checked — O(1) lookup
5. The database persists across runs in `data/sudoku.db`

------------------------------------
<img width="715" height="884" alt="image" src="https://github.com/user-attachments/assets/371f054b-e4f4-45c4-a3f4-ec505036ac6a" />

