"""Configuration constants for difficulty levels and board sizes."""

from __future__ import annotations

from sudoku.models import Difficulty


# Clue ratios per difficulty: (min_ratio, max_ratio) of total cells to keep as clues.
# These are scaled proportionally for any board size.
DIFFICULTY_CLUE_RATIOS: dict[Difficulty, tuple[float, float]] = {
    Difficulty.EASY: (0.44, 0.56),    # ~44-56% of cells given
    Difficulty.MEDIUM: (0.33, 0.43),  # ~33-43% of cells given
    Difficulty.HARD: (0.27, 0.32),    # ~27-32% of cells given
    Difficulty.EXPERT: (0.21, 0.26),  # ~21-26% of cells given
}


def clue_count_range(n: int, difficulty: Difficulty) -> tuple[int, int]:
    """Return (min_clues, max_clues) for a given board size and difficulty."""
    total = n * n
    lo, hi = DIFFICULTY_CLUE_RATIOS[difficulty]
    return max(1, int(total * lo)), int(total * hi)
