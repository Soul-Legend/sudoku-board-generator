"""Sudoku solver using constraint propagation and backtracking."""

from __future__ import annotations

import numpy as np

from sudoku.models import Board, BoardSize


class Solver:
    """Solves Sudoku puzzles using constraint propagation + backtracking.

    Can also count solutions (up to a limit) to verify uniqueness.
    """

    def __init__(self, size: BoardSize) -> None:
        self._n = size.n
        self._box_r = size.box_rows
        self._box_c = size.box_cols
        self._all_values = frozenset(range(1, self._n + 1))

    def solve(self, board: Board) -> Board | None:
        """Return a solved board, or None if unsolvable."""
        grid = board.grid.copy()
        if self._backtrack(grid):
            return Board(grid=grid, size=board.size)
        return None

    def count_solutions(self, board: Board, limit: int = 2) -> int:
        """Count solutions up to `limit`. Useful for checking uniqueness."""
        grid = board.grid.copy()
        counter = [0]
        self._count_backtrack(grid, counter, limit)
        return counter[0]

    def has_unique_solution(self, board: Board) -> bool:
        """Check that the board has exactly one solution."""
        return self.count_solutions(board, limit=2) == 1

    def _get_candidates(self, grid: np.ndarray, row: int, col: int) -> set[int]:
        """Get valid candidate values for a cell using constraint propagation."""
        used: set[int] = set()

        # Row constraints
        used.update(grid[row, :])
        # Column constraints
        used.update(grid[:, col])
        # Box constraints
        br = (row // self._box_r) * self._box_r
        bc = (col // self._box_c) * self._box_c
        used.update(grid[br : br + self._box_r, bc : bc + self._box_c].flat)

        used.discard(0)
        return set(self._all_values - used)

    def _find_best_empty(self, grid: np.ndarray) -> tuple[int, int, set[int]] | None:
        """Find the empty cell with the fewest candidates (MRV heuristic)."""
        best: tuple[int, int, set[int]] | None = None
        best_count = self._n + 1

        for r in range(self._n):
            for c in range(self._n):
                if grid[r, c] == 0:
                    candidates = self._get_candidates(grid, r, c)
                    if not candidates:
                        return None  # Dead end: no valid values
                    if len(candidates) < best_count:
                        best = (r, c, candidates)
                        best_count = len(candidates)
                        if best_count == 1:
                            return best  # Can't do better

        return best

    def _backtrack(self, grid: np.ndarray) -> bool:
        """Solve the grid in-place using backtracking with MRV."""
        result = self._find_best_empty(grid)
        if result is None:
            # No empty cells found — either solved or dead end
            return not np.any(grid == 0)

        row, col, candidates = result
        for val in candidates:
            grid[row, col] = val
            if self._backtrack(grid):
                return True
            grid[row, col] = 0

        return False

    def _count_backtrack(
        self, grid: np.ndarray, counter: list[int], limit: int
    ) -> None:
        """Count solutions up to limit."""
        if counter[0] >= limit:
            return

        result = self._find_best_empty(grid)
        if result is None:
            if not np.any(grid == 0):
                counter[0] += 1
            return

        row, col, candidates = result
        for val in candidates:
            grid[row, col] = val
            self._count_backtrack(grid, counter, limit)
            grid[row, col] = 0
            if counter[0] >= limit:
                return
