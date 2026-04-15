"""CLI interface with interactive menus and flag-based bypass."""

from __future__ import annotations

import sys
from pathlib import Path

import click
import questionary
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from sudoku.config import clue_count_range
from sudoku.generator import BacktrackingStrategy, GenerationStrategy, ShuffleStrategy
from sudoku.models import BoardSize, Difficulty, Puzzle
from sudoku.pdf_builder import PageSize, PdfBuilder
from sudoku.puzzle_maker import PuzzleMaker
from sudoku.repository import PuzzleRepository

console = Console()

# Map size -> strategy; shuffle is fast for all practical sizes
_STRATEGY_MAP: dict[str, type[GenerationStrategy]] = {
    "shuffle": ShuffleStrategy,
    "backtracking": BacktrackingStrategy,
}


def _generate_puzzles(
    count: int,
    size: BoardSize,
    difficulty: Difficulty,
    repo: PuzzleRepository,
    strategy: GenerationStrategy,
    max_retries_per_puzzle: int = 100,
) -> list[Puzzle]:
    """Generate `count` unique puzzles, skipping duplicates via the repository."""
    maker = PuzzleMaker(size)
    puzzles: list[Puzzle] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Generating {count} puzzles...", total=count
        )

        attempts = 0
        while len(puzzles) < count:
            solution = strategy.generate(size)
            puzzle = maker.make_puzzle(solution, difficulty)

            if not repo.exists(puzzle.sha256):
                repo.save(puzzle)
                puzzles.append(puzzle)
                progress.advance(task)
                attempts = 0
            else:
                attempts += 1
                if attempts >= max_retries_per_puzzle:
                    console.print(
                        f"[yellow]Warning: Could not find more unique puzzles "
                        f"after {max_retries_per_puzzle} retries. "
                        f"Generated {len(puzzles)}/{count}.[/yellow]"
                    )
                    break

    return puzzles


def _interactive_generate() -> dict:
    """Run the interactive menu and return parameters."""
    console.print("\n[bold cyan]═══ Sudoku Puzzle Generator ═══[/bold cyan]\n")

    size_str = questionary.select(
        "Board size:",
        choices=[
            questionary.Choice("4×4  (Mini)", value="4"),
            questionary.Choice("9×9  (Classic)", value="9"),
            questionary.Choice("16×16 (Large)", value="16"),
            questionary.Choice("25×25 (Huge)", value="25"),
            questionary.Choice("Custom...", value="custom"),
        ],
    ).ask()

    if size_str is None:
        sys.exit(0)

    if size_str == "custom":
        size_str = questionary.text(
            "Enter board size (must be a perfect square, e.g. 4, 9, 16, 25):",
            validate=lambda x: x.isdigit() and int(x) >= 4,
        ).ask()
        if size_str is None:
            sys.exit(0)

    size = int(size_str)

    diff_str = questionary.select(
        "Difficulty:",
        choices=[
            questionary.Choice("Easy", value="easy"),
            questionary.Choice("Medium", value="medium"),
            questionary.Choice("Hard", value="hard"),
            questionary.Choice("Expert", value="expert"),
        ],
    ).ask()

    if diff_str is None:
        sys.exit(0)

    count_str = questionary.text(
        "Number of puzzles to generate:",
        default="10",
        validate=lambda x: x.isdigit() and int(x) >= 1,
    ).ask()

    if count_str is None:
        sys.exit(0)

    per_page_str = questionary.select(
        "Puzzles per PDF page:",
        choices=[
            questionary.Choice("1 per page", value="1"),
            questionary.Choice("2 per page", value="2"),
            questionary.Choice("4 per page", value="4"),
        ],
    ).ask()

    if per_page_str is None:
        sys.exit(0)

    include_solutions = questionary.confirm(
        "Include solution pages?", default=True
    ).ask()

    if include_solutions is None:
        sys.exit(0)

    output = questionary.text(
        "Output PDF filename:",
        default=f"sudoku_{size}x{size}_{diff_str}_{count_str}.pdf",
    ).ask()

    if output is None:
        sys.exit(0)

    return {
        "size": size,
        "difficulty": diff_str,
        "count": int(count_str),
        "per_page": int(per_page_str),
        "solutions": include_solutions,
        "output": output,
    }


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:  # type: ignore[arg-type]
    """Sudoku Puzzle Generator — generate unique puzzles and export as PDF."""
    if ctx.invoked_subcommand is None:
        # No subcommand → show interactive main menu
        _main_menu()


def _main_menu() -> None:
    """Top-level interactive menu."""
    while True:
        console.print("\n[bold cyan]═══ Sudoku Puzzle Generator ═══[/bold cyan]\n")

        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("Generate puzzles", value="generate"),
                questionary.Choice("View statistics", value="stats"),
                questionary.Choice("Exit", value="exit"),
            ],
        ).ask()

        if action is None or action == "exit":
            console.print("[dim]Goodbye![/dim]")
            break
        elif action == "generate":
            params = _interactive_generate()
            _run_generate(**params)
        elif action == "stats":
            _run_stats()


