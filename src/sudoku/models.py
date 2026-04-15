"""Data models for Sudoku boards and puzzles."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from math import isqrt
from typing_extensions import Self

import numpy as np


class Difficulty(Enum):
    """Puzzle difficulty levels."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


@dataclass(frozen=True)
class BoardSize:
    """Defines a Sudoku board size. N must be a perfect square (4, 9, 16, 25...)."""

    n: int

    def __post_init__(self) -> None:
        root = isqrt(self.n)
        if root * root != self.n or self.n < 4:
            raise ValueError(
                f"Board size must be a perfect square >= 4, got {self.n}"
            )

    @property
    def box_rows(self) -> int:
        """Number of rows in each box."""
        return isqrt(self.n)

    @property
    def box_cols(self) -> int:
        """Number of columns in each box."""
        return isqrt(self.n)

    @property
    def total_cells(self) -> int:
        return self.n * self.n


@dataclass(frozen=True)
class Board:
    """Immutable Sudoku board. Values are 0 for empty, 1..N for filled cells."""

    grid: np.ndarray
    size: BoardSize

    def __post_init__(self) -> None:
        if self.grid.shape != (self.size.n, self.size.n):
            raise ValueError(
                f"Grid shape {self.grid.shape} doesn't match size {self.size.n}"
            )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Board):
            return NotImplemented
        return self.size == other.size and np.array_equal(self.grid, other.grid)

    def __hash__(self) -> int:
        return hash(self.canonical_string)

    @property
    def canonical_string(self) -> str:
        """Row-major comma-separated string representation."""
        return ",".join(str(v) for v in self.grid.flat)

    @property
    def sha256(self) -> str:
        """SHA-256 hash of the canonical string."""
        return hashlib.sha256(self.canonical_string.encode()).hexdigest()

    def is_complete(self) -> bool:
        """True if no empty cells."""
        return int(np.count_nonzero(self.grid)) == self.size.total_cells

    def is_valid(self) -> bool:
        """Check that no row, column, or box has duplicate non-zero values."""
        n = self.size.n
        box_r, box_c = self.size.box_rows, self.size.box_cols

        for i in range(n):
            row = self.grid[i, :]
            row_vals = row[row > 0]
            if len(row_vals) != len(set(row_vals)):
                return False

            col = self.grid[:, i]
            col_vals = col[col > 0]
            if len(col_vals) != len(set(col_vals)):
                return False

        for br in range(0, n, box_r):
            for bc in range(0, n, box_c):
                box = self.grid[br : br + box_r, bc : bc + box_c].flatten()
                box_vals = box[box > 0]
                if len(box_vals) != len(set(box_vals)):
                    return False

        return True

    @classmethod
    def from_string(cls, s: str, size: BoardSize) -> Self:
        """Create a Board from a canonical comma-separated string."""
        values = [int(x) for x in s.split(",")]
        grid = np.array(values, dtype=np.int32).reshape(size.n, size.n)
        return cls(grid=grid, size=size)

    def copy(self) -> Board:
        """Create a mutable copy."""
        return Board(grid=self.grid.copy(), size=self.size)


@dataclass(frozen=True)
class Puzzle:
    """A Sudoku puzzle: a board with blanks and its solution."""

    puzzle_board: Board
    solution_board: Board
    difficulty: Difficulty

    def __post_init__(self) -> None:
        if self.puzzle_board.size != self.solution_board.size:
            raise ValueError("Puzzle and solution must have the same size")

    @property
    def size(self) -> BoardSize:
        return self.puzzle_board.size

    @property
    def sha256(self) -> str:
        return self.puzzle_board.sha256

    @property
    def clue_count(self) -> int:
        return int(np.count_nonzero(self.puzzle_board.grid))

    @property
    def blank_count(self) -> int:
        return self.size.total_cells - self.clue_count


@dataclass
class PuzzleRecord:
    """A stored puzzle with metadata."""

    id: int | None
    puzzle: Puzzle
    created_at: datetime = field(default_factory=datetime.now)
