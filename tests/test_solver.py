"""Tests for the Sudoku solver."""

import numpy as np
import pytest

from sudoku.models import Board, BoardSize
from sudoku.solver import Solver


class TestSolver:
    def test_solve_4x4(self):
        size = BoardSize(4)
        grid = np.array([
            [0, 2, 0, 4],
            [3, 0, 1, 0],
            [0, 1, 0, 3],
            [4, 0, 2, 0],
        ], dtype=np.int32)
        board = Board(grid=grid, size=size)
        solver = Solver(size)

        solved = solver.solve(board)
        assert solved is not None
        assert solved.is_complete()
        assert solved.is_valid()

    def test_solve_preserves_given_clues(self):
        size = BoardSize(4)
        grid = np.array([
            [0, 2, 0, 4],
            [3, 0, 1, 0],
            [0, 1, 0, 3],
            [4, 0, 2, 0],
        ], dtype=np.int32)
        board = Board(grid=grid, size=size)
        solver = Solver(size)

        solved = solver.solve(board)
        assert solved is not None
        for r in range(4):
            for c in range(4):
                if grid[r, c] != 0:
                    assert solved.grid[r, c] == grid[r, c]

    def test_unsolvable_returns_none(self):
        size = BoardSize(4)
        # Row has two 1s — impossible
        grid = np.array([
            [1, 1, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ], dtype=np.int32)
        board = Board(grid=grid, size=size)
        solver = Solver(size)

        assert solver.solve(board) is None

    def test_unique_solution(self):
        size = BoardSize(4)
        grid = np.array([
            [1, 2, 3, 4],
            [3, 4, 1, 2],
            [0, 0, 4, 3],
            [4, 3, 2, 1],
        ], dtype=np.int32)
        board = Board(grid=grid, size=size)
        solver = Solver(size)

        assert solver.has_unique_solution(board)

    def test_multiple_solutions(self):
        size = BoardSize(4)
        # Very few clues — likely multiple solutions
        grid = np.array([
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ], dtype=np.int32)
        board = Board(grid=grid, size=size)
        solver = Solver(size)

        assert solver.count_solutions(board, limit=2) == 2
        assert not solver.has_unique_solution(board)

    def test_solve_9x9(self):
        size = BoardSize(9)
        # A known valid 9x9 puzzle
        grid = np.array([
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ], dtype=np.int32)
        board = Board(grid=grid, size=size)
        solver = Solver(size)

        solved = solver.solve(board)
        assert solved is not None
        assert solved.is_complete()
        assert solved.is_valid()
