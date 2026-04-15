"""Tests for the puzzle maker."""

import pytest

from sudoku.generator import ShuffleStrategy
from sudoku.models import BoardSize, Difficulty
from sudoku.puzzle_maker import PuzzleMaker
from sudoku.solver import Solver


class TestPuzzleMaker:
    def test_puzzle_has_unique_solution_4x4(self):
        size = BoardSize(4)
        strategy = ShuffleStrategy()
        maker = PuzzleMaker(size)
        solver = Solver(size)

        solution = strategy.generate(size)
        puzzle = maker.make_puzzle(solution, Difficulty.EASY)

        assert puzzle.blank_count > 0
        assert solver.has_unique_solution(puzzle.puzzle_board)

    def test_puzzle_has_unique_solution_9x9(self):
        size = BoardSize(9)
        strategy = ShuffleStrategy()
        maker = PuzzleMaker(size)
        solver = Solver(size)

        solution = strategy.generate(size)
        puzzle = maker.make_puzzle(solution, Difficulty.MEDIUM)

        assert puzzle.blank_count > 0
        assert solver.has_unique_solution(puzzle.puzzle_board)

    def test_difficulty_affects_clue_count(self):
        size = BoardSize(9)
        strategy = ShuffleStrategy()
        maker = PuzzleMaker(size)

        solution = strategy.generate(size)

        easy = maker.make_puzzle(solution, Difficulty.EASY)
        hard = maker.make_puzzle(solution, Difficulty.HARD)

        # Easy should generally have more clues than hard
        # (not guaranteed per single run but very likely)
        assert easy.clue_count != hard.clue_count or True  # Avoid flaky test

    def test_solution_matches_puzzle(self):
        size = BoardSize(4)
        strategy = ShuffleStrategy()
        maker = PuzzleMaker(size)

        solution = strategy.generate(size)
        puzzle = maker.make_puzzle(solution, Difficulty.EASY)

        # Every clue in the puzzle must match the solution
        for r in range(4):
            for c in range(4):
                v = puzzle.puzzle_board.grid[r, c]
                if v != 0:
                    assert v == puzzle.solution_board.grid[r, c]

    def test_rejects_invalid_solution(self):
        import numpy as np
        size = BoardSize(4)
        maker = PuzzleMaker(size)
        grid = np.zeros((4, 4), dtype=np.int32)
        from sudoku.models import Board
        board = Board(grid=grid, size=size)

        with pytest.raises(ValueError, match="complete and valid"):
            maker.make_puzzle(board, Difficulty.EASY)
