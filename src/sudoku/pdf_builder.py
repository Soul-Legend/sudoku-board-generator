"""PDF builder for Sudoku puzzles using the Builder pattern."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import numpy as np
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from sudoku.models import Puzzle


class PageSize(Enum):
    A4 = "a4"
    LETTER = "letter"


_PAGE_SIZES = {
    PageSize.A4: A4,
    PageSize.LETTER: letter,
}


class PdfBuilder:
    """Builds a PDF document containing Sudoku puzzles.

    Supports configurable layout (1, 2, or 4 puzzles per page),
    optional solution pages, and any board size.
    """

    def __init__(
        self,
        output_path: Path,
        puzzles_per_page: int = 2,
        include_solutions: bool = True,
        page_size: PageSize = PageSize.A4,
    ) -> None:
        if puzzles_per_page not in (1, 2, 4):
            raise ValueError("puzzles_per_page must be 1, 2, or 4")

        self._output_path = output_path
        self._per_page = puzzles_per_page
        self._include_solutions = include_solutions
        self._page_dims = _PAGE_SIZES[page_size]
        self._puzzles: list[Puzzle] = []

    def add_puzzle(self, puzzle: Puzzle) -> PdfBuilder:
        """Add a puzzle to the PDF."""
        self._puzzles.append(puzzle)
        return self

    def add_puzzles(self, puzzles: list[Puzzle]) -> PdfBuilder:
        """Add multiple puzzles to the PDF."""
        self._puzzles.extend(puzzles)
        return self

    def build(self) -> Path:
        """Render the PDF and return the output path."""
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        c = Canvas(str(self._output_path), pagesize=self._page_dims)
        page_w, page_h = self._page_dims

        # Render puzzle pages
        self._render_pages(c, page_w, page_h, is_solution=False)

        # Render solution pages
        if self._include_solutions:
            self._render_pages(c, page_w, page_h, is_solution=True)

        c.save()
        return self._output_path

    def _render_pages(
        self, c: Canvas, page_w: float, page_h: float, is_solution: bool
    ) -> None:
        """Render all puzzles across pages."""
        margin = 15 * mm
        header_height = 12 * mm
        spacing = 8 * mm

        usable_w = page_w - 2 * margin
        usable_h = page_h - 2 * margin

        if self._per_page == 1:
            cols, rows = 1, 1
        elif self._per_page == 2:
            cols, rows = 1, 2
        else:
            cols, rows = 2, 2

        cell_w = (usable_w - (cols - 1) * spacing) / cols
        cell_h = (usable_h - (rows - 1) * spacing) / rows

        grid_max = min(cell_w, cell_h - header_height)

        for page_start in range(0, len(self._puzzles), self._per_page):
            batch = self._puzzles[page_start : page_start + self._per_page]

            # Page title
            c.setFont("Helvetica-Bold", 10)
            label = "Solutions" if is_solution else "Sudoku Puzzles"
            c.drawCentredString(page_w / 2, page_h - 10 * mm, label)

            for idx, puzzle in enumerate(batch):
                col = idx % cols
                row = idx // cols

                x = margin + col * (cell_w + spacing)
                y = page_h - margin - header_height - row * (cell_h + spacing)

                board = puzzle.solution_board if is_solution else puzzle.puzzle_board
                n = board.size.n
                cell_size = grid_max / n

                # Header
                c.setFont("Helvetica-Bold", 9)
                puzzle_num = page_start + idx + 1
                diff_label = puzzle.difficulty.value.capitalize()
                header = f"#{puzzle_num} — {n}x{n} {diff_label}"
                if is_solution:
                    header = f"Solution #{puzzle_num}"
                c.drawString(x, y + 2 * mm, header)

                grid_y_top = y - 2 * mm
                self._draw_grid(c, board.grid, n, board.size.box_rows, board.size.box_cols,
                                x, grid_y_top, cell_size, is_solution, puzzle)

            c.showPage()

    def _draw_grid(
        self,
        c: Canvas,
        grid: np.ndarray,
        n: int,
        box_r: int,
        box_c: int,
        x0: float,
        y0: float,
        cell_size: float,
        is_solution: bool,
        puzzle: Puzzle,
    ) -> None:
        """Draw a single Sudoku grid."""
        total = cell_size * n

        # Background
        c.setFillColorRGB(1, 1, 1)
        c.rect(x0, y0 - total, total, total, fill=1)

        # Cell values
        font_size = max(6, min(16, cell_size * 0.55))
        for r in range(n):
            for col_idx in range(n):
                val = grid[r, col_idx]
                if val == 0:
                    continue

                cx = x0 + col_idx * cell_size + cell_size / 2
                cy = y0 - r * cell_size - cell_size / 2 - font_size * 0.35

                # Given clues in bold black, solved cells in gray (on solution pages)
                if is_solution and puzzle.puzzle_board.grid[r, col_idx] == 0:
                    c.setFillColorRGB(0.4, 0.4, 0.4)
                    c.setFont("Helvetica", font_size)
                else:
                    c.setFillColorRGB(0, 0, 0)
                    c.setFont("Helvetica-Bold", font_size)

                # For sizes > 9, use hex-like labels (A=10, B=11, etc.)
                label = self._value_label(val)
                c.drawCentredString(cx, cy, label)

        # Grid lines
        c.setStrokeColorRGB(0, 0, 0)

        # Thin cell lines
        c.setLineWidth(0.5)
        for i in range(n + 1):
            # Horizontal
            c.line(x0, y0 - i * cell_size, x0 + total, y0 - i * cell_size)
            # Vertical
            c.line(x0 + i * cell_size, y0, x0 + i * cell_size, y0 - total)

        # Thick box lines
        c.setLineWidth(2.0)
        for i in range(box_r + 1):
            y = y0 - i * box_r * cell_size
            c.line(x0, y, x0 + total, y)
        for j in range(box_c + 1):
            x = x0 + j * box_c * cell_size
            c.line(x, y0, x, y0 - total)

        # Outer border
        c.setLineWidth(2.5)
        c.rect(x0, y0 - total, total, total)

    @staticmethod
    def _value_label(val: int) -> str:
        """Convert a numeric value to its display label."""
        if val <= 9:
            return str(val)
        # For 16x16+: A=10, B=11, ..., G=16, etc.
        return chr(ord("A") + val - 10)
