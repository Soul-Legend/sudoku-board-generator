"""Tests for PDF builder."""

from pathlib import Path

import numpy as np

from sudoku.models import Board, BoardSize, Difficulty, Puzzle
from sudoku.pdf_builder import PdfBuilder, PageSize


def _make_puzzle_9x9() -> Puzzle:
    """Create a simple 9x9 puzzle for testing."""
    size = BoardSize(9)
    # Known valid 9x9 solution
    solution = np.array([
        [5, 3, 4, 6, 7, 8, 9, 1, 2],
        [6, 7, 2, 1, 9, 5, 3, 4, 8],
        [1, 9, 8, 3, 4, 2, 5, 6, 7],
        [8, 5, 9, 7, 6, 1, 4, 2, 3],
        [4, 2, 6, 8, 5, 3, 7, 9, 1],
        [7, 1, 3, 9, 2, 4, 8, 5, 6],
        [9, 6, 1, 5, 3, 7, 2, 8, 4],
        [2, 8, 7, 4, 1, 9, 6, 3, 5],
        [3, 4, 5, 2, 8, 6, 1, 7, 9],
    ], dtype=np.int32)

    puzzle_grid = solution.copy()
    puzzle_grid[0, 2] = 0
    puzzle_grid[0, 3] = 0
    puzzle_grid[1, 1] = 0
    puzzle_grid[1, 2] = 0

    return Puzzle(
        puzzle_board=Board(grid=puzzle_grid, size=size),
        solution_board=Board(grid=solution, size=size),
        difficulty=Difficulty.MEDIUM,
    )


class TestPdfBuilder:
    def test_creates_pdf_file(self, tmp_path):
        output = tmp_path / "test.pdf"
        puzzle = _make_puzzle_9x9()

        path = PdfBuilder(output, puzzles_per_page=1).add_puzzle(puzzle).build()

        assert path.exists()
        assert path.stat().st_size > 0

    def test_multiple_puzzles_per_page(self, tmp_path):
        output = tmp_path / "test_2pp.pdf"
        puzzles = [_make_puzzle_9x9() for _ in range(4)]

        path = (
            PdfBuilder(output, puzzles_per_page=2, include_solutions=True)
            .add_puzzles(puzzles)
            .build()
        )

        assert path.exists()
        assert path.stat().st_size > 0

    def test_four_per_page(self, tmp_path):
        output = tmp_path / "test_4pp.pdf"
        puzzles = [_make_puzzle_9x9() for _ in range(8)]

        path = (
            PdfBuilder(output, puzzles_per_page=4, include_solutions=False)
            .add_puzzles(puzzles)
            .build()
        )

        assert path.exists()

    def test_invalid_per_page_raises(self):
        from pathlib import Path
        import pytest
        with pytest.raises(ValueError, match="1, 2, or 4"):
            PdfBuilder(Path("x.pdf"), puzzles_per_page=3)

    def test_letter_page_size(self, tmp_path):
        output = tmp_path / "test_letter.pdf"
        puzzle = _make_puzzle_9x9()

        path = (
            PdfBuilder(output, page_size=PageSize.LETTER)
            .add_puzzle(puzzle)
            .build()
        )

        assert path.exists()
