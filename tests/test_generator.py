"""Tests for board generation strategies."""

import pytest

from sudoku.generator import BacktrackingStrategy, ShuffleStrategy
from sudoku.models import BoardSize


class TestShuffleStrategy:
    def test_generates_valid_complete_4x4(self):
        strategy = ShuffleStrategy()
        board = strategy.generate(BoardSize(4))
        assert board.is_complete()
        assert board.is_valid()

    def test_generates_valid_complete_9x9(self):
        strategy = ShuffleStrategy()
        board = strategy.generate(BoardSize(9))
        assert board.is_complete()
        assert board.is_valid()

    def test_generates_different_boards(self):
        strategy = ShuffleStrategy()
        size = BoardSize(9)
        boards = [strategy.generate(size) for _ in range(10)]
        hashes = {b.sha256 for b in boards}
        # Very unlikely to get duplicates in 10 random boards
        assert len(hashes) == 10

    def test_generates_valid_16x16(self):
        strategy = ShuffleStrategy()
        board = strategy.generate(BoardSize(16))
        assert board.is_complete()
        assert board.is_valid()


class TestBacktrackingStrategy:
    def test_generates_valid_complete_4x4(self):
        strategy = BacktrackingStrategy()
        board = strategy.generate(BoardSize(4))
        assert board.is_complete()
        assert board.is_valid()

    def test_generates_valid_complete_9x9(self):
        strategy = BacktrackingStrategy()
        board = strategy.generate(BoardSize(9))
        assert board.is_complete()
        assert board.is_valid()
