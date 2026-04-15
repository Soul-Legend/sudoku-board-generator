"""Tests for the puzzle repository."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from sudoku.models import Board, BoardSize, Difficulty, Puzzle
from sudoku.repository import PuzzleRepository


def _make_puzzle(val: int = 1) -> Puzzle:
    """Create a simple test puzzle."""
    size = BoardSize(4)
    solution = np.array([
        [1, 2, 3, 4],
        [3, 4, 1, 2],
        [2, 1, 4, 3],
        [4, 3, 2, 1],
    ], dtype=np.int32)
    puzzle_grid = solution.copy()
    puzzle_grid[0, 0] = 0
    # Make each puzzle unique by varying cell value
    puzzle_grid[0, 1] = val if val <= 4 else val % 4 + 1

    return Puzzle(
        puzzle_board=Board(grid=puzzle_grid, size=size),
        solution_board=Board(grid=solution, size=size),
        difficulty=Difficulty.EASY,
    )


class TestPuzzleRepository:
    def test_save_and_exists(self, tmp_path):
        repo = PuzzleRepository(tmp_path / "test.db")
        puzzle = _make_puzzle()

        assert not repo.exists(puzzle.sha256)
        repo.save(puzzle)
        assert repo.exists(puzzle.sha256)
        repo.close()

    def test_duplicate_raises(self, tmp_path):
        repo = PuzzleRepository(tmp_path / "test.db")
        puzzle = _make_puzzle()

        repo.save(puzzle)
        with pytest.raises(ValueError, match="already exists"):
            repo.save(puzzle)
        repo.close()

    def test_count(self, tmp_path):
        repo = PuzzleRepository(tmp_path / "test.db")
        assert repo.count() == 0

        repo.save(_make_puzzle(1))
        repo.save(_make_puzzle(2))
        assert repo.count() == 2
        assert repo.count(size=4) == 2
        assert repo.count(size=9) == 0
        repo.close()

    def test_save_batch(self, tmp_path):
        repo = PuzzleRepository(tmp_path / "test.db")
        puzzles = [_make_puzzle(i) for i in range(1, 5)]
        records = repo.save_batch(puzzles)

        assert len(records) == 4
        assert repo.count() == 4
        repo.close()

    def test_save_batch_skips_duplicates(self, tmp_path):
        repo = PuzzleRepository(tmp_path / "test.db")
        repo.save(_make_puzzle(1))

        # Batch includes the duplicate
        puzzles = [_make_puzzle(1), _make_puzzle(2)]
        records = repo.save_batch(puzzles)

        assert len(records) == 1  # Only 1 new puzzle saved
        assert repo.count() == 2
        repo.close()

    def test_get_all(self, tmp_path):
        repo = PuzzleRepository(tmp_path / "test.db")
        repo.save(_make_puzzle(1))
        repo.save(_make_puzzle(2))

        all_records = repo.get_all()
        assert len(all_records) == 2

        by_size = repo.get_all(size=4)
        assert len(by_size) == 2

        by_wrong_size = repo.get_all(size=9)
        assert len(by_wrong_size) == 0
        repo.close()

    def test_context_manager(self, tmp_path):
        with PuzzleRepository(tmp_path / "test.db") as repo:
            repo.save(_make_puzzle())
            assert repo.count() == 1

    def test_persistence_across_instances(self, tmp_path):
        db_path = tmp_path / "test.db"

        with PuzzleRepository(db_path) as repo:
            repo.save(_make_puzzle(1))

        with PuzzleRepository(db_path) as repo:
            assert repo.count() == 1
            assert repo.exists(_make_puzzle(1).sha256)
