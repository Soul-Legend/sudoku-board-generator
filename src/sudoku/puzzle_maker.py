"""Puzzle maker: removes clues from a complete board to create a puzzle."""

from __future__ import annotations

import random

import numpy as np

from sudoku.config import clue_count_range
from sudoku.models import Board, BoardSize, Difficulty, Puzzle
from sudoku.solver import Solver


class PuzzleMaker:
    """Creates puzzles by removing cells from a solved board.

    Ensures the resulting puzzle has a unique solution.
    """

    def __init__(self, size: BoardSize) -> None:
        self._size = size
        self._solver = Solver(size)

    def make_puzzle(self, solution: Board, difficulty: Difficulty) -> Puzzle:
        """Remove cells from a solved board to create a puzzle of given difficulty.

        The puzzle is guaranteed to have a unique solution.
        """
        if not solution.is_complete() or not solution.is_valid():
            raise ValueError("Solution board must be complete and valid")

        n = self._size.n
        min_clues, max_clues = clue_count_range(n, difficulty)
        target_clues = random.randint(min_clues, max_clues)

        grid = solution.grid.copy()
        cells = [(r, c) for r in range(n) for c in range(n)]
        random.shuffle(cells)

        removed = 0
        target_removals = n * n - target_clues

        for r, c in cells:
            if removed >= target_removals:
                break

            val = grid[r, c]
            grid[r, c] = 0

            test_board = Board(grid=grid.copy(), size=self._size)
            if self._solver.has_unique_solution(test_board):
                removed += 1
            else:
                # Removing this cell creates ambiguity — put it back
                grid[r, c] = val

        puzzle_board = Board(grid=grid, size=self._size)
        return Puzzle(
            puzzle_board=puzzle_board,
            solution_board=solution,
            difficulty=difficulty,
        )
