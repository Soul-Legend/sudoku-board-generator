"""Tests for Sudoku models."""

import numpy as np
import pytest

from sudoku.models import Board, BoardSize, Difficulty, Puzzle


class TestBoardSize:
    def test_valid_sizes(self):
        for n in (4, 9, 16, 25):
            bs = BoardSize(n)
            assert bs.n == n

    def test_invalid_size_not_square(self):
        with pytest.raises(ValueError, match="perfect square"):
            BoardSize(6)

    def test_invalid_size_too_small(self):
        with pytest.raises(ValueError, match="perfect square"):
            BoardSize(1)

    def test_box_dimensions(self):
        bs = BoardSize(9)
        assert bs.box_rows == 3
        assert bs.box_cols == 3

        bs4 = BoardSize(4)
        assert bs4.box_rows == 2
        assert bs4.box_cols == 2

    def test_total_cells(self):
        assert BoardSize(9).total_cells == 81
        assert BoardSize(4).total_cells == 16


class TestBoard:
    def test_canonical_string_roundtrip(self):
        size = BoardSize(4)
        grid = np.array([
            [1, 2, 3, 4],
            [3, 4, 1, 2],
            [2, 1, 4, 3],
            [4, 3, 2, 1],
        ], dtype=np.int32)
        board = Board(grid=grid, size=size)

        s = board.canonical_string
        restored = Board.from_string(s, size)
        assert board == restored

    def test_sha256_deterministic(self):
        size = BoardSize(4)
        grid = np.ones((4, 4), dtype=np.int32)
        b1 = Board(grid=grid.copy(), size=size)
        b2 = Board(grid=grid.copy(), size=size)
        assert b1.sha256 == b2.sha256

    def test_sha256_different_for_different_boards(self):
        size = BoardSize(4)
        g1 = np.ones((4, 4), dtype=np.int32)
        g2 = np.ones((4, 4), dtype=np.int32) * 2
        assert Board(grid=g1, size=size).sha256 != Board(grid=g2, size=size).sha256

    def test_is_complete(self):
        size = BoardSize(4)
        full = np.ones((4, 4), dtype=np.int32)
        assert Board(grid=full, size=size).is_complete()

        partial = full.copy()
        partial[0, 0] = 0
        assert not Board(grid=partial, size=size).is_complete()

    def test_is_valid_correct_board(self):
        size = BoardSize(4)
        grid = np.array([
            [1, 2, 3, 4],
            [3, 4, 1, 2],
            [2, 1, 4, 3],
            [4, 3, 2, 1],
        ], dtype=np.int32)
        assert Board(grid=grid, size=size).is_valid()

    def test_is_valid_duplicate_in_row(self):
        size = BoardSize(4)
        grid = np.array([
            [1, 1, 3, 4],
            [3, 4, 1, 2],
            [2, 1, 4, 3],
            [4, 3, 2, 1],
        ], dtype=np.int32)
        assert not Board(grid=grid, size=size).is_valid()

    def test_is_valid_with_zeros(self):
        size = BoardSize(4)
        grid = np.array([
            [1, 0, 3, 4],
            [3, 4, 1, 2],
            [2, 1, 4, 3],
            [4, 3, 2, 0],
        ], dtype=np.int32)
        assert Board(grid=grid, size=size).is_valid()

    def test_wrong_shape_raises(self):
        with pytest.raises(ValueError, match="shape"):
            Board(grid=np.zeros((3, 3), dtype=np.int32), size=BoardSize(4))


class TestPuzzle:
    def test_clue_and_blank_count(self):
        size = BoardSize(4)
        solution = np.array([
            [1, 2, 3, 4],
            [3, 4, 1, 2],
            [2, 1, 4, 3],
            [4, 3, 2, 1],
        ], dtype=np.int32)
        puzzle = solution.copy()
        puzzle[0, 0] = 0
        puzzle[1, 1] = 0

        p = Puzzle(
            puzzle_board=Board(grid=puzzle, size=size),
            solution_board=Board(grid=solution, size=size),
            difficulty=Difficulty.EASY,
        )
        assert p.clue_count == 14
        assert p.blank_count == 2

    def test_mismatched_sizes_raises(self):
        with pytest.raises(ValueError, match="same size"):
            Puzzle(
                puzzle_board=Board(grid=np.zeros((4, 4), dtype=np.int32), size=BoardSize(4)),
                solution_board=Board(grid=np.zeros((9, 9), dtype=np.int32), size=BoardSize(9)),
                difficulty=Difficulty.EASY,
            )