def _run_generate(
    size: int,
    difficulty: str,
    count: int,
    per_page: int,
    solutions: bool,
    output: str,
    strategy_name: str = "shuffle",
    page_size: str = "a4",
    db_path: str | None = None,
) -> None:
    """Core generation logic shared by interactive and flag modes."""
    try:
        board_size = BoardSize(size)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    try:
        diff = Difficulty(difficulty)
    except ValueError:
        console.print(f"[red]Error: Invalid difficulty '{difficulty}'[/red]")
        return

    strategy_cls = _STRATEGY_MAP.get(strategy_name)
    if strategy_cls is None:
        console.print(f"[red]Error: Unknown strategy '{strategy_name}'[/red]")
        return

    strategy = strategy_cls()
    db = Path(db_path) if db_path else None

    with PuzzleRepository(db) as repo:
        # Show config summary
        min_c, max_c = clue_count_range(size, diff)
        console.print(f"\n[bold]Configuration:[/bold]")
        console.print(f"  Board size:  {size}×{size}")
        console.print(f"  Difficulty:  {diff.value.capitalize()}")
        console.print(f"  Clue range:  {min_c}–{max_c}")
        console.print(f"  Count:       {count}")
        console.print(f"  Strategy:    {strategy_name}")
        console.print(f"  Output:      {output}\n")

        existing = repo.count(size=size)
        console.print(f"[dim]Previously generated {size}×{size} puzzles: {existing}[/dim]\n")

        puzzles = _generate_puzzles(count, board_size, diff, repo, strategy)

        if not puzzles:
            console.print("[red]No puzzles were generated.[/red]")
            return

        console.print(f"\n[green]Generated {len(puzzles)} unique puzzle(s).[/green]")

        # Build PDF
        console.print(f"[dim]Building PDF...[/dim]")
        pdf = (
            PdfBuilder(
                output_path=Path(output),
                puzzles_per_page=per_page,
                include_solutions=solutions,
                page_size=PageSize(page_size),
            )
            .add_puzzles(puzzles)
            .build()
        )
        console.print(f"[bold green]PDF saved to {pdf}[/bold green]")

        total = repo.count(size=size)
        console.print(f"[dim]Total {size}×{size} puzzles in database: {total}[/dim]")


def _run_stats(db_path: str | None = None) -> None:
    """Show statistics about stored puzzles."""
    db = Path(db_path) if db_path else None

    with PuzzleRepository(db) as repo:
        console.print("\n[bold cyan]═══ Puzzle Statistics ═══[/bold cyan]\n")

        total = repo.count()
        if total == 0:
            console.print("[dim]No puzzles generated yet.[/dim]")
            return

        table = Table(title=f"Total Puzzles: {total}")
        table.add_column("Size", style="cyan")
        table.add_column("Easy", justify="right")
        table.add_column("Medium", justify="right")
        table.add_column("Hard", justify="right")
        table.add_column("Expert", justify="right")
        table.add_column("Total", justify="right", style="bold")

        for size in [4, 9, 16, 25]:
            row_total = repo.count(size=size)
            if row_total == 0:
                continue
            row = [f"{size}×{size}"]
            for diff in Difficulty:
                row.append(str(repo.count(size=size, difficulty=diff.value)))
            row.append(str(row_total))
            table.add_row(*row)

        console.print(table)


@main.command()  # type: ignore[attr-defined]
@click.option("--size", "-s", type=int, help="Board size (4, 9, 16, 25, ...)")
@click.option(
    "--difficulty", "-d",
    type=click.Choice(["easy", "medium", "hard", "expert"]),
    help="Puzzle difficulty",
)
@click.option("--count", "-n", type=int, help="Number of puzzles to generate")
@click.option(
    "--per-page", "-p", type=click.Choice(["1", "2", "4"]), help="Puzzles per PDF page"
)
@click.option("--solutions/--no-solutions", default=True, help="Include solution pages")
@click.option("--output", "-o", type=str, help="Output PDF filename")
@click.option(
    "--strategy",
    type=click.Choice(["shuffle", "backtracking"]),
    default="shuffle",
    help="Generation strategy",
)
@click.option(
    "--page-size",
    type=click.Choice(["a4", "letter"]),
    default="a4",
    help="PDF page size",
)
@click.option("--db", type=str, default=None, help="Custom database path")
def generate(
    size: int | None,
    difficulty: str | None,
    count: int | None,
    per_page: str | None,
    solutions: bool,
    output: str | None,
    strategy: str,
    page_size: str,
    db: str | None,
) -> None:
    """Generate Sudoku puzzles and export as PDF."""
    # If any required param is missing, fall into interactive mode for those
    if size is None or difficulty is None or count is None:
        params = _interactive_generate()
        # Override with any flags that were provided
        if size is not None:
            params["size"] = size
        if difficulty is not None:
            params["difficulty"] = difficulty
        if count is not None:
            params["count"] = count
        if per_page is not None:
            params["per_page"] = int(per_page)
        if output is not None:
            params["output"] = output
        params["strategy_name"] = strategy
        params["page_size"] = page_size
        params["db_path"] = db
        _run_generate(**params)
    else:
        _run_generate(
            size=size,
            difficulty=difficulty,
            count=count,
            per_page=int(per_page) if per_page else 2,
            solutions=solutions,
            output=output or f"sudoku_{size}x{size}_{difficulty}_{count}.pdf",
            strategy_name=strategy,
            page_size=page_size,
            db_path=db,
        )


@main.command()  # type: ignore[attr-defined]
@click.option("--db", type=str, default=None, help="Custom database path")
def stats(db: str | None) -> None:
    """Show statistics about generated puzzles."""
    _run_stats(db_path=db)


if __name__ == "__main__":
    main()
