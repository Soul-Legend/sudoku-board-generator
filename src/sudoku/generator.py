"""Sudoku board generation strategies."""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

import numpy as np

from sudoku.models import Board, BoardSize
from sudoku.solver import Solver


class GenerationStrategy(ABC):
    """Abstract base for board generation strategies."""

    @abstractmethod
    def generate(self, size: BoardSize) -> Board:
        """Generate a complete, valid Sudoku board."""


class ShuffleStrategy(GenerationStrategy):
    """Generate boards by constructing a seed and applying random permutations.

    Very fast — O(N²) per board. Works well for all practical sizes.
    The seed is built using a known valid pattern, then rows, columns,
    bands, stacks, and digit labels are shuffled to produce randomness.
    """

    def generate(self, size: BoardSize) -> Board:
        n = size.n
        box_r = size.box_rows
        box_c = size.box_cols

        # Build seed using (row*box_c + row//box_r + col) % n + 1
        grid = np.zeros((n, n), dtype=np.int32)
        for r in range(n):
            for c in range(n):
                grid[r, c] = (r * box_c + r // box_r + c) % n + 1

        grid = self._shuffle_grid(grid, size)
        return Board(grid=grid, size=size)

    @staticmethod
    def _shuffle_grid(grid: np.ndarray, size: BoardSize) -> np.ndarray:
        n = size.n
        box_r = size.box_rows
        box_c = size.box_cols

        # 1) Shuffle rows within each band
        for band in range(box_r):
            rows_in_band = list(range(band * box_r, (band + 1) * box_r))
            random.shuffle(rows_in_band)
            grid[band * box_r : (band + 1) * box_r, :] = grid[rows_in_band, :]

        # 2) Shuffle columns within each stack
        for stack in range(box_c):
            cols_in_stack = list(range(stack * box_c, (stack + 1) * box_c))
            random.shuffle(cols_in_stack)
            grid[:, stack * box_c : (stack + 1) * box_c] = grid[:, cols_in_stack]

        # 3) Shuffle bands (groups of rows)
        bands = list(range(box_r))
        random.shuffle(bands)
        new_grid = np.zeros_like(grid)
        for i, b in enumerate(bands):
            new_grid[i * box_r : (i + 1) * box_r, :] = (
                grid[b * box_r : (b + 1) * box_r, :]
            )
        grid = new_grid

        # 4) Shuffle stacks (groups of columns)
        stacks = list(range(box_c))
        random.shuffle(stacks)
        new_grid = np.zeros_like(grid)
        for i, s in enumerate(stacks):
            new_grid[:, i * box_c : (i + 1) * box_c] = (
                grid[:, s * box_c : (s + 1) * box_c]
            )
        grid = new_grid

        # 5) Relabel digits randomly
        perm = list(range(1, n + 1))
        random.shuffle(perm)
        mapping = np.zeros(n + 1, dtype=np.int32)
        for original, new_val in enumerate(perm, start=1):
            mapping[original] = new_val
        grid = mapping[grid]

        # 6) Random transpose
        if random.random() < 0.5:
            grid = grid.T.copy()

        return grid


class BacktrackingStrategy(GenerationStrategy):
    """Generate boards via randomized backtracking.

    Slower but guarantees uniform randomness and works for any size.
    """

    def generate(self, size: BoardSize) -> Board:
        grid = np.zeros((size.n, size.n), dtype=np.int32)
        solver = Solver(size)
        self._fill(grid, solver, size)
        return Board(grid=grid, size=size)

    def _fill(self, grid: np.ndarray, solver: Solver, size: BoardSize) -> bool:
        for r in range(size.n):
            for c in range(size.n):
                if grid[r, c] == 0:
                    candidates = list(solver._get_candidates(grid, r, c))
                    random.shuffle(candidates)
                    for val in candidates:
                        grid[r, c] = val
                        if self._fill(grid, solver, size):
                            return True
                        grid[r, c] = 0
                    return False
        return True
