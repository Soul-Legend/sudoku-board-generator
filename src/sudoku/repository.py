"""SQLite repository for persistent puzzle storage and deduplication."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from sudoku.models import Board, BoardSize, Difficulty, Puzzle, PuzzleRecord

_DEFAULT_DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class PuzzleRepository:
    """Stores puzzles in SQLite with hash-based deduplication.

    Uses SHA-256 hashes of the puzzle board's canonical string for O(1) lookup.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is None:
            db_path = _DEFAULT_DB_DIR / "sudoku.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS puzzles (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                hash        TEXT    UNIQUE NOT NULL,
                size        INTEGER NOT NULL,
                difficulty  TEXT    NOT NULL,
                puzzle      TEXT    NOT NULL,
                solution    TEXT    NOT NULL,
                created_at  TEXT    NOT NULL
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_puzzles_hash ON puzzles(hash)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_puzzles_size ON puzzles(size)"
        )
        self._conn.commit()

    def exists(self, puzzle_hash: str) -> bool:
        """Check if a puzzle with this hash already exists."""
        cur = self._conn.execute(
            "SELECT 1 FROM puzzles WHERE hash = ?", (puzzle_hash,)
        )
        return cur.fetchone() is not None

    def save(self, puzzle: Puzzle) -> PuzzleRecord:
        """Save a puzzle. Raises ValueError if it already exists."""
        h = puzzle.sha256
        if self.exists(h):
            raise ValueError(f"Puzzle with hash {h[:16]}... already exists")

        now = datetime.now().isoformat()
        cur = self._conn.execute(
            """INSERT INTO puzzles (hash, size, difficulty, puzzle, solution, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                h,
                puzzle.size.n,
                puzzle.difficulty.value,
                puzzle.puzzle_board.canonical_string,
                puzzle.solution_board.canonical_string,
                now,
            ),
        )
        self._conn.commit()
        return PuzzleRecord(
            id=cur.lastrowid,
            puzzle=puzzle,
            created_at=datetime.fromisoformat(now),
        )

    def save_batch(self, puzzles: list[Puzzle]) -> list[PuzzleRecord]:
        """Save multiple puzzles in a single transaction."""
        records: list[PuzzleRecord] = []
        now = datetime.now().isoformat()
        with self._conn:
            for puzzle in puzzles:
                h = puzzle.sha256
                if self.exists(h):
                    continue
                cur = self._conn.execute(
                    """INSERT INTO puzzles (hash, size, difficulty, puzzle, solution, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        h,
                        puzzle.size.n,
                        puzzle.difficulty.value,
                        puzzle.puzzle_board.canonical_string,
                        puzzle.solution_board.canonical_string,
                        now,
                    ),
                )
                records.append(
                    PuzzleRecord(
                        id=cur.lastrowid,
                        puzzle=puzzle,
                        created_at=datetime.fromisoformat(now),
                    )
                )
        return records

    def count(self, size: int | None = None, difficulty: str | None = None) -> int:
        """Count stored puzzles, optionally filtered."""
        query = "SELECT COUNT(*) FROM puzzles"
        params: list[str | int] = []
        conditions: list[str] = []

        if size is not None:
            conditions.append("size = ?")
            params.append(size)
        if difficulty is not None:
            conditions.append("difficulty = ?")
            params.append(difficulty)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cur = self._conn.execute(query, params)
        row = cur.fetchone()
        return row[0] if row else 0

    def get_all(
        self, size: int | None = None, difficulty: str | None = None
    ) -> list[PuzzleRecord]:
        """Retrieve all stored puzzles, optionally filtered."""
        query = "SELECT id, hash, size, difficulty, puzzle, solution, created_at FROM puzzles"
        params: list[str | int] = []
        conditions: list[str] = []

        if size is not None:
            conditions.append("size = ?")
            params.append(size)
        if difficulty is not None:
            conditions.append("difficulty = ?")
            params.append(difficulty)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cur = self._conn.execute(query, params)
        records: list[PuzzleRecord] = []
        for row in cur.fetchall():
            board_size = BoardSize(row[2])
            puzzle = Puzzle(
                puzzle_board=Board.from_string(row[4], board_size),
                solution_board=Board.from_string(row[5], board_size),
                difficulty=Difficulty(row[3]),
            )
            records.append(
                PuzzleRecord(
                    id=row[0],
                    puzzle=puzzle,
                    created_at=datetime.fromisoformat(row[6]),
                )
            )
        return records

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> PuzzleRepository:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
